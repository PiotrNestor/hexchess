from __future__ import annotations

from pathlib import Path

from Cython.Build import cythonize
from setuptools import Extension, setup


ROOT_DIR = Path(__file__).resolve().parent
README_PATH = ROOT_DIR / 'README.md'


setup(
    name='hexchess-cyengine',
    version='0.1.0',
    description='Cython build of the hexchess Python engine',
    long_description=README_PATH.read_text(encoding='utf-8'),
    long_description_content_type='text/markdown',
    packages=['cyengine'],
    package_dir={'cyengine': '.'},
    ext_modules=cythonize(
        [
            Extension(
                name='cyengine._native_engine',
                sources=['_native_engine.pyx'],
            )
        ],
        compiler_directives={
            'language_level': '3',
            'binding': True,
        },
    ),
    zip_safe=False,
)