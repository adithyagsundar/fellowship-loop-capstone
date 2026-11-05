#!/usr/bin/env python3
"""Durable sequential orchestration of fresh, role-restricted Claude invocations."""
import argparse
import fcntl
import json
from pathlib import Path
import shutil
import signal
import sys
import time
import uuid
from common import ROOT, execute, revision, save, snapshot, verify

ROLES = ('coder', 'reviewer', 'tester')


def accepted(role, directory, digest):
    try:
        result = json.loads((directory / 'result.json').read_text())
        handoff = json.loads((directory / 'handoff.json').read_text())
        return (not result.get('is_error', True) and result.get('subtype') == 'success'
                and handoff.get('role') == role and handoff.get('source_digest') == digest
                and handoff.get('verdict') in (('DONE', 'PASS') if role == 'coder' else ('PASS',)))
    except (OSError, ValueError):
        return False


def command(role, prompt, config, mcp):
    return ['claude', '-p', prompt, '--model', config['model'], '--tools', '',
            '--allowedTools', 'mcp__doom__*', '--strict-mcp-config', '--mcp-config', str(mcp),
            '--setting-sources', '', '--disable-slash-commands', '--no-chrome',
            '--no-session-persistence', '--permission-mode', 'dontAsk',
            '--max-turns', str(config['max_turns_per_agent']),
            '--max-budget-usd', str(config['max_budget_usd_per_agent']), '--output-format', 'json']


def invoke(role, task, attempt, run, config, history, timeout):
    directory = attempt / role
    directory.mkdir()
    mcp = directory / 'mcp.json'
    save(mcp, {'mcpServers': {'doom': {'command': sys.executable, 'args': [str(ROOT / 'loop/mcp/server.py'), '--root', str(ROOT), '--role', role, '--run', str(run), '--invocation', str(directory)]}}})
    prompt = (ROOT / 'loop/prompts' / (role + '.md')).read_text()
    prompt += '\nTask: ' + task['id'] + ': ' + task['description']
    prompt += '\nCurrent source digest: ' + snapshot()['digest']
    prompt += '\nRead prior handoffs and failures at these repository-relative paths:\n' + '\n'.join(history)
    prompt += '\nUse the MCP handoff tool to finish. Do not claim unperformed actions.'
    (directory / 'prompt.txt').write_text(prompt)
    cmd = command(role, prompt, config, mcp)
    save(directory / 'invocation.json', {'role': role, 'argv_without_prompt': [*cmd[:2], '<saved in prompt.txt>', *cmd[3:]], 'source': snapshot()['digest']})
    started = time.monotonic()
    record = {'returncode': None}
    try:
        record = execute(cmd, directory / 'stdout.json', timeout)
        raw = json.loads((directory / 'stdout.json').read_text())
        if not isinstance(raw, dict):
            raise ValueError('Expected Claude JSON result object')
        save(directory / 'result.json', raw)
    except Exception as error:
        record['error'] = str(error)
    finally:
        record['seconds'] = round(time.monotonic() - started, 3)
        save(directory / 'process.json', record)
    return directory, record


def run_loop(run, state, config):
    limits = config
    start = time.monotonic()
    history = state['history']
    initial = snapshot()
    if state.get('source_digest') != initial['digest']:
        state['events'].append({'type': 'source_changed', 'old': state.get('source_digest'), 'new': initial['digest']})
        state['completed'] = []
        state['source_digest'] = initial['digest']
    state['status'] = 'RUNNING'
    save(run / 'state.json', state)
    try:
        if state.get('baseline_digest') != initial['digest']:
            remaining = limits['max_seconds_per_run'] - state['seconds'] - (time.monotonic() - start)
            if remaining <= 0:
                state['status'], state['reason'] = 'EXHAUSTED', 'Run time budget reached'
                return
            baseline = run / ('baseline-' + uuid.uuid4().hex[:8])
            print('Running protected baseline verification', flush=True)
            verify(baseline, timeout=max(1, min(300, remaining / 3)))
            history.append(str((baseline / 'result.json').relative_to(ROOT)))
            state['baseline_digest'] = initial['digest']
            save(run / 'state.json', state)
        for task in config['tasks']:
            task_id = task['id']
            if task_id in state['completed']:
                continue
            while state['attempts'].get(task_id, 0) < limits['max_retries']:
                remaining = limits['max_seconds_per_run'] - state['seconds'] - (time.monotonic() - start)
                if remaining <= 0 or state['charged_usd'] + limits['max_budget_usd_per_agent'] > limits['max_budget_usd_per_run']:
                    state['status'], state['reason'] = 'EXHAUSTED', 'Run time or reserved cost budget reached'
                    return
                state['attempts'][task_id] = state['attempts'].get(task_id, 0) + 1
                attempt = run / f"{task_id}-{state['attempts'][task_id]:02}-{uuid.uuid4().hex[:8]}"
                attempt.mkdir()
                before = snapshot()['digest']
                state['current_attempt'] = str(attempt.relative_to(ROOT))
                save(run / 'state.json', state)
                all_pass = True
                for role in ROLES:
                    remaining = limits['max_seconds_per_run'] - state['seconds'] - (time.monotonic() - start)
                    if remaining <= 0 or state['charged_usd'] + limits['max_budget_usd_per_agent'] > limits['max_budget_usd_per_run']:
                        state['status'], state['reason'] = 'EXHAUSTED', 'Run time or reserved cost budget reached'
                        return
                    # Reserve maximum before launch; interruptions cannot lose budget accounting.
                    charge = {'role': role, 'path': str((attempt / role).relative_to(ROOT)), 'actual_usd': None, 'charged_usd': limits['max_budget_usd_per_agent']}
                    state['usage'].append(charge)
                    state['charged_usd'] += charge['charged_usd']
                    save(run / 'state.json', state)
                    print(f'{task_id}: attempt {state["attempts"][task_id]}, {role}', flush=True)
                    directory, process = invoke(role, task, attempt, run, config, history, min(remaining, limits['max_seconds_per_agent']))
                    try:
                        raw = json.loads((directory / 'result.json').read_text())
                        cost = raw.get('total_cost_usd')
                        if isinstance(cost, (int, float)) and cost >= 0:
                            state['charged_usd'] += cost - charge['charged_usd']
                            charge['actual_usd'] = charge['charged_usd'] = cost
                        charge['usage'] = raw.get('usage')
                        charge['modelUsage'] = raw.get('modelUsage')
                    except (OSError, ValueError):
                        pass
                    charge['seconds'] = process['seconds']
                    for file in ('handoff.json', 'process.json'):
                        if (directory / file).exists():
                            history.append(str((directory / file).relative_to(ROOT)))
                    for result in directory.glob('verification-*/result.json'):
                        history.append(str(result.relative_to(ROOT)))
                    digest = snapshot()['digest']
                    if process['returncode'] != 0 or not accepted(role, directory, digest):
                        all_pass = False
                    # Reviewer/tester must not modify source, even through unexpected routes.
                    if role != 'coder' and digest != after_coder:
                        all_pass = False
                    if role == 'coder':
                        after_coder = digest
                    state['source_digest'] = digest
                    save(run / 'state.json', state)
                after = snapshot()['digest']
                save(attempt / 'decision.json', {'pass': all_pass, 'before': before, 'after': after})
                if all_pass:
                    state['completed'].append(task_id)
                    state['unchanged_failures'] = 0
                    save(run / 'state.json', state)
                    break
                state['unchanged_failures'] = state.get('unchanged_failures', 0) + 1 if before == after else 0
                if state['unchanged_failures'] >= 2:
                    state['status'], state['reason'] = 'STALLED', 'Two failed cycles without source changes'
                    return
            else:
                state['status'], state['reason'] = 'EXHAUSTED', f'Repair attempt limit reached for {task_id}'
                return
        state['status'] = 'SUCCESS'
        state['reason'] = 'Every selected task passed independent MCP handoffs and fresh tester checks; this is not full assignment acceptance'
    except KeyboardInterrupt:
        state['status'], state['reason'] = 'INTERRUPTED', 'Resume with the same run; incomplete attempt retained and counted'
    except Exception as error:
        state['status'], state['reason'] = 'ERROR', repr(error)
    finally:
        state['seconds'] += round(time.monotonic() - start, 3)
        state['source_digest'] = snapshot()['digest']
        save(run / 'state.json', state)
        print(state['status'] + ': ' + state.get('reason', ''), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--new', action='store_true', help='Start a new run; preserve prior runs')
    parser.add_argument('--run', help='Resume a repository-relative run directory')
    parser.add_argument('--tasks', help='Comma-separated task IDs for a new run; default: all')
    parser.add_argument('--verify-only', action='store_true', help='Run build/tests without calling an agent')
    args = parser.parse_args()
    (ROOT / 'artifacts').mkdir(exist_ok=True)
    lock = (ROOT / 'artifacts/loop.lock').open('a')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('Another loop/verification owns the repository lock')
    config = json.loads((ROOT / 'loop/agents.yaml').read_text())
    if args.verify_only:
        output = ROOT / 'artifacts/runs' / ('verification-' + uuid.uuid4().hex[:12])
        result = verify(output)
        print(json.dumps({'evidence': str(output.relative_to(ROOT)), **result}, indent=2))
        return 0 if result['status'] == 'PASS' else 1
    pointer = ROOT / 'artifacts/state.json'
    if args.new or (not args.run and not pointer.exists()):
        run = ROOT / 'artifacts/runs' / ('loop-' + time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '-' + uuid.uuid4().hex[:8])
        run.mkdir(parents=True)
        if args.tasks:
            selected = args.tasks.split(',')
            if set(selected) - {t['id'] for t in config['tasks']}:
                raise SystemExit('Unknown task')
            config['tasks'] = [t for t in config['tasks'] if t['id'] in selected]
        state = {'status': 'NEW', 'revision': revision(), 'source_digest': snapshot()['digest'], 'completed': [], 'attempts': {}, 'usage': [], 'charged_usd': 0, 'seconds': 0, 'history': [], 'events': []}
        save(run / 'config.json', config)
        save(run / 'state.json', state)
        save(run / 'source.json', snapshot())
        for path in snapshot()['files']:
            target = run / 'source' / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / path, target)
        (run / 'working-tree.patch').write_text(__import__('subprocess').check_output(['git', 'diff'], cwd=ROOT, text=True))
    else:
        if args.tasks:
            raise SystemExit('--tasks is only valid for a new run')
        run = (ROOT / (args.run or json.loads(pointer.read_text())['run'])).resolve()
        if not run.is_relative_to(ROOT / 'artifacts/runs'):
            raise SystemExit('Run must be under artifacts/runs')
        state = json.loads((run / 'state.json').read_text())
        config = json.loads((run / 'config.json').read_text())
        if state['status'] in ('EXHAUSTED', 'STALLED'):
            raise SystemExit('Terminal run; use --new for a separately budgeted run')
        if state['status'] == 'SUCCESS' and state['source_digest'] == snapshot()['digest']:
            print('SUCCESS: unchanged source already verified; use --new to repeat')
            return 0
    save(pointer, {'run': str(run.relative_to(ROOT))})
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    run_loop(run, state, config)
    return 0 if state['status'] == 'SUCCESS' else 1


if __name__ == '__main__':
    sys.exit(main())
