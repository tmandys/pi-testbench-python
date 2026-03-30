#!/usr/bin/env python3

# vim: set expandtab:
import pkgutil
import importlib
import pytest
import pi_testbench

# Find recursively all modules in package
def get_all_submodules(package):
    modules = []
    # walk_packages search subdir (devices etc.)
    for loader, name, is_pkg in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        modules.append(name)
    return modules

@pytest.mark.parametrize("module_name", get_all_submodules(pi_testbench))
def test_everything_imports(module_name):
    """Try import every *.py file in project."""
    try:
        importlib.import_module(module_name)
    except Exception as e:
        pytest.fail(f"Module {module_name} import failed: {e}")



"""
import pi_testbench.rpi as rpi
import pi_testbench.core as core
import pi_testbench.io_rpigpio
import pi_testbench.io_gpiozero
from pi_testbench.devices import *
from pi_testbench.modules import *
"""

