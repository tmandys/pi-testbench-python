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

class NXPPWMDriver(I2CDevice):
    def __init__(self, bus_id: str, addr: int, channels: int):
        super().__init__( bus_id, addr)
        self._channels = channels


    def _write_to_driver(self, pa: int, data: list):
        buf = [0x80 | pa] + data
        logging.getLogger().debug(f"NXPPWM ({self.addr:#x}) write: {buf}")
        self.write_read(buf, 0)

class PCA9634(NXPPWMDriver):

    _PA_MODE1: Final = 0x00
    _PA_MODE2: Final = 0x01
    _PA_PWM0: Final = 0x02
    _PA_PWM1: Final = 0x03
    _PA_PWM2: Final = 0x04
    _PA_PWM3: Final = 0x05
    _PA_PWM4: Final = 0x06
    _PA_PWM5: Final = 0x07
    _PA_PWM6: Final = 0x08
    _PA_PWM7: Final = 0x09
    _PA_GRPPWM: Final = 0x0A
    _PA_GRPFREQ: Final = 0x0B
    _PA_LEDOUT0: Final = 0x0C
    _PA_LEDOUT1: Final = 0x0D
    _PA_SUBADDR1: Final = 0x0E
    _PA_SUBADDR2: Final = 0x0F
    _PA_SUBADDR3: Final = 0x10
    _PA_ALLCALLADDR: Final = 0x11

    def __init__(self, bus_id: str, addr: int):
        super().__init__(bus_id, addr, channels=8)

    def _setup_impl(self):
        data = [
            0, # MODE1
            0b00010101, # MODE2 Mode register 2    (totem, /oe..hi-Z)
            0, 0, 0, 0, 0, 0, 0, 0, # PWM brightness 0-7
            0xFF, # GRPPWM group duty cycle control
            0xFF, # GRPFREQ group frequency (not used)
            0x0, # LEDOUT0 LED output state 0
            0x0, # LEDOUT1 LED output state 1
        ]
        self._regs = data
        self._write_to_driver(self._PA_MODE1, data)

    def set_pwm(self, channel, val):
        if channel >= self._channels or channel < 0:
            TestbenchError(f"Channel {channel} of range 0..{self._channels-1}")
        val = max(min(val, 255), 0)
        self._write_to_driver(self._PA_PWM0 + channel, [val])
        self._regs[self._PA_PWM0 + channel] = val
        addr = self._PA_LEDOUT0 + channel // 4
        shift = channel % 4
        out = (self._regs[addr] & ~(0b11 << shift)) | (0b01 << shift)
        self._write_to_driver(addr, [out])
        self._regs[addr] = out

