from __future__ import annotations

import ctypes
import hmac
import json
import logging
import os
import socket
import subprocess
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional

from .config import Config
from .metrics import build_snapshot, connect_read_only


LOGGER = logging.getLogger("cc_usage_display")


def lan_addresses() -> list[str]:
    addresses: set[str] = set()
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect(("8.8.8.8", 80))
            addresses.add(probe.getsockname()[0])
        finally:
            probe.close()
    except OSError:
        pass

    try:
        for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            address = item[4][0]
            if not address.startswith("127."):
                addresses.add(address)
    except OSError:
        pass

    return sorted(addresses)


def focus_cc_switch(exe: Optional[str]) -> bool:
    if sys.platform == "darwin":
        # `open -a` both launches and activates an application, so it works
        # whether CC Switch is already running or still closed.
        app = exe if exe and Path(exe).is_dir() else "CC Switch"
        try:
            subprocess.run(
                ["open", "-a", app],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except (OSError, subprocess.CalledProcessError) as error:
            LOGGER.warning("Could not open CC Switch on macOS: %s", error)
            return False

    if sys.platform != "win32":
        return False

    if _focus_existing_window():
        return True
    if not exe:
        return False

    path = Path(exe)
    if not path.exists():
        return False
    try:
        subprocess.Popen(
            [str(path)],
            cwd=str(path.parent),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        return True
    except OSError as error:
        LOGGER.warning("Could not launch CC Switch: %s", error)
        return False


def _focus_existing_window() -> bool:
    try:
        user32 = ctypes.windll.user32
    except AttributeError:
        return False

    handles: list[int] = []
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def callback(hwnd, _lparam):
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        if "CC Switch" in buffer.value or "CC-Switch" in buffer.value:
            handles.append(int(hwnd))
        return True

    user32.EnumWindows(callback_type(callback), 0)
    for hwnd in handles:
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        if user32.SetForegroundWindow(hwnd):
            return True
    return False


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "CCUsageDisplay/0.1"
    config: Config

    def _authorized(self) -> bool:
        if not self.config.token:
            return True
        supplied = self.headers.get("Authorization", "")
        expected = f"Bearer {self.config.token}"
        return hmac.compare_digest(supplied, expected)

    def _send_json(self, status: HTTPStatus, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send_json(
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "refresh_seconds": self.config.refresh_seconds,
                },
            )
            return

        if self.path.split("?", 1)[0] != "/api/usage":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        if not self._authorized():
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return

        try:
            conn = connect_read_only(self.config.db_path)
            try:
                snapshot = build_snapshot(conn, usd_to_cny=self.config.usd_to_cny)
            finally:
                conn.close()
        except Exception as error:  # noqa: BLE001 - surfaced to the device log
            LOGGER.exception("Failed to read CC Switch usage")
            self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": str(error)})
            return

        self._send_json(HTTPStatus.OK, snapshot.payload())

    def do_POST(self) -> None:  # noqa: N802
        if not self._authorized():
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return

        path = self.path.split("?", 1)[0]
        if path == "/api/action/refresh":
            self._send_json(HTTPStatus.OK, {"ok": True, "message": "refreshed"})
            return
        if path == "/api/action/focus":
            ok = focus_cc_switch(self.config.cc_switch_exe)
            self._send_json(
                HTTPStatus.OK if ok else HTTPStatus.SERVICE_UNAVAILABLE,
                {"ok": ok, "message": "focused" if ok else "could not focus"},
            )
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def log_message(self, fmt: str, *args) -> None:
        LOGGER.info("%s - %s", self.address_string(), fmt % args)


class DashboardServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def serve(config: Config) -> None:
    handler = type("ConfiguredDashboardHandler", (DashboardHandler,), {"config": config})
    server = DashboardServer((config.host, config.port), handler)
    LOGGER.info("CC Switch DB: %s", config.db_path)
    LOGGER.info("Companion token: %s", config.token)
    LOGGER.info("Listening on %s:%d", config.host, config.port)
    for address in lan_addresses():
        LOGGER.info("Device URL: http://%s:%d/api/usage", address, config.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        LOGGER.info("Stopping companion")
    finally:
        server.server_close()
