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

class INA219(I2CDevice):
    BRNG_16V: Final = 0
    BRNG_32V: Final = 1
    PG_0: Final = 0
    PG_2: Final = 1
    PG_4: Final = 2
    PG_8: Final = 3
    ADC_9BIT: Final = 0
    ADC_10BIT: Final = 1
    ADC_11BIT: Final = 2
    ADC_12BIT: Final = 3
    ADC_1S: Final = 0x8
    ADC_2S: Final = 0x9
    ADC_4S: Final = 0xA
    ADC_8S: Final = 0xB
    ADC_16S: Final = 0xC
    ADC_32S: Final = 0xD
    ADC_64S: Final = 0xE
    ADC_128S: Final = 0xF
    MODE_PD: Final = 0
    MODE_SHUNT_TRIGGER: Final = 1
    MODE_BUS_TRIGGER: Final = 2
    MODE_SHUNT_BUS_TRIGGER: Final = 3
    MODE_ADC_OFF: Final = 4
    MODE_SHUNT_CONT: Final = 5
    MODE_BUS_CONT: Final = 6
    MODE_SHUNT_BUS_CONT: Final = 7

    _PA_CONFIG: Final = 0x00
    _PA_SHUNT_V: Final = 0x01
    _PA_BUS_V: Final = 0x02
    _PA_POWER: Final = 0x03
    _PA_CURRENT: Final = 0x04
    _PA_CALIBRATION: Final = 0x05

    def __init__(self, bus_id: str, addr: int,
            i_max: float,
            r_shunt: float,
            brng: int = BRNG_32V,
            pg: int = PG_8,
            badc: int = ADC_12BIT,
            sadc: int = ADC_12BIT,
            mode: int = MODE_SHUNT_BUS_CONT):
        super().__init__(bus_id, addr)

        self._brng = brng & 1
        self._pg = pg & 0x3
        self._badc = badc & 0xf
        self._sadc = sadc & 0xf
        self._mode = mode & 0x7
        if self._mode == self.MODE_ADC_OFF:
            self._mode = self.MODE_SHUNT_BUS_TRIGGER
        self._current_lsb = i_max / 32768.0
        self._calibration = int(0.04096 / (r_shunt * self._current_lsb))

    def _setup_impl(self) -> None:
        self._config = (self._brng << 13) | (self._pg << 11) | (self._badc << 7) | (self._sadc << 3)
        self._continuous = self._mode in [self.MODE_SHUNT_CONT, self.MODE_BUS_CONT, MODE_SHUNT_BUS_CONT]
        if self._continuous:
            self._config |= self._mode
        else:
            if self._mode != self.MODE_PD:
                self._config |= self.ADC_OFF
        self.write_reg16(self._PA_CONFIG, self._config)
        self.write_reg16(self._PA_CALIBRATION, self._calibration)

    def _reset_impl(self) -> None:
        self.write_reg16(self._PA_CONFIG, 0x8000)

    def measure(self) -> tuple:
        voltage = None
        power = None
        current = None
        if self._mode != self.MODE_PD:
            if not self._continuous:
                config = (self._config & 0xFFF8) | self._mode
                self.write_reg16(self._PA_CONFIG, config)
            start_time = time.monotonic()

            while True:
                val = self.read_reg16(self._PA_BUS_V)
                if val & 0x2:
                    if val & 0x1:
                        voltage = math.nan()
                        if self._mode in [self.MODE_SHUNT_BUS_CONT, self.MODE_SHUNT_BUS_TRIGGER]:
                            power = math.nan()
                    else:
                        if not self._mode in [self.MODE_SHUNT_CONT, self.MODE_SHUNT_TRIGGER]:
                            voltage = (val[0] << 6) | (val[1] >> 2)
                            voltage *= 0.004
                        if self._mode in [self.MODE_SHUNT_BUS_CONT, self.MODE_SHUNT_BUS_TRIGGER]:
                            val = self.read_reg16(self._PA_POWER)
                            power = (val[0] << 8 | val[1]) * 20 * self._current_lsb
                    break
                if (time.monotonic() - start_time) >  0.2:
                    TestbenchError(f"Cannot probe {self}")
                time.sleep(0.001)
            if not self._mode in [self.MODE_BUS_CONT, self.MODE_BUS_TRIGGER]:
                raw_current = self.read_reg16(self._PA_CURRENT)
                if raw_current > 32767:
                    raw_current -= 65536
                current *= self._current_lsb
        return (voltage, power, current)

