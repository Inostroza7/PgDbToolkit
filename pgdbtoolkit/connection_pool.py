# connection_pool.py

"""
Implementación de pools de conexiones para PostgreSQL.
Este módulo proporciona clases para gestionar pools de conexiones tanto
sincrónicos como asincrónicos para bases de datos PostgreSQL.
"""

import logging
from typing import Dict, Any, Optional, Callable, List, TypeVar, Generic, Union, Tuple
import time
import asyncio
import psycopg
from psycopg_pool import ConnectionPool as PsycopgConnectionPool
from psycopg_pool import AsyncConnectionPool as PsycopgAsyncConnectionPool
from contextlib import contextmanager, asynccontextmanager

from .config import get_pool_config
from .exceptions import PoolError, ConnectionError

# Configuración del logger
logger = logging.getLogger("pg_toolkit.pool")

T = TypeVar('T')

class PgConnectionPool:
    """
    Gestor de pool de conexiones sincrónicas a PostgreSQL.
    Proporciona una interfaz simplificada para el manejo de pools de conexiones.
    """
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        min_size: int = 5,
        max_size: int = 20,
        timeout: float = 30.0,
        max_lifetime: int = 3600,
        max_idle: int = 600,
        check_connection: bool = True,
        name: Optional[str] = None
    ):
        """
        Inicializa un pool de conexiones sincrónicas.
        
        Args:
            config (Dict[str, Any], opcional): Configuración de la conexión.
            min_size (int): Tamaño mínimo del pool. Por defecto 5 conexiones.
            max_size (int): Tamaño máximo del pool. Por defecto 20 conexiones.
            timeout (float): Tiempo máximo de espera para obtener una conexión.
            max_lifetime (int): Tiempo máximo de vida de una conexión en segundos.
            max_idle (int): Tiempo máximo que una conexión puede estar inactiva.
            check_connection (bool): Si se debe verificar la conexión antes de usarla.
            name (str, opcional): Nombre del pool para identificación en logs.
        """
        # Obtener la configuración
        self.pool_config = get_pool_config(config)
        self.min_size = min_size if min_size is not None else self.pool_config.get('min_size', 5)
        self.max_size = max_size if max_size is not None else self.pool_config.get('max_size', 20)
        self.timeout = timeout if timeout is not None else self.pool_config.get('timeout', 30.0)
        self.max_lifetime = max_lifetime if max_lifetime is not None else self.pool_config.get('max_lifetime', 3600)
        self.max_idle = max_idle if max_idle is not None else self.pool_config.get('max_idle', 600)
        self.check_connection = check_connection
        self.name = name or f"pool-{id(self)}"
        
        # Extraer parámetros de conexión del diccionario
        conn_params = {k: v for k, v in self.pool_config.items() 
                      if k not in ('min_size', 'max_size', 'timeout', 'max_lifetime', 'max_idle')
                      and not isinstance(v, dict)}  # Excluir valores que sean diccionarios
        
        # Crear el pool
        try:
            self.pool = PsycopgConnectionPool(
                # Convertir parámetros a una cadena de conexión
                conninfo=self._build_conninfo(conn_params),
                min_size=self.min_size,
                max_size=self.max_size,
                timeout=self.timeout,
                max_lifetime=self.max_lifetime,
                max_idle=self.max_idle,
                check=PsycopgConnectionPool.check_connection if self.check_connection else None,
                name=self.name,
                open=True
            )
            logger.info(f"Pool de conexiones '{self.name}' inicializado con min_size={self.min_size}, max_size={self.max_size}")
        except Exception as e:
            logger.error(f"Error al inicializar el pool de conexiones '{self.name}': {e}")
            raise PoolError(f"Error al inicializar el pool de conexiones: {e}")
    
    def __enter__(self):
        """Permite usar el pool como un contexto."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cierra el pool al salir del contexto."""
        self.close()
    
    @contextmanager
    def connection(self):
        """
        Obtiene una conexión del pool.
        
        Yields:
            psycopg.Connection: Una conexión de la base de datos.
        
        Raises:
            PoolError: Si no se puede obtener una conexión del pool.
        """
        conn = None
        try:
            conn = self.pool.getconn()
            # Establecer autocommit para permitir ver cambios inmediatamente entre conexiones
            conn.autocommit = True
            logger.debug(f"Conexión obtenida del pool '{self.name}'")
            yield conn
            # Ya no necesitamos hacer commit aquí si autocommit está activado
        except Exception as e:
            # Hacer rollback en caso de error si no está en autocommit
            if conn and not getattr(conn, 'autocommit', False):
                conn.rollback()
                logger.debug(f"Rollback automático realizado en la conexión del pool '{self.name}'")
            logger.error(f"Error al obtener conexión del pool '{self.name}': {e}")
            raise PoolError(f"Error al obtener conexión del pool: {e}")
        finally:
            if conn:
                self.pool.putconn(conn)
                logger.debug(f"Conexión devuelta al pool '{self.name}'")
    
    def wait(self, timeout: float = None):
        """
        Espera hasta que el pool tenga min_size conexiones disponibles.
        
        Args:
            timeout (float, opcional): Tiempo máximo de espera en segundos.
        
        Raises:
            PoolError: Si se agota el tiempo de espera.
        """
        try:
            self.pool.wait(timeout=timeout)
        except Exception as e:
            logger.error(f"Error al esperar conexiones en el pool '{self.name}': {e}")
            raise PoolError(f"Error al esperar conexiones en el pool: {e}")
    
    def close(self):
        """
        Cierra el pool de conexiones.
        """
        try:
            self.pool.close()
            logger.info(f"Pool de conexiones '{self.name}' cerrado")
        except Exception as e:
            logger.error(f"Error al cerrar el pool de conexiones '{self.name}': {e}")
    
    def stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del pool.
        
        Returns:
            Dict[str, Any]: Estadísticas del pool.
        """
        return self.pool.get_stats()
    
    def resize(self, min_size: int = None, max_size: int = None):
        """
        Cambia el tamaño del pool.
        
        Args:
            min_size (int, opcional): Nuevo tamaño mínimo del pool.
            max_size (int, opcional): Nuevo tamaño máximo del pool.
        """
        # Actualizar los valores de instancia
        if min_size is not None:
            self.min_size = min_size
        
        if max_size is not None:
            self.max_size = max_size
        
        # Recrear el pool con los nuevos tamaños
        # Guardar las conexiones actuales
        old_pool = self.pool
        
        # Extraer parámetros de conexión del diccionario
        conn_params = {k: v for k, v in self.pool_config.items() 
                      if k not in ('min_size', 'max_size', 'timeout', 'max_lifetime', 'max_idle')
                      and not isinstance(v, dict)}
        
        try:
            # Crear un nuevo pool con los nuevos tamaños
            self.pool = PsycopgConnectionPool(
                conninfo=self._build_conninfo(conn_params),
                min_size=self.min_size,
                max_size=self.max_size,
                timeout=self.timeout,
                max_lifetime=self.max_lifetime,
                max_idle=self.max_idle,
                check=PsycopgConnectionPool.check_connection if self.check_connection else None,
                name=self.name,
                open=True
            )
            # Cerrar el pool antiguo
            old_pool.close()
            logger.info(f"Pool de conexiones '{self.name}' redimensionado a min_size={self.min_size}, max_size={self.max_size}")
        except Exception as e:
            # Si hay un error, restaurar el pool antiguo
            self.pool = old_pool
            logger.error(f"Error al redimensionar el pool '{self.name}': {e}")
            raise PoolError(f"Error al redimensionar el pool: {e}")

    def _build_conninfo(self, params: Dict[str, Any]) -> str:
        """
        Construye una cadena de conexión a partir de un diccionario de parámetros.
        
        Args:
            params (Dict[str, Any]): Parámetros de conexión.
            
        Returns:
            str: Cadena de conexión.
        """
        conninfo_parts = []
        for key, value in params.items():
            if value is not None:
                # Convertir el valor a string y escapar posibles espacios o caracteres especiales
                value_str = str(value)
                if ' ' in value_str or "'" in value_str:
                    value_str = f"'{value_str.replace('\'', '\'\'')}'"
                conninfo_parts.append(f"{key}={value_str}")
        
        return " ".join(conninfo_parts)


class PgAsyncConnectionPool:
    """
    Gestor de pool de conexiones asíncronas a PostgreSQL.
    Proporciona una interfaz simplificada para el manejo de pools de conexiones asíncronas.
    """
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        min_size: int = 5,
        max_size: int = 20,
        timeout: float = 30.0,
        max_lifetime: int = 3600,
        max_idle: int = 600,
        check_connection: bool = True,
        name: Optional[str] = None
    ):
        """
        Inicializa un pool de conexiones asíncronas.
        
        Args:
            config (Dict[str, Any], opcional): Configuración de la conexión.
            min_size (int): Tamaño mínimo del pool. Por defecto 5 conexiones.
            max_size (int): Tamaño máximo del pool. Por defecto 20 conexiones.
            timeout (float): Tiempo máximo de espera para obtener una conexión.
            max_lifetime (int): Tiempo máximo de vida de una conexión en segundos.
            max_idle (int): Tiempo máximo que una conexión puede estar inactiva.
            check_connection (bool): Si se debe verificar la conexión antes de usarla.
            name (str, opcional): Nombre del pool para identificación en logs.
        """
        # Obtener la configuración
        self.pool_config = get_pool_config(config)
        self.min_size = min_size if min_size is not None else self.pool_config.get('min_size', 5)
        self.max_size = max_size if max_size is not None else self.pool_config.get('max_size', 20)
        self.timeout = timeout if timeout is not None else self.pool_config.get('timeout', 30.0)
        self.max_lifetime = max_lifetime if max_lifetime is not None else self.pool_config.get('max_lifetime', 3600)
        self.max_idle = max_idle if max_idle is not None else self.pool_config.get('max_idle', 600)
        self.check_connection = check_connection
        self.name = name or f"async-pool-{id(self)}"
        
        # Extraer parámetros de conexión del diccionario
        self.conn_params = {k: v for k, v in self.pool_config.items() 
                          if k not in ('min_size', 'max_size', 'timeout', 'max_lifetime', 'max_idle')
                          and not isinstance(v, dict)}  # Excluir valores que sean diccionarios
        
        # Crear el pool (lo abriremos en el método open)
        self.pool = None
    
    def _build_conninfo(self, params: Dict[str, Any]) -> str:
        """
        Construye una cadena de conexión a partir de un diccionario de parámetros.
        
        Args:
            params (Dict[str, Any]): Parámetros de conexión.
            
        Returns:
            str: Cadena de conexión.
        """
        conninfo_parts = []
        for key, value in params.items():
            if value is not None:
                # Convertir el valor a string y escapar posibles espacios o caracteres especiales
                value_str = str(value)
                if ' ' in value_str or "'" in value_str:
                    value_str = f"'{value_str.replace('\'', '\'\'')}'"
                conninfo_parts.append(f"{key}={value_str}")
        
        return " ".join(conninfo_parts)
    
    async def open(self):
        """
        Abre el pool de conexiones.
        
        Raises:
            PoolError: Si no se puede abrir el pool.
        """
        try:
            self.pool = PsycopgAsyncConnectionPool(
                # Convertir parámetros a una cadena de conexión
                conninfo=self._build_conninfo(self.conn_params),
                min_size=self.min_size,
                max_size=self.max_size,
                timeout=self.timeout,
                max_lifetime=self.max_lifetime,
                max_idle=self.max_idle,
                check=PsycopgAsyncConnectionPool.check_connection if self.check_connection else None,
                name=self.name,
                open=False  # No abrir automáticamente
            )
            
            # Configurar un timeout más corto para la apertura inicial para detectar errores rápidamente
            await self.pool.open(wait=True, timeout=5.0)
            
            # Verificar que podemos obtener al menos una conexión
            try:
                conn = await self.pool.getconn(timeout=5.0)
                await self.pool.putconn(conn)
            except Exception as e:
                # Si no podemos obtener una conexión, cerramos el pool y lanzamos una excepción
                await self.pool.close()
                raise PoolError(f"No se pudo obtener una conexión del pool: {e}")
                
            logger.info(f"Pool de conexiones async '{self.name}' inicializado con min_size={self.min_size}, max_size={self.max_size}")
        except Exception as e:
            logger.error(f"Error al inicializar el pool de conexiones async '{self.name}': {e}")
            # Limpiar el pool si se creó pero hubo un error
            if hasattr(self, 'pool') and self.pool is not None:
                try:
                    await self.pool.close()
                except Exception:
                    pass
            self.pool = None
            raise PoolError(f"Error al inicializar el pool de conexiones async: {e}")
    
    async def __aenter__(self):
        """Permite usar el pool como un contexto asíncrono."""
        if self.pool is None:
            await self.open()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cierra el pool al salir del contexto asíncrono."""
        await self.close()
    
    @asynccontextmanager
    async def connection(self):
        """
        Obtiene una conexión del pool de manera asíncrona.
        
        Yields:
            psycopg.AsyncConnection: Una conexión asíncrona de la base de datos.
        
        Raises:
            PoolError: Si no se puede obtener una conexión del pool.
        """
        if self.pool is None:
            await self.open()
            
        conn = None
        try:
            conn = await self.pool.getconn()
            # Establecer autocommit para permitir ver cambios inmediatamente entre conexiones
            await conn.set_autocommit(True)
            logger.debug(f"Conexión async obtenida del pool '{self.name}'")
            yield conn
            # Ya no necesitamos hacer commit aquí si autocommit está activado
        except Exception as e:
            # Hacer rollback en caso de error si no está en autocommit
            if conn:
                is_autocommit = False
                try:
                    is_autocommit = conn.autocommit
                except Exception:
                    pass  # Ignorar error al verificar autocommit
                
                if not is_autocommit:
                    await conn.rollback()
                    logger.debug(f"Rollback automático realizado en la conexión async del pool '{self.name}'")
            logger.error(f"Error al obtener conexión async del pool '{self.name}': {e}")
            raise PoolError(f"Error al obtener conexión async del pool: {e}")
        finally:
            if conn:
                await self.pool.putconn(conn)
                logger.debug(f"Conexión async devuelta al pool '{self.name}'")
    
    async def wait(self, timeout: float = None):
        """
        Espera hasta que el pool tenga min_size conexiones disponibles.
        
        Args:
            timeout (float, opcional): Tiempo máximo de espera en segundos.
        
        Raises:
            PoolError: Si se agota el tiempo de espera.
        """
        if self.pool is None:
            await self.open()
            
        try:
            await self.pool.wait(timeout=timeout)
        except Exception as e:
            logger.error(f"Error al esperar conexiones en el pool async '{self.name}': {e}")
            raise PoolError(f"Error al esperar conexiones en el pool async: {e}")
    
    async def close(self):
        """
        Cierra el pool de conexiones de manera asíncrona.
        """
        if self.pool is None:
            return
            
        try:
            await self.pool.close()
            logger.info(f"Pool de conexiones async '{self.name}' cerrado")
        except Exception as e:
            logger.error(f"Error al cerrar el pool de conexiones async '{self.name}': {e}")
    
    async def stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del pool de manera asíncrona.
        
        Returns:
            Dict[str, Any]: Estadísticas del pool.
        """
        if self.pool is None:
            return {}
            
        # El método get_stats() de PsycopgAsyncConnectionPool no es una corutina
        return self.pool.get_stats()
    
    async def resize(self, min_size: int = None, max_size: int = None):
        """
        Cambia el tamaño del pool de manera asíncrona.
        
        Args:
            min_size (int, opcional): Nuevo tamaño mínimo del pool.
            max_size (int, opcional): Nuevo tamaño máximo del pool.
        """
        if self.pool is None:
            await self.open()
            
        # Actualizar los valores de instancia
        if min_size is not None:
            self.min_size = min_size
        
        if max_size is not None:
            self.max_size = max_size
        
        # Recrear el pool con los nuevos tamaños
        old_pool = self.pool
        
        try:
            # Crear un nuevo pool con los nuevos tamaños
            self.pool = PsycopgAsyncConnectionPool(
                conninfo=self._build_conninfo(self.conn_params),
                min_size=self.min_size,
                max_size=self.max_size,
                timeout=self.timeout,
                max_lifetime=self.max_lifetime,
                max_idle=self.max_idle,
                check=PsycopgAsyncConnectionPool.check_connection if self.check_connection else None,
                name=self.name,
                open=False
            )
            await self.pool.open()
            
            # Cerrar el pool antiguo
            await old_pool.close()
            logger.info(f"Pool de conexiones async '{self.name}' redimensionado a min_size={self.min_size}, max_size={self.max_size}")
        except Exception as e:
            # Si hay un error, restaurar el pool antiguo
            self.pool = old_pool
            logger.error(f"Error al redimensionar el pool async '{self.name}': {e}")
            raise PoolError(f"Error al redimensionar el pool async: {e}")