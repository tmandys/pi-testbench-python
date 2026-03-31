import pytest
from pi_testbench.core import *
from pi_testbench.devices import *
from pi_testbench.modules import *

# --- FIXTURES

@pytest.fixture
def rig():
    return Rig()

class LoggingIOController(IOControllerMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calls = []

    def i2c_write_read(self, i2c_device: I2CDevice, out_data, in_count):
        #print(f"i2c({self}, {i2c_device}, {out_data}, {in_count}")
        self.calls.append(("i2c_write_read", i2c_device.bus_id, i2c_device.addr, out_data, in_count))
        result = []
        for i in range(0, in_count):
            result.append(i)
        return result

@pytest.fixture
def mainboard():
    class MyMainboard(LoggingIOController, Mainboard):
        def __init__(self):
            super().__init__()

        def get_aliases(self):
            return ["mainboard", "main", ]

        def get_capabilities(self):
            return {
                "i2c": {
                    "type": "i2c",
                    "num": 0,
                },
            }

        def get_configuration(self):
            return {
                "i2c": {
                },
            }

    return MyMainboard()

@pytest.fixture
def module():

    # factory
    modules = {}
    def _make(module_class, **kwargs):
        key = (module_class, )
        if key in modules:
            return modules[key]
        m = module_class(M24Cxx("i2c", 0x54, 8), **kwargs)
        modules[key] = m
        return m
    yield _make

    # potential cleanup

@pytest.fixture
def device():
    # factory
    devices = {}
    def _make(device_class, addr=0x80, **kwargs):
        key = (device_class, addr)
        if key in devices:
            return devices[key]
        d = device_class("i2c", addr, **kwargs)
        devices[key] = d
        return d
    yield _make

    # potential cleanup


def test_modules(rig, mainboard, module, device):
    rig.assign_mainboard(mainboard)
    m1 = module(UTBModule)
    rig.add_module(m1)

