import unittest
import asyncio
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ais.ai_core import REXAICore, ProviderType

class TestAIModule(unittest.TestCase):
    """Tests for REX AI Core"""

    def test_ai_core_not_initialized(self):
        """Test AI Core not initialized without calling initialize()"""
        ai = REXAICore(data_path=tempfile.mkdtemp())
        # Without calling initialize(), _initialized should be False
        self.assertFalse(ai._initialized)

    def test_ai_core_initialization(self):
        """Test AI Core initialization"""
        async def run():
            ai = REXAICore(data_path=tempfile.mkdtemp())
            success = await ai.initialize()
            # Initialize should return a bool (success status)
            self.assertIsInstance(success, bool)
            # After initialization, _initialized should be True
            self.assertTrue(ai._initialized)
        asyncio.run(run())

    def test_ai_core_generation_offline(self):
        """Test AI Core generation in offline mode"""
        async def run():
            ai = REXAICore(data_path=tempfile.mkdtemp())
            await ai.initialize()
            # Should return offline response
            response = ai._offline_response("test prompt")
            self.assertIn("Offline Mode", response)
            self.assertIn("no ai provider", response.lower())
        asyncio.run(run())

    def test_provider_type_enum(self):
        """Test ProviderType enumeration"""
        self.assertEqual(ProviderType.OLLAMA.value, "ollama")

    def test_create_conversation(self):
        """Test conversation creation returns conversation ID"""
        ai = REXAICore(data_path=tempfile.mkdtemp())
        cid = ai.create_conversation("test-conv")
        self.assertEqual(cid, "test-conv")

    def test_create_conversation_auto_id(self):
        """Test conversation creation with auto-generated ID"""
        ai = REXAICore(data_path=tempfile.mkdtemp())
        cid = ai.create_conversation()
        self.assertIsNotNone(cid)
        self.assertIsInstance(cid, str)
        self.assertGreater(len(cid), 0)

    def test_get_conversation(self):
        """Test getting a conversation"""
        ai = REXAICore(data_path=tempfile.mkdtemp())
        ai.create_conversation("test-conv")
        conv = ai.get_conversation("test-conv")
        self.assertIsNotNone(conv)

    def test_get_conversation_nonexistent(self):
        """Test getting a nonexistent conversation"""
        ai = REXAICore(data_path=tempfile.mkdtemp())
        conv = ai.get_conversation("nonexistent")
        self.assertIsNone(conv)


if __name__ == '__main__':
    unittest.main()