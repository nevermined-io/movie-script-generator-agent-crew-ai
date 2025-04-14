from setuptools import setup, find_packages

setup(
    name="movie-script-generator",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "crewai",
        "langchain-openai",
        "tenacity",
        "pydantic"
    ]
) 