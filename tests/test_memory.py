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


    def i2c_write_read(self, i2c_device: I2CDevice, out_data, in_count, addr=None):
        if len(out_data) <= 0:
            return []
        if i2c_device.size > 2048:
            i2c_device.pointer = (out_data[0] << 8) + out_data[1]
            start = 2
        else:
            i2c_device.pointer = out_data[0]
            match i2c_device.size:
                case 512:
                    mask = 0x1
                case 1024:
                    mask = 0x3
                case 2048:
                    mask = 0x7
                case _:
                    mask = 0
            i2c_device.pointer += 256 * (addr & mask)
            start = 1
        #print(f"pointer: {i2c_device.pointer}/{i2c_device.size}, {out_data[0:3]}")
        for i in range(start, len(out_data)):
            i2c_device.data[i2c_device.pointer] = out_data[i]
            i2c_device.pointer += 1
        result = []
        for i in range(0, in_count):
            result.append(i2c_device.data[i2c_device.pointer])
            i2c_device.pointer += 1
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

@pytest.fixture
def device():
    # factory
    devices = {}
    def _make(size, **kwargs):
        key = (size, )
        if key in devices:
            return devices[key]
        d = M24Cxx("i2c", 0x50, size, **kwargs)
        d.data = [0xFF] * size
        d.pointer = 0
        devices[key] = d
        return d
    yield _make

    # potential cleanup


def test_memory(rig, mainboard, module, device):
    rig.assign_mainboard(mainboard)
    rig.add_module(module)
    memory = device(256)
    module.add_i2c_device(memory)
    rig.configure()

    assert memory.size == 256
    assert memory.read_array(0, 4) == [0xFF, 0xFF, 0xFF, 0xFF]
    assert memory.read_string(0, 5) is None
    assert memory.read_number(2, 4) is None
    assert memory.read_number(2, 4, True) == -1

    memory.write_string(0, "ABCD", 2)
    assert memory.data[0:4] == [ord("A"), ord("B"), 0xFF, 0xFF]
    assert memory.read_string(0, 1) == "A"
    assert memory.read_string(0, 2) == "AB"

    memory.write_string(10, "ABCD", 8)
    assert memory.data[10:18] == [ord("A"), ord("B"), ord("C"), ord("D"), 0x0, 0x0, 0x0, 0x0]
    assert memory.read_string(10, 2) == "AB"

    assert memory.read_string(10, 8) == "ABCD"

    memory.write_number(2, -2, 4)
    assert memory.data[2] == 0xFE

    assert memory.read_number(2, 4, True) == -2
    assert memory.read_number(2, 4) == 0xFFFFFFFE

    dt = datetime.datetime(2025, 5, 31, 18, 40, 59)
    memory.write_datetime(20, dt, 1)
    assert memory.data[20:26] == [25, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]
    assert memory.read_datetime(20) is None
    assert memory.read_datetime(20, 1) == datetime.datetime(2025, 1, 1, 0, 0, 0)
    memory.write_datetime(20, dt, 3)
    assert memory.data[20:26] == [25, 5, 31, 0xFF, 0xFF, 0xFF]
    assert memory.read_datetime(20) is None
    assert memory.read_datetime(20, 3) == datetime.datetime(2025, 5, 31, 0, 0, 0)
    memory.write_datetime(20, dt)
    assert memory.data[20:26] == [25, 5, 31, 18, 40, 59]
    assert memory.read_datetime(20) == dt

    arr = []
    for i in range(0, memory.size):
        arr.append(i)
    memory.write_array(0, arr)
    assert memory.data == arr
    assert memory.read_array(0, len(arr)) == arr
    memory.erase()
    assert memory.read_array(0, memory.size) == [0xFF] * memory.size

    with pytest.raises(ValueError):
        memory.write_array(0, [0xFF] * (memory.size+1))
    with pytest.raises(ValueError):
        memory.write_number(memory.size, 1, 1)
    with pytest.raises(ValueError):
        memory.read_array(0, memory.size+1)
    with pytest.raises(ValueError):
        memory.read_number(memory.size, 1)

    with pytest.raises(ValueError):
        device(255)

    memory = device(512)
    assert memory.size == 512
    memory.assign_controller(mainboard, "i2c")
    arr = []
    for i in range(0, memory.size):
        arr.append(i >> 1)
    memory.write_array(0, arr)
    assert memory.data == arr
    assert memory.read_array(0, len(arr)) == arr

    memory = device(1024)
    assert memory.size == 1024
    memory.assign_controller(mainboard, "i2c")
    arr = []
    for i in range(0, memory.size):
        arr.append(i >> 2)
    memory.write_array(0, arr)
    print(f"data: {memory.data}")
    assert memory.data == arr
    assert memory.read_array(0, len(arr)) == arr

    memory = device(2048)
    assert memory.size == 2048
    memory.assign_controller(mainboard, "i2c")
    arr = []
    for i in range(0, memory.size):
        arr.append(i >> 3)
    memory.write_array(0, arr)
    assert memory.data == arr
    assert memory.read_array(0, len(arr)) == arr

    memory = device(4096)
    assert memory.size == 4096
    memory.assign_controller(mainboard, "i2c")
    arr = []
    for i in range(0, memory.size):
        arr.append(i>>4 & 0xff)
    memory.write_array(0, arr)
    assert memory.data == arr
    assert memory.read_array(0, len(arr)) == arr

def test_module_memory(rig, mainboard, module, device):
    rig.assign_mainboard(mainboard)
    rig.add_module(module)
    memory = device(256)
    module.add_i2c_device(memory)
    rig.configure()

    common_map = CommonMemoryMap(memory)
    assert common_map.default_stamp(datetime.datetime(2025, 2, 1, 19, 30, 40)) == "25032"

    assert common_map.size == 128
    assert common_map.offset == 0
    assert common_map.is_valid() == False
    assert common_map.get_version() is None
    assert common_map.get_id_version() is None
    data = {
        "system_id": "TST",
        "module_id": "PYTEST",
        "module_version": 123,
    }
    common_map.write_data(data)
    assert common_map.is_valid() == True
    d = common_map.read_data()
    assert d["system_id"] == data["system_id"]
    assert d["module_id"] == data["module_id"]
    assert common_map.get_version() == data["module_version"]
    assert common_map.get_id_version() == (data["module_id"], data["module_version"])

    memory_map = ModuleMemoryMap(memory, [
            ("string1", "STRING", 8, "String[8]", "STRING1"),
            ("number1", "number", 2, "Unsigned number", 100),
            ("int1", "int", 4, "Signed number", 0),
            ("string2", "string", 16, "String[16]", lambda: "callable"),
            ("dt1", "datetime", 3, "Datetime"),
        ], 64)
    assert memory_map.get_defaults() == {"string1": "STRING1", "number1": 100, "int1": 0, "string2": "callable"}
    data = {"string1": "abcd", "int1": -4, "string2": "AbCd", "dt1": datetime.datetime(2025, 2, 20, 19, 40, 50), "number1": 888}
    memory_map.write_data(data)
    assert memory_map.read_data() == {"string1": data["string1"].upper(), "number1": data["number1"], "int1": data["int1"], "string2": data["string2"], "dt1": datetime.datetime(2025, 2, 20)}

