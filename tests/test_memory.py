import pytest
from pi_testbench.core import *
from pi_testbench.devices.i2c_memory import *
from pi_testbench.modules.module_memory import *
import datetime

# --- FIXTURES

@pytest.fixture
def rig():
    return Rig()

class MemoryIOController(IOControllerMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calls = []
        self.size = 32
        self.data = [0xFF] * self.size
        self.pointer = 0


    def i2c_write_read(self, i2c_device: I2CDevice, out_data, in_count):
        if len(out_data) <= 0:
            return []
        self.pointer = out_data[0]
        for i in range(1, len(out_data)):
            self.data[self.pointer] = out_data[i]
            self.pointer += 1
        result = []
        for i in range(0, in_count):
            result.append(self.data[self.pointer])
            self.pointer += 1
        return result

@pytest.fixture
def mainboard():
    class MyMainboard(MemoryIOController, Mainboard):

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

    class MyModule(MemoryIOController, Module):

        def get_configuration(self):
            return {
                "i2c": {
                },
            }

    return MyModule()

class MyModuleMemory(ModuleMemoryMixin, M24Cxx):
    CUSTOM_MAP: Final = [
        ("string1", "STRING", 8, "String[8]", "STRING1"),
        ("number1", "number", 2, "Unsigned number", 100),
        ("int1", "int", 4, "Signed number", 0),
        ("string2", "string", 16, "String[16]", "Hello"),
        ("dt1", "datetime", 8, "Datetime"),
    ]

@pytest.fixture
def device():
    return MyModuleMemory("i2c", 0x54, 8)


def test_memory(rig, mainboard, module, device):
    rig.assign_mainboard(mainboard)
    rig.add_module(module)
    module.add_i2c_device(device)
    rig.configure()

    assert device.read_array(0, 4) == [0xFF, 0xFF, 0xFF, 0xFF]
    assert device.read_string(0, 5) is None
    assert device.read_number(2, 4) is None
    assert device.read_number(2, 4, True) == -1

    device.write_string(0, "ABCD", 2)
    assert mainboard.data[0:4] == [ord("A"), ord("B"), 0xFF, 0xFF]
    assert device.read_string(0, 1) == "A"
    assert device.read_string(0, 2) == "AB"

    device.write_string(10, "ABCD", 8)
    assert mainboard.data[10:18] == [ord("A"), ord("B"), ord("C"), ord("D"), 0x0, 0x0, 0x0, 0x0]
    assert device.read_string(10, 2) == "AB"
    assert device.read_string(10, 8) == "ABCD"

    device.write_number(2, -2, 4)
    assert mainboard.data[2] == 0xFE

    print(f"data: {mainboard.data}")
    assert device.read_number(2, 4, True) == -2
    assert device.read_number(2, 4) == 0xFFFFFFFE

    dt = datetime.datetime(2025, 5, 31, 18, 40, 59)
    device.write_datetime(20, dt, 1)
    assert mainboard.data[20:26] == [25, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]
    assert device.read_datetime(20) is None
    assert device.read_datetime(20, 1) == datetime.datetime(2025, 1, 1, 0, 0, 0)
    device.write_datetime(20, dt, 3)
    assert mainboard.data[20:26] == [25, 5, 31, 0xFF, 0xFF, 0xFF]
    assert device.read_datetime(20) is None
    assert device.read_datetime(20, 3) == datetime.datetime(2025, 5, 31, 0, 0, 0)
    device.write_datetime(20, dt)
    assert mainboard.data[20:26] == [25, 5, 31, 18, 40, 59]
    assert device.read_datetime(20) == dt

    arr = []
    for i in range(0, mainboard.size):
        arr.append(i)
    device.write_array(0, arr)
    assert mainboard.data == arr
    assert device.read_array(0, len(arr)) == arr

def test_module_memory(rig, mainboard, module, device):
    rig.assign_mainboard(mainboard)
    rig.add_module(module)
    module.add_i2c_device(device)
    rig.configure()
 


