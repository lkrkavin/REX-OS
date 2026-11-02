import unittest
import tempfile
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ais.user_memory import UserMemory


class TestUserMemory(unittest.TestCase):
    def setUp(self):
        # Use a temp directory for test database
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_user_memory_init(self):
        memory = UserMemory(user_id=1, base_path=self.temp_dir)
        # Should initialize without errors
        self.assertIsNotNone(memory.db_path)

    def test_preference_set_get(self):
        memory = UserMemory(user_id=1, base_path=self.temp_dir)
        memory.set_preference("theme", "dark")
        result = memory.get_preference("theme")
        self.assertEqual(result, "dark")

    def test_preference_default(self):
        memory = UserMemory(user_id=2, base_path=self.temp_dir)
        result = memory.get_preference("nonexistent_key", "default_value")
        self.assertEqual(result, "default_value")


if __name__ == '__main__':
    unittest.main()