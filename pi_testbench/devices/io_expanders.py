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

from ..core import I2CDevice, TestbenchError

class PCF857x(I2CDevice):
    def __init__(self, bus_id: str, addr: int, num_bytes: int):
        super().__init__(bus_id, addr)
        self._num_bytes = num_bytes
        self._last_state = 0

    @property
    def input_count(self):
        return self._num_bytes << 8

    def _setup_impl(self):
        self.set_outputs((1 << (self._num_bytes * 8)) - 1)

    def get_inputs(self) -> int:
        data = self.write_read([], self._num_bytes)
        return int.from_bytes(data, byteorder='little')

    def set_outputs(self, value: int):
        self.write_read(value.to_bytes(self._num_bytes, "little"), 0)
        self._last_state = value

    def get_pin(self, idx: int) -> bool:
        return bool(self.get_inputs() & (1 << idx))

    def set_pin(self, idx: int, level: bool):
        if level:
            new_state = self._last_state | (1 << idx)
        else:
            new_state = self._last_state & ~(1 << idx)
        self.set_outputs(new_state)

class PCF8574(PCF857x):
    def __init__(self, bus_id: str, addr: int):
        super().__init__(bus_id, addr, 1)

class PCF8575(PCF857x):
    def __init__(self, bus_id: str, addr: int):
        super().__init__(bus_id, addr, 2)

