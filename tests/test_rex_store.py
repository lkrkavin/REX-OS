import unittest

from omni.store import (
    InstallerFormat, StoreCatalog, StoreListing, StoreSourceKind,
    classify_installer, validate_https_url,
)


class TestStoreCatalog(unittest.TestCase):
    def test_sources_include_multiple_discovery_channels(self):
        catalog = StoreCatalog()
        kinds = {source.kind for source in catalog.list_sources()}
        self.assertIn(StoreSourceKind.APT, kinds)
        self.assertIn(StoreSourceKind.FLATPAK, kinds)
        self.assertIn(StoreSourceKind.WEBSITE, kinds)
        self.assertIn(StoreSourceKind.LOCAL_FILE, kinds)
        self.assertIn(StoreSourceKind.MICROSOFT_STORE, kinds)

    def test_search_only_returns_listings_from_enabled_sources(self):
        catalog = StoreCatalog()
        catalog.add_listing(StoreListing(
            app_id="editor", name="Example Editor", description="Code editor",
            publisher="Example", categories=("development",), source_id="rex"
        ))
        self.assertEqual(len(catalog.search("editor")), 1)
        catalog.set_source_enabled("rex", False)
        self.assertEqual(catalog.search("editor"), [])

    def test_unknown_source_rejected(self):
        catalog = StoreCatalog()
        with self.assertRaises(ValueError):
            catalog.add_listing(StoreListing(
                app_id="x", name="X", description="X", publisher="X",
                source_id="missing"
            ))

    def test_url_requires_public_https(self):
        self.assertEqual(validate_https_url("https://example.com/app"), "https://example.com/app")
        for url in ("http://example.com/a", "file:///etc/passwd",
                    "https://localhost/a", "https://127.0.0.1/a",
                    "https://user:pass@example.com/a"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_https_url(url)

    def test_installer_classification_does_not_execute(self):
        self.assertEqual(classify_installer("setup.EXE").format, InstallerFormat.WINDOWS_EXE)
        self.assertEqual(classify_installer("package.apk").format, InstallerFormat.ANDROID_APK)
        self.assertEqual(classify_installer("unknown.bin").format, InstallerFormat.UNKNOWN)

    def test_invalid_listing_rejected(self):
        with self.assertRaises(ValueError):
            StoreListing(app_id="", name="X", description="X", publisher="X")


if __name__ == "__main__":
    unittest.main()
