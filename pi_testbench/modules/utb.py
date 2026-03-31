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
            ("addr_pca9634", "int", 1, "PCA9634 I2C address", 0x4F),
            ("addr_pcf8574_0", "int", 1, "PCF8574 #0 I2C address", 0x27),
            ("addr_pcf8574_1", "int", 1, "PCF8574 #1 I2C address", 0x26),
            ("addr_ina219_0", "int", 1, "INA219 #0 I2C address", 0x47),
            ("addr_ina219_1", "int", 1, "INA219 #1 I2C address", 0x46),
            ("addr_ads1115_0", "int", 1, "ADS1115 #0 I2C address", 0x48),
            ("addr_ads1115_1", "int", 1, "ADS1115 #1 I2C address", 0x49),
            ("addr_ads1115_2", "int", 1, "ADS1115 #2 I2C address", 0x4A),
            ("addr_ads1115_3", "int", 1, "ADS1115 #3 I2C address", 0x4B),
            ("imax_ina219_0", "int", 4, "INA219 #0 Imax[mA]", 2000),
            ("imax_ina219_1", "int", 4, "INA219 #1 Imax[mA]", 2000),
            ("rshunt_ina219_0", "number", 4, "INA219 #0 R shunt [mOhm]", 20),
            ("rshunt_ina219_1", "number", 4, "INA219 #1 R shunt [mOhm]", 20),
            ("addr_ina219_1", "int", 1, "INA219 #1 I2C address", 0x46),
            #("toggle_pin", "string", 8, "I2C bus toggle pin", ""),
        ])

class UTBModule(Module):
    ID = "UTB"
    MODULE_MEMORY_CLASS = UTBModuleMemoryMap
    def __init__(self, storage, toggle_pin=None):
        super().__init__()
        self._storage = storage
        self._module_memory = self.MODULE_MEMORY_CLASS(storage)
        self._toggle_pin_capability_id = toggle_pin
        self._module_data = None
        self.add_i2c_device(storage)

    def _read_module_configuration(self):
        # TODO: we need initialized bus
        self._module_data = self._module_memory.read_data()
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
        self._i2c_pwr_devices = []
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
            }
        for num in range(0, 8):
            capabilities[f"aout{num}"] = {
                "type": "analog",
                "num": num,
                "access": "w",
            }
            capabilities[f"pwm{num}"] = {
                "type": "pwm",
                "num": num,
                "access": "w",
            }

        for num in range(0, 2):
            capabilities[f"pwri{num}"] = {
                "type": "analog",
                "num": num,
                "access": "r",
            }
            capabilities[f"pwrp{num}"] = {
                "type": "analog",
                "num": num,
                "access": "r",
            }
            capabilities[f"pwrv{num}"] = {
                "type": "analog",
                "num": num,
                "access": "r",
            }

        for num in range(0, 16):
            capabilities[f"ain{num}"] = {
                "type": "analog",
                "num": "num",
                "access": "r",
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
        super().configure(configuration)
        self._read_module_configuration()

