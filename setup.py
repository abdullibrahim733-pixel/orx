from setuptools import setup, Extension
import pybind11

ext_modules = [
    Extension(
        "orx.cpp.orx_cpp",
        ["src/cpp/raycaster.cpp"],
        include_dirs=[pybind11.get_include()],
        language="c++",
        extra_compile_args=["-O3", "-std=c++17"],
    ),
]

setup(ext_modules=ext_modules)
