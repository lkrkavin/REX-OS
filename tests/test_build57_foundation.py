import tempfile
import unittest
from pathlib import Path
from services.ecosystem import REXEcosystem, create_default_ecosystem
from services.desktop_control import DesktopControl
from services.command_router import DesktopCommandRouter

class TestEcosystem(unittest.TestCase):
    def test_default_modules(self):
        report=create_default_ecosystem().health()
        self.assertEqual(report["total"],6)
        self.assertEqual(report["registered"],6)
        self.assertEqual(report["online"],0)
    def test_offline_module(self):
        registry=REXEcosystem()
        registry.register("sample","Sample","test",lambda:False)
        self.assertEqual(registry.status("sample").state,"offline")
    def test_invalid_id(self):
        with self.assertRaises(ValueError):
            REXEcosystem().register("../bad","Bad","test")

class TestDesktopControl(unittest.TestCase):
    def test_default_denies_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            entry=Path(directory)/"sample.desktop"
            entry.write_text("[Desktop Entry]\nType=Application\nName=Sample\nExec=/usr/bin/true\n",encoding="utf-8")
            control=DesktopControl()
            control.desktop_dirs=(Path(directory),)
            result=control.launch_application("sample.desktop")
            self.assertFalse(result.success)
            self.assertIn("approval",result.message.lower())
    def test_invalid_entry_rejected(self):
        self.assertFalse(DesktopControl(lambda *_:True).launch_application("../bad.desktop").success)
    def test_no_shell_executor(self):
        control=DesktopControl()
        self.assertFalse(hasattr(control,"run_command"))
        self.assertFalse(hasattr(control,"execute_shell"))
    def test_keyboard_action_fails_closed(self):
        result=DesktopControl().press_key("ENTER")
        self.assertFalse(result.success)
        self.assertIn("approval",result.message.lower())
    def test_unknown_command_is_left_for_ai(self):
        self.assertIsNone(DesktopCommandRouter().execute("explain quantum computing"))
    def test_unsafe_key_is_rejected(self):
        result=DesktopControl(lambda *_:True).press_key("CTRL+ALT+DELETE")
        self.assertFalse(result.success)

if __name__=="__main__":
    unittest.main()
