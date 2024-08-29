from pgdbtools import PgDbTools

pgdb = PgDbTools()


columns = {
    "id": "SERIAL PRIMARY KEY",
    "nombre": "VARCHAR(100)",
    "edad": "INT"
}

# Crear la tabla
print(pgdb.create_table("personas", columns))

