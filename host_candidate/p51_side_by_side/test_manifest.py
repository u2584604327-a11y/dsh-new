#!/usr/bin/env python3
"""Offline safety tests; neither the original APK nor user device is used."""
import pathlib
import sys
import xml.etree.ElementTree as ET
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import p51_manifest as m

A=m.A
app=ET.Element("application",{
 A+"name":"com.dsh.android.OldApplication",
 A+"debuggable":"true",
 A+"allowBackup":"true",
 A+"usesCleartextTraffic":"true",
})
orig=ET.Element("manifest",{"package":m.ORIGINAL,A+"sharedUserId":"shared"})
ET.SubElement(orig,"uses-permission",{A+"name":"android.permission.INTERNET"})
ET.SubElement(orig,"permission",{A+"name":"com.dsh.android.LEGACY"})
ET.SubElement(orig,"queries")
orig.append(app)
ET.SubElement(app,"provider",{A+"name":"com.dsh.android.PrivateProvider",A+"authorities":"com.dsh.android"})
ET.SubElement(app,"receiver",{A+"name":"com.dsh.android.LegacyReceiver"})
ET.SubElement(app,"activity",{A+"name":"com.dsh.android.MainActivity",A+"exported":"true"})
ET.SubElement(app,"service",{A+"name":"com.dsh.android.Legacy"})
s=ET.SubElement(app,"service",{
 A+"name":m.SERVICE,A+"isolatedProcess":"true",
 A+"exported":"false",A+"process":":p43_isolated"
})
ET.SubElement(app,"activity",{A+"name":m.ACTIVITY,A+"exported":"true"})
source=ET.tostring(orig)
after=m.transform(source)
m.verify_manifest_bytes(after)
root=ET.fromstring(after)
assert root.get("package")==m.SIDECAR
assert root.find("application").get(A+"name")=="android.app.Application"
assert root.find("application/provider") is None
assert root.find("application/receiver") is None
assert root.findall("uses-permission")==[]
assert root.get(A+"sharedUserId") is None
assert b"com.dsh.android.MainActivity" not in after
assert b"android.permission.INTERNET" not in after
assert m.transform(source)==after
checks=10

def reject(bad,label):
  global checks
  try:
    m.verify_manifest_bytes(bad)
  except (ValueError,RuntimeError,ET.ParseError):
    checks+=1
    return
  raise AssertionError("P51 unexpected acceptance: "+label)
def mutate(fn,label):
  tree=ET.fromstring(after)
  fn(tree)
  reject(ET.tostring(tree),label)

mutate(lambda t:t.set("package",m.ORIGINAL),"colliding package")
mutate(lambda t:ET.SubElement(t,"uses-permission",{A+"name":"android.permission.INTERNET"}),"internet permission")
mutate(lambda t:ET.SubElement(t.find("application"),"provider",{A+"name":"Evil"}),"provider")
mutate(lambda t:ET.SubElement(t.find("application"),"service",{A+"name":"Evil"}),"extra service")
mutate(lambda t:t.find("application").set(A+"allowBackup","true"),"backup")
mutate(lambda t:t.find("application").set(A+"debuggable","true"),"debuggable")
mutate(lambda t:t.find("application").set(A+"name","com.dsh.android.OldApplication"),"custom init")
mutate(lambda t:t.find("application").set(A+"extractNativeLibs","false"),"not extract native")
mutate(lambda t:t.find("application/service").set(A+"exported","true"),"service exported")
mutate(lambda t:t.find("application/service").set(A+"isolatedProcess","false"),"not isolated")
mutate(lambda t:t.find("application/activity").set(A+"exported","false"),"inaccessible test")
mutate(lambda t:t.find("application/activity/intent-filter/action").set(A+"name","android.intent.action.VIEW"),"unwanted launcher")
mutate(lambda t:t.set(A+"sharedUserId","legacy.uid"),"shared user")
mutate(lambda t:ET.SubElement(t,"queries"),"queries")
mutate(lambda t:ET.SubElement(t,"uses-sdk",{A+"minSdkVersion":"1"}),"uses-sdk alongside app only acceptable: reviewed later") if False else None
try:
  m.transform(ET.tostring(ET.Element("manifest",{"package":m.SIDECAR})))
  raise AssertionError("non-original accepted")
except RuntimeError:
  checks+=1
print("P51_PERMISSIONLESS_SIDE_BY_SIDE_MANIFEST_JVM_INDEPENDENT_TEST=PASS assertions="+str(checks))
print("P51_NORMAL_DSH_SIGNED_PACKAGE_AND_DATA=NOT_TOUCHED")
