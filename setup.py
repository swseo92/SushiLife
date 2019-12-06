from distutils.core import setup
from Cython.Build import cythonize

import numpy as np


setup(
    name='SushiLife',
    version='1.10',
    packages=['SushiLife', 'SushiLife.data', "SushiLife.Optimizer", "SushiLife.Statistics", "SushiLife.Plot", "SushiLife.TA", "SushiLife.Cython"],
    url='https://github.com/swseo92/SushiLife',
    license='',
    author='swseo92',
    author_email='swseo.astro@gmail.com',
    description='',

    ext_modules=cythonize(["./SushiLife/Cython/*.pyx", "./SushiLife/*.pyx"]),
    include_dirs=[np.get_include()]
)
