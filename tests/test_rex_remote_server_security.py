import json
import os
import unittest
from unittest.mock import patch

from services.rex_remote_server import RexRemoteServer


class TestRexRemoteServerSecurity(unittest.TestCase):
    def test_authentication_rejects_when_secret_not_configured(self):
        with patch.dict(os.environ, {}, clear=True):
            server = RexRemoteServer()
            self.assertFalse(server.authenticate_client(json.dumps({
                "type": "authenticate", "token": "anything"
            })))

    def test_authentication_accepts_only_matching_token(self):
        with patch.dict(os.environ, {"REX_REMOTE_AUTH_TOKEN": "test-secret"}, clear=True):
            server = RexRemoteServer()
            self.assertTrue(server.authenticate_client(json.dumps({
                "type": "authenticate", "token": "test-secret"
            })))
            self.assertFalse(server.authenticate_client(json.dumps({
                "type": "authenticate", "token": "wrong"
            })))
            self.assertFalse(server.authenticate_client(json.dumps({
                "type": "ping", "token": "test-secret"
            })))

    def test_malformed_authentication_is_rejected(self):
        with patch.dict(os.environ, {"REX_REMOTE_AUTH_TOKEN": "test-secret"}, clear=True):
            server = RexRemoteServer()
            self.assertFalse(server.authenticate_client("not-json"))
            self.assertFalse(server.authenticate_client(json.dumps([])))

    def test_remote_mutating_actions_fail_closed(self):
        with patch.dict(os.environ, {"REX_REMOTE_AUTH_TOKEN": "test-secret"}, clear=True):
            server = RexRemoteServer()
            for action in (
                {"type": "open_app", "app": "calc"},
                {"type": "keyboard_text", "text": "unapproved"},
                {"type": "key_press", "key": "ENTER"},
                {"type": "lock"},
                {"type": "terminate_process", "pid": 1},
            ):
                result = server.execute_action(action)
                self.assertFalse(result["success"])
                self.assertIn("disabled", result["error"].lower())

    def test_invalid_action_payload_is_rejected(self):
        with patch.dict(os.environ, {"REX_REMOTE_AUTH_TOKEN": "test-secret"}, clear=True):
            server = RexRemoteServer()
            self.assertFalse(server.execute_action(None)["success"])
            self.assertFalse(server.execute_action("open_app")["success"])


if __name__ == "__main__":
    unittest.main()
