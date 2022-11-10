from setuptools import setup, find_packages

setup(
    name='tp-framework',
    description="",
    author="Luca COMPAGNA, Giulia CLERICI, Mattia SIMONE",
    version="0.5.0-alpha",
    packages=find_packages(exclude=["tests"]),
    url='',
    license='',
    zip_safe=False,
    entry_points={
        "console_scripts": [
            "tpframework = tp_framework.cli.main:main"
        ]
    }
)
