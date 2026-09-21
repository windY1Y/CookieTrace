#!/usr/bin/env python3
"""Container runtime. Only its own children and declared output directory are touched."""
import argparse
import hashlib
import html
import http.server
import json
import math
import os
from pathlib import Path
import re
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time

BROWSER = Path('/opt/cookietrace/browser')
OUTPUT = Path('/ct-output')
RAW = Path('/data/backtrack/yangyi-experiments/results_new')
DEMO_NAME = 'ct_demo_cookie'
DEMO_VALUE = 'ct_demo_value'
DEMO_ROOT = Path(__file__).resolve().parent/'examples'


def write_json(path, data):
    temp = path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')
    temp.replace(path)


def runtime_check(bundle):
    chrome = bundle/'chrome'
    if not chrome.is_file() or not os.access(chrome, os.X_OK):
        raise RuntimeError(f'Browser executable missing or not executable: {chrome}')
    with chrome.open('rb') as f:
        header = f.read(20)
    if header[:4] != b'\x7fELF' or len(header) < 20 or header[4] != 2 or int.from_bytes(header[18:20], 'little') != 62:
        raise RuntimeError('Expected a Linux x86-64 ELF browser executable.')
    required = ['icudtl.dat', 'resources.pak', 'chrome_100_percent.pak', 'chrome_200_percent.pak',
                'snapshot_blob.bin', 'v8_context_snapshot.bin', 'locales']
    missing = [name for name in required if not (bundle/name).exists()]
    if missing:
        raise RuntimeError('Incomplete browser bundle: '+', '.join(missing))
    if not any((bundle/'locales').glob('*.pak')):
        raise RuntimeError('Browser locales directory has no .pak files.')
    checked = []
    # out/sys may contain optional Qt shims, test libraries and Vulkan validation
    # layers. Do not require dependencies for every unrelated build artifact.
    runtime_libraries = ['libEGL.so', 'libGLESv2.so', 'libvk_swiftshader.so', 'libvulkan.so.1']
    for binary in [chrome, *[bundle/name for name in runtime_libraries if (bundle/name).exists()]]:
        r = subprocess.run(['ldd', str(binary)], capture_output=True, text=True, timeout=20)
        text = r.stdout+r.stderr
        checked.append({'file': binary.name, 'dependencies': text.strip()})
        if 'not found' in text or r.returncode != 0:
            raise RuntimeError('Unresolved runtime dependencies for '+binary.name+':\n'+text)
    if not shutil.which('Xvfb'):
        raise RuntimeError('Xvfb is not installed in the runtime image.')
    return {'architecture': 'linux-x86_64', 'browser_size_bytes': chrome.stat().st_size,
            'dependency_checks': checked,
            'scope': 'Static bundle/dependency preflight only; run --demo to test CookieTrace functionality.'}


def stop_group(child):
    if child is None:
        return
    # Popen(start_new_session=True) owns this process group. Never search by process name.
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        child.wait(timeout=3)
    except subprocess.TimeoutExpired:
        pass
    # Descendants can remain even when the leader has exited.
    try:
        os.killpg(child.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    child.wait(timeout=3)


def start_xvfb(log):
    read_fd, write_fd = os.pipe()
    child = None
    try:
        child = subprocess.Popen(['Xvfb', '-displayfd', str(write_fd), '-screen', '0', '1280x800x24',
                                  '-nolisten', 'tcp', '-ac'], pass_fds=(write_fd,),
                                 stdout=log, stderr=log, start_new_session=True)
        os.close(write_fd); write_fd = None
        deadline = time.monotonic()+15
        data = b''
        while b'\n' not in data and time.monotonic() < deadline:
            readable, _, _ = select.select([read_fd], [], [], .2)
            if readable:
                chunk = os.read(read_fd, 64)
                if not chunk:
                    break
                data += chunk
            if child.poll() is not None:
                break
        if not re.fullmatch(rb'\d+\n', data):
            raise RuntimeError('Xvfb failed to allocate a display; inspect xvfb.log.')
        return child, ':'+data.decode().strip()
    except BaseException:
        stop_group(child)
        raise
    finally:
        os.close(read_fd)
        if write_fd is not None:
            os.close(write_fd)


class DemoHandler(http.server.BaseHTTPRequestHandler):
    demo_case = 'direct'

    def do_GET(self):
        if self.path == '/demo.html':
            content = (DEMO_ROOT/(self.demo_case+'.html')).read_bytes()
            mime = 'text/html; charset=utf-8'
        elif self.path == '/demo.js':
            content, mime = (DEMO_ROOT/(self.demo_case+'.js')).read_bytes(), 'application/javascript'
        else:
            self.send_error(404); return
        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers(); self.wfile.write(content)

    def log_message(self, fmt, *args):
        pass


def write_report(output, status, result, demo_case=None):
    """Render only this run's observed data; escape all browser-controlled strings."""
    esc = lambda value: html.escape(str(value), quote=True)
    sources = result['sources'] if result else []
    trace = result['trace'] if result else {}
    cookie = trace.get('cookie', 'No validated cookie result')
    lines = ['CookieTrace result', 'Status: '+str(status['status']),
             'Details: '+str(status.get('message', '')), 'Cookie: '+cookie,
             'Source records: '+str(len(sources))]
    if demo_case:
        lines += ['Demo: '+demo_case, 'Expected cookie: '+DEMO_NAME+'='+DEMO_VALUE,
                  'Expected literals: '+DEMO_NAME+', '+DEMO_VALUE]
    rows = []
    for source in sources:
        lines.append(f"- {source['string_value']!r} | {source['script_name']} | position {source['position']}")
        rows.append('<tr><td><code>'+esc(source['string_value'])+'</code></td><td>'+esc(source['script_name'])+'</td><td>'+esc(source['position'])+'</td></tr>')
    (output/'summary.txt').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    expectation = ('<h2>Expected demo output</h2><p><code>'+DEMO_NAME+'='+DEMO_VALUE+
                   '</code></p><p>The trace should include the cookie name and value literals.</p>') if demo_case else ''
    links = ['<a href="status.json">Status JSON</a>', '<a href="browser.log">Browser log</a>']
    if result:
        links += ['<a href="sources.json">Source JSON</a>', '<a href="paths.json">Path JSON</a>']
    document = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>CookieTrace result</title><style>body{font:16px/1.6 system-ui,sans-serif;max-width:1100px;margin:40px auto;padding:0 24px;color:#183044}h1,h2{line-height:1.2}table{border-collapse:collapse;width:100%}td,th{padding:12px;border:1px solid #ced8df;text-align:left;overflow-wrap:anywhere}code{white-space:pre-wrap}a{color:#075f97}.status{padding:16px;background:#edf4f7;border-radius:8px}</style>
<h1>CookieTrace result</h1>'''
    document += '<p class="status"><strong>'+esc(status['status'])+'</strong><br>'+esc(status.get('message',''))+'</p>'
    document += expectation+'<h2>Observed cookie</h2><p><code>'+esc(cookie)+'</code></p>'
    document += '<h2>Observed source records</h2><table><tr><th>Literal</th><th>Script</th><th>Position</th></tr>'
    document += ''.join(rows) or '<tr><td colspan="3">No validated source records were produced.</td></tr>'
    document += '</table><h2>Run files</h2><p>'+' | '.join(links)+'</p></html>'
    (output/'report.html').write_text(document, encoding='utf-8')


def read_result(raw, run_id, target, prefix, demo=False):
    """Only accept the exact pair from this run and a completed three-timestamp record."""
    source_path = raw/f'job_{run_id}.json'
    path_path = raw/f'job_{run_id}_path.json'
    try:
        source_bytes, path_bytes = source_path.read_bytes(), path_path.read_bytes()
        sources, trace = json.loads(source_bytes), json.loads(path_bytes)
    except (OSError, ValueError, UnicodeError):
        return None, 'Waiting for both complete JSON files.'
    if not isinstance(sources, list) or not sources:
        return None, 'Source JSON is empty or is not an array.'
    if any(not isinstance(s, dict) or not isinstance(s.get('position'), int)
           or not isinstance(s.get('script_name'), str) or not isinstance(s.get('string_value'), str)
           for s in sources):
        return None, 'Source JSON does not match the expected CookieTrace schema.'
    if not isinstance(trace, dict) or not isinstance(trace.get('cookie'), str):
        return None, 'Path JSON has no cookie string.'
    timestamps = trace.get('timestamps')
    if not isinstance(timestamps, list) or len(timestamps) < 3 or any(
            not isinstance(t, (int, float)) or isinstance(t, bool) or not math.isfinite(t) for t in timestamps):
        return None, 'Waiting for the final path JSON with three stage timestamps.'
    if not isinstance(trace.get('source_scripts'), list):
        return None, 'Waiting for final source_scripts metadata.'
    cookie = trace['cookie']
    if '=' not in cookie:
        return None, 'Malformed cookie string in result.'
    found_name = cookie.split('=', 1)[0].strip()
    found_prefix = re.split(r'[0-9]', found_name, maxsplit=1)[0]
    if target and found_name != target:
        return None, f'Engine selected {found_name!r}, but the requested exact cookie is {target!r}. The legacy prefix matcher may have stopped at another cookie.'
    if prefix != found_prefix:
        return None, f'Output cookie prefix {found_prefix!r} does not match {prefix!r}.'
    if demo:
        literals = '\n'.join(s['string_value'] for s in sources)
        if DEMO_NAME not in literals or DEMO_VALUE not in literals:
            return None, 'Demo sources do not contain the expected cookie-name and value literals.'
        if cookie.split('=', 1)[1].split(';', 1)[0] != DEMO_VALUE:
            return None, 'Demo cookie value does not match.'
    fingerprint = hashlib.sha256(source_bytes+b'\0'+path_bytes).hexdigest()
    return {'sources': sources, 'trace': trace, 'fingerprint': fingerprint,
            'cookie_name': found_name}, ''


def monitor(child, raw, run_id, target, prefix, timeout, settle, demo=False):
    start = time.monotonic()
    fingerprint, stable_since = None, None
    reason = 'No result received.'
    while time.monotonic()-start < timeout:
        result, reason = read_result(raw, run_id, target, prefix, demo)
        now = time.monotonic()
        if result:
            if result['fingerprint'] != fingerprint:
                fingerprint, stable_since = result['fingerprint'], now
            if now-stable_since >= settle:
                if child.poll() not in (None, 0):
                    return 'browser_failed', 4, None, 'Browser exited unsuccessfully despite a result file.'
                return 'success', 0, result, 'Validated source/path JSON and target cookie.'
        else:
            fingerprint, stable_since = None, None
        code = child.poll()
        if code is not None and not result:
            return ('browser_failed', 4, None, reason) if code else ('no_result', 3, None, reason)
        if code not in (None, 0):
            return 'browser_failed', 4, None, reason
        time.sleep(.2)
    return 'timeout', 124, None, reason


def browser_command(a, chrome, profile, url):
    prefix = DEMO_NAME if a.demo else a.cookie_prefix
    flags = f'--run_mode=backtrack --accessing_domain=job --cookie_prefix={prefix} --instance_id={a.run_id}'
    cmd = [str(chrome), '--disable-gpu', '--no-sandbox', '--disable-setuid-sandbox',
           '--no-first-run', '--no-default-browser-check', '--disable-background-networking',
           '--disable-component-update', '--disable-sync', '--disable-extensions',
           '--disable-breakpad', '--disable-crash-reporter', '--password-store=basic',
           '--disk-cache-size=0', '--media-cache-size=0', '--disk-cache-dir=/dev/null',
           '--user-data-dir='+str(profile), '--js-flags='+flags]
    if a.proxy:
        cmd.append('--proxy-server='+a.proxy)
    else:
        cmd.append('--no-proxy-server')
    if a.ignore_certificate_errors:
        cmd.append('--ignore-certificate-errors')
    return cmd+[url]


def run(a):
    started = time.monotonic()
    status = {'status': 'failed', 'exit_code': 2, 'run_id': a.run_id}
    result = None
    browser = xvfb = server = None
    temp = None
    files = []
    try:
        OUTPUT.mkdir(parents=True, exist_ok=True)
        report = runtime_check(BROWSER)
        write_json(OUTPUT/'preflight.json', report)
        if a.check:
            status.update(status='check_passed', exit_code=0, message=report['scope'])
            return 0
        if not re.fullmatch(r'[a-f0-9]{32}', a.run_id):
            raise RuntimeError('Invalid run ID.')
        if any(RAW.iterdir()):
            raise RuntimeError('Raw output directory must be empty; refusing to accept old results.')
        temp = tempfile.TemporaryDirectory(prefix='cookietrace-')
        profile = Path(temp.name)/'profile'
        profile.mkdir()
        Path('/tmp/ct-home').mkdir(exist_ok=True)
        xvfb_log = (OUTPUT/'xvfb.log').open('wb'); files.append(xvfb_log)
        browser_log = (OUTPUT/'browser.log').open('wb'); files.append(browser_log)
        xvfb, display = start_xvfb(xvfb_log)
        target = DEMO_NAME if a.demo else a.cookie_name
        prefix = DEMO_NAME if a.demo else a.cookie_prefix
        url = a.url
        if a.demo:
            handler = type('SelectedDemoHandler', (DemoHandler,), {'demo_case': getattr(a, 'demo_case', 'direct')})
            server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            url = f'http://127.0.0.1:{server.server_port}/demo.html'
        env = os.environ.copy(); env['DISPLAY'] = display
        for key in ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy'):
            env.pop(key, None)
        command = browser_command(a, BROWSER/'chrome', profile, url)
        write_json(OUTPUT/'command.json', {'argv': command, 'url': url, 'engine_prefix': prefix,
                                         'exact_cookie_name': target, 'display': display,
                                         'completion': 'Validated result JSON; not document.readyState timing.'})
        browser = subprocess.Popen(command, cwd=temp.name, env=env, stdout=browser_log,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        outcome, code, result, reason = monitor(browser, RAW, a.run_id, target, prefix,
                                              a.timeout, a.settle_seconds, a.demo)
        if result:
            write_json(OUTPUT/'sources.json', result['sources'])
            write_json(OUTPUT/'paths.json', result['trace'])
        status.update(status=outcome, exit_code=code, message=reason,
                      browser_returncode_before_cleanup=browser.poll(),
                      source_count=len(result['sources']) if result else 0)
        return code
    except KeyboardInterrupt:
        status.update(status='interrupted', exit_code=130, message='Interrupted; only this run is being stopped.')
        return 130
    except Exception as exc:
        status.update(status='failed', exit_code=2, message=str(exc))
        return 2
    finally:
        # Avoid interruption halfway through cleanup; Docker's host watchdog remains in force.
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        stop_group(browser)
        stop_group(xvfb)
        if server:
            server.shutdown(); server.server_close()
        for file in files:
            file.close()
        if temp:
            temp.cleanup()
        status['elapsed_seconds'] = round(time.monotonic()-started, 3)
        try:
            write_json(OUTPUT/'status.json', status)
            if not a.check:
                write_report(OUTPUT, status, result, getattr(a, 'demo_case', 'direct') if a.demo else None)
        except OSError as exc:
            print(f'Cannot write status.json: {exc}', file=sys.stderr)
        print(json.dumps(status), flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--demo', action='store_true')
    p.add_argument('--demo-case', choices=['direct', 'function'], default='direct')
    mode.add_argument('--url')
    p.add_argument('--run-id', required=True)
    p.add_argument('--cookie-prefix')
    p.add_argument('--cookie-name')
    p.add_argument('--timeout', type=float, default=120)
    p.add_argument('--settle-seconds', type=float, default=2)
    p.add_argument('--proxy')
    p.add_argument('--ignore-certificate-errors', action='store_true')
    def interrupted(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    return run(p.parse_args())


if __name__ == '__main__':
    sys.exit(main())
