import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest

from evaluation.sandbox import DockerSandbox, decode_snapshot, validate_files


class FileBoundaryTests(unittest.TestCase):
    def test_paths_and_payloads_cannot_escape_or_exceed_limits(self):
        for path in ("../secret", "/secret", "C:/secret", "a\\b", ".git/config", "a/../b", "a//b"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                validate_files({path: "data"})
        with self.assertRaises(ValueError):
            validate_files({"large.py": "x" * 16385})
        with self.assertRaises(ValueError):
            validate_files({"a": 1})
        validate_files({"package/module.py": "value = 1\n"})

    def test_archive_links_and_traversal_are_rejected_without_extraction(self):
        for name, kind in (("../escape", tarfile.REGTYPE), ("link", tarfile.SYMTYPE), ("link", tarfile.LNKTYPE)):
            with self.subTest(name=name, kind=kind):
                stream = io.BytesIO()
                with tarfile.open(fileobj=stream, mode="w") as archive:
                    member = tarfile.TarInfo(name)
                    member.type = kind
                    member.linkname = "/etc/passwd"
                    archive.addfile(member)
                with self.assertRaises(ValueError):
                    decode_snapshot(stream.getvalue())

    def test_mutable_image_and_unbounded_limits_are_rejected(self):
        with self.assertRaises(ValueError):
            DockerSandbox({}, image="python:latest")
        for timeout in (0, -1, 31, float("nan"), True):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                DockerSandbox({}, timeout=timeout)


@unittest.skipUnless(os.environ.get("CODE_COMMENTS_DOCKER") == "1", "opt-in Docker integration")
class DockerBoundaryTests(unittest.TestCase):
    def test_real_container_has_no_host_private_network_or_root_write_access(self):
        with tempfile.TemporaryDirectory() as temporary:
            canary = Path(temporary) / "host-secret.txt"
            canary.write_text("host only", encoding="utf-8")
            probe = """import json, os, pathlib, socket
r = {'uid': os.getuid(), 'host': pathlib.Path(HOST).exists(), 'private': pathlib.Path('/workspace/private').exists(), 'socket': pathlib.Path('/var/run/docker.sock').exists()}
try:
 pathlib.Path('/root-write-probe').write_text('bad'); r['root_write'] = True
except OSError: r['root_write'] = False
try:
 socket.create_connection(('1.1.1.1',443),timeout=1).close(); r['network'] = True
except OSError: r['network'] = False
print(json.dumps(r))
""".replace("HOST", repr(str(canary)))
            with DockerSandbox({"policy.py": "value = 1\n"}) as sandbox:
                result = sandbox.run(["python", "-I", "-B", "-c", probe])
                self.assertEqual(result.returncode, 0, result.output)
                self.assertEqual(json.loads(result.output), {"uid": 65534, "host": False, "private": False, "socket": False, "root_write": False, "network": False})
                self.assertEqual(sandbox.snapshot(), {"policy.py": "value = 1\n"})
                with self.assertRaises(RuntimeError):
                    sandbox.run(["python", "--version"])
            self.assertEqual(canary.read_text(encoding="utf-8"), "host only")

    def test_symlink_snapshot_is_rejected(self):
        with DockerSandbox({}) as sandbox:
            result = sandbox.run(["python", "-I", "-B", "-c", "import os; os.symlink('/etc/passwd','leak')"])
            self.assertEqual(result.returncode, 0)
            with self.assertRaises(ValueError):
                sandbox.snapshot()

    def test_snapshot_stops_background_writers(self):
        program = """import subprocess,sys,time
from pathlib import Path
Path('counter').write_text('0')
child=subprocess.Popen([sys.executable,'-I','-B','-c',"from pathlib import Path; import time; n=0\\nwhile True:\\n n+=1;Path('/tmp/next').write_text(str(n));Path('counter').write_text(str(n));time.sleep(0.01)"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
deadline=time.monotonic()+2
while time.monotonic()<deadline:
 if Path('counter').read_text() not in ('','0'): break
 if child.poll() is not None: raise RuntimeError('writer died')
 time.sleep(0.01)
else: raise RuntimeError('writer never progressed')
print(child.pid)
"""
        with DockerSandbox({}) as sandbox:
            result = sandbox.run(["python", "-I", "-B", "-c", program])
            self.assertEqual(result.returncode, 0, result.output)
            pid = int(result.output)
            files = sandbox.snapshot()
            # A stopped write may be partial; assert quiescence, not atomic writes.
            import subprocess
            probe = f"from pathlib import Path; import time; p=Path('/proc/{pid}/stat'); print(p.read_text().rsplit(')',1)[1].split()[0]); a=Path('counter').read_text(); time.sleep(0.05); print(a==Path('counter').read_text())"
            stopped = subprocess.run(['docker', 'exec', sandbox.name, 'python', '-I', '-B', '-c', probe], capture_output=True, text=True, timeout=5)
            self.assertEqual(stopped.returncode, 0, stopped.stderr)
            self.assertEqual(stopped.stdout.splitlines(), ['T', 'True'])
            self.assertIn('counter', files)

    def test_timeout_closes_container(self):
        with DockerSandbox({}, timeout=1) as sandbox:
            result = sandbox.run(["python", "-I", "-B", "-c", "while True: pass"])
            self.assertTrue(result.timed_out)
            self.assertTrue(sandbox.closed)

    def test_output_flood_is_bounded_and_container_closed(self):
        with DockerSandbox({}) as sandbox:
            result = sandbox.run(["python", "-I", "-B", "-c", "print('x' * 400000)"])
            self.assertTrue(result.output_limited)
            self.assertLessEqual(len(result.output.encode()), 262144)
            self.assertTrue(sandbox.closed)
