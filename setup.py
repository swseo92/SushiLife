from distutils.core import setup
from Cython.Build import cythonize


setup(
    name='SushiLife',
    version='1.0',
    packages=['SushiLife', 'SushiLife.data', "SushiLife.Optimizer"],
    url='https://github.com/swseo92/SushiLife',
    license='',
    author='swseo92',
    author_email='swseo.astro@gmail.com',
    description='',

    ext_modules=cythonize(["./SushiLife/*.pyx"])
)
