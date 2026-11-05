#!/usr/bin/env python3
"""Restricted SSH integration for a separately owned and explicitly paired Mac."""
import re,shutil,subprocess,shlex
_HOST=re.compile(r"^(?=.{1,253}$)[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?$")
_USER=re.compile(r"^[A-Za-z_][A-Za-z0-9_-]{0,31}$")
_APP=re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._+-]{0,100}$")
class MacRemoteError(RuntimeError):pass
class MacRemoteManager:
 def __init__(self,host,user,port=22,known_hosts=None):
  if not _HOST.fullmatch(host or "") or not _USER.fullmatch(user or ""):raise ValueError("Invalid Mac host or username")
  if not isinstance(port,int) or not 1<=port<=65535:raise ValueError("Invalid SSH port")
  if not shutil.which("ssh"):raise MacRemoteError("OpenSSH client is not installed")
  self.host=host;self.user=user;self.port=port;self.known_hosts=known_hosts
 def _base(self):
  args=["ssh","-T","-p",str(self.port),"-o","BatchMode=yes","-o","StrictHostKeyChecking=yes","-o","ConnectTimeout=8"]
  if self.known_hosts:args.extend(["-o","UserKnownHostsFile="+self.known_hosts])
  args.append(self.user+"@"+self.host)
  return args
 def _run_fixed(self,remote_command,timeout=15):
  result=subprocess.run(self._base()+[remote_command],capture_output=True,text=True,timeout=timeout,check=False)
  if result.returncode:raise MacRemoteError((result.stderr or "SSH command failed").strip()[:1000])
  return result.stdout
 def test_connection(self):
  output=self._run_fixed("sw_vers -productName && sw_vers -productVersion")
  if "mac" not in output.lower():raise MacRemoteError("The paired SSH endpoint did not identify itself as macOS")
  return output.strip()
 def list_applications(self):
  output=self._run_fixed("mdfind \"kMDItemContentType == 'com.apple.application-bundle'\"",30)
  return [line.strip() for line in output.splitlines() if line.strip().endswith(".app")][:300]
 def launch_application(self,app_name):
  if not _APP.fullmatch(app_name or ""):raise ValueError("Invalid application name")
  self._run_fixed("open -a "+shlex.quote(app_name),20)
  return True
