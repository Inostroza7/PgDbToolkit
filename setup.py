from setuptools import setup, find_packages
from pgdbtoolkit.__version__ import __version__
from pathlib import Path

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