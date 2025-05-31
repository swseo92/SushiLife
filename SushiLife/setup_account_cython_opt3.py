from setuptools import Extension, setup
from Cython.Build import cythonize
import numpy

extensions = [
    Extension(
        "SushiLife.Account_cython_opt3",
        ["SushiLife/Account_cython_opt3.pyx"],
        include_dirs=[numpy.get_include()]
    )
]

setup(
    name="SushiLifeAccountCythonOpt3",
    ext_modules=cythonize(extensions, compiler_directives={'language_level': "3"}),
    include_dirs=[numpy.get_include()]
)
