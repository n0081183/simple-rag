"""SSH/SFTP client for RunPod pipeline (ADR 002)."""

from __future__ import annotations

import logging
import os
import re
import stat
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import paramiko

logger = logging.getLogger(__name__)

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")
# tqdm / huggingface progress bars (skip in UI log stream)
_PROGRESS_BAR = re.compile(r"(\d+%\|[\s█▏▎▍▌▋▊▉]+|it/s\]|\[A)")


@dataclass
class SSHConfig:
    host: str
    port: int = 22
    username: str = "root"
    private_key_path: str | None = None


def _clean_stream_text(text: str) -> str:
    text = _ANSI_ESCAPE.sub("", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.strip()


def _is_ui_log_line(text: str) -> bool:
    """Keep structured pipeline logs; drop tqdm/HF spinner one-liners."""
    if not text:
        return False
    if text.startswith("["):
        return True
    if _PROGRESS_BAR.search(text):
        return False
    if "|" in text and ("it/s" in text or "█" in text):
        return False
    return len(text) < 240


def _emit_log_line(text: str, lines: list[str], on_line: Callable[[str], None] | None, prefix: str) -> None:
    cleaned = _clean_stream_text(text)
    if not cleaned or not _is_ui_log_line(cleaned):
        return
    lines.append(cleaned)
    if on_line:
        on_line(f"{prefix}{cleaned}")


def _read_stream(
    stream,
    lines: list[str],
    on_line: Callable[[str], None] | None,
    prefix: str = "",
) -> None:
    """Read PTY output; split on \\n and \\r so tqdm/HF bars become separate or filtered lines."""
    buf = ""
    while True:
        chunk = stream.read(4096)
        if not chunk:
            break
        if isinstance(chunk, bytes):
            chunk = chunk.decode("utf-8", errors="replace")
        buf += chunk
        while True:
            idx_n = buf.find("\n")
            idx_r = buf.find("\r")
            if idx_n == -1 and idx_r == -1:
                break
            candidates = [i for i in (idx_n, idx_r) if i >= 0]
            idx = min(candidates)
            seg = buf[:idx]
            buf = buf[idx + 1 :]
            if seg:
                _emit_log_line(seg, lines, on_line, prefix)
    if buf.strip():
        _emit_log_line(buf, lines, on_line, prefix)


class SSHSession:
    """SSH session with streaming exec and SFTP."""

    def __init__(self, config: SSHConfig):
        self.config = config
        self._client: paramiko.SSHClient | None = None
        self._sftp: paramiko.SFTPClient | None = None

    def connect(self) -> None:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        kwargs: dict = {
            "hostname": self.config.host,
            "port": self.config.port,
            "username": self.config.username,
            "timeout": 30,
        }
        key_path = self.config.private_key_path or os.path.expanduser("~/.ssh/id_ed25519")
        if key_path and Path(key_path).is_file():
            kwargs["key_filename"] = key_path
        else:
            kwargs["allow_agent"] = True
            kwargs["look_for_keys"] = True
        client.connect(**kwargs)
        self._client = client
        self._sftp = client.open_sftp()
        logger.info("ssh_connected host=%s port=%s", self.config.host, self.config.port)

    def disconnect(self) -> None:
        if self._sftp:
            self._sftp.close()
            self._sftp = None
        if self._client:
            self._client.close()
            self._client = None

    @property
    def sftp(self) -> paramiko.SFTPClient:
        if not self._sftp:
            raise RuntimeError("SSH not connected")
        return self._sftp

    def run(
        self,
        command: str,
        on_line: Callable[[str], None] | None = None,
    ) -> tuple[int, str, str]:
        if not self._client:
            raise RuntimeError("SSH not connected")
        stdin, stdout, stderr = self._client.exec_command(command, get_pty=True)
        del stdin
        out_lines: list[str] = []
        err_lines: list[str] = []

        _read_stream(stdout, out_lines, on_line)
        _read_stream(stderr, err_lines, on_line, prefix="[stderr] ")
        code = stdout.channel.recv_exit_status()
        return code, "\n".join(out_lines), "\n".join(err_lines)

    def upload_file(self, local: Path, remote: str) -> None:
        remote_parent = str(Path(remote).parent)
        try:
            self.sftp.stat(remote_parent)
        except FileNotFoundError:
            self._mkdir_p(remote_parent)
        self.sftp.put(str(local), remote)

    def upload_tree(self, local_dir: Path, remote_dir: str) -> None:
        local_dir = local_dir.resolve()
        for root, dirs, files in os.walk(local_dir):
            rel = Path(root).relative_to(local_dir)
            remote_root = f"{remote_dir.rstrip('/')}/{rel}".replace("\\", "/")
            if str(rel) != ".":
                self._mkdir_p(remote_root)
            for f in files:
                local_f = Path(root) / f
                remote_f = f"{remote_root}/{f}".replace("//", "/")
                self.sftp.put(str(local_f), remote_f)

    def download_file(self, remote: str, local: Path, on_progress: Callable[[int, int], None] | None = None) -> None:
        local.parent.mkdir(parents=True, exist_ok=True)
        if on_progress:
            size = self.sftp.stat(remote).st_size

            def _cb(done: int, total: int) -> None:
                on_progress(done, size)

            self.sftp.get(remote, str(local), callback=_cb)
        else:
            self.sftp.get(remote, str(local))

    def _mkdir_p(self, remote_path: str) -> None:
        parts = remote_path.strip("/").split("/")
        cur = ""
        for p in parts:
            cur = f"{cur}/{p}"
            try:
                self.sftp.stat(cur)
            except FileNotFoundError:
                self.sftp.mkdir(cur)

    def __enter__(self) -> SSHSession:
        self.connect()
        return self

    def __exit__(self, *args) -> None:
        self.disconnect()


def test_ssh_connection(config: SSHConfig) -> dict:
    """Quick connectivity + GPU check."""
    with SSHSession(config) as session:
        code, out, err = session.run("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader")
        if code != 0:
            raise RuntimeError(err or out or "nvidia-smi failed")
        gpu_line = out.strip().split("\n")[0] if out else "unknown"
        return {"ok": True, "gpu": gpu_line, "host": config.host}
