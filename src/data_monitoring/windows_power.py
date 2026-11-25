"""Request that Windows keep the system awake while collection is running."""

import ctypes
import logging
import sys
from contextlib import contextmanager

logger = logging.getLogger(__name__)
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001


@contextmanager
def keep_awake(enabled: bool):
    if not enabled or sys.platform != "win32":
        yield
        return

    set_execution_state = ctypes.windll.kernel32.SetThreadExecutionState
    set_execution_state.argtypes = [ctypes.c_uint32]
    set_execution_state.restype = ctypes.c_uint32
    previous_state = set_execution_state(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
    if not previous_state:
        logger.warning("Windows did not accept the request to prevent idle sleep")
        yield
        return

    logger.info("Windows idle sleep prevention enabled for the Bajs collector")
    try:
        yield
    finally:
        set_execution_state(previous_state | ES_CONTINUOUS)
