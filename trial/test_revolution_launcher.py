"""Launcher network configuration only: no files, keys, or network are used."""
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import try_revolution as launcher


class LauncherNetworkTest(unittest.TestCase):
    def environment(self, proxies):
        with patch.object(launcher, "RUNTIME", Path("TEST_FIXTURE_RUNTIME")), \
             patch.object(Path, "exists", return_value=False), \
             patch.object(Path, "write_text"), \
             patch.object(launcher.urllib.request, "getproxies", return_value=proxies):
            return launcher.isolated_environment("TEST_FIXTURE.db", sample=False,
                                                 contact_email="test@example.invalid")

    def test_system_proxy_survives_loopback_bypass(self):
        with patch.dict(os.environ, {}, clear=True):
            env = self.environment({"https": "http://127.0.0.1:12345"})
        self.assertEqual(env["HTTPS_PROXY"], "http://127.0.0.1:12345")
        self.assertIn("127.0.0.1", env["NO_PROXY"])
        self.assertEqual(env["NO_PROXY"], env["no_proxy"])

    def test_explicit_environment_proxy_keeps_precedence(self):
        with patch.dict(os.environ, {"HTTPS_PROXY": "http://127.0.0.1:12346"}, clear=True):
            env = self.environment({"https": "http://127.0.0.1:12345"})
        self.assertEqual(env["HTTPS_PROXY"], "http://127.0.0.1:12346")

    def test_no_proxy_is_invented_when_none_is_configured(self):
        with patch.dict(os.environ, {}, clear=True):
            env = self.environment({})
        self.assertNotIn("HTTPS_PROXY", env)

    def test_resume_accepts_only_existing_adjacent_database_and_secret(self):
        runtime = Path("TEST_FIXTURE_RUNTIME").resolve()
        with patch.object(Path, "is_file", return_value=True):
            self.assertEqual(launcher.resume_database(runtime,"saved.db"), (runtime/"saved.db").as_posix())
            with self.assertRaises(RuntimeError):
                launcher.resume_database(runtime,"../elsewhere.db")
            with self.assertRaises(RuntimeError):
                launcher.resume_database(runtime,"saved.txt")
        with patch.object(Path, "is_file", return_value=False):
            with self.assertRaises(RuntimeError):
                launcher.resume_database(runtime,"saved.db")


if __name__ == "__main__":
    unittest.main()
