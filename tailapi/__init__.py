#!/usr/bin/env python3
import rich.traceback as RichTraceback

RichTraceback.install(show_locals=True)

import hy

hy.macros.require(
    "tailapi.tailapi",
    # The Python equivalent of `(require tailapi.tailapi *)`
    None,
    assignments="ALL",
    prefix="",
)
hy.macros.require_reader("tailapi.tailapi", None, assignments="ALL")
from tailapi.tailapi import *

from addict import Dict

if __name__ == "__main__":
    main(obj=Dict())
