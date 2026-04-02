import pytest
from pi_testbench.core import *
from pi_testbench.mainboards.rpi import *
import datetime

# --- FIXTURES

@pytest.fixture
def rig():
    return Rig()


@pytest.fixture
def mainboard():
    class MyMainboard(RpiMainboard):

        def get_aliases(self):
            return ["mainboard", "main", "rpi",  ]

        def get_capabilities(self):
            return {
                "i2c": {
                    "type": "i2c",
                    "num": 0,
                },
            }

    return MyMainboard()


def test_memory(rig, mainboard):
    rig.assign_mainboard(mainboard)
    assert mainboard.is_rpi5 is not None

