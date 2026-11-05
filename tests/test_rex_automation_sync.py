import json,tempfile,unittest
from pathlib import Path
from services.automation_engine import AutomationEngine,AutomationRule
from services.sync_service import SyncService

class TestAutomationEngine(unittest.TestCase):
 def test_rejects_arbitrary_shell_action(self):
  with tempfile.TemporaryDirectory() as d:
   engine=AutomationEngine(str(Path(d)/"rules.json"))
   with self.assertRaises(ValueError):
    engine.add_rule(AutomationRule("bad","manual","shell",{"command":"rm -rf /"}))
 def test_requires_approval_before_dispatch(self):
  with tempfile.TemporaryDirectory() as d:
   engine=AutomationEngine(str(Path(d)/"rules.json"))
   engine.add_rule(AutomationRule("open-app","manual","launch_app",{"app_id":"firefox.desktop"}))
   calls=[]
   result=engine.dispatch("manual",lambda a,args:calls.append((a,args)) or True,lambda rule:False)
   self.assertFalse(result[0]["success"]);self.assertEqual(calls,[])

class TestSyncService(unittest.TestCase):
 def test_exports_only_allowlisted_nonsecret_files(self):
  with tempfile.TemporaryDirectory() as d:
   base=Path(d)/"config";base.mkdir()
   (base/"ui_preferences.json").write_text('{"theme":"dark"}')
   (base/"openrouter_key.json").write_text('{"key":"must-not-export"}')
   bundle=Path(d)/"bundle.json";result=SyncService(base).export_bundle(bundle)
   self.assertEqual(result["files"],["ui_preferences.json"])
   self.assertNotIn("must-not-export",bundle.read_text())
 def test_detects_tampered_bundle(self):
  with tempfile.TemporaryDirectory() as d:
   base=Path(d)/"config";service=SyncService(base);bundle=Path(d)/"bundle.json"
   service.export_bundle(bundle);data=json.loads(bundle.read_text());data["payload"]["files"]["ui_preferences.json"]={"x":1};bundle.write_text(json.dumps(data))
   with self.assertRaises(ValueError):service.import_bundle(bundle)

if __name__=="__main__":unittest.main()
