from setuptools import setup, find_packages

setup(
    name="movie-script-generator",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "pytest",
        "pytest-cov",
        "pytest-asyncio",
        "httpx"
    ],
) 