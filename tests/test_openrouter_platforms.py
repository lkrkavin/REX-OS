import unittest
from unittest.mock import patch
from ais.ai_providers import ProviderType, OpenRouterProvider, create_provider
from omni.platform_support import PlatformSupport

class TestOpenRouter(unittest.TestCase):
    def test_provider_factory(self):
        provider=create_provider(ProviderType.OPENROUTER)
        self.assertIsInstance(provider,OpenRouterProvider)
    def test_missing_key_is_unavailable(self):
        with patch.dict("os.environ",{},clear=True):
            with patch.object(OpenRouterProvider,"_read_keyring",return_value=None):
                provider=OpenRouterProvider()
                import asyncio
                self.assertFalse(asyncio.run(provider.check_availability()))
    def test_model_list_is_available_without_network(self):
        provider=OpenRouterProvider()
        import asyncio
        models=asyncio.run(provider.list_models())
        self.assertTrue(any(m.name=="openai/gpt-4o-mini" for m in models))
        self.assertTrue(all(m.provider==ProviderType.OPENROUTER for m in models))

class TestPlatformSupport(unittest.TestCase):
    def test_reports_four_platforms(self):
        names={item.platform for item in PlatformSupport().detect()}
        self.assertEqual(names,{"Linux","Windows","Android","macOS"})
    def test_macos_is_not_reported_as_native(self):
        mac=next(x for x in PlatformSupport().detect() if x.platform=="macOS")
        self.assertIn(mac.mode,{"remote-device","unavailable"})

if __name__=="__main__":
    unittest.main()
