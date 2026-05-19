"""SSH client for RunPod pipeline execution (ADR 002)."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from dataclasses import dataclass

import paramiko

logger = logging.getLogger(__name__)


@dataclass
class SSHConfig:
    host: str
    port: int = 22
    username: str = "root"
    private_key_path: str | None = None


class SSHSession:
    """Minimal SSH session for remote command execution with log streaming."""

    def __init__(self, config: SSHConfig):
        self.config = config
        self._client: paramiko.SSHClient | None = None

    def connect(self) -> None:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        kwargs: dict = {
            "hostname": self.config.host,
            "port": self.config.port,
            "username": self.config.username,
        }
        if self.config.private_key_path:
            kwargs["key_filename"] = self.config.private_key_path
        client.connect(**kwargs)
        self._client = client
        logger.info("ssh_connected host=%s", self.config.host)

    def disconnect(self) -> None:
        if self._client:
            self._client.close()
            self._client = None

    def run(
        self,
        command: str,
        on_line: Callable[[str], None] | None = None,
    ) -> tuple[int, str, str]:
        if not self._client:
            raise RuntimeError("SSH not connected")
        stdin, stdout, stderr = self._client.exec_command(command)
        del stdin
        out_lines: list[str] = []
        err_lines: list[str] = []
        for line in stdout:
            text = line if isinstance(line, str) else line.decode("utf-8", errors="replace")
            out_lines.append(text.rstrip("\n"))
            if on_line:
                on_line(text.rstrip("\n"))
        for line in stderr:
            text = line if isinstance(line, str) else line.decode("utf-8", errors="replace")
            err_lines.append(text.rstrip("\n"))
            if on_line:
                on_line(f"[stderr] {text.rstrip()}")
        code = stdout.channel.recv_exit_status()
        return code, "\n".join(out_lines), "\n".join(err_lines)

    def __enter__(self) -> SSHSession:
        self.connect()
        return self

    def __exit__(self, *args) -> None:
        self.disconnect()


def stream_command(session: SSHSession, command: str) -> Iterator[str]:
    """Yield stdout lines from a remote command."""
    lines: list[str] = []

    def capture(line: str) -> None:
        lines.append(line)

    code, _, _ = session.run(command, on_line=capture)
    yield from lines
    if code != 0:
        raise RuntimeError(f"Remote command failed with exit {code}")
