import pytest
from pi_testbench.core import *
from pi_testbench.devices import *

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

    return MyMainboard()

@pytest.fixture
def module():

    class MyModule(LoggingIOController, Module):

        def get_aliases(self):
            return [self.name, ]

        def get_configuration(self):
            return {
                "i2c": {
                }
            }


    # factory
    modules = {}
    def _make(name, config = None):
        if name in modules:
            return modules[name]
        m = MyModule()
        m._NAME= name
        if config is not None:
            m._configuration = config  # inject configuration
        modules[name] = m
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


def test_i2c_device(rig, mainboard, module, device):
    rig.assign_mainboard(mainboard)
    m1 = module("m1")
    rig.add_module(m1)

    d = device(ADS1115)
    m1.add_i2c_device(d)
    rig.configure()
    d.set_comparator(d.COMP_QUEUE_1, 0.5, 5.0)
    d.set_mode()
    assert d.measure() > 0
    d.reset()

    d = device(PCF8574)
    m1.add_i2c_device(d)
    rig.configure()
    d.set_outputs(0)
    assert d.get_inputs() is not None
    d.set_pin(7, True)
    assert d.get_pin(7) is not None
    d.reset()

    d = device(INA219, i_max=5, r_shunt=0.02)
    m1.add_i2c_device(d)
    rig.configure()
    with pytest.raises(TestbenchError):  # requires response
        d.measure()
    d.reset()

    d = device(PCA9634)
    m1.add_i2c_device(d)
    rig.configure()
    d.set_pwm(0, 85)
    d.reset()

