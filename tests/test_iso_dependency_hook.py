import pathlib
import subprocess
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
HOOK = ROOT / "build/config/hooks/normal/03-install-pip-deps.hook.chroot"


class TestIsoDependencyHook(unittest.TestCase):
    def test_hook_has_clean_posix_shebang_and_valid_shell_syntax(self):
        raw = HOOK.read_bytes()
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"), "hook must not start with a UTF-8 BOM")
        self.assertTrue(raw.startswith(b"#!/bin/sh\n"), "shebang must be the first bytes")
        subprocess.run(["sh", "-n", str(HOOK)], check=True)

    def test_hook_fails_visibly_instead_of_hiding_pip_errors(self):
        source = HOOK.read_text(encoding="utf-8")
        self.assertIn("set -eu", source)
        self.assertIn("python3 -m pip install", source)
        self.assertNotIn("2>/dev/null", source)
        self.assertNotIn("|| echo", source)

    def test_correct_python_distributions_and_runtime_modules_are_declared(self):
        source = HOOK.read_text(encoding="utf-8")
        self.assertIn("mss", source)
        self.assertNotIn("python-mss", source)
        for module in (
            "speech_recognition",
            "pyaudio",
            "pocketsphinx",
            "pyttsx3",
            "pyautogui",
            "mss",
            "transliterate",
            "indic_transliteration",
        ):
            self.assertIn(module, source)


if __name__ == "__main__":
    unittest.main()
