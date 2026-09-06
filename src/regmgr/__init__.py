"""Simplified wrapper for the Python winreg module."""

__author__  = "kubinka0505"
__credits__ = __author__
__version__ = "1.0"
__date__    = "14th May 2023"

#-=-=-=-#

from .config import *
from .core import *
from .path import *
from .utils import *

#-=-=-=-#

import os

if not os.sys.platform.lower().startswith("win"):
    raise exceptions.setup.WRONG_OS

DEBUG_ENVIRONMENT_NAME = "PYTHON_REGISTRY_UAC"

import ctypes
from warnings import warn

if (
    not ctypes.windll.shell32.IsUserAnAdmin()
    and DEBUG_ENVIRONMENT_NAME.lower() not in os.environ
):
    warn(exceptions.setup.NOT_ADMIN)

del warn, DEBUG_ENVIRONMENT_NAME