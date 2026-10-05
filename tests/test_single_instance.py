import socket
import threading

from desktop import acquire_lock, notify_existing, relaunch_command, serve_lock


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_lock_is_exclusive_and_released():
    port = free_port()
    first = acquire_lock(port)
    assert first is not None
    assert acquire_lock(port) is None
    first.close()
    again = acquire_lock(port)
    assert again is not None
    again.close()


def test_notify_calls_show_callback():
    port = free_port()
    lock = acquire_lock(port)
    shown = threading.Event()
    serve_lock(lock, shown.set)
    assert notify_existing(port) is True
    assert shown.wait(2)
    lock.close()


def test_lock_can_be_retaken_right_after_a_notification():
    port = free_port()
    lock = acquire_lock(port)
    shown = threading.Event()
    serve_lock(lock, shown.set)
    notify_existing(port)
    shown.wait(2)
    lock.close()
    retaken = acquire_lock(port)
    assert retaken is not None
    retaken.close()


def test_notify_without_instance_returns_false():
    assert notify_existing(free_port()) is False


def test_relaunch_command_from_sources_waits_for_lock():
    cmd = relaunch_command()
    assert cmd[-1] == "--wait-lock"
    assert cmd[1].endswith("desktop.py")
