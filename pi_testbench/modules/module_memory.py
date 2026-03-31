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

class MemoryMap:
    def __init__(self, storage: StorageMixin, mapping: dict, offset: int, size: int = 0):
        self._storage = storage
        self._mapping = mapping
        self._offset = offset
        if size <= 0:
            size = 0
            for map in mapping:
                size += map[2]
        self._size = size

    @property
    def offset(self):
        return self._offset

    @property
    def size(self):
        return self._size

    @property
    def mapping(self):
        return self._mapping

    def erase(self, addr: int, len: int = 0):
        if len <= 0:
            len = self._size
        self.write_array(addr, [0xFF] * len)

    def read_data(self):
        res  = {}
        addr = self._offset
        for name, type, size, *_ in self._mapping:
            if name is not None:
                match type:
                    case "STRING" | "string":
                        res[name] = self._storage.read_string(addr, size)
                    case "int":
                        res[name] = self._storage.read_number(addr, size, True)
                    case "number":
                        res[name] = self._storage.read_number(addr, size)
                    case "datetime":
                        res[name] = self._storage.read_datetime(addr, size)
            addr += size
        return res

    def write_data(self, data):
        addr = self._offset
        for name, type, size, *_ in self._mapping:
            if name is not None and name in data:
                match type:
                    case "STRING":
                        self._storage.write_string(addr, data[name].upper(), size)
                    case "string":
                        self._storage.write_string(addr, data[name], size)
                    case "int" | "number":
                        self._storage.write_number(addr, data[name], size)
                    case "datetime":
                        self._storage.write_datetime(addr, data[name], size)
            addr += size

    def get_defaults(self):
        res = {}
        for map in self._mapping:
            if len(map) >= 5:
                name, type, size, descr, default, *_ = map
                if callable(default):
                    res[name] = default()
                else:
                    res[name] = default
        return res

class CommonMemoryMap(MemoryMap):
    _MAGIC: Final = 0xAA55
    SIZE = 128

    def default_stamp(self, stamp: datetime.datetime = datetime.datetime.now()):
        return stamp.strftime("%y%j")

    def __init__(self, storage):
        super().__init__(storage, [
                (None, "number", 2, "Magic", self._MAGIC),
                (None, None, 6, "Reserved"),
                ("system_id", "STRING", 8, "System id", "TSTBENCH"),
                ("module_id", "STRING", 8, "Module id used to identify board"), #None, lambda: [cls.ID for cls in registered_boards]),
                ("summodule_id", "STRING", 8, "Submodule id"),
                ("version", "number", 2, "Board version in decimal form 'xxyy' corresponding to xx.yy"), # no default value not to overwrite easily value
                ("serial_number", "number", 8, "Unique serial number"), # dtto
                ("human_name", "string", 16, "Human readable board name, e.g. MyBoard"),
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
            ], 0, self.SIZE)

    def is_valid(self):
        return self._storage.read_number(0, 2) == self._MAGIC

    def get_version(self):
        return self._storage.read_number(32, 2)

    def get_id_version(self):
        if self.is_valid():
            module_id = self._storage.read_string(16, 8)
            version = self.get_version()
            #logging.getLogger().debug("adapter_id: %s, ver: %s", (adapter_id, version))
            if module_id is None or version is None:
                return None
            return (module_id, version)
        else:
            return None

    def write_data(self, data):
        super().write_data(data)
        if not self.is_valid():
            self._storage.write_number(0, self._MAGIC, 2)

class ModuleMemoryMap(MemoryMap):
    def __init__(self, storage: StorageMixin, mapping: dict, size: int = 0):
        super().__init__(storage, mapping, CommonMemoryMap.SIZE, size if size > 0 else 128)

