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

from ..core import *
import subprocess
import logging
from smbus2 import SMBus as SMBus2, i2c_msg
from rpi_hardware_pwm import HardwarePWM
import time
import re
from evdev import InputDevice, categorize, ecodes, list_devices
from abc import ABC, abstractmethod

#import datetime

## @package rpi
# Support for Raspberry Pi beyond GPIO


## Raspberry Pi 3/4/5 mainboard implementation
class RpiMainboard(Mainboard, ABC):

    def __init__(self, use_i2c):
        super().__init__()
        self._capabilities = None

        self._pwm = {}
        self._i2c_buses = {}
        self._is_rpi5 = False
        proc = subprocess.run(['cat', '/sys/firmware/devicetree/base/model'], capture_output=True)
        logging.getLogger().debug(f"Response: {proc}")
        if proc.stdout != None:
            proc.stdout = proc.stdout.decode("utf-8")
        if proc.stderr != None:
            proc.stderr = proc.stderr.decode("utf-8")
        if proc.returncode == 0:
            self._is_rpi5 = re.match("^Raspberry Pi 5", proc.stdout) != None
            logging.getLogger().debug(f"RPI5: {self._is_rpi5}")

    def __del__(self):
        super().__del__()

    @property
    def is_rpi5(self):
        return self._is_rpi5

    def get_aliases(self) -> list:
        return ["mainboard", "rpi", "rpi5" if self.is_rpi5 else "rpi4", ]

    def i2c_write_read(self, i2c_device: I2CDevice, out_data, in_count):
        # logging.getLogger().debug(f"{__name__}({i2c_device.addr:#X}, {out_data}, {in_count})")
        i2c_bus = self._i2c_buses.get(i2c_device.capability_id)
        if not bus:
            # lazy bus initialization
            i2c_bus = SMBus2(self.get_capabilities[i2c_device.capability_id]["num"])
            self._i2c_buses[i2c_device.capability_id] = i2c_bus

        if out_data != None and len(out_data) > 0:
            write = i2c_msg.write(i2c_addr, out_data)
        else:
            write = None
        if in_count > 0:
            read = i2c_msg.read(i2c_addr, in_count)
        else:
            read = None

        result = None
        if read != None and write != None:
            i2c_bus.i2c_rdwr(write, read) # combined read&write
            result = list(read)
        elif read != None:
            i2c_bus.i2c_rdwr(read)
            result = list(read)
        elif write != None:
            i2c_bus.i2c_rdwr(write)
        return result

    # --- Digital single
    def read_pin(self, id: str) -> bool:
        return self._read_gpio(self.capabilities[id]["num"])

    def write_pin(self, id: int, value: bool) -> None:
        self._write_gpio(self.get_capabilities[id]["num"], value)

    def set_pin_event_handler(self, num, edge, name = None, handler = None):
        raise NotImlementedErrror(self.self.NOT_IMPLEMENTED)


    ## RPi4 PWM frequency supported at least to 5MHz
    def write_pwm(self, id: str, duty_cycle: float, freq: float = None) -> None:
        channel = self.get_capabilities[id]["num"]
        duty_cycle2 = duty_cycle / 255 * 100
        logging.getLogger().debug(f"Set PWM({channel}, {duty_cycle2}, {freq}")
        if duty_cycle == 0:
            if str(channel) in self._pwm:
                self._pwm[str(channel)].stop()
                del self._pwm[str(channel)]
        else:
            if not str(channel) in self._pwm:
                if freq == None:
                    freq = 15555
                if self._is_rpi5:
                    chip_no = 2
                else:
                    chip_no = 0
                logging.getLogger().debug(f"HardwarePWM({channel}, {freq}, {chip_no}")
                self._pwm[str(channel)] = HardwarePWM(pwm_channel=channel, hz=freq, chip=chip_no)
            self._pwm[str(channel)].start(duty_cycle2)


    def _set_gpio_function(self, num, func):

        if self._is_rpi5:
            params = ['pinctrl']
        else:
            params = ['raspi-gpio']
        params.append('set')
        params.append(str(num))
        match func:
            case "i2c":
                if self._is_rpi5:
                    params.append("a3")
                else:
                    params.append("a0")
                #params.append("du")
            case "pwm":
                params.append("a0")
            case "gpio":
                return
            case _:
                raise TestbenchError(f"GPIO{num}: Unknown function type '{func}")
        logging.getLogger().debug(f"exec: {params}")
        subprocess.call(params, shell=False)

    # abstract to be implemented
    @abstractmethod
    def _set_gpio_as_input(self, num: int, pull_up_down: str): ...

    @abstractmethod
    def _set_gpio_event_handler(self, num: int, edge, name = None, handler = None): ...

    @abstractmethod
    def _set_gpio_as_output(self, num: int, init: bool): ...

    @abstractmethod
    def _read_gpio(self, num: int) -> bool: ...

    @abstractmethod
    def _write_gpio(self, num, val: bool): ...

    def on_pin_change(self, source):
        pass

    def get_capabilities(self) -> dict:
        capabilities = {}
        for num in range(0, 28):
            capabilities[f"gpio{num}"] = {
                "type": "pin",
                "num": num,
                "options": {
                    "dir": ["in", "out", "i", "o", "input", "output",],
                    "mode": ["up", "down", "floating", ],
                    "trigger": ["falling", "raising", "both"],
                    "init": [0, 1],
                }
            }
        for num in range(0, 2):
            capabilities[f"pwm{num}"] = {
                "type": "pwm",
                "num": num,
                "gpio": 12 + num,
            }
        capabilities |= {
            "i2c": {
                "type": "i2c",
                "num": 1,
            },
            "i2c_scl": {
                "type": "i2c",
                "gpio": 3,
            },
            "i2c_sda": {
                "type": "i2c",
                "gpio": 2,
            },
        }
        return capabilities

    def configure(self, configuration):
        # items should be ok as were tested in rig
        self.check_configuration()
        for name, cfg in configuration.items():
            cap = self.get_capabilities()[cfg["capability_id"]]

            item = self._io_map[name]
            self._set_gpio_function(cap["num"], cap["type"])
            match cap["type"]:
                case "gpio":
                    if cfg.get("dir", "i")[0] == "i":
                        match cfg.get("mode", None):
                            case "up":
                                put = True
                            case "down":
                                pud = False
                            case _:
                                pud = None
                        self._set_gpio_as_input(cap["num"], pud)
                        if cfg.get("trigger"):
                            logging.getLogger().debug(f"GPIO event callback: {cap['num']}({cfg['trigger']})")
                            if "handler" in cfg:
                                self._set_gpio_event_handler(cap["num"], cfg["trigger"], name, cfg["handler"])
                            else:
                                self._set_gpio_event_handler(cap["num"], cfg["trigger"], name)
                    else:
                        self._set_gpio_as_output(cap["num"], cfg.get("init", 0))
                case "pwm":
                    self.set_pwm(item["num"], 0)
                    self._pwm_state[name] = 0
                case "i2c":
                    pass

