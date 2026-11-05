import unittest
from unittest.mock import patch
from connect.mac_remote import MacRemoteManager

class TestMacRemoteValidation(unittest.TestCase):
 def test_rejects_shell_like_host(self):
  with self.assertRaises(ValueError): MacRemoteManager('mac.local;touch /tmp/x','user')
 def test_rejects_shell_like_username(self):
  with self.assertRaises(ValueError): MacRemoteManager('mac.local','user;bad')
 def test_rejects_invalid_application_name(self):
  with patch('connect.mac_remote.shutil.which',return_value='/usr/bin/ssh'):
   manager=MacRemoteManager('mac.local','user')
   with self.assertRaises(ValueError): manager.launch_application('Safari; touch /tmp/x')

if __name__=='__main__': unittest.main()
