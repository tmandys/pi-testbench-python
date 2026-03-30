import pytest
from pi_testbench.core import *

# --- FIXTURES

@pytest.fixture
def rig():
    return Rig()

class LoggingIOController(IOControllerMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calls = []
        self.values = {}

    def read_pin(self, id: str) -> bool:
        self.calls.append(("read_pin", id))
        return self.values.get(id, False)

    def write_pin(self, id: int, value: bool) -> None:
        self.calls.append(("write_pin", id, value))
        self.values[id] = value

    def set_pin_event_handler(self, num, edge, name = None, handler = None):
        self.calls.append(("set_pin_event_handler", num, edge, name))

    def read_port(self, id: str) -> int:
        self.calls.append(("read_port", id))
        return self.values.get(id, 0)

    def write_port(self, id: str, value: int) -> None:
        self.calls.append(("write_port", id, value))
        self.values[id] = value

    def read_analog(self, id: str) -> float:
        self.calls.append(("read_analog", id))
        return self.values.get(id, 0)

    def write_analog(self, id: str, value: float) -> None:
        self.calls.append(("write_analog", id, value))
        self.values[id] = value

    def write_pwm(self, id: str, duty_cycle: float, freq: float = None) -> None:
        self.calls.append(("write_pwm", id, duty_cycle))

    def i2c_write_read(self, i2c_device: I2CDevice, out_data, in_count):
        print(f"i2c({self}, {i2c_device}, {out_data}, {in_count}")
        self.calls.append(("i2c_write_read", i2c_device.bus_id, i2c_device.addr, out_data, in_count))
        result = []
        for i in range(0, in_count):
            result.append(i)
        return result

    def toggle_i2c_bus(self, i2c_device: I2CDevice, enabled: bool):
        self.calls.append(("toggle_i2c_bus", i2c_device.bus_id, i2c_device.addr, enabled))

@pytest.fixture
def mainboard():
    class MyMainboard(LoggingIOController, Mainboard):
        def __init__(self):
            super().__init__()

        def get_aliases(self):
            return ["mainboard", "main", ]

        def get_capabilities(self):
            return {
                "io0": {
                    "type": "pin",
                    "num": 0,
                    "options": {
                        "dir": ["in", "out"],
                        "mode": ["up", "down", "float"],
                    },
                },
                "io1": {
                    "type": "pin",
                    "num": 1,
                    "options": {
                        "dir": ["in", "out"],
                        "mode": ["up", "down", "float"],
                    },
                },
                "port0": {
                    "type": "port",
                    "num": 0,
                },
                "i2c0": {
                    "type": "i2c",
                    "num": 0,
                },
                "i2c1": {
                    "type": "i2c",
                    "num": 1,
                },
                "pwm0": {
                    "type": "pwm",
                    "num": 0,
                },
                "a0": {
                    "type": "analog",
                    "num": 0,
                },
            }

    return MyMainboard()

@pytest.fixture
def module():

    class MyModule(LoggingIOController, Module):

        def toggle_i2c_bus(self, i2c_device: I2CDevice, enabled: bool):
            self.calls.append(("toggle_i2c_bus", i2c_device.bus_id, i2c_device.addr, enabled))

        def get_aliases(self):
            return [self.name, ]

        def get_capabilities(self):
            return {
                "io0": {
                    "type": "pin",
                    "num": 10,
                },
                "io11": {
                    "type": "pin",
                    "num": 11,
                },
                "port0": {
                    "type": "port",
                    "num": 0,
                },
                "i2c2": {
                    "type": "i2c",
                    "num": 2,
                },
                "pwm10": {
                    "type": "pwm",
                    "num": 0x80,
                },
                "a10": {
                    "type": "analog",
                    "num": 0,
                },
            }
        def get_configuration(self):
            return {
                "m_io0_0": {
                    "controller": "mainboard",
                    "capability_id": "io0",
                    "dir": "in",
                    "mode": "down",
                },
                "mo_io0": {
                    "capability_id": "io0",
                    "dir": "in",
                },
                "io0": {
                },
                "m1_io0": {
                    "controller": "m1",
                    "capability_id": "io0",
                    "dir": "in",
                },
                "m_port0": {
                    "controller": "mainboard",
                    "capability_id": "port0",
                },
                "port0": {
                },
                "i2c0": {
                },
                "i2c2": {
                },
                "a0": {
                },
                "a10": {
                },
                "m1_a0": {
                    "controller": "m1",
                    "capability_id": "a10",
                },
                "pwm0": {
                },
                "pwm10": {
                },

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

    class MyI2CDevice(I2CDevice):
        def _setup_impl(self):
            self.write_read(["S", "E", "T", "U", "P"], 0)

        def _reset_impl(self):
            self.write_read(["R", "E", "S", "E", "T"], 0)


    # factory
    devices = {}
    def _make(bus_id, addr):
        key = (bus_id, addr)
        if key in devices:
            return devices[key]
        d = MyI2CDevice(bus_id, addr)
        devices[key] = d
        return d
    yield _make

    # potential cleanup


def test_basic_initialization(rig, mainboard, module, device):
    assert rig._mainboard is None
    assert not rig._modules
    assert not rig._timers

    rig.assign_mainboard(mainboard)
    assert rig._mainboard == mainboard

    rig.assign_mainboard(None)
    assert rig._mainboard is None

    m1 = module("M1")
    assert m1.name == "M1"
    rig.add_module(m1)
    assert len(rig._modules) == 1
    assert list(rig._modules)[0] == m1.name
    assert list(rig._modules.values())[0] == m1
    assert m1._rig == rig
    rig.add_module(m1)
    assert len(rig._modules) == 1
    m2 = module("M2")
    rig.add_module(m2)
    assert len(rig._modules) == 2
    assert list(rig._modules.values())[0] == m1
    assert list(rig._modules.values())[1] == m2
    rig.remove_module(m1)
    assert len(rig._modules) == 1
    assert list(rig._modules)[0] == m2.name
    assert list(rig._modules.values())[0] == m2
    assert m1._rig is None

    assert m1.assign_rig(None) == None
    m1.assign_rig(rig)
    assert list(rig._modules)[-1] == m1.name
    assert m1._rig == rig
    m1.assign_rig(None)
    assert len(rig._modules) == 1
    assert m1._rig is None

    m3 = module("M3")
    rig.remove_module(m3)
    assert len(rig._modules) == 1
    m3._NAME = "M2"
    with pytest.raises(TestbenchError):
        rig.add_module(m3)

    m1.assign_rig(None)

    #assert hasattr(basic_rig, 'boards')
    d = device("i2c", 0x10)
    assert d.bus_id == "i2c"
    assert d.addr == 0x10

    assert m1.get_aliases() == ["M1"]
    m1.add_i2c_device(d)
    assert d.module == m1
    assert len(m1._i2c_devices) == 1
    assert m1._i2c_devices[0] == d
    m1.add_i2c_device(d)
    assert len(m1._i2c_devices) == 1
    d2 = device("i2c", 0x80)
    m1.add_i2c_device(d2)
    assert len(m1._i2c_devices) == 2
    assert m1._i2c_devices[1] == d2
    m1.remove_i2c_device(d)
    assert len(m1._i2c_devices) == 1
    assert m1._i2c_devices[0] == d2

    d.assign_module(m1)
    assert d.module == m1
    assert len(m1._i2c_devices) == 2
    assert m1._i2c_devices[-1] == d
    d.assign_module(m2)
    assert d.module == m2
    assert len(m1._i2c_devices) == 1
    assert len(m2._i2c_devices) == 1
    assert m2._i2c_devices[-1] == d
    d.assign_module(None)
    assert d.module is None
    assert len(m2._i2c_devices) == 0


def test_configuration_sanity(rig, mainboard, module, device):
    rig.assign_mainboard(mainboard)
    assert mainboard.can_handle("mainboard", "io0") == True
    assert mainboard.can_handle(None, "io0") == True
    assert mainboard.can_handle("main", "io0") == True
    assert mainboard.can_handle("module", "io0") == False
    assert mainboard.can_handle("main", "io0", "pin") == True
    assert mainboard.can_handle("main", "io0", "analog") == False

    config = {
        "io0_0": {
            "capability_id": "io0",
            "dir": "in",
            "mode": "down",
        },
        "io0_1": {
            "capability_id": "io0",
            "dir": "in",
        },
        "io0_2": {
            "capability_id": "io0",
            "mode": "down",
        },
        "io0_3": {
            "capability_id": "io0",
        },
        "io1": {
            "capability_id": "io1",
            "dir": "out",
            "mode": "up",
        }
    }
    assert mainboard.check_configuration(config) is None

    config["io0_1"]["dir"] = "out"
    with pytest.raises(TestbenchError):
        mainboard.check_configuration(config)
    config["io0_1"]["unused"] = True
    assert mainboard.check_configuration(config) is None
    config["io1"]["mode"] = "unknown"
    with pytest.raises(TestbenchError):
        mainboard.check_configuration(config)
    config["io1"]["mode"] = "float"
    assert mainboard.check_configuration(config) is None

    mainboard.configure(config)


def test_configuration(rig, mainboard, module, device):
    rig.assign_mainboard(mainboard)
    m1 = module("m1")
    rig.add_module(m1)

    assert rig._configuration[("m1", "m_io0_0")]["__controller__"] == mainboard
    assert rig._configuration[("m1", "mo_io0")]["__controller__"] == m1
    assert rig._configuration[("m1", "io0")]["__controller__"] == m1
    assert rig._configuration[("m1", "m1_io0")]["__controller__"] == m1
    assert rig._configuration[("m1", "m_port0")]["__controller__"] == mainboard
    assert rig._configuration[("m1", "port0")]["__controller__"] == m1
    assert rig._configuration[("m1", "i2c0")]["__controller__"] == mainboard
    assert rig._configuration[("m1", "i2c2")]["__controller__"] == m1
    assert rig._configuration[("m1", "a0")]["__controller__"] == mainboard
    assert rig._configuration[("m1", "a10")]["__controller__"] == m1
    assert rig._configuration[("m1", "m1_a0")]["__controller__"] == m1
    assert rig._configuration[("m1", "pwm0")]["__controller__"] == mainboard
    assert rig._configuration[("m1", "pwm10")]["__controller__"] == m1

    rig.write_pin("m_io0_0", 1)
    assert mainboard.calls.pop() == ("write_pin", "io0", 1)
    assert rig.read_pin("m1.m_io0_0") == 1
    assert mainboard.calls.pop() == ("read_pin", "io0")
    with pytest.raises(TestbenchError):
        rig.read_pin("m2.m_io0_0")
    with pytest.raises(TestbenchError):
        rig.read_pin("unknown")
    rig.write_pin("mo_io0", 0)
    assert m1.calls.pop() == ("write_pin", "io0", 0)
    assert rig.read_pin("m1.mo_io0") == 0
    assert m1.calls.pop() == ("read_pin", "io0")
    rig.write_pin("io0", 0)
    assert m1.calls.pop() == ("write_pin", "io0", 0)
    assert rig.read_pin("m1.mo_io0") == 0
    assert m1.calls.pop() == ("read_pin", "io0")
    rig.write_pin("m1_io0", 1)
    assert m1.calls.pop() == ("write_pin", "io0", 1)
    assert rig.read_pin("m1.m1_io0") == 1
    assert m1.calls.pop() == ("read_pin", "io0")

    rig.write_port("m_port0", 155)
    assert mainboard.calls.pop() == ("write_port", "port0", 155)
    assert rig.read_port("m_port0") == 155
    assert mainboard.calls.pop() == ("read_port", "port0")
    rig.write_port("port0", 255)
    assert m1.calls.pop() == ("write_port", "port0", 255)
    assert rig.read_port("port0") == 255
    assert m1.calls.pop() == ("read_port", "port0")

    rig.write_analog("a0", 1.2)
    assert mainboard.calls.pop() == ("write_analog", "a0", 1.2)
    assert rig.read_analog("a0") == 1.2
    assert mainboard.calls.pop() == ("read_analog", "a0")
    rig.write_analog("a10", 3.2)
    assert m1.calls.pop() == ("write_analog", "a10", 3.2)
    assert rig.read_analog("a10") == 3.2
    assert m1.calls.pop() == ("read_analog", "a10")
    rig.write_analog("m1_a0", 5.2)
    assert m1.calls.pop() == ("write_analog", "a10", 5.2)
    assert rig.read_analog("m1_a0") == 5.2
    assert m1.calls.pop() == ("read_analog", "a10")

    rig.write_pwm("pwm0", 55)
    assert mainboard.calls.pop() == ("write_pwm", "pwm0", 55)
    rig.write_pwm("pwm10", 66)
    assert m1.calls.pop() == ("write_pwm", "pwm10", 66)

    m2 = module("m2")
    rig.add_module(m2)

    assert rig._configuration[("m1", "m_io0_0")]["__controller__"] == mainboard
    assert rig._configuration[("m1", "mo_io0")]["__controller__"] == m1
    assert rig._configuration[("m1", "io0")]["__controller__"] == m1
    assert rig._configuration[("m1", "m1_io0")]["__controller__"] == m1
    assert rig._configuration[("m1", "m_port0")]["__controller__"] == mainboard
    assert rig._configuration[("m1", "port0")]["__controller__"] == m1
    assert rig._configuration[("m1", "i2c0")]["__controller__"] == mainboard
    assert rig._configuration[("m1", "i2c2")]["__controller__"] == m1
    assert rig._configuration[("m1", "a0")]["__controller__"] == mainboard
    assert rig._configuration[("m1", "a10")]["__controller__"] == m1
    assert rig._configuration[("m1", "m1_a0")]["__controller__"] == m1
    assert rig._configuration[("m1", "pwm0")]["__controller__"] == mainboard
    assert rig._configuration[("m1", "pwm10")]["__controller__"] == m1

    assert rig._configuration[("m2", "m_io0_0")]["__controller__"] == mainboard
    assert rig._configuration[("m2", "mo_io0")]["__controller__"] == m2
    assert rig._configuration[("m2", "io0")]["__controller__"] == m2
    assert rig._configuration[("m2", "m1_io0")]["__controller__"] == m1
    assert rig._configuration[("m2", "m_port0")]["__controller__"] == mainboard
    assert rig._configuration[("m2", "port0")]["__controller__"] == m2
    assert rig._configuration[("m1", "i2c0")]["__controller__"] == mainboard
    assert rig._configuration[("m2", "i2c2")]["__controller__"] == m2
    assert rig._configuration[("m2", "a0")]["__controller__"] == mainboard
    assert rig._configuration[("m2", "a10")]["__controller__"] == m2
    assert rig._configuration[("m2", "m1_a0")]["__controller__"] == m1
    assert rig._configuration[("m2", "pwm0")]["__controller__"] == mainboard
    assert rig._configuration[("m2", "pwm10")]["__controller__"] == m2

    rig.write_port("m1.port0", 100)
    assert m1.calls.pop() == ("write_port", "port0", 100)
    rig.write_port("m2.port0", 200)
    assert m2.calls.pop() == ("write_port", "port0", 200)
    rig.write_port("port0", 50)
    assert m1.calls.pop() == ("write_port", "port0", 50)

def test_i2c_device(rig, mainboard, module, device):
    rig.assign_mainboard(mainboard)
    m1 = module("m1")
    rig.add_module(m1)
    d1 = device("i2c0", 0x10)
    d2 = device("i2c2", 0x20)
    m1.add_i2c_device(d1)
    m1.add_i2c_device(d2)
    rig.configure()
    assert isinstance(mainboard.get_i2c_bus_lock("i2c0"), I2CBusRLock)
    with pytest.raises(TestbenchError):
        mainboard.get_i2c_bus_lock("unknown")

    lock = mainboard.get_i2c_bus_lock("i2c0")
    d1.acquire_bus()
    try:
        assert lock._lock_level == 1
        assert m1.calls.pop() == ("toggle_i2c_bus", d1.bus_id, d1.addr, True)
        d1.acquire_bus()
        try:
            assert lock._lock_level == 2
            assert len(m1.calls) == 0
        finally:
            d1.release_bus()
        assert lock._lock_level == 1
        assert len(m1.calls) == 0
    finally:
        d1.release_bus()
    assert lock._lock_level == 0
    assert m1.calls.pop() == ("toggle_i2c_bus", d1.bus_id, d1.addr, False)

    assert d1.controller == mainboard
    assert d1.module == m1
    assert d2.controller == m1
    assert d2.module == m1
    # setup + payload
    assert d1.write_read(["A"], 0) == []
    assert mainboard.calls.pop(-2) == ("i2c_write_read", "i2c0", d1.addr, ["S", "E", "T", "U", "P"], 0)
    assert mainboard.calls.pop() == ("i2c_write_read", "i2c0", d1.addr, ["A"], 0)
    assert len(m1.calls) == 2
    assert m1.calls.pop(-2) == ("toggle_i2c_bus", d1.bus_id, d1.addr, True)
    assert m1.calls.pop() == ("toggle_i2c_bus", d1.bus_id, d1.addr, False)
    assert d1.write_read(["B", "C"], 2) == [0, 1]
    assert len(mainboard.calls) == 1
    assert mainboard.calls.pop() == ("i2c_write_read", "i2c0", d1.addr, ["B", "C"], 2)

    d1.write_reg16(0x78, 0x1234)
    assert mainboard.calls.pop() == ("i2c_write_read", "i2c0", d1.addr, [0x78, 0x12, 0x34], 0)
    d1.read_reg16(0x87) == 0x0102
    assert mainboard.calls.pop() == ("i2c_write_read", "i2c0", d1.addr, [0x87], 2)

    mainboard.calls.clear()
    # already initialized so no setup
    d1.setup()
    assert len(mainboard.calls) == 0
    d1.setup(True)
    assert len(mainboard.calls) == 1
    assert mainboard.calls.pop() == ("i2c_write_read", "i2c0", d1.addr, ["S", "E", "T", "U", "P"], 0)

    d1.reset()
    assert mainboard.calls.pop() == ("i2c_write_read", "i2c0", d1.addr, ["R", "E", "S", "E", "T"], 0)
    assert d1._initialized is None

