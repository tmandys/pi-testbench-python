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

class ADS1115(I2CDevice):
    MUX_AIN_0_1 = 0x0
    MUX_AIN_0_3 = 0x1
    MUX_AIN_1_3 = 0x2
    MUX_AIN_2_3 = 0x3
    MUX_AIN_0 = 0x4
    MUX_AIN_1 = 0x5
    MUX_AIN_2 = 0x6
    MUX_AIN_3 = 0x7
    PG_6V144: Final = 0x0
    PG_4V096: Final = 0x1
    PG_2V048: Final = 0x2
    PG_1V024: Final = 0x3
    PG_0V512: Final = 0x4
    PG_0V256: Final = 0x5
    DR_8SPS: Final = 0x0
    DR_16SPS: Final = 0x1
    DR_32SPS: Final = 0x2
    DR_64SPS: Final = 0x3
    DR_128SPS: Final = 0x4
    DR_250SPS: Final = 0x5
    DR_475SPS: Final = 0x6
    DR_860SPS: Final = 0x7
    COMP_DISABLE: Final = 0x00
    COMP_QUEUE_1: Final = 0x01
    COMP_QUEUE_2: Final = 0x02
    COMP_QUEUE_4: Final = 0x03
    COMP_QUEUE_MASK: Final = 0x03
    COMP_MODE_TRAD: Final = 0x0
    COMP_MODE_WINDOW: Final = 0x4
    COMP_POLARITY_LOW: Final = 0x0
    COMP_POLARITY_HIGH: Final = 0x8
    COMP_LATCH_DISABLE: Final = 0x0
    COMP_LATCH_ENABLE: Final = 0x10
    COMP_QUEUE_DISABLE: Final = 0x0

    _PA_CONVERSION: Final = 0x00
    _PA_CONFIG: Final = 0x01
    _PA_LO_THRESH: Final = 0x02
    _PA_HI_THRESH: Final = 0x03

    def __init__(self, bus_id: str, addr: int):
        super().__init__(bus_id, addr)

    def _setup_impl(self) -> None:
        self._set_config(self._get_config())

    def _get_config(self, trigger: bool = False, mux: int = MUX_AIN_0_1, pg: int = PG_6V144, continuous: bool = False,
            dr: int = DR_128SPS, comp: int = 0):
        config = ((mux & 0x7) << 12) | ((pg & 0x7) << 9) | ((dr & 0x7) << 5)
        if trigger:
            config |= 1 << 15
        if not continuous:
            config |= 1 << 8
        if comp & self.COMP_MODE_WINDOW:
            config |= 1 << 4
        if comp & self.COMP_POLARITY_HIGH:
            config |= 1 << 3
        if comp & self.COMP_LATCH_ENABLE:
            config |= 1 << 2
        config |= 0x3 if comp & self.COMP_QUEUE_MASK == 0 else (comp & self.COMP_QUEUE_MASK) - 1
        return config

    @property
    def current_config(self):
        self.setup()
        return self._current_config

    def _set_config(self, config: int):
        self.write_reg16(self._PA_CONFIG, config)
        match (config >> 9) & 0x7:
            case self.PG_6V144:
                self._lsb = 6.144
            case self.PG_4V096:
                self._lsb = 4.096
            case self.PG_2V048:
                self._lsb = 2.048
            case self.PG_1V024:
                self._lsb = 1.024
            case self.PG_0V512:
                self._lsb = 0.512
            case _:
                self._lsb = 0.256
        self._lsb /= 32768
        self._continuous = (config >> 8) & 1 == 0
        self._current_config = config

    def _reset_impl(self) -> None:
        self._set_config(self._get_config())
        self.write_reg16(self._PA_LO_THRESH, 0x8000)
        self.write_reg16(self._PA_HI_THRESH, 0x7FFF)

    def set_comparator(self, comp: int = None, lo_threshold: float = None, hi_threshold: float = None):
        if comp is not None:
            config = self.current_config & 0xFFE0
            config |= self._get_config(comp=comp) & 0x1F
            self._set_config(config)
        if lo_threshold is not None:
            val = int(lo_threshold / self._lsb)
            if val < 0:
                val += 65536
            self.write_reg16(self._PA_LO_THRESH, val)
        if hi_threshold is not None:
            val = int(hi_threshold / self._lsb)
            if val < 0:
                val += 65536
            self.write_reg16(self._PA_HI_THRESH, val)

    def set_mode(self, mux: int = MUX_AIN_0_1, pg: int = PG_6V144, continuous: bool = False, dr: int = DR_128SPS):
        config = self.current_config & 0x1F
        config |= self._get_config(mux=mux, pg=pg, continuous=continuous, dr=dr) & 0xFFE0
        self._set_config(config)

    def measure(self) -> float:
        if not self._continuous:
            self._set_config(self.current_config | 1<<15)
            start_time = time.monotonic()
            while True:
                config = self.read_reg16(self._PA_CONFIG)
                if config & 0x8000 == 0:
                    break
                if (time.monotonic() - start_time) >  0.2:
                    TestbenchError(f"Cannot probe {self}")
                time.sleep(0.001)
        val = self.read_reg16(self._PA_CONVERSION)
        if val > 32767:
            val -= 65536
        return val * self._lsb
