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

    def i2c_write_read(self, i2c_device: I2CDevice, out_data, in_count, addr = None):
        #print(f"i2c({self}, {i2c_device}, {out_data}, {in_count}, {addr}")
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
        m = module_class(M24Cxx("i2c", 0x54, 256), **kwargs)
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
    config = {}
    for cap_id, cap in m1.capabilities.items():
        config[cap_id] = {}
    rig.configure(config)

    #print(f"i2cdevices: {m1._i2c_devices}")
    #print(f"config: {rig._configuration}")
    #print(f"caps: {m1.capabilities}")
    assert rig.read_pin("io0") is not None
    rig.write_pin("io15", True)
    assert rig.read_port("port0") is not None
    rig.write_port("port1", 0x20)
    rig.write_analog("aout1", 4.5)
    with pytest.raises(TestbenchError):
        rig.write_analog("aout1", 6)
    with pytest.raises(TestbenchError):
        rig.write_analog("aout0", -1)
    rig.write_pwm("pwm7", 0.85)

    assert rig.read_analog("ain0_0") is not None
    with pytest.raises(TestbenchError):
        rig.read_analog("pwri0")
    
