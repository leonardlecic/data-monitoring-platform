from types import SimpleNamespace

import pytest

from data_monitoring import windows_power


def test_keep_awake_restores_previous_state_after_interrupt(monkeypatch):
    requests = []
    previous_state = windows_power.ES_CONTINUOUS | 0x00000002

    def set_execution_state(flags):
        requests.append(flags)
        return previous_state

    kernel32 = SimpleNamespace(SetThreadExecutionState=set_execution_state)
    monkeypatch.setattr(windows_power, "ctypes", SimpleNamespace(
        windll=SimpleNamespace(kernel32=kernel32),
        c_uint32=windows_power.ctypes.c_uint32,
    ))
    monkeypatch.setattr(windows_power, "sys", SimpleNamespace(platform="win32"))

    with pytest.raises(KeyboardInterrupt), windows_power.keep_awake(True):
        assert requests == [windows_power.ES_CONTINUOUS | windows_power.ES_SYSTEM_REQUIRED]
        raise KeyboardInterrupt

    assert requests[-1] == previous_state
