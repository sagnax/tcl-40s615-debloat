import contextlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import tvtool


class HomeTV:
    identity = {"serial": "transport-test", "hardware_serial": "device-test", "fingerprint": "build-test"}
    user = 0

    def __init__(self):
        self.current = tvtool.HOME_ORIGINAL
        self.states = {"com.google.android.tvlauncher": 0, "me.efesser.flauncher": 0}
        self.accessibility = "com.spocky.projengmenu/TestService:org.example.reader/Service"
        self.writes = []
        self.fail_selection = False

    def state(self, package):
        return self.states[package]

    def set_state(self, package, state):
        self.writes.append((package, state))
        self.states[package] = state

    def shell(self, *args):
        if args[:3] == ("cmd", "package", "resolve-activity"):
            return self.current
        if args[:3] == ("cmd", "package", "set-home-activity"):
            if self.fail_selection and args[-1] == tvtool.HOME_TARGET:
                raise RuntimeError("Falha simulada na seleção")
            self.current = args[-1]
        elif args[:3] == ("settings", "get", "secure"):
            return self.accessibility
        elif args[:3] == ("settings", "put", "secure"):
            self.accessibility = args[-1]
        elif args[:2] == ("am", "start"):
            return "Status: ok\n"
        return ""


class OpsTV:
    identity = HomeTV.identity
    user = 0

    def __init__(self):
        self.modes = {"RUN_IN_BACKGROUND": "allow", "RUN_ANY_IN_BACKGROUND": "foreground"}
        self.writes = []

    def state(self, _):
        return 0

    def shell(self, *args):
        if args[:3] == ("cmd", "appops", "get"):
            return f"{args[-1]}: {self.modes[args[-1]]}"
        if args[:3] == ("cmd", "appops", "set"):
            self.writes.append(args)
            self.modes[args[-2]] = args[-1]
        return ""


class PublicWorkflowTests(unittest.TestCase):
    def test_identity_allows_transport_change_only_for_same_physical_device(self):
        saved = HomeTV.identity
        current = {**saved, "serial": "new-transport"}
        self.assertTrue(tvtool.identity_matches(saved, current))
        self.assertFalse(tvtool.identity_matches(saved, {**current, "hardware_serial": "other-device"}))
        self.assertFalse(tvtool.identity_matches(saved, {**current, "fingerprint": "other-build"}))
        unknown = {**saved, "hardware_serial": "unknown"}
        self.assertFalse(tvtool.identity_matches(unknown, {**unknown, "serial": "new-transport"}))
        self.assertFalse(tvtool.identity_matches({}, saved))

    def test_home_dry_run_preserves_state_and_accessibility(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(tvtool, "ROOT", Path(tmp)), contextlib.redirect_stdout(io.StringIO()):
            tv = HomeTV()
            before = tv.accessibility
            tvtool.home(tv, SimpleNamespace(execute=False))
            self.assertFalse(tv.writes)
            self.assertEqual(tv.accessibility, before)
            self.assertFalse((Path(tmp) / "reports").exists())

    def test_home_preserves_other_accessibility_services_and_restores(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(tvtool, "ROOT", Path(tmp)), contextlib.redirect_stdout(io.StringIO()):
            tv = HomeTV()
            before = tv.accessibility
            tvtool.home(tv, SimpleNamespace(execute=True))
            self.assertEqual(tv.current, tvtool.HOME_TARGET)
            self.assertEqual(tv.states["com.google.android.tvlauncher"], 3)
            self.assertEqual(tv.accessibility, "org.example.reader/Service")
            journal = next((Path(tmp) / "reports").glob("*-home.json"))
            tvtool.restore_home(tv, SimpleNamespace(journal=journal, execute=True))
            self.assertEqual(tv.current, tvtool.HOME_ORIGINAL)
            self.assertEqual(tv.states["com.google.android.tvlauncher"], 0)
            self.assertEqual(tv.accessibility, before)

    def test_home_failure_restores_original_launcher(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(tvtool, "ROOT", Path(tmp)), contextlib.redirect_stdout(io.StringIO()):
            tv = HomeTV()
            tv.fail_selection = True
            before = tv.accessibility
            with self.assertRaises(RuntimeError):
                tvtool.home(tv, SimpleNamespace(execute=True))
            self.assertEqual(tv.current, tvtool.HOME_ORIGINAL)
            self.assertEqual(tv.states["com.google.android.tvlauncher"], 0)
            self.assertEqual(tv.accessibility, before)
            journal = next((Path(tmp) / "reports").glob("*-home.json"))
            self.assertEqual(tvtool.read_json(journal)["status"], "rolled-back")

    def test_unknown_home_does_not_disable_anything(self):
        tv = HomeTV()
        tv.current = "org.example.home/.Main"
        with self.assertRaises(ValueError):
            tvtool.home(tv, SimpleNamespace(execute=True))
        self.assertFalse(tv.writes)

    def test_appops_restore_keeps_original_modes_and_never_changes_microphone(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(tvtool, "ROOT", Path(tmp)), contextlib.redirect_stdout(io.StringIO()):
            tv = OpsTV()
            original = dict(tv.modes)
            tvtool.alexa(tv, SimpleNamespace(execute=False))
            self.assertFalse(tv.writes)
            tvtool.alexa(tv, SimpleNamespace(execute=True))
            self.assertTrue(all(x == "ignore" for x in tv.modes.values()))
            journal = next((Path(tmp) / "reports").glob("*-alexa.json"))
            tvtool.restore_alexa(tv, SimpleNamespace(journal=journal, execute=True))
            self.assertEqual(tv.modes, original)
            self.assertTrue(all("RECORD_AUDIO" not in cmd for cmd in tv.writes))

    def test_appops_rejects_unknown_output_or_uid_modes(self):
        self.assertEqual(tvtool.appop_mode("No operations.\nDefault mode: allow", "RUN_IN_BACKGROUND"), "allow")
        for output in ["Uid mode: RUN_IN_BACKGROUND: ignore", "permission denied", ""]:
            with self.subTest(output=output), self.assertRaises(ValueError):
                tvtool.appop_mode(output, "RUN_IN_BACKGROUND")

    def test_profiles_are_valid_and_do_not_disable_content_or_core(self):
        root = Path(__file__).resolve().parents[1]
        names = set()
        for path in (root / "profiles").glob("*.json"):
            names.update(x["package"] for x in tvtool.manifest_packages(json.loads(path.read_text())))
        self.assertEqual(names, {"com.google.android.katniss", "com.google.android.feedback",
                                 "com.google.android.tvrecommendations", "com.tcl.guard", "com.tcl.ttvs"})
        for package in ["com.tcl.tv", "com.tcl.system.server", "com.tcl.partnercustomizer"]:
            with self.assertRaises(ValueError):
                tvtool.manifest_packages({"packages": [{"package": package, "reason": "test"}]})


if __name__ == "__main__":
    unittest.main()
