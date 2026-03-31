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

from __future__ import annotations

__author__ = "Tomas Mandys"
__copyright__ = "Copyright (C) 2026 MandySoft"
__licence__ = "Apache 2.0"
__version__ = "0.1"
from typing import final
from collections.abc import Callable
from threading import Thread, Event, Timer, Lock, RLock
from datetime import timedelta, datetime
from timeit import default_timer
import logging
import time
import re

## @package core
# Core library for Pi Testbench

## Periodic task triggered in specific timeout
class Job(Thread):
    def __init__(self, interval: int, execute: Callable, *args, **kwargs):
        Thread.__init__(self)
        self.daemon = False
        self._stopped = Event()
        self._interval = interval
        self._execute = execute
        self._args = args
        self._kwargs = kwargs
        self._state = 0

    def stop(self, join: bool=True):
        self._state = -1
        self._stopped.set()
        if join:
            try:
                self.join()
            except RuntimeError:
                pass

    def pause(self):
        if self._state == 0:
            self._state = 1
        self._stopped.set()

    def restart(self):
        if self._state == 1:
            self._state = 0
        self._stopped.set()

    def run(self):
        # logging.getLogger().debug(f"job interval: {self._interval} s, {1/self._interval.total_seconds() if self._interval.total_seconds() > 0 else 0} Hz")
        while self._state >= 0:
            while not self._stopped.wait(timeout=self._interval.total_seconds() if self._state <= 0 else None):
                new_interval = self._execute(*self._args, **self._kwargs)
                if new_interval != None and new_interval != self._interval:
                    self._interval = new_interval
                    # logging.getLogger().debug(f"job new interval: {self._interval} s, {1/self._interval.total_seconds() if self._interval.total_seconds() > 0 else 0} Hz")
            self._stopped.clear()

## Custom properties
class Properties:
    def __init__(self):
        self._values = {}

    @final
    def set(self, name: str, value):
        self._values[name] = value

    @final
    def get(self, name: str, default = None):
        return self._values.get(name, default)


## General error
class TestbenchError(Exception):
    __test__ = False  # skip in Pytest
    def __init__(self, message):
        super().__init__(message)


## I2C target/slave device
class I2CDevice:
    def __init__(self, bus_id: str, addr: int):
        self._initialized = None
        self._controller = None
        self._capability_id = None
        self._module = None
        self._bus_id = bus_id
        self._addr = addr

    @property
    def bus_id(self) -> str:
        return self._bus_id

    @property
    def addr(self) -> int:
        return self._addr

    @property
    def module(self):
        return self._module

    @property
    def controller(self):
        return self._controller

    @property
    def capability_id(self):
        return self._capability_id

    def _get_bus_lock(self):
        if not self.controller:
            raise TestbenchError(f"Controller not assgned in {self}")
        return self.controller.get_i2c_bus_lock(self.capability_id)

    def acquire_bus(self):
        self._get_bus_lock().acquire(self)

    def release_bus(self):
        self._get_bus_lock().release()

    def assign_controller(self, controller: IOControllerMixin, capability_id: str):
        if (controller != self._controller) | (self._capability_id != capability_id):
            self._initialized = None
            self._controller = controller
            self._capability_id = capability_id

    def assign_module(self, module: Module) -> None:
        if module != self._module:
            self._initialized = None
            save_module = self._module
            self._module = module
            if save_module:
                save_module.remove_i2c_device(self)
            if module:
                module.add_i2c_device(self)

    def __str__(self):
        class_name = self.__class__.__name__
        return f"{class_name}(bus_id: {self.bus_id}, addr: {self.addr:#X})"

    def __repr__(self):
        return self.__str__()

    @final
    def setup(self, force=False):
        #print(f"i2c.setup({force}, initialized: {self._initialized}")
        if force:
            self._initialized = None
        if self._initialized is not None:
            return
        if not self._controller:
            raise TestbenchError(f"Controller is not assigned {self}")
        if not self._module:
            raise TestbenchError(f"Module is not assigned {self}")
        self._initialized = False
        try:
            self.acquire_bus()
            try:
                self._setup_impl()
            finally:
                self.release_bus()
            self._initialized = True
        except Exception as ex:
            self._initialized = None
            raise ex

    @final
    def reset(self):
        if self._initialized is not None:
            try:
                self.acquire_bus()
                try:
                    self._reset_impl()
                finally:
                    self.release_bus()
            finally:
                self._initialized = None

    def _setup_impl(self):
        pass

    def _reset_impl(self):
        pass

    @final
    def write_read(self, out_data, in_count: int):
        self.acquire_bus()
        try:
            if self._initialized is None:
                # lazy setup
                self.setup()
            result = self._controller.i2c_write_read(self, out_data, in_count)
        finally:
            self.release_bus()
        return result

    @final
    def write_reg16(self, pa: int, value: int) -> None:
        value &= 0xFFFF
        self.write_read([pa & 0xFF, *value.to_bytes(2, byteorder="big")], 0)

    @final
    def read_reg16(self, pa: int) -> int:
        res = self.write_read([pa & 0xFF], 2)
        return res[0] << 8 | res[1]

### Extends recursive/reentrant lock to call a handler when lock is acquired/released
class I2CBusRLock:
    def __init__(self):
        self._real_lock = RLock()
        self._lock_level = 0

    def acquire(self, i2c_device, blocking=True, timeout=-1):
        result = self._real_lock.acquire(blocking, timeout)
        if result:
            if self._lock_level == 0:
                try:
                    self._i2c_device = i2c_device
                    self._first_lock_impl()
                except Exception as e:
                    self._real_lock.release()
                    raise e
            self._lock_level += 1
        return result

    def release(self):
        if self._lock_level > 0:
            self._lock_level -= 1
            if self._lock_level == 0:
                try:
                    self._final_unlock_impl()
                except Exception as e:
                    logging.error(f"Unlock callback function error {e}")
        self._real_lock.release()

    def _first_lock_impl(self):
        self._i2c_device.module.toggle_i2c_bus(self._i2c_device, True)

    def _final_unlock_impl(self):
        self._i2c_device.module.toggle_i2c_bus(self._i2c_device, False)

    # with lock:  is not implemented as we need pass i2c_device parameter
    #def __enter__(self):
    #    self.acquire()
    #    return self

    #def __exit__(self, exc_type, exc_val, exc_tb):
    #    self.release()

class IOControllerMixin:

    NOT_IMPLEMENTED = "Function is not implemented"

    def __init__(self, *args, **kwargs):
        self._i2c_buses = {}
        for key, capability in self.capabilities.items():
            if capability["type"] == "i2c":
                self._i2c_buses[key] = I2CBusRLock()   # recursive/reentrant lock

        super().__init__(*args, **kwargs)

    def get_i2c_bus_lock(self, id: str) -> I2CBusRLock:
        if id in self._i2c_buses:
            return self._i2c_buses[id]
        raise TestbenchError(f"I2C bus '{id}' not found")

    def i2c_write_read(self, i2c_device: I2CDevice, out_data, in_count):
        raise NotImlementedErrror(self.self.NOT_IMPLEMENTED)

    # --- Digital single
    def read_pin(self, id: str) -> bool:
        raise NotImlementedErrror(self.self.NOT_IMPLEMENTED)

    def write_pin(self, id: int, value: bool) -> None:
        raise NotImlementedErrror(self.self.NOT_IMPLEMENTED)

    def set_pin_event_handler(self, num, edge, name = None, handler = None):
        raise NotImlementedErrror(self.self.NOT_IMPLEMENTED)

    # --- Digital Group (Bulk) ---
    def read_port(self, id: str) -> int:
        raise NotImlementedErrror(self.self.NOT_IMPLEMENTED)

    def write_port(self, id: str, value: int) -> None:
        raise NotImlementedErrror(self.self.NOT_IMPLEMENTED)

    # --- Analog ---
    def read_analog(self, id: str) -> float:
        raise NotImlementedErrror(self.self.NOT_IMPLEMENTED)

    def write_analog(self, id: str, value: float) -> None:
        raise NotImlementedErrror(self.self.NOT_IMPLEMENTED)

    def write_pwm(self, id: str, duty_cycle: float, freq: float = None) -> None:
        raise NotImlementedErrror(self.self.NOT_IMPLEMENTED)

    ## Capabilities provided by entity
    ## {
    ##     "io1":
    ##          ....
    ##          "access": r/w/rw
    ##          "options": {
    ##              "mode": ["in", "out"]
    ##          },
    ## }
    def get_capabilities(self) -> dict:
        return {}

    @property
    def capabilities(self) -> dict:
        if not hasattr(self, "_capabilities"):
            self._capabilities = self.get_capabilities()
        return self._capabilities

    def get_aliases(self) -> list:
        return [self.__class__.__name__]

    def can_handle(self, controller_id: str, capability_id: str, as_type: str = None, access: str = None) -> bool:
        #print(f"can_handle({controller_id}, {capability_id}, {as_type})")
        if controller_id:
            if controller_id not in self.get_aliases():
                #print(f"not in aliases: {self.get_aliases()}")
                return False
        if capability_id not in self.capabilities:
            #print(f"not in caps: {list(self.capabilities)}")
            return False
        if as_type and as_type != self.capabilities[capability_id]["type"]:
            #print(f"not type: {as_type} != {self.capabilities[capability_id]}.type")
            return False
        if access and access not in self.capabilities.get("access", access):
            #print(f"not access: {access} != {self.capabilities[capability_id]}.access")
            return False
        #print(f"TRUE")
        return True

    def check_configuration(self, configuration: dict):
        invalid = []
        capability_cfg = {}
        collision = {}
        for key, cfg in configuration.items():
            if cfg.get("unused"):
                continue
            cap = self.capabilities[cfg["capability_id"]]
            capability_cfg.setdefault(cfg["capability_id"], {})[key] = cfg
            options = cap.get("options", {})
            for opt_id, opt_list in options.items():
                cfg_opt = cfg.get(opt_id)
                if cfg_opt is not None:
                    if cfg_opt not in opt_list:
                        invalid.append(f"{key}.{opt_id}: {cfg_opt}")
                    else:
                        collision.setdefault(f"{cfg['capability_id']}{opt_id}", {}).setdefault(cfg_opt, []).append(key)

        if invalid:
            raise TestbenchError(f"Unknown/wrong options: {invalid}")

        for cap_opt_id, vals in collision.items():
            coll = []
            if len(vals) > 1:
                for names in vals.values():
                    coll += names
                invalid.append(f"{cap_opt_id}: {coll}")
        if invalid:
            raise TestbenchError(f"Configuration collision: {invalid}")

    def configure(self, config: dict):
        pass


class Mainboard(IOControllerMixin):
    def __init__(self):
        super().__init__()

## Orchestrates mainboard and modules
class Rig:
    def __init__(self):
        self._mainboard = None

        self._modules = {}
        self._timers = {}

    def __del__(self):
        self._mainboard = None

    def close(self):
        # logging.getLogger().debug(f"{__name__}")
        for key in list(self._timers):
            self._cancel_timer(key)
        for module_name, module in self._modules.items():
            module.close()
        self._modules = None

    def assign_mainboard(self, mainboard: Mainboard):
        if self._mainboard != mainboard:
            self._mainboard = mainboard
            self.configure()

    def add_module(self, module: Module):
        if module.name in self._modules:
            if self._modules[module.name] != module:
                raise TestbenchError(f"Ambigious module name {module.name}")
        else:
            self._modules[module.name] = module
            module.assign_rig(self)
            self.configure()

    def remove_module(self, module: Module):
        if module.name in self._modules:
            module.close()
            del self._modules[module.name]
            module.assign_rig(None)
            self.configure()

    def configure(self):
        configuration = {}
        if self._mainboard:
            # merge configuration, prefix id by module name
            cfg_modules = {}
            cfg_modules[self._mainboard] = {}
            for module in self._modules.values():
                cfg_modules[module] = {}
            for module_name, module in self._modules.items():
                for key, cfg in module.configuration.items():
                    if cfg.get("unused", False):
                        continue
                    cfg = cfg.copy()

                    cfg.setdefault("capability_id", key)
                    configuration[(module_name, key)] = cfg
                    if module.can_handle(cfg.get("controller"), cfg["capability_id"]):
                        cfg["__controller__"] = module
                        cfg_modules[module][key] = cfg

            unknown = []
            #print(f"rig config: {configuration}, {self._mainboard.capabilities},{self._modules}")
            for key, cfg in configuration.items():
                if cfg.get("__controller__"):
                    continue
                if self._mainboard.can_handle(cfg.get("controller"), cfg["capability_id"]):
                    cfg["__controller__"] = self._mainboard
                    cfg_modules[self._mainboard][key[1]] = cfg
                    #print(f"canhandle: {cfg}, {cfg_modules}")
                    continue
                found = False
                for module_name, module in self._modules.items():
                    if module.can_handle(cfg.get("controller"), cfg["capability_id"]):
                        cfg["__controller__"] = module
                        cfg_modules[module][key[1]] = cfg
                        found = True
                        break
                if not found:
                    unknown.append(key)
            if unknown:
                raise TestbenchError(f"Cannot find target controller for {unknown}")

            self._configuration = configuration
            #print(f"{cfg_modules}")
            for module, cfg_module in cfg_modules.items():
                module.configure(cfg_module)
        self._configuration = configuration

    def _find_controller(self, name: str | tuple, type: str, access: str = None) -> tuple:
        #print(f"_find_controller: {name}, {type}, {access}")
        if not isinstance(name, tuple):
            parts = name.split(".", 1)
            if len(parts) > 1:
                name = tuple(parts)   # tuple
        if isinstance(name, tuple):
            cfg = self._configuration.get(name)
            if cfg and cfg["__controller__"].can_handle(cfg.get("controller"), cfg["capability_id"], type, access):
                return (cfg["__controller__"], cfg["capability_id"])
        else:
            for key, cfg in self._configuration.items():
                if key[1] == name:
                    if cfg["__controller__"].can_handle(cfg.get("controller"), cfg["capability_id"], type, access):
                        return (cfg["__controller__"], cfg["capability_id"])
            #print(f"configuration: {self._configuration}")
        raise TestbenchError(f"Cannot handle '{name}' as type '{type}'")


    def read_pin(self, name: str) -> bool:
        controller, id = self._find_controller(name, "pin", "r")
        return controller.read_pin(id)

    def write_pin(self, name: str, value: bool) -> None:
        controller, id = self._find_controller(name, "pin", "w")
        controller.write_pin(id, value)

    def read_port(self, name: str) -> int:
        controller, id= self._find_controller(name, "port", "r")
        return controller.read_port(id)

    def write_port(self, name: str, value: int) -> None:
        controller, id = self._find_controller(name, "port", "w")
        controller.write_port(id, value)

    def read_analog(self, name: str) -> float:
        controller, id= self._find_controller(name, "analog", "r")
        return controller.read_analog(id)

    def write_analog(self, name: str, value: float) -> None:
        controller, id = self._find_controller(name, "analog", "w")
        controller.write_analog(id, value)

    def write_pwm(self, name: string, duty_cycle: float, freq: float = None) -> None:
        controller, id  = self._find_controller(name, "pwm")
        controller.write_pwm(id, duty_cycle, freq)

    def _add_and_start_timer(self, name: str, timer):
        self._cancel_timer(name)
        self._timers[name] = timer
        self._timers[name].start()

    def _finalize_timer(self, name: str):
        if self._timers.__contains__(name):
            del self._timers[name]

    def _reset_timer(self, name: str):
        if self._timers.__contains__(name):
            self._timers[name].cancel()
            try:
                self._timers[name].join()
            except RuntimeError:
                pass
            self._timers[name].start()

    def _cancel_timer(self, name: str):
        if self._timers.__contains__(name):
            self._timers[name].cancel()
            try:
                self._timers[name].join()
            except RuntimeError:
                pass
            self._finalize_timer(name)

class Module(IOControllerMixin):
    _NAME = ""

    def __init__(self):
        super().__init__()
        self._i2c_devices = []
        self._rig = None

    def close(self):
        pass

    @property
    def name(self):
        return self._NAME if self._NAME else self.__class__.__name__

    def get_configuration(self) -> dict:
        return {}

    def assign_rig(self, rig) -> None:
        if self._rig != rig:
            save_rig = self._rig
            self._rig = rig
            if save_rig:
                save_rig.remove_module(self)
            if rig:
                rig.add_module(self)

    @property
    def configuration(self) -> dict:
        if not hasattr(self, "_configuration"):
            self._configuration = self.get_configuration()
        return self._configuration

    def add_i2c_device(self, i2c_device: I2CDevice) -> None:
        if i2c_device in self._i2c_devices:
            return
        self._i2c_devices.append(i2c_device)
        i2c_device.assign_module(self)

    def remove_i2c_device(self, i2c_device: I2CDevice):
        if i2c_device in self._i2c_devices:
            self._i2c_devices.remove(i2c_device)
            i2c_device.assign_module(None)

    def toggle_i2c_bus(self, i2c_device: I2CDevice, enabled: bool):
        pass

    def configure(self, configuration: dict):
        bus_ids = {}
        invalid = set()
        for i2c_device in self._i2c_devices:
            try:
                controller, capability_id = self._rig._find_controller(i2c_device.bus_id, "i2c")
            except TestbenchError:
                invalid.add(i2c_device.bus_id)
                continue
            i2c_device.assign_controller(controller, capability_id)
        if invalid:
            #print(f"module: {self.name}, configuration: {configuration}")
            raise TestbenchError(f"Unknown i2c bus: {invalid}")

