from __future__ import annotations

import ipaddress
import json
import os
import socket
from pathlib import Path
from typing import Any


def install() -> None:
    """Allow loopback only and record every child-process socket connection."""

    audit_path = os.getenv("HERMES_R4_NETWORK_AUDIT")
    if not audit_path:
        return

    def record(event: dict[str, Any]) -> None:
        with Path(audit_path).open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(event, sort_keys=True) + "\n")

    record({"event": "guard_installed", "pid": os.getpid()})
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex

    def is_loopback(address: Any) -> bool:
        if not isinstance(address, tuple) or not address:
            return True
        host = str(address[0]).split("%", 1)[0]
        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            return False

    def check(address: Any) -> None:
        if not is_loopback(address):
            record({"event": "blocked_non_loopback", "pid": os.getpid()})
            raise OSError("Hermes R4 probe blocks non-loopback network connections")

    def guarded_connect(sock: socket.socket, address: Any):
        check(address)
        return original_connect(sock, address)

    def guarded_connect_ex(sock: socket.socket, address: Any):
        check(address)
        return original_connect_ex(sock, address)

    socket.socket.connect = guarded_connect
    socket.socket.connect_ex = guarded_connect_ex
