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
from ..devices.i2c_memory import *
import logging
import time
import datetime

## @package module_memory
# On board memory abstraction

"""
class ModuleMemoryMap:
    def __init__:
        pass
"""

class ModuleMemoryMixin(StorageMixin):

    # EEPROM 256 bytes
    HEADER_ADDR: Final = 0
    HEADER_SIZE: Final = 128
    CUSTOM_ADDR: Final = HEADER_SIZE
    CUSTOM_SIZE: Final = 128

    MAGIC: Final = 0xAA55

    # (name, type: [string, STRING, datetime, int...signed, number], size, descr, [default value, [options]] )
    HEADER_MAP: Final = [
        (None, "number", 2, "Magic", MAGIC),
        (None, None, 6, "Reserved"),
        ("system_id", "STRING", 8, "System id", "TSTBENCH"),
        ("adapter_id", "STRING", 8, "Adapter id used to identify plugged-in adapter", None, lambda: [cls.ID for cls in registered_boards]),
        ("board_id", "STRING", 8, "Board id", "RPIBEN"),
        ("version", "number", 2, "Board version in decimal form 'xxyy' corresponding to xx.yy"), # no default value not to overwrite easily value
        ("serial_number", "number", 8, "Unique serial number"), # dtto
        ("human_name", "string", 16, "Human readable board name, e.g. Digie35", "Digie35"),
        ("manufacturer", "string", 8, "Manufacturer name", "2P"),
        ("pcb_by", "string", 3, "PCB manufacturer nick"),
        ("pcb_stamp", "number", 2, "PCB stamp ('YY9WW' or 'YYDDD')"),
        ("pcba_smd_by", "string", 3, "PCBA SMD by nick"),
        ("pcba_smd_stamp", "number", 2, "PCBA SMD stamp ('YY9WW' or 'YYDDD')"),
        ("pcba_tht_by", "string", 3, "PCBA SMD by nick"),
        ("pcba_tht_stamp", "number", 2, "PCBA SMD stamp ('YY9WW' or 'YYDDD')"),
        ("tested1_by", "string", 3, "Tested phase 1 by nick"),
        ("tested1_stamp", "number", 2, "Tested phase 1 stamp ('YY9WW' or 'YYDDD')"),
        ("tested2_by", "string", 3, "Tested phase 2 by nick"),
        ("tested2_stamp", "number", 2, "Tested phase 2 stamp ('YY9WW' or 'YYDDD')"),
        #("dt_param", "datetime", 8, "Datetime example"),
    ]

    CUSTOM_MAP  = []

    def get_version(self):
        return self.read_number(32, 2)

    def get_id_version(self):
        w = self.read_number(0, 2)
        if w == self.MAGIC:
            adapter_id = self.read_string(16, 8)
            version = self.get_version()
            #logging.getLogger().debug("adapter_id: %s, ver: %s", (adapter_id, version))
            if adapter_id == None or version == None:
                return None
            return (adapter_id, version)
        else:
            return None

    def reset(self, addr, len):
        arr = []
        for i in range(0, len):
            arr.append(0xFF)
        self.write_array(addr, arr)

    def erase(self):
        self.reset(self.HEADER_ADDR, self.HEADER_SIZE)
        self.reset(self.CUSTOM_ADDR, self.CUSTOM_SIZE)

    def read_data(self, addr, map):
        res  = {}
        for item in map:
            if item[0] != None:
                if item[1].upper() == "STRING":
                    res[item[0]] = self.read_string(addr, item[2])
                elif item[1] == "int":
                    res[item[0]] = self.read_number(addr, item[2], True)
                elif item[1] == "number":
                    res[item[0]] = self.read_number(addr, item[2])
                elif item[1] == "datetime":
                    res[item[0]] = self.read_datetime(addr)
            addr += item[2]
        return res

    def write_data(self, addr, map, data):
        for item in map:
            if item[0] != None and item[0] in data:
                if item[1] == "STRING":
                    self.write_string(addr, data[item[0]].upper(), item[2])
                elif item[1] == "string":
                    self.write_string(addr, data[item[0]], item[2])
                elif item[1] in ["int", "number"]:
                    self.write_number(addr, data[item[0]], item[2])
                elif item[1] == "datetime":
                    self.write_datetime(addr, data[item[0]])
            addr += item[2]

    def read_header(self):
        return self.read_data(self.HEADER_ADDR, self.HEADER_MAP)

    def write_header(self, hdr):
        self.write_number(0, self.MAGIC, self.HEADER_MAP[0][2])
        self.write_data(self.HEADER_ADDR, self.HEADER_MAP, hdr)

    def read_custom(self):
        return self.read_data(self.CUSTOM_ADDR, self.CUSTOM_MAP)

    def write_custom(self, data):
        return self.write_data(self.CUSTOM_ADDR, self.CUSTOM_MAP, data)

