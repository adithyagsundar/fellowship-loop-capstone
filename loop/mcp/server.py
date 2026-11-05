#!/usr/bin/env python3
"""Role-scoped MCP stdio server. No arbitrary shell or caller-selected commands."""
import argparse
import json
from pathlib import Path
import sys
import signal
import uuid
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import ROOT, save, snapshot, verify


def schema(properties=None, required=None):
    return {'type': 'object', 'properties': properties or {}, 'required': required or [], 'additionalProperties': False}


class Server:
    def __init__(self, root, role, run, invocation):
        self.root = Path(root).resolve()
        self.role = role
        self.run = Path(run).resolve()
        self.invocation = Path(invocation).resolve()
        if role not in ('coder', 'reviewer', 'tester'):
            raise ValueError('Unknown role')
        if not self.run.is_relative_to(self.root / 'artifacts' / 'runs') or not self.invocation.is_relative_to(self.run):
            raise ValueError('Evidence must be inside the run')
        self.invocation.mkdir(parents=True, exist_ok=True)

    def path(self, name, write=False):
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts or any(p.startswith('.') for p in relative.parts):
            raise PermissionError('Absolute, traversal and hidden paths denied')
        path = self.root / relative
        # Reject symlinks even when their target happens to be allowed.
        if any(p.is_symlink() for p in [path, *path.parents] if p != self.root.parent):
            raise PermissionError('Symlinks denied')
        path = path.resolve()
        if not path.is_relative_to(self.root):
            raise PermissionError('Outside repository')
        if write:
            if self.role != 'coder' or relative.parts[0] not in ('platform', 'web') or path.suffix not in ('.c', '.h', '.js', '.html', '.css'):
                raise PermissionError('Coder may write only port source in platform/ and web/')
            if path.exists() and path.stat().st_nlink != 1:
                raise PermissionError('Hard-linked files denied')
        elif not (relative.parts[0] in ('platform', 'web', 'tests', 'loop', 'third_party')
                  or str(relative) in ('README.md', 'AGENTS.md', 'SANDBOX.md', 'build.sh', 'Dockerfile', 'artifacts/README.md')
                  or path.is_relative_to(self.run)):
            raise PermissionError('Path is outside readable source/current run')
        return path

    def definitions(self):
        string = {'type': 'string'}
        definitions = [
            ('list_files', 'List readable source and current-run evidence paths.', schema()),
            ('read_file', 'Read a UTF-8 file, with optional 1-based start line and line count.', schema({'path': string, 'start': {'type': 'integer'}, 'count': {'type': 'integer'}}, ['path'])),
            ('handoff', 'Save an immutable report for this role. Reviewer/tester must use PASS or FAIL. Include evidence paths.', schema({'verdict': {'type': 'string', 'enum': ['PASS', 'FAIL', 'DONE']}, 'summary': string}, ['verdict', 'summary']))]
        if self.role == 'coder':
            definitions.append(('write_file', 'Replace a port source file. Tests, loop, build scripts and evidence are protected.', schema({'path': string, 'content': string}, ['path', 'content'])))
        if self.role == 'tester':
            definitions.append(('verify', 'Run the fixed build and protected acceptance suite; preserve logs and source hashes. Must be called before passing.', schema()))
        return [{'name': n, 'description': d, 'inputSchema': s} for n, d, s in definitions]

    def call(self, name, args):
        allowed = {d['name']: d for d in self.definitions()}
        if name not in allowed:
            raise PermissionError('Tool unavailable to role')
        spec = allowed[name]['inputSchema']
        if set(args) - set(spec['properties']) or set(spec['required']) - set(args):
            raise ValueError('Invalid arguments')
        if name == 'list_files':
            result = [name for name in ('README.md', 'AGENTS.md', 'SANDBOX.md', 'build.sh', 'Dockerfile', 'artifacts/README.md') if (self.root / name).is_file()]
            for folder in ('platform', 'web', 'tests', 'loop', 'third_party'):
                for path in (self.root / folder).rglob('*'):
                    if path.is_file() and '__pycache__' not in path.parts:
                        try:
                            self.path(str(path.relative_to(self.root)))
                            result.append(str(path.relative_to(self.root)))
                        except PermissionError:
                            pass
            result += [str(p.relative_to(self.root)) for p in self.run.rglob('*')
                       if p.is_file() and p.suffix in ('.json', '.log', '.md', '.txt')
                       and 'source' not in p.relative_to(self.run).parts]
            return sorted(result)
        if name == 'read_file':
            path = self.path(args['path'])
            if path.stat().st_size > 2_000_000:
                raise ValueError('File too large')
            start, count = args.get('start', 1), args.get('count', 250)
            if not isinstance(start, int) or not isinstance(count, int) or start < 1 or not 1 <= count <= 1000:
                raise ValueError('Invalid line range')
            lines = path.read_text().splitlines()
            return {'total_lines': len(lines), 'text': '\n'.join(f'{i+1}: {line}' for i, line in enumerate(lines) if start-1 <= i < start-1+count)}
        if name == 'write_file':
            path = self.path(args['path'], write=True)
            if not isinstance(args['content'], str) or len(args['content']) > 1_000_000:
                raise ValueError('Invalid content')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(args['content'])
            return {'written': args['path']}
        if name == 'verify':
            directory = self.invocation / ('verification-' + uuid.uuid4().hex[:12])
            result = verify(directory, self.root)
            return {'path': str(directory.relative_to(self.root)), **result,
                    'logs': {p.name: {'path': str(p.relative_to(self.root)), 'excerpt': p.read_text(errors='replace')[-12000:]}
                             for p in directory.glob('*.log')}}
        if name == 'handoff':
            if args['verdict'] not in ('PASS', 'FAIL', 'DONE') or not isinstance(args['summary'], str) or not args['summary'].strip():
                raise ValueError('Invalid report')
            if self.role != 'coder' and args['verdict'] == 'DONE':
                raise ValueError('A verifier must report PASS or FAIL')
            path = self.invocation / 'handoff.json'
            if path.exists():
                raise ValueError('Handoff already submitted; immutable')
            record = {'role': self.role, **args, 'source_digest': snapshot(self.root)['digest']}
            if self.role == 'tester' and args['verdict'] == 'PASS':
                paths = sorted(self.invocation.glob('verification-*/result.json'), key=lambda p: p.stat().st_mtime_ns)
                latest = json.loads(paths[-1].read_text()) if paths else {}
                if latest.get('status') != 'PASS' or latest.get('source_digest') != record['source_digest']:
                    raise ValueError('Fresh passing verification required')
            save(path, record)
            return {'path': str(path.relative_to(self.root))}

    def dispatch(self, message):
        method, params = message.get('method'), message.get('params', {})
        if method == 'initialize':
            return {'protocolVersion': '2025-03-26', 'capabilities': {'tools': {}}, 'serverInfo': {'name': 'doom-loop', 'version': '1.0.0'}}
        if method == 'ping':
            return {}
        if method == 'tools/list':
            return {'tools': self.definitions()}
        if method == 'tools/call':
            try:
                result = self.call(params['name'], params.get('arguments', {}))
                response = {'content': [{'type': 'text', 'text': json.dumps(result)}], 'isError': False}
            except Exception as error:
                response = {'content': [{'type': 'text', 'text': str(error)}], 'isError': True}
            with (self.invocation / 'tools.jsonl').open('a') as stream:
                # Record paths and results, not entire write contents.
                stream.write(json.dumps({'tool': params.get('name'), 'path': params.get('arguments', {}).get('path'), 'response': response}) + '\n')
            return response
        raise ValueError('Unsupported method')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default=str(ROOT))
    parser.add_argument('--role', required=True)
    parser.add_argument('--run', required=True)
    parser.add_argument('--invocation', required=True)
    args = parser.parse_args()
    server = Server(args.root, args.role, args.run, args.invocation)
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    for line in sys.stdin:
        message = None
        try:
            message = json.loads(line)
            if 'id' not in message:
                continue
            result = {'jsonrpc': '2.0', 'id': message['id'], 'result': server.dispatch(message)}
        except Exception as error:
            result = {'jsonrpc': '2.0', 'id': message.get('id') if isinstance(message, dict) else None,
                      'error': {'code': -32602, 'message': str(error)}}
        print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
