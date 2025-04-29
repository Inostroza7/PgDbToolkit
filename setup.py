from setuptools import setup, find_packages
from pathlib import Path
import re

# Leer la versión desde el archivo __version__.py sin importarlo
with open('pgdbtoolkit/__version__.py', 'r') as f:
    version_file = f.read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    if version_match:
        __version__ = version_match.group(1)
    else:
        raise RuntimeError("No se encontró la versión en pgdbtoolkit/__version__.py")

with Path("requirements.txt").open() as f:
    install_requires = f.read().splitlines()

setup(
    name="PgDbToolkit",
    version=__version__,
    author="Gustavo Inostroza",
    author_email="gusinostrozar@gmail.com",
    description="A package for managing PostgreSQL database operations",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/Inostroza7/PgDbToolkit",
    packages=find_packages(),
    install_requires=install_requires,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
)