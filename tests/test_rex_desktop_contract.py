import unittest
from pathlib import Path
from ui.rex_hub import APP_COMMANDS

ROOT=Path(__file__).resolve().parents[1]

class TestREXDesktopContract(unittest.TestCase):
    def test_browser_launcher_has_installed_browser(self):
        self.assertEqual(APP_COMMANDS["Browser"],["firefox-esr"])
        packages=(ROOT/"build/config/package-lists/rex-desktop.list.chroot").read_text()
        self.assertIn("\nfirefox-esr\n",packages)
    def test_cross_platform_runtime_packages_are_declared(self):
        packages=(ROOT/"build/config/package-lists/rex-desktop.list.chroot").read_text()
        for package in ("wine","winetricks","libfuse2","flatpak"):
            self.assertIn("\n"+package+"\n",packages)
    def test_desktop_sources_match_iso_payload(self):
        for name in ("rex_hub.py","rex_omni.py"):
            source=(ROOT/"ui"/name).read_text()
            mirror=(ROOT/"build/config/includes.chroot/opt/rex-os/ui"/name).read_text()
            self.assertEqual(source,mirror)
    def test_omni_exposes_safe_local_and_compatibility_workflows(self):
        source=(ROOT/"ui/rex_omni.py").read_text()
        for feature in ("import_appimage","launch_appimage","launch_windows_installer","install_bottles","show_waydroid_info"):
            self.assertIn("def "+feature,source)
        self.assertIn('subprocess.Popen(["wine",str(path)]',source)
    def test_voice_assistant_is_connected_to_desktop_and_iso(self):
        source=(ROOT/"ui/rex_assistant.py").read_text()
        mirror=(ROOT/"build/config/includes.chroot/opt/rex-os/ui/rex_assistant.py").read_text()
        self.assertEqual(source,mirror)
        for feature in ("class VoiceCaptureWorker","recognize_sphinx","def start_voice_capture",
                        "def speak_response","espeak-ng","Speak REX replies aloud"):
            self.assertIn(feature,source)
        packages=(ROOT/"build/config/package-lists/rex-desktop.list.chroot").read_text()
        for package in ("python3-speechrecognition","python3-pyaudio",
                        "python3-pocketsphinx","pocketsphinx-en-us","espeak-ng"):
            self.assertIn("\n"+package+"\n",packages)
    def test_openrouter_connection_button_performs_authenticated_check(self):
        source=(ROOT/"ui/rex_ai_settings.py").read_text()
        self.assertIn("/api/v1/auth/key",source)
        self.assertNotIn('def test(self):\n        QMessageBox.information',source)
        mirror=(ROOT/"build/config/includes.chroot/opt/rex-os/ui/rex_ai_settings.py").read_text()
        self.assertEqual(source,mirror)

if __name__=="__main__":unittest.main()
