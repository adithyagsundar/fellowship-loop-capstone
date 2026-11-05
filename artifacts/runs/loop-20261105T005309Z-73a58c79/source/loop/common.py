"""Shared evidence and process primitives; Python standard library only."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRS = ('platform', 'web', 'tests', 'loop', 'third_party', 'assets')
ROOT_FILES = ('build.sh', 'Makefile', 'Dockerfile', 'README.md', 'AGENTS.md', 'SANDBOX.md')


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def files(root=ROOT):
    result = [root / name for name in ROOT_FILES if (root / name).is_file()]
    for name in SOURCE_DIRS:
        result.extend(p for p in (root / name).rglob('*') if p.is_file()
                      and '__pycache__' not in p.parts and p.suffix != '.pyc')
    return sorted(result)


def snapshot(root=ROOT):
    hashes = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in files(root)}
    digest = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    return {'digest': digest, 'files': hashes}


def revision(root=ROOT):
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()


def execute(command, log, timeout, cwd=ROOT, env=None):
    """No shared stdin; kill the process group on timeout/interruption."""
    started = time.monotonic()
    with Path(log).open('w') as stream:
        process = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                   stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = process.wait(timeout=timeout)
        except BaseException:
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=3)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
            raise
    return {'returncode': code, 'seconds': round(time.monotonic() - started, 3)}


def verify(output, root=ROOT, timeout=300):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    before = snapshot(root)
    save(output / 'source.json', {'revision': revision(root), **before})
    result = {'status': 'FAIL', 'source_digest': before['digest'], 'commands': []}
    try:
        # Build script is human-owned and is never writable through coder tools.
        for name, command in [('build', ['bash', 'build.sh']),
                              ('tests', ['python3', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v'])]:
            record = execute(command, output / (name + '.log'), timeout, cwd=root)
            result['commands'].append({'name': name, **record})
            if record['returncode'] != 0:
                break
        else:
            if snapshot(root)['digest'] == before['digest']:
                result['status'] = 'PASS'
            else:
                result['error'] = 'Source changed during verification'
    except Exception as error:
        result['error'] = str(error)
    finally:
        save(output / 'result.json', result)
    return result
