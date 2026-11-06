"""Bounded local Docker execution. Never mounts the repository or Docker socket."""

from dataclasses import dataclass
import io
import json
import math
from pathlib import PurePosixPath
import re
import subprocess
import tarfile
import threading
import time
import uuid


IMAGE = "python@sha256:4840d514c583a4d3d8cad3940e68dee6f0f6f3635c12fcd0a3d74c21a5b93a54"
MAX_OUTPUT = 262144
MAX_FILE = 16384
MAX_TOTAL = 32768

SNAPSHOT_SCRIPT = """import os, pathlib, signal, sys, tarfile, time
excluded = {1, os.getpid()}
def candidates():
 return [p for p in pathlib.Path('/proc').iterdir() if p.name.isdigit() and int(p.name) not in excluded]
for attempt in range(10):
 for p in candidates():
  try: os.kill(int(p.name), signal.SIGSTOP)
  except ProcessLookupError: pass
 time.sleep(0.01)
 stable = True
 for p in candidates():
  try:
   state = (p / 'stat').read_text().rsplit(')', 1)[1].split()[0]
   if state not in ('T', 't', 'Z'): stable = False
  except FileNotFoundError: pass
 if stable: break
else: raise RuntimeError('candidate processes did not quiesce')
with tarfile.open(fileobj=sys.stdout.buffer, mode='w|', dereference=False) as archive:
 archive.add('/workspace', arcname='.')
"""


def _validate_path(name: str) -> None:
    if not isinstance(name, str) or not name or len(name) > 200:
        raise ValueError("invalid workspace path")
    path = PurePosixPath(name)
    if (path.is_absolute() or path.as_posix() != name or name == "."
            or any(part in ("..", ".git") for part in path.parts)
            or any(character in name for character in ("\\", ":", "\x00", "\n", "\r"))):
        raise ValueError(f"unsafe workspace path: {name!r}")


def validate_files(files: dict[str, str]) -> None:
    if not isinstance(files, dict) or len(files) > 64:
        raise ValueError("workspace must contain at most 64 files")
    total = 0
    for name, text in files.items():
        _validate_path(name)
        if not isinstance(text, str):
            raise ValueError("workspace files must contain UTF-8 text")
        size = len(text.encode("utf-8"))
        if size > MAX_FILE:
            raise ValueError("workspace file exceeds byte limit")
        total += size
    if total > MAX_TOTAL:
        raise ValueError("workspace exceeds total byte limit")


def decode_snapshot(data: bytes) -> dict[str, str]:
    if len(data) > MAX_OUTPUT:
        raise ValueError("snapshot archive exceeds byte limit")
    files = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
            members = archive.getmembers()
            if len(members) > 256:
                raise ValueError("snapshot has too many entries")
            for member in members:
                name = member.name.removeprefix("./")
                if member.isdir() and name in ("", "."):
                    continue
                _validate_path(name)
                if member.isdir():
                    continue
                if not member.isfile() or member.size > MAX_FILE or name in files:
                    raise ValueError("snapshot contains links, special, duplicate or oversized files")
                files[name] = archive.extractfile(member).read(MAX_FILE + 1).decode("utf-8")
    except (tarfile.TarError, UnicodeError) as error:
        raise ValueError("invalid snapshot archive") from error
    validate_files(files)
    return files


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    raw: bytes
    timed_out: bool
    output_limited: bool
    elapsed_seconds: float

    @property
    def output(self) -> str:
        return self.raw.decode("utf-8", errors="replace")


def _capture(command: list[str], data: bytes, timeout: float) -> CommandResult:
    started = time.monotonic()
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = bytearray()
    limited = threading.Event()

    def read_output():
        while chunk := process.stdout.read(4096):
            room = MAX_OUTPUT - len(output)
            output.extend(chunk[:room])
            if len(chunk) > room:
                limited.set()
                process.kill()
                break

    def write_input():
        try:
            process.stdin.write(data)
            process.stdin.close()
        except (BrokenPipeError, OSError):
            pass

    reader = threading.Thread(target=read_output, daemon=True)
    writer = threading.Thread(target=write_input, daemon=True)
    reader.start()
    writer.start()
    timed_out = False
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        process.wait(timeout=5)
    except BaseException:
        process.kill()
        process.wait(timeout=5)
        raise
    finally:
        reader.join(timeout=5)
        writer.join(timeout=5)
        process.stdout.close()
        process.stdin.close()
    return CommandResult(process.returncode, bytes(output), timed_out, limited.is_set(), time.monotonic() - started)


def _docker(arguments: list[str]) -> str:
    result = subprocess.run(["docker", *arguments], capture_output=True, text=True, timeout=20)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


class DockerSandbox:
    def __init__(self, files: dict[str, str], *, image: str = IMAGE, timeout: float = 10):
        validate_files(files)
        if not re.fullmatch(r"[a-zA-Z0-9./_-]+@sha256:[a-f0-9]{64}", image):
            raise ValueError("sandbox image must be pinned by digest")
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 30:
            raise ValueError("command timeout must be greater than zero and at most 30 seconds")
        self.files = dict(files)
        self.image = image
        self.timeout = timeout
        self.name = "cc-eval-" + uuid.uuid4().hex
        self.closed = True
        self.sealed = False

    def __enter__(self):
        try:
            self.closed = False
            _docker([
                "run", "-d", "--rm", "--pull", "never", "--name", self.name,
                "--label", "code-comments.offline=true", "--network", "none", "--read-only",
                "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--user", "65534:65534",
                "--memory", "256m", "--memory-swap", "256m", "--cpus", "1", "--pids-limit", "64",
                "--tmpfs", "/workspace:rw,nosuid,nodev,size=16m,uid=65534,gid=65534",
                "--tmpfs", "/tmp:rw,nosuid,nodev,size=16m,uid=65534,gid=65534",
                "--workdir", "/workspace", "--entrypoint", "python", self.image,
                "-I", "-B", "-c", "import time; time.sleep(3600)",
            ])
            loader = "import json,pathlib,sys\nfor name,text in json.load(sys.stdin).items():\n p=pathlib.Path(name);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8')"
            result = self.run(["python", "-I", "-B", "-c", loader], json.dumps(self.files))
            if result.returncode or result.timed_out or result.output_limited:
                raise RuntimeError("sandbox initialization failed: " + result.output)
            return self
        except BaseException:
            self.close()
            raise

    def run(self, command: list[str], stdin: str = "") -> CommandResult:
        if self.closed or self.sealed:
            raise RuntimeError("sandbox is closed or sealed for snapshot")
        if not command or any(not isinstance(part, str) or "\x00" in part for part in command):
            raise ValueError("command must be a nonempty argument list")
        data = stdin.encode("utf-8")
        if len(data) > MAX_OUTPUT:
            raise ValueError("command input exceeds byte limit")
        try:
            result = _capture(["docker", "exec", "-i", "--workdir", "/workspace", self.name, *command], data, self.timeout)
            if result.timed_out or result.output_limited:
                self.close()
            return result
        except BaseException:
            self.close()
            raise

    def snapshot(self) -> dict[str, str]:
        if self.closed or self.sealed:
            raise RuntimeError("sandbox is closed or already sealed")
        # docker cp cannot read tmpfs; stop candidate processes before in-container export.
        self.sealed = True
        try:
            result = _capture(["docker", "exec", self.name, "python", "-I", "-B", "-c", SNAPSHOT_SCRIPT], b"", self.timeout)
            if result.returncode or result.timed_out or result.output_limited:
                raise ValueError("workspace snapshot failed or exceeded limits")
            return decode_snapshot(result.raw)
        except BaseException:
            self.close()
            raise

    def close(self) -> None:
        if not self.closed:
            result = subprocess.run(["docker", "rm", "-f", self.name], capture_output=True, text=True, timeout=20)
            if result.returncode and "No such container" not in result.stderr:
                raise RuntimeError("could not remove task container " + self.name + ": " + result.stderr)
            self.closed = True

    def __exit__(self, *_):
        self.close()
