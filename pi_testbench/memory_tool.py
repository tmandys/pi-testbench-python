#!/usr/bin/env python3

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
import logging
import time
import datetime
from timeit import default_timer
import sys
import argparse
import locale
import re
from pi_testbench.core import *
from pi_testbench.mainboards import rpi
from pi_testbench.devices import i2c_memory
from pi_testbench.modules import *

def add_arg_opts(arg_parser, options):
    prefix, group_name, mapping_class = options
    mem_map = mapping_class(None)
    res = []
    module_group = arg_parser.add_argument_group(group_name)
    for map in mem_map.mapping:
        name, type, size, help, default, enum, *_ = list(map) + [None] * 5
        if name is None:
            continue
        name = "--" + prefix + name
        name = name.replace('_', '-')
        if enum:
            choices = []
            opts = []
            if callable(enum):
                enum = enum()
            for opt in enum:
                if isinstance(enum, dict):
                    opts.append(f"{opt}..{enum['opt']}")
                else:
                    opts.append(str(opt))
                if type in ["number", "int"]:
                    choices.append(int(opt))
                else:
                    choices.append(str(opt))
            help += " (" + (", ".join(opts)) + ")"
        else:
            choices = None
        if default is not None:
            help += f", default: {default}"

        kwargs = {}
        if help:
            kwargs["help"] = help
        if not choices:
            kwargs["metavar"] = "VAL"
        match type:
            case "string":
                module_group.add_argument(name, **kwargs)
            case "STRING":
                module_group.add_argument(name, type=str.upper, **kwargs)
            case "datetime":
                module_group.add_argument(name, action="store_true", **kwargs)
            case "number" | "int":
                module_group.add_argument(name, type=int, **kwargs)

def process_map(args, memory_mapping, write_default, now):
    res = memory_mapping.get_defaults() if write_default else {}
    for map in memory_mapping.mapping:
        name, type, *_ = map
        if name is None:
            continue
        if hasattr(args, name):
            val = getattr(args, name)
            if type == "datetime":
                if val:
                    res[name] = now
            else:
                if val is not None:
                    res[name] = val
    return res

def main():
    locale.setlocale(locale.LC_ALL, 'C')
    arg_parser = argparse.ArgumentParser(
        #prog=,
        description="Testbench module memory config tool, v%s" % __version__,
        epilog='''\

Examples or args:
  universal test board
    -w --default --module-id UTB --version 104 --c-serial-number 123456789
''',
        formatter_class=argparse.RawTextHelpFormatter,
    )
    arg_group = arg_parser.add_argument_group("Memory parameters")
    arg_group.add_argument("-a", "--address", type=lambda x: int(x, 0), default=0x57, help=f"I2C address of memory, default: %(default)s")
    arg_group.add_argument("-t", "--toggle-pin", type=str, default="", help=f"Toggle pin name to enable I2C routing to module, default: %(default)s")
    arg_group.add_argument("-w", "--write", action="store_true", help=f"Write values")
    arg_group.add_argument("--erase", action="store_true", help=f"Erase all values first")
    arg_group.add_argument("--default", action="store_true", help=f"Write default values not specified as parameter")

    arg_group = arg_parser.add_argument_group("General parameters")
    arg_group.add_argument("--dry-run", action="store_true", help=f"Do not write physically anything")
    arg_group.add_argument("-v", "--verbose", action="count", default=0, help="Verbose output")
    arg_group.add_argument("-V", action="version", version=f"{__version__}")

    maps = {
        "": ("", "Common Module Parameters", CommonMemoryMap),
        UTBModule.ID: ("utb-", "UTB Parameters", UTBModuleMemoryMap),
    }

    for key, item in maps.items():
        add_arg_opts(arg_parser, item)

    args = arg_parser.parse_args()
    LOGGING_FORMAT = "%(asctime)s: %(name)s: %(levelname)s: %(message)s"
    logging.basicConfig(format=LOGGING_FORMAT)
    log = logging.getLogger()

    # logging.NOTSET logs everything
    verbose2level = (logging.CRITICAL, logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG)
    args.verbose = min(max(args.verbose, 0), len(verbose2level) - 1)
    log.setLevel(verbose2level[args.verbose])

    log.debug(f"Parsed args: {args}")

    rig = Rig()
    bus_id = 1
    mainboard = rpi.RpiMainboard()
    rig.assign_mainboard(mainboard)
    rig.configure({"i2c": {} })
    try:
        memory = i2c_memory.M24Cxx("i2c", args.address, 256)
        memory.assign_controller(mainboard, "i2c")

        log.debug(f"Bus_id: {memory.bus_id}, i2c_addr: {memory.addr}")
        module_id = args.module_id
        common_map = CommonMemoryMap(memory)
        old_common_data = common_map.read_data()
        if not module_id:
            module_id = old_common_data.get("module_id")
        module_map = maps[module_id][2](memory) if module_id and module_id in maps else None

        old_module_data = module_map.read_data() if module_map else None
        if not args.write:
            print(old_common_data)
            print(old_module_data)
            sys.exit()

        log.debug(f"Old common data: {old_common_data}")
        log.debug(f"Old module data: {old_module_data}")

        now = datetime.now()

        new_common_data = process_map(args, common_map, args.default, now)
        new_module_data = process_map(args, module_map, args.default, now) if module_map else None

        # test options related to another module. Args parser knows all
        unknown = []
        for key, map in maps.items():
            if key and key != module_id:
                for unknown_map in maps[key][2](None).mapping:
                    unknown_key = f"{map[0]}{unknown_map[0]}".replace("-", "_")
                    if hasattr(args, unknown_key) and getattr(args, unknown_key) is not None:
                        unknown.append(f"--{unknown_key.replace('_', '-')}")
        if unknown:
            print(f"Params non related to current module: {unknown}")
            sys.exit()

        if args.erase:
            log.debug("Erasing memory")
            if not args.dry_run:
                memory.erase()
            else:
                print("DRY RUN: erase memory")
        if not new_common_data and not new_module_data:
            log.debug("No data provided, skipping write")
            sys.exit()

        if new_common_data:
            log.debug(f"Writing new common data: {new_common_data}")
            if not args.dry_run:
                common_map.write_data(new_common_data)
            else:
                log.debug(f"Common data to be written: {new_common_data}")
        if new_module_data:
            log.debug(f"Writing new module data: {new_module_data}")
            if not args.dry_run:
                module_map.write_data(new_module_data)
            else:
                log.debug(f"Module data to be written: {new_module_data}")

        log.debug(f"Common: {common_map.read_data()}")
        if module_map:
            log.debug(f"Module data: {module_map.read_data()}")
    finally:
        pass


if __name__ == "__main__":
   main()
