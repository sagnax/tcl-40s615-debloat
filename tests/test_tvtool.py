import contextlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch, Mock, call

import tvtool


class FakeTV:
    identity = {"serial": "test", "hardware_serial": "test", "fingerprint": "test"}
    user = 0

    def __init__(self):
        self.states = {"org.example.one": 0, "org.example.two": 1}
        self.fail = None

    def state(self, pkg):
        return self.states[pkg]

    def set_state(self, pkg, state):
        # Simula perda da conexão depois da alteração na TV.
        self.states[pkg] = state
        if pkg == self.fail:
            raise RuntimeError("conexão perdida")


class ToolTests(unittest.TestCase):
    def test_parse_per_user_state(self):
        dump = '  User 0: installed=true hidden=false enabled=0\n  User 10: installed=true enabled=3\n'
        self.assertEqual(tvtool.enabled_state(dump, 0), 0)
        self.assertEqual(tvtool.enabled_state(dump, 10), 3)
        with self.assertRaises(ValueError):
            tvtool.enabled_state('User 0: installed=false enabled=0', 0)
        with self.assertRaises(ValueError):
            tvtool.enabled_state('User 0: installed=true enabled=9', 0)

    def test_protected_and_invalid_manifest(self):
        for name in ['com.google.android.gms', 'com.android.systemui', 'com.tcl.tvinput',
                     'com.google.android.apps.mediashell', 'org.example.launcher', 'x; reboot']:
            with self.subTest(name=name), self.assertRaises(ValueError):
                # Cast receiver conhecido também é protegido explicitamente.
                tvtool.manifest_packages({'packages': [{'package': name, 'reason': 'test'}]})
        with self.assertRaises(ValueError):
            tvtool.manifest_packages({'packages': [{'package': 'org.example.app'}]})

    def test_dry_run_and_interrupted_restore(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(tvtool, 'ROOT', Path(tmp)), contextlib.redirect_stdout(io.StringIO()):
            manifest = Path(tmp) / 'manifest.json'
            manifest.write_text(json.dumps({'packages': [
                {'package': 'org.example.one', 'reason': 'unused'},
                {'package': 'org.example.two', 'reason': 'unused'},
            ]}))
            tv = FakeTV()
            args = SimpleNamespace(manifest=manifest, execute=False)
            tvtool.apply(tv, args)
            self.assertEqual(tv.states['org.example.one'], 0)
            self.assertFalse((Path(tmp) / 'reports').exists())
            args.execute = True
            tv.fail = 'org.example.two'
            with self.assertRaises(RuntimeError):
                tvtool.apply(tv, args)
            journal = next((Path(tmp) / 'reports').glob('*journal.json'))
            self.assertEqual(tvtool.read_json(journal)['changes'][1]['status'], 'pending')
            tv.fail = None
            tvtool.restore(tv, SimpleNamespace(journal=journal, execute=True))
            self.assertEqual(tv.states, {'org.example.one': 0, 'org.example.two': 1})
            tvtool.restore(tv, SimpleNamespace(journal=journal, execute=True))

    def test_restore_refuses_different_tv(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = Path(tmp) / 'journal.json'
            tvtool.save_json(journal, {'identity': {}, 'user': 0, 'changes': []})
            with self.assertRaises(ValueError):
                tvtool.restore(FakeTV(), SimpleNamespace(journal=journal, execute=True))

    def test_restore_dry_run_and_external_change(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            tv = FakeTV()
            journal = Path(tmp) / 'journal.json'
            data = {'identity': tv.identity, 'user': 0, 'changes': [
                {'package': 'org.example.one', 'before': 0, 'status': 'applied'}]}
            tvtool.save_json(journal, data)
            tv.states['org.example.one'] = 3
            tvtool.restore(tv, SimpleNamespace(journal=journal, execute=False))
            self.assertEqual(tv.states['org.example.one'], 3)
            self.assertEqual(tvtool.read_json(journal), data)
            tv.states['org.example.one'] = 2
            with self.assertRaises(ValueError):
                tvtool.restore(tv, SimpleNamespace(journal=journal, execute=True))
            self.assertEqual(tv.states['org.example.one'], 2)

    def test_restore_home_enables_original_before_selection(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            journal = Path(tmp) / 'home.json'
            data = {'identity': FakeTV.identity, 'user': 0,
                    'before_home': 'com.google.android.tvlauncher/.MainActivity',
                    'after_home': 'me.efesser.flauncher/.MainActivity',
                    'before_google_state': 0,
                    'before_accessibility': 'com.spocky.projengmenu/TestService',
                    'status': 'applied'}
            tvtool.save_json(journal, data)
            tv = Mock(identity=FakeTV.identity, user=0)
            tv.state.return_value = 3
            tv.shell.side_effect = lambda *a: data['after_home'] if a[:2] == ('cmd', 'package') else ''
            args = SimpleNamespace(journal=journal, execute=False)
            tvtool.restore_home(tv, args)
            tv.set_state.assert_not_called()
            args.execute = True
            tvtool.restore_home(tv, args)
            enable_call = call.set_state('com.google.android.tvlauncher', 0)
            home_call = call.shell('cmd', 'package', 'set-home-activity', '--user', '0', data['before_home'])
            self.assertLess(tv.mock_calls.index(enable_call), tv.mock_calls.index(home_call))
            tv.set_state.assert_called_once_with('com.google.android.tvlauncher', 0)
            self.assertEqual(tvtool.read_json(journal)['status'], 'restored')

    def test_restore_removed_app_dry_run_then_install_before_state(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            journal = Path(tmp) / 'removed.json'
            data = {'identity': FakeTV.identity, 'user': 0, 'package': 'com.tcl.smartalexa',
                    'before_state': 0, 'operation': 'pm uninstall -k --user 0', 'status': 'applied'}
            tvtool.save_json(journal, data)
            tv = Mock(identity=FakeTV.identity, user=0)
            tv.shell.return_value = '  User 0: installed=false enabled=0'
            args = SimpleNamespace(journal=journal, execute=False)
            tvtool.restore_app(tv, args)
            self.assertEqual(tv.shell.call_count, 1)
            tv.set_state.assert_not_called()
            args.execute = True
            tvtool.restore_app(tv, args)
            install_call = call.shell('cmd', 'package', 'install-existing', '--user', '0', data['package'])
            state_call = call.set_state(data['package'], 0)
            self.assertLess(tv.mock_calls.index(install_call), tv.mock_calls.index(state_call))
            self.assertEqual(tvtool.read_json(journal)['status'], 'restored')


if __name__ == '__main__':
    unittest.main()
