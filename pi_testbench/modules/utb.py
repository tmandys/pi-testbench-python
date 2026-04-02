# vim: set expandtab:
# -*- coding: utf-8 -*-
#
# Copyright 2026 MandySoft

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


__author__ = "Tomas Mandys"
__copyright__ = "Copyright (C) 2026 MandySoft"
__licence__ = "Apache 2.0"
__version__ = "0.1"

from typing import Final
from ..core import *
from ..devices import *
from .module_memory import *
import logging
import time
import datetime
from timeit import default_timer

## @package board
# Board and adapter Support

class UTBModuleMemoryMap(ModuleMemoryMap):
    def __init__(self, storage: StorageMixin):
        super().__init__(storage, [
            ("addr_pca9634", "number", 1, "PCA9634 I2C address", 0x4F),
            ("addr_pcf8574_0", "number", 1, "PCF8574 #0 I2C address", 0x27),
            ("addr_pcf8574_1", "number", 1, "PCF8574 #1 I2C address", 0x26),
            ("addr_ina219_0", "number", 1, "INA219 #0 I2C address", 0x47),
            ("addr_ina219_1", "number", 1, "INA219 #1 I2C address", 0x46),
            ("addr_ads1115_0", "number", 1, "ADS1115 #0 I2C address", 0x48),
            ("addr_ads1115_1", "number", 1, "ADS1115 #1 I2C address", 0x49),
            ("addr_ads1115_2", "number", 1, "ADS1115 #2 I2C address", 0x4A),
            ("addr_ads1115_3", "number", 1, "ADS1115 #3 I2C address", 0x4B),
            ("imax_ina219_0", "number", 4, "INA219 #0 Imax[mA]", 2000),
            ("imax_ina219_1", "mumber", 4, "INA219 #1 Imax[mA]", 2000),
            ("rshunt_ina219_0", "number", 4, "INA219 #0 R shunt [mOhm]", 20),
            ("rshunt_ina219_1", "number", 4, "INA219 #1 R shunt [mOhm]", 20),
            ("k_ads1115_0_0", "number", 2, "ADS1115 #0/0 divider ratio", 0xFFFF),
            ("k_ads1115_0_1", "number", 2, "ADS1115 #0/1 divider ratio", 0xFFFF),
            ("k_ads1115_0_2", "number", 2, "ADS1115 #0/2 divider ratio", 0xFFFF),
            ("k_ads1115_0_3", "number", 2, "ADS1115 #0/3 divider ratio", 0xFFFF),
            ("k_ads1115_1_0", "number", 2, "ADS1115 #1/0 divider ratio", 0xFFFF),
            ("k_ads1115_1_1", "number", 2, "ADS1115 #1/1 divider ratio", 0xFFFF),
            ("k_ads1115_1_2", "number", 2, "ADS1115 #1/2 divider ratio", 0xFFFF),
            ("k_ads1115_1_3", "number", 2, "ADS1115 #1/3 divider ratio", 0xFFFF),
            ("k_ads1115_2_0", "number", 2, "ADS1115 #2/0 divider ratio", 0xFFFF),
            ("k_ads1115_2_1", "number", 2, "ADS1115 #2/1 divider ratio", 0xFFFF),
            ("k_ads1115_2_2", "number", 2, "ADS1115 #2/2 divider ratio", 0xFFFF),
            ("k_ads1115_2_3", "number", 2, "ADS1115 #2/3 divider ratio", 0xFFFF),
            ("k_ads1115_3_0", "number", 2, "ADS1115 #3/0 divider ratio", 0xFFFF),
            ("k_ads1115_3_1", "number", 2, "ADS1115 #3/1 divider ratio", 0xFFFF),
            ("k_ads1115_3_2", "number", 2, "ADS1115 #3/2 divider ratio", 0xFFFF),
            ("k_ads1115_3_3", "number", 2, "ADS1115 #3/3 divider ratio", 0xFFFF),
            ("v_max_ao0", "number", 1, "V max. for analog output #0 (0..6.4V)", 200),
            ("v_max_ao1", "number", 1, "V max. for analog output #1 (0..6.4V)", 200),
            ("v_max_ao2", "number", 1, "V max. for analog output #2 (0..6.4V)", 200),
            ("v_max_ao3", "number", 1, "V max. for analog output #3 (0..6.4V)", 200),
            ("v_max_ao4", "number", 1, "V max. for analog output #4 (0..6.4V)", 200),
            ("v_max_ao5", "number", 1, "V max. for analog output #5 (0..6.4V)", 200),
            ("v_max_ao6", "number", 1, "V max. for analog output #6 (0..6.4V)", 200),
            ("v_max_ao7", "number", 1, "V max. for analog output #7 (0..6.4V)", 200),
            #("toggle_pin", "string", 8, "I2C bus toggle pin", ""),
        ])

class UTBModule(Module):
    _ANALOG_IN = 0
    _ANALOG_PWR = 1

    ID = "UTB"
    MODULE_MEMORY_CLASS = UTBModuleMemoryMap

    def __init__(self, storage, toggle_pin=None):
        super().__init__()
        self._storage = storage
        self._module_memory = self.MODULE_MEMORY_CLASS(storage)
        self._toggle_pin_capability_id = toggle_pin
        self._module_data = None
        self.add_i2c_device(storage)

    @property
    def module_memory(self):
        return self._module_memory

    def read_pin(self, id: str) -> bool:
        map = self.capabilities[id]["device_map"]
        return self._i2c_io_devices[map[0]].get_pin(map[1])

    def write_pin(self, id: int, value: bool) -> None:
        map = self.capabilities[id]["device_map"]
        self._i2c_io_devices[map[0]].set_pin(map[1], value)

    def read_port(self, id: str) -> int:
        map = self.capabilities[id]["device_map"]
        return self._i2c_io_devices[map[0]].get_inputs()

    def write_port(self, id: str, value: int) -> None:
        map = self.capabilities[id]["device_map"]
        self._i2c_io_devices[map[0]].set_outputs(value)

    def read_analog(self, id: str) -> float:
        map = self.capabilities[id]["device_map"]
        match map[0]:
            case self._ANALOG_IN:
                d = self._i2c_analog_in_devices[map[1]]
                d.set_mode(map[2])
                res = d.measure()
                k1 = self._module_data[f"k_ads1115_{map[1]}_{map[3]}"]
                k2 = self._module_data[f"k_ads1115_{map[1]}_{map[4]}"]
                if k1 != k2:
                    raise TestbenchError(f"Different divider ratio for {id}")
                if k1 == 0:
                    raise TestbenchError(f"Zero divider ratio for {id}")
                res = (res * 0xFFFF) / k1
            case self._ANALOG_PWR:
                d = self._i2c_pwr_devices[map[1]]
                res = d.measure()[map[2]]
        return res

    def write_analog(self, id: str, value: float) -> None:
        map = self.capabilities[id]["device_map"]
        vmax = self._module_data[f"v_max_ao{map[1]}"] * 6.4 / 255
        if value > vmax or value < 0:
            raise TestbenchError(f"Voltage {value} out of range 0..{vmax}")
        duty = int(value / vmax * 255)
        d = self._i2c_pwr_device
        d.set_pwm(map[1], duty)

    def write_pwm(self, id: str, duty_cycle: float, freq: float = None) -> None:
        # TODO: currently fixed frquency 97kHz, there is a hack tto use group blinking for period 24Hz - 0.09Hz
        map = self.capabilities[id]["device_map"]
        d = self._i2c_pwr_device
        d.set_pwm(map[1], int(duty_cycle * 255))

    def _read_module_configuration(self):
        # TODO: we need initialized bus
        self._module_data = self._module_memory.get_defaults()
        common_map = CommonMemoryMap(self._storage)
        if common_map.is_valid():
            self._module_data |= self._module_memory.read_data()
        #print(f"module_data: {self._module_data}")
        bus_id = self._storage.bus_id
        # get configuration from memory
        #self._toggle_pin_capability_id = self._module_data["toggle_pin"]
        self._i2c_analog_in_devices = []
        for i in range(0, 4):
            dev = ADS1115(bus_id, self._module_data[f"addr_ads1115_{i}"])
            self._i2c_analog_in_devices.append(dev)
            self.add_i2c_device(dev)
        self._i2c_io_devices = []
        for i in range(0, 2):
            dev = PCF8574(bus_id, self._module_data[f"addr_pcf8574_{i}"])
            self._i2c_io_devices.append(dev)
            self.add_i2c_device(dev)
        self._i2c_pwr_devices = []
        for i in range(0, 2):
            dev = INA219(bus_id, self._module_data[f"addr_ina219_{i}"],
                i_max=self._module_data[f"imax_ina219_{i}"],
                r_shunt=self._module_data[f"rshunt_ina219_{i}"],
            )
            self._i2c_pwr_devices.append(dev)
            self.add_i2c_device(dev)
        dev = PCA9634(bus_id, self._module_data["addr_pca9634"])
        self._i2c_pwr_device = dev
        self.add_i2c_device(dev)

    def get_capabilities(self):
        capabilities = {}
        for num in range(0, 16):
            capabilities[f"io{num}"] = {
                "type": "pin",
                "num": num,
                "access": "rw",
                "device_map": (num // 8, num % 8),
            }
        for num in range(0, 2):
            capabilities[f"port{num}"] = {
                "type": "port",
                "num": num,
                "access": "rw",
                "device_map": (num // 2, ),
            }
        for num in range(0, 8):
            capabilities[f"aout{num}"] = {
                "type": "analog",
                "num": num,
                "access": "w",
                "device_map": (0, num),
            }
            capabilities[f"pwm{num}"] = {
                "type": "pwm",
                "num": num,
                "access": "w",
                "device_map": (0, num),
            }

        for num in range(0, 2):
            capabilities[f"pwri{num}"] = {
                "type": "analog",
                "num": num,
                "access": "r",
                "device_map": (self._ANALOG_PWR, num, 2),
            }
            capabilities[f"pwrp{num}"] = {
                "type": "analog",
                "num": num,
                "access": "r",
                "device_map": (self._ANALOG_PWR, num, 1),
            }
            capabilities[f"pwrv{num}"] = {
                "type": "analog",
                "num": num,
                "access": "r",
                "device_map": (self._ANALOG_PWR, num, 0),
            }

        for num in range(0, 16):
            capabilities[f"ain{num // 4}_{num % 4}"] = {
                "type": "analog",
                "num": num,
                "access": "r",
                "device_map": (self._ANALOG_IN, num // 4, ADS1115.MUX_AIN_0 + num % 4, num % 4, num % 4),
            }
        for num in range(0, 4):
            capabilities[f"ain{num}_0_1"] = {
                "type": "analog",
                "num": num,
                "access": "r",
                "device_map": (self._ANALOG_IN, num, ADS1115.MUX_AIN_0_1, 0, 1),
            }
            capabilities[f"ain{num}_0_3"] = {
                "type": "analog",
                "num": num,
                "access": "r",
                "device_map": (self._ANALOG_IN, num, ADS1115.MUX_AIN_0_3, 0, 3),
            }
            capabilities[f"ain{num}_1_3"] = {
                "type": "analog",
                "num": num,
                "access": "r",
                "device_map": (self._ANALOG_IN, num, ADS1115.MUX_AIN_1_3, 1, 3),
            }
            capabilities[f"ain{num}_2_3"] = {
                "type": "analog",
                "num": num,
                "access": "r",
                "device_map": (self._ANALOG_IN, num, ADS1115.MUX_AIN_2_3, 2, 3),
            }

        return capabilities

    def get_configuration(self):
        configuration = {}
        if self._toggle_pin_capability_id:
            configuration["toggle_bus"] = {
                "capability_id": self._toggle_pin_capability_id,
                "dir": "out",
                "init": 0,
            }
        configuration["i2c"] = {
            "capability_id": self._storage.bus_id,
        }
        if self._storage.controller:
            configuration["i2c"]["controller"] = storage.controller

        return configuration

    def toggle_i2c_bus(self, i2c_device, enable: bool):
        if self._toggle_pin_capability_id:
            self.rig.write_pin("toggle_bus", enable)

    def configure(self, configuration):
        super().configure(configuration)   # resolve "static" devices, i.e. i2c
        self._read_module_configuration()
        super().configure(configuration)  # resolve new devices

