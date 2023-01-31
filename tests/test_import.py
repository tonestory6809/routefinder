import importlib
import sys, os

sys.path.append(os.path.realpath(os.path.dirname(__file__) + "/.."))


def test_import():
    importlib.import_module("routefinder.calculate_route")
    importlib.import_module("routefinder.compile_data")
    importlib.import_module("routefinder.libraries")
