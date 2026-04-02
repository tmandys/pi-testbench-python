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

#from __future__ import annotations

__author__ = "Tomas Mandys"
__copyright__ = "Copyright (C) 2026 MandySoft"
__licence__ = "Apache 2.0"
__version__ = "0.1"
from typing import Final
import logging
import time
import math
import datetime

from ..core import I2CDevice, TestbenchError

class StorageMixin:

    def _read_impl(self, addr: int, count: int):
        raise NotImplementedError(f"Class {self.__class__.__name__} does not implement _read_impl")

    def _write_impl(self, addr: int, data):
        raise NotImplementedError(f"Class {self.__class__.__name__} does not implement _write_impl")

    def read_number(self, addr: int, count: int, signed: bool = False):
        data = self.read_array(addr, count)
        res = 0
        for i in range(0, count):
            res += data[i] << (i * 8)
        if not signed and res == (1 << 8*count) - 1:
            # uninitialized value
            return None
        if signed and (res & (1<<(8*count-1))):
            res -= 1 << 8*count
        return res

    def write_number(self, addr: int, val: int, count: int):
        if val == None:
            val = 0
        data = []
        for i in range(0, count):
            data.append(val & 0xFF)
            val >>= 8
        self.write_array(addr, data)

    def read_array(self, addr: int, count: int):
        return self._read_impl(addr, count)

    def write_array(self, addr: int, data):
        self._write_impl(addr, data)

    def read_string(self, addr: int, max_len: int):
        ret = ""
        data = self.read_array(addr, max_len)
        if data[0] == 0xFF:
            # uninitialized value
            return None
        i = 0
        while i < len(data):
            if data[i] == 0:
                break
            ret += chr(data[i])
            i += 1
        return ret

    def write_string(self, addr: int, str: str, max_len: int):
        if str == None:
            str = ""
        data = []
        i = 0
        while i < len(str) and i < max_len:
            data.append(ord(str[i]))
            i += 1
        while i < max_len:
            data.append(0)
            i += 1
        self.write_array(addr, data)

    def read_datetime(self, addr: int, count: int = 6):
        arr = self.read_array(addr, count)
        dt = [2000, 1, 1, 0, 0, 0]
        valid = count >= 1
        if valid:
            for i in range(0, min(len(dt), count)):
                match i:
                    case 0:
                        valid = arr[i] < 40
                        arr[i] = dt[i] + arr[i]
                    case 1:
                        valid = arr[i] in range(1, 13)
                    case 2:
                        valid = arr[i] in range(1, 32)
                    case 3:
                        valid = arr[i] < 24
                    case 4:
                        valid = arr[i] < 60
                    case 5:
                        valid = arr[i] < 60

                if not valid:
                    break
                dt[i] = arr[i]
        if valid:
            return datetime.datetime(dt[0], dt[1], dt[2], dt[3], dt[4], dt[5])
        else:
            return None

    def write_datetime(self, addr: int, dt, count: int = 6):
        if dt != None:
            arr = [
                dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second
            ]
            if arr[0] < 2000:
                arr[0] = 0
            else:
                arr[0] = arr[0] - 2000
        else:
            arr = [0, 0, 0, 0, 0, 0]
        self.write_array(addr, arr[0:min(len(arr), count)])

class M24Cxx(I2CDevice, StorageMixin):
    def __init__(self, bus_id: str, addr: int, size: int, page_size: int = 8):
        super().__init__(bus_id, addr)
        print(f"M24Cxx({bus_id}, {addr:x}, {size}, {page_size})")
        if size not in [128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536]:
            raise ValueError(f"Wrong memory size")
        self._size = size
        self._page_size = page_size

    @property
    def size(self):
        return self._size

    def _get_i2c_addr(self, addr):
        match self.size:
            case 128 | 256:
                return (self.addr, [addr])
            case 512:
                return ((self.addr & ~0x1) | addr // 256, [addr % 256])
            case 1024:
                return ((self.addr & ~0x3) | addr // 256, [addr % 256])
            case 2048:
                return ((self.addr & ~0x8) | addr // 256, [addr % 256])
            case _:
                return (self.addr, [addr >> 8, addr & 0xFF])

    def _read_impl(self, addr: int, count: int):
        if addr + count > self._size:
            raise ValueError(f"Address overflow: {addr+count} > {self._size}")
        if self.size > 256 and self.size < 4096:
            result = []
            while count > 0:
                page_end = (addr & 0xFF00) + 256
                if page_end - addr >= count:
                    l = count
                else:
                    l = page_end - addr
                i2c_addr, addr2 = self._get_i2c_addr(addr)
                result += self.write_read(addr2, l, i2c_addr)
                addr += l
                count -= l
            return result
        else:
            i2c_addr, addr2 = self._get_i2c_addr(addr)
            return self.write_read(addr2, count, i2c_addr)

    def _write_impl(self, addr: int, data):
        count = len(data)
        if addr + count > self._size:
            raise ValueError(f"Address overflow: {addr+count} > {self._size}")
        i = 0
        while count > 0:
            i2c_addr = self.addr
            page_end = (addr & ~(self._page_size - 1)) + self._page_size
            if page_end - addr >= count:
                l = count
            else:
                l = page_end - addr
            i2c_addr, addr2 = self._get_i2c_addr(addr)
            #print(f"DEBUG: write i2c: {i2c_addr:#x}, addr: {addr}/{addr2}, page: {page_end}, l: {l}, i: {i}, data: {data[i:i+l]}")
            self.write_read(addr2 + data[i:i+l], 0, i2c_addr)
            addr += l
            i += l
            count -= l
            time.sleep(0.01)   # 5ms EEPROM write delay (otherwise check ACK)

    def erase(self):
        self.write_array(0, [0xFF] * self._size)
