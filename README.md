# pi-testbench-python
Universal platform based on RPI for testing assembled PCBs


Development
-----------

Tests

  pytest

  # print results of all tests
  pytest -v 

  # print console output from print
  pytest -s

  # run particular test
  pytest tests/test_core.py

  # run by name
  pytest -k "core"
