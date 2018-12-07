from distutils.core import setup
from Cython.Build import cythonize

setup(
    name="cython",
    ext_modules=cythonize(["./SushiLife/*.pyx"])
)