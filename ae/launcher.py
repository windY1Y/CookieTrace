#!/usr/bin/env python3
"""Linux host launcher; standard library only. No host /data mutations."""
import argparse
import datetime as dt
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
from urllib.parse import urlsplit
import uuid

ROOT = Path(__file__).resolve().parent
INTERNAL_OUTPUT = '/data/backtrack/yangyi-experiments/results_new'
LABEL = 'org.cookietrace.ae.run'
COOKIE_RE = re.compile(r'[A-Za-z_][A-Za-z0-9_.-]*\Z')


def parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    action = p.add_mutually_exclusive_group(required=True)
    action.add_argument('--build', action='store_true', help='Build runtime image only; does not copy Chromium into it')
    action.add_argument('--check', action='store_true', help='Check browser bundle and runtime shared libraries')
    action.add_argument('--demo', action='store_true', help='Run a built-in local cookie example, without external network')
    action.add_argument('--url', help='HTTP(S) URL, or a hostname (https:// is added)')
    target = p.add_mutually_exclusive_group()
    target.add_argument('--cookie-name', help='Full cookie name; output name is checked exactly')
    target.add_argument('--cookie-prefix', help='Legacy engine prefix: part of name before its first digit')
    p.add_argument('--browser-dir', type=Path, default=ROOT/'browser'/'sys', help='Directory containing chrome and its resources')
    p.add_argument('--output-dir', type=Path, default=ROOT/'results', help='Parent directory; a unique run subdirectory is always created')
    p.add_argument('--image', default='cookietrace-ae:debian12-v1')
    p.add_argument('--base-image', default='debian:12-slim', help='For --build; may be pinned to a digest')
    p.add_argument('--timeout', type=float, default=120, help='Seconds allowed for browser analysis')
    p.add_argument('--settle-seconds', type=float, default=2, help='Require completed JSON files to remain unchanged this long')
    p.add_argument('--proxy', help='Optional Chromium proxy URL; no proxy by default')
    p.add_argument('--network', choices=['bridge', 'host', 'none'], help='Default: none for demo/check, bridge for URL')
    p.add_argument('--ignore-certificate-errors', action='store_true', help='Opt in for a controlled TLS replay environment')
    p.add_argument('--shm-size', default='1g', help='Container /dev/shm size')
    p.add_argument('--memory', help='Optional Docker memory limit, e.g. 8g (not a measured minimum)')
    p.add_argument('--cpus', type=float, help='Optional Docker CPU limit')
    p.add_argument('--dry-run', action='store_true', help='Print configuration and planned commands; do not invoke Docker or write files')
    return p


def normalize_url(value):
    if any(ord(c) < 32 or c.isspace() for c in value):
        raise ValueError('URL must not contain whitespace or control characters; percent-encode it.')
    if '://' not in value:
        value = 'https://' + value
    u = urlsplit(value)
    if u.scheme not in ('http', 'https') or not u.hostname:
        raise ValueError('Only HTTP(S) URLs are supported.')
    if u.username or u.password:
        raise ValueError('URL credentials are not supported; use a public test page.')
    _ = u.port
    return value


def engine_prefix(name):
    if not COOKIE_RE.fullmatch(name):
        raise ValueError('Supported cookie names start with a letter/underscore and contain letters, digits, _, ., or -.')
    return re.split(r'[0-9]', name, maxsplit=1)[0]


def validate(a):
    if a.url and not (a.cookie_name or a.cookie_prefix):
        raise ValueError('--url requires --cookie-name or --cookie-prefix.')
    if not a.url and (a.cookie_name or a.cookie_prefix):
        raise ValueError('Cookie options apply to --url only; --demo supplies its own target.')
    for value, name in ((a.timeout, 'timeout'), (a.settle_seconds, 'settle-seconds')):
        if not math.isfinite(value) or value <= 0:
            raise ValueError('--'+name+' must be a finite positive number.')
    if a.timeout <= a.settle_seconds:
        raise ValueError('--timeout must exceed --settle-seconds.')
    if a.cpus is not None and (not math.isfinite(a.cpus) or a.cpus <= 0):
        raise ValueError('--cpus must be finite and positive.')
    for value in (a.image, a.base_image):
        if not value or value.startswith('-') or any(c.isspace() for c in value):
            raise ValueError('Invalid Docker image reference.')
    if a.url:
        a.url = normalize_url(a.url)
    a.target = 'ct_demo_cookie' if a.demo else a.cookie_name
    a.prefix = engine_prefix(a.target) if a.target else a.cookie_prefix
    if a.cookie_prefix:
        if engine_prefix(a.cookie_prefix) != a.cookie_prefix:
            raise ValueError('--cookie-prefix must not contain digits: the current engine stops before the first digit.')
    a.network = a.network or ('bridge' if a.url else 'none')
    if a.proxy:
        u = urlsplit(a.proxy)
        if u.scheme not in ('http', 'https', 'socks5') or not u.hostname or u.username or u.password:
            raise ValueError('Proxy must be an http/https/socks5 URL without embedded credentials.')
        if any(c.isspace() or ord(c) < 32 for c in a.proxy):
            raise ValueError('Invalid proxy URL.')
        _ = u.port
        if a.network == 'none':
            raise ValueError('A proxy cannot be used with --network none.')
        if u.hostname in ('localhost', '127.0.0.1', '::1') and a.network != 'host':
            raise ValueError('A host loopback proxy requires --network host on Linux; container localhost is different.')
    a.browser_dir = a.browser_dir.expanduser().resolve()
    a.output_dir = a.output_dir.expanduser().resolve()
    for path in (a.browser_dir, a.output_dir):
        if ',' in str(path) or '\n' in str(path) or '\r' in str(path):
            raise ValueError('Docker bind source paths cannot contain commas or line breaks in this launcher.')


def docker(args, **kwargs):
    return subprocess.run(['docker', *args], check=True, timeout=kwargs.pop('timeout', 30), **kwargs)


def check_engine():
    if sys.platform != 'linux':
        raise ValueError('Run this launcher on Linux x86-64 (or an x86-64 Linux WSL environment).')
    if not shutil.which('docker'):
        raise ValueError('Docker CLI is not installed. Install Docker Engine and enable access for your user.')
    endpoint = os.environ.get('DOCKER_HOST') if not os.environ.get('DOCKER_CONTEXT') else None
    if not endpoint:
        endpoint = docker(['context', 'inspect', '--format', '{{.Endpoints.docker.Host}}'], capture_output=True, text=True).stdout.strip()
    if not endpoint.startswith('unix://'):
        raise ValueError('Use a local Docker daemon; remote daemons cannot bind the client browser/output directories.')
    info = json.loads(docker(['info', '--format', '{{json .}}'], capture_output=True, text=True).stdout)
    if info.get('OSType') != 'linux' or info.get('Architecture') not in ('x86_64', 'amd64'):
        raise ValueError('This prebuilt browser requires an x86-64 Linux Docker engine; CPU emulation is not validated.')


def inspect_image(image):
    return json.loads(docker(['image', 'inspect', image], capture_output=True, text=True).stdout)[0]['Id']


def create_command(a, run_dir, run_id, image):
    command = ['docker', 'create', '--name', 'cookietrace-'+run_id,
               '--label', LABEL+'='+run_id, '--platform', 'linux/amd64',
               '--init', '--read-only', '--cap-drop', 'ALL',
               '--security-opt', 'no-new-privileges', '--network', a.network,
               '--user', f'{os.getuid() if hasattr(os,"getuid") else 1000}:{os.getgid() if hasattr(os,"getgid") else 1000}',
               '--shm-size', a.shm_size,
               '--tmpfs', '/tmp:rw,nosuid,nodev,size=1g,mode=1777',
               '--env', 'HOME=/tmp/ct-home', '--env', 'XDG_CACHE_HOME=/tmp/ct-cache',
               '--mount', f'type=bind,src={a.browser_dir},dst=/opt/cookietrace/browser,readonly',
               '--mount', f'type=bind,src={run_dir},dst=/ct-output',
               '--mount', f'type=bind,src={run_dir / "raw"},dst={INTERNAL_OUTPUT}']
    if a.memory:
        command += ['--memory', a.memory]
    if a.cpus:
        command += ['--cpus', str(a.cpus)]
    command += [image, '--run-id', run_id, '--timeout', str(a.timeout),
                '--settle-seconds', str(a.settle_seconds)]
    if a.check:
        command += ['--check']
    elif a.demo:
        command += ['--demo']
    else:
        command += ['--url', a.url, '--cookie-prefix', a.prefix]
        if a.target:
            command += ['--cookie-name', a.target]
    if a.proxy:
        command += ['--proxy', a.proxy]
    if a.ignore_certificate_errors:
        command += ['--ignore-certificate-errors']
    return command


def remove_owned(name, run_id):
    """Only remove the container carrying this invocation's random ownership label."""
    try:
        data = json.loads(docker(['inspect', name], capture_output=True, text=True, timeout=10).stdout)[0]
        if data.get('Config', {}).get('Labels', {}).get(LABEL) != run_id:
            return
        if data.get('State', {}).get('Running'):
            docker(['stop', '--time', '5', name], capture_output=True, timeout=15)
        docker(['rm', '--force', name], capture_output=True, timeout=15)
    except (subprocess.SubprocessError, OSError, ValueError) as exc:
        print(f'Cleanup warning for {name}: {exc}. If Docker was interrupted, inspect this container manually.', file=sys.stderr)


def execute(a):
    validate(a)
    if a.build:
        cmd = ['docker', 'build', '--platform', 'linux/amd64', '--build-arg',
               'BASE_IMAGE='+a.base_image, '-t', a.image, str(ROOT/'docker')]
        if a.dry_run:
            print(json.dumps(cmd, indent=2)); return 0
        check_engine()
        return subprocess.run(cmd, check=False).returncode
    run_id = uuid.uuid4().hex
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    run_dir = a.output_dir/(stamp+'-'+run_id[:12])
    if a.dry_run:
        print(json.dumps({'run_dir': str(run_dir), 'engine_prefix': a.prefix,
                          'exact_output_name': a.target, 'command': create_command(a, run_dir, run_id, a.image)}, indent=2))
        return 0
    check_engine()
    chrome = a.browser_dir/'chrome'
    if not chrome.is_file() or not os.access(chrome, os.X_OK):
        raise ValueError(f'Missing executable {chrome}. Supply --browser-dir pointing at your out/sys directory.')
    try:
        image_id = inspect_image(a.image)
    except subprocess.CalledProcessError as exc:
        raise ValueError('Runtime image not found; first run: bash run.sh --build') from exc
    # Never reuse an existing run directory or write inside the browser bundle.
    if run_dir == a.browser_dir or a.browser_dir in run_dir.parents:
        raise ValueError('Output directory must not be inside the browser bundle.')
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir/'raw').mkdir()
    metadata = {'run_id': run_id, 'browser_dir': str(a.browser_dir), 'image_id': image_id,
                'image_tag': a.image, 'network': a.network, 'url': a.url,
                'cookie_name': a.target, 'engine_prefix': a.prefix,
                'timeout_seconds': a.timeout, 'started_utc': stamp,
                'browser_bytes': chrome.stat().st_size,
                'note': 'No Selenium; results are validated JSON, not a page-load performance measurement.'}
    metadata_path = run_dir/'launcher.json'
    metadata_path.write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8')
    name = 'cookietrace-'+run_id
    child = None
    attempted = False
    print(f'Results: {run_dir}', flush=True)
    if a.target and a.prefix != a.target:
        print(f'Engine uses prefix {a.prefix!r}; final cookie name must equal {a.target!r}. A different first match is an error.', flush=True)
    code = 2
    try:
        attempted = True
        subprocess.run(create_command(a, run_dir, run_id, image_id), check=True, capture_output=True, text=True, timeout=45)
        child = subprocess.Popen(['docker', 'start', '--attach', name])
        try:
            child.wait(timeout=a.timeout+90)
        except subprocess.TimeoutExpired:
            print('Container exceeded the host watchdog; stopping this run only.', file=sys.stderr)
            code = 124
        else:
            state = json.loads(docker(['inspect', name], capture_output=True, text=True).stdout)[0]['State']
            code = int(state['ExitCode'])
            metadata['container_oom_killed'] = state.get('OOMKilled', False)
            status_path = run_dir/'status.json'
            if code == 0:
                try:
                    status = json.loads(status_path.read_text(encoding='utf-8'))
                    if status.get('status') not in ('success', 'check_passed'):
                        code = 2
                except (OSError, ValueError):
                    code = 2
    except KeyboardInterrupt:
        code = 130
        print('Interrupted; stopping only this run.', file=sys.stderr)
    finally:
        if attempted:
            remove_owned(name, run_id)
        if child and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill(); child.wait(timeout=5)
        metadata['launcher_exit_code'] = code
        metadata_path.write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8')
    return code


def main():
    if sys.version_info < (3, 9):
        print('Python 3.9+ is required.', file=sys.stderr); return 2
    def interrupt(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupt)
    try:
        return execute(parser().parse_args())
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        detail = getattr(exc, 'stderr', None)
        print(f'Error: {exc}' + (f'\n{detail.strip()}' if isinstance(detail, str) and detail.strip() else ''), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
