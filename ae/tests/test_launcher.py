import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


launcher = load('launcher_under_test', ROOT/'launcher.py')
runtime = load('runtime_under_test', ROOT/'docker'/'runtime.py')
RUN_ID = 'a'*32


def pair(raw, name='ct_demo_cookie', value='ct_demo_value', run_id=RUN_ID):
    sources = [{'position': 10, 'script_name': 'http://localhost/demo.js', 'string_value': name},
               {'position': 20, 'script_name': 'http://localhost/demo.js', 'string_value': value}]
    trace = {'cookie': name+'='+value+'; path=/', 'timestamps': [1., 2., 3.],
             'source_scripts': ['http://localhost/demo.js']}
    (raw/f'job_{run_id}.json').write_text(json.dumps(sources))
    (raw/f'job_{run_id}_path.json').write_text(json.dumps(trace))


class HostTests(unittest.TestCase):
    def test_safe_command_with_spaces_and_arbitrary_url_path(self):
        with tempfile.TemporaryDirectory(prefix='ct test ') as folder:
            args = launcher.parser().parse_args(['--url', 'https://example.org/a/b?c=1&d=2',
                         '--cookie-name', '__cmpconsent123', '--browser-dir', folder,
                         '--output-dir', folder+'/results'])
            launcher.validate(args)
            self.assertEqual(args.prefix, '__cmpconsent')
            cmd = launcher.create_command(args, Path(folder)/'run', RUN_ID, 'image@sha256:dummy')
            self.assertIn(args.url, cmd)
            self.assertIn(f'type=bind,src={Path(folder).resolve()},dst=/opt/cookietrace/browser,readonly', cmd)
            self.assertIn(f'type=bind,src={Path(folder)/"run"/"raw"},dst={launcher.INTERNAL_OUTPUT}', cmd)
            self.assertNotIn('--privileged', cmd)
            self.assertNotIn('--proxy', cmd)

    def test_dry_run_does_not_touch_files_or_docker(self):
        with tempfile.TemporaryDirectory() as folder:
            args = launcher.parser().parse_args(['--demo', '--dry-run', '--output-dir', folder+'/missing'])
            with patch.object(launcher.subprocess, 'run', side_effect=AssertionError('Docker invoked')):
                with patch('builtins.print'):
                    self.assertEqual(launcher.execute(args), 0)
            self.assertFalse((Path(folder)/'missing').exists())

    def test_bad_inputs_rejected(self):
        cases = [ ['--url', 'example.com'],
                  ['--url', 'file:///tmp/a', '--cookie-name', 'a'],
                  ['--url', 'example.com', '--cookie-name', 'a --bad'],
                  ['--url', 'example.com', '--cookie-prefix', 'a1'],
                  ['--url', 'example.com', '--cookie-name', 'a', '--proxy', 'http://127.0.0.1:7895'],
                  ['--demo', '--timeout', 'nan'], ['--demo', '--timeout', '1'],
                  ['--demo', '--proxy', 'http://proxy:1234'],
                  ['--demo', '--cookie-name', 'a'] ]
        for argv in cases:
            with self.subTest(argv=argv), self.assertRaises(ValueError):
                launcher.validate(launcher.parser().parse_args(argv))

    def test_loopback_proxy_explicit_host_network(self):
        args = launcher.parser().parse_args(['--url', 'example.com', '--cookie-name', '_ga',
                                            '--network', 'host', '--proxy', 'http://127.0.0.1:7895'])
        launcher.validate(args)
        self.assertEqual(args.url, 'https://example.com')

    def test_cleanup_refuses_container_with_different_label(self):
        inspected = subprocess.CompletedProcess([], 0, stdout=json.dumps([{'Config': {'Labels': {launcher.LABEL:'other'}}}]))
        with patch.object(launcher, 'docker', return_value=inspected) as docker:
            launcher.remove_owned('some-container', RUN_ID)
            self.assertEqual(docker.call_count, 1)

    def test_host_orchestration_records_image_and_checks_status(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            bundle = root/'sys'; bundle.mkdir()
            chrome = bundle/'chrome'; chrome.write_text('simulated'); chrome.chmod(0o755)
            args = launcher.parser().parse_args(['--demo', '--browser-dir', str(bundle),
                                                '--output-dir', str(root/'results')])
            def create(cmd, **kwargs):
                self.assertEqual(cmd[:2], ['docker', 'create'])
                runs = list((root/'results').iterdir())
                (runs[0]/'status.json').write_text(json.dumps({'status':'success'}))
                return subprocess.CompletedProcess(cmd, 0, stdout='id')
            state = subprocess.CompletedProcess([], 0, stdout=json.dumps([{'State':{'ExitCode':0,'OOMKilled':False}}]))
            with patch.object(launcher,'check_engine'), patch.object(launcher,'inspect_image',return_value='sha256:verified'), \
                 patch.object(launcher.subprocess,'run',side_effect=create), patch.object(launcher.subprocess,'Popen') as popen, \
                 patch.object(launcher,'docker',return_value=state), patch.object(launcher,'remove_owned') as cleanup, \
                 patch('builtins.print'):
                popen.return_value.wait.return_value=0
                popen.return_value.poll.return_value=0
                self.assertEqual(launcher.execute(args),0)
                cleanup.assert_called_once()
            run = next((root/'results').iterdir())
            metadata = json.loads((run/'launcher.json').read_text())
            self.assertEqual(metadata['image_id'],'sha256:verified')
            self.assertEqual(metadata['launcher_exit_code'],0)
            self.assertEqual(list(bundle.iterdir()),[chrome])


class ResultTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.raw = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_successful_demo(self):
        pair(self.raw)
        data, reason = runtime.read_result(self.raw, RUN_ID, 'ct_demo_cookie', 'ct_demo_cookie', True)
        self.assertIsNotNone(data, reason)

    def test_partial_json_and_incomplete_timestamp_not_success(self):
        pair(self.raw)
        p = self.raw/f'job_{RUN_ID}_path.json'
        p.write_text('{')
        self.assertIsNone(runtime.read_result(self.raw, RUN_ID, 'ct_demo_cookie', 'ct_demo_cookie')[0])
        p.write_text(json.dumps({'cookie':'ct_demo_cookie=v', 'timestamps':[1, 2]}))
        self.assertIsNone(runtime.read_result(self.raw, RUN_ID, 'ct_demo_cookie', 'ct_demo_cookie')[0])

    def test_exact_name_rejects_other_cookie_with_same_prefix(self):
        pair(self.raw, name='cookie123')
        data, reason = runtime.read_result(self.raw, RUN_ID, 'cookie456', 'cookie')
        self.assertIsNone(data)
        self.assertIn('cookie123', reason)

    def test_wrong_run_id_not_accepted(self):
        pair(self.raw, run_id='b'*32)
        self.assertIsNone(runtime.read_result(self.raw, RUN_ID, 'ct_demo_cookie', 'ct_demo_cookie')[0])

    def test_demo_rejects_unexpected_source_literals(self):
        pair(self.raw, value='wrong')
        self.assertIsNone(runtime.read_result(self.raw, RUN_ID, 'ct_demo_cookie', 'ct_demo_cookie', True)[0])


@unittest.skipUnless(sys.platform == 'linux', 'Real process-group lifecycle tests require Linux')
class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ct-runtime-test-')
        self.root = Path(self.temp.name)
        self.children = []
        self.old_signals = {s: signal.getsignal(s) for s in (signal.SIGTERM, signal.SIGINT)}

    def tearDown(self):
        for child in self.children:
            runtime.stop_group(child)
        for sig, handler in self.old_signals.items():
            signal.signal(sig, handler)
        self.temp.cleanup()

    def sleeper(self):
        p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], start_new_session=True)
        self.children.append(p)
        return p

    def test_late_pair_after_partial_write(self):
        child = self.sleeper()
        def writer():
            (self.root/f'job_{RUN_ID}.json').write_text('[')
            time.sleep(.25)
            pair(self.root)
        t = threading.Thread(target=writer); t.start()
        result = runtime.monitor(child, self.root, RUN_ID, 'ct_demo_cookie', 'ct_demo_cookie', 3, .2, True)
        t.join()
        self.assertEqual(result[0], 'success')

    def test_timeout_and_unrelated_process_survives(self):
        child, unrelated = self.sleeper(), self.sleeper()
        result = runtime.monitor(child, self.root, RUN_ID, 'a', 'a', .4, .1)
        self.assertEqual(result[1], 124)
        runtime.stop_group(child)
        self.assertIsNone(unrelated.poll())

    def test_browser_crash_is_not_success(self):
        child = subprocess.Popen([sys.executable, '-c', 'raise SystemExit(7)'], start_new_session=True)
        self.children.append(child); child.wait()
        pair(self.root)
        self.assertEqual(runtime.monitor(child, self.root, RUN_ID, 'ct_demo_cookie', 'ct_demo_cookie', 1, .1)[1], 4)

    def test_local_demo_http_server(self):
        server = runtime.http.server.ThreadingHTTPServer(('127.0.0.1',0), runtime.DemoHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            js = urlopen(f'http://127.0.0.1:{server.server_port}/demo.js', timeout=2).read()
            self.assertIn(b'document.cookie', js)
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_full_runtime_orchestration_with_simulated_browser(self):
        # Simulator tests control flow and file validation, NOT real V8 instrumentation.
        bundle = self.root/'browser'; bundle.mkdir()
        output = self.root/'output'; output.mkdir()
        raw = output/'raw'; raw.mkdir()
        executable = bundle/'chrome'
        executable.write_text('''#!/usr/bin/env python3
import json, os, pathlib, sys, time
flags=next(a for a in sys.argv if a.startswith('--js-flags='))
run_id=flags.split('--instance_id=')[1].split()[0]
p=pathlib.Path(os.environ['CT_TEST_RAW'])
sources=[dict(position=1,script_name='http://local/demo.js',string_value='ct_demo_cookie'),dict(position=2,script_name='http://local/demo.js',string_value='ct_demo_value')]
(p/('job_'+run_id+'.json')).write_text(json.dumps(sources))
(p/('job_'+run_id+'_path.json')).write_text(json.dumps(dict(cookie='ct_demo_cookie=ct_demo_value; path=/', timestamps=[1,2,3], source_scripts=['http://local/demo.js'])))
time.sleep(60)
''')
        executable.chmod(0o755)
        fake_xvfb = self.sleeper()
        a = type('Args', (), dict(run_id=RUN_ID, demo=True, check=False, url=None,
                  cookie_name=None, cookie_prefix=None, proxy=None, ignore_certificate_errors=False,
                  timeout=3, settle_seconds=.2))()
        with patch.object(runtime,'BROWSER',bundle), patch.object(runtime,'OUTPUT',output), \
             patch.object(runtime,'RAW',raw), patch.object(runtime,'runtime_check',return_value={'scope':'simulated'}), \
             patch.object(runtime,'start_xvfb',return_value=(fake_xvfb, ':999')), \
             patch.dict(os.environ, {'CT_TEST_RAW':str(raw)}), patch('builtins.print'):
            self.assertEqual(runtime.run(a), 0)
        self.assertTrue((output/'sources.json').is_file())
        self.assertEqual(json.loads((output/'status.json').read_text())['status'], 'success')
        self.assertIsNotNone(fake_xvfb.poll())


if __name__ == '__main__':
    unittest.main(verbosity=2)
