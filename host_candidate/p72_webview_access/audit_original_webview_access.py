#!/usr/bin/env python3
"""P72 precise access-flags proof for original browser WebView accessor.

Investigate reported original Android IllegalAccessError:
AiBrowserView.currentWebView() inaccessible to BrowserBridge. Only pinned
signed v138 private APK, no code execution, user data or raw DEX logging.
"""
import argparse,collections,hashlib,json,re,zipfile
from androguard.core.dex import DEX
V138="3ca56655d79afc57431636e340823e7071bc830615ca615c485b0b9a30b6e3e5"
VIEW="Lcom/dsh/android/browser/AiBrowserView;"
BRIDGE="Lcom/dsh/android/browser/BrowserBridge;"
NAME="currentWebView"
def access_category(flags):
 if flags & 0x0001:return "PUBLIC"
 if flags & 0x0002:return "PRIVATE"
 if flags & 0x0004:return "PROTECTED"
 return "PACKAGE_PRIVATE"
def inspect(path):
 data=open(path,"rb").read()
 if hashlib.sha256(data).hexdigest()!=V138:
  raise ValueError("P72_BASELINE_SHA_MISMATCH")
 with zipfile.ZipFile(path) as archive:
  if archive.testzip() is not None:raise ValueError("P72_ORIGINAL_APK_CRC")
  dex=[(n,DEX(archive.read(n))) for n in archive.namelist()
       if re.fullmatch(r"classes\d*\.dex",n)]
 results=[]
 for dexname,parsed in dex:
  for cl in parsed.get_classes():
   if cl.get_name() not in (VIEW,BRIDGE):continue
   for method in cl.get_methods():
    if cl.get_name()==VIEW and method.get_name()==NAME:
     results.append({"type":"TARGET_ACCESSOR","dex":dexname,
                     "access":access_category(method.get_access_flags()),
                     "descriptor_is_webview":
                       method.get_descriptor()=="()Landroid/webkit/WebView;"})
    if cl.get_name()!=BRIDGE or method.get_code() is None:continue
    for _,ins in method.get_instructions_idx():
     if not ins.get_name().startswith("invoke-"):continue
     output=ins.get_output()
     if VIEW+"->"+NAME+"(" not in output:continue
     results.append({"type":"BRIDGE_CALLSITE","dex":dexname,
                     "opcode":ins.get_name(),
                     "call_signature_webview":
                       (VIEW+"->"+NAME+"()Landroid/webkit/WebView;") in output})
 targets=[x for x in results if x["type"]=="TARGET_ACCESSOR"]
 callers=[x for x in results if x["type"]=="BRIDGE_CALLSITE"]
 return {"accessors":targets,"bridge_callsites":callers,
         "target_unique":len(targets)==1,
         "native_bridge_call_present":bool(callers),
         "cross_class_invokes_private":
           any(x["access"]=="PRIVATE" for x in targets) and bool(callers),
         "method_visibility_fix_candidate":
           len(targets)==1 and targets[0]["access"] in ("PRIVATE","PACKAGE_PRIVATE",
           "PROTECTED") and targets[0]["descriptor_is_webview"] and bool(callers),
         "current_v139_user_installed_art_runtime_verified":False}
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("original_v138");a=p.parse_args()
 r=inspect(a.original_v138)
 print("P72_SIGNED_V138_BROWSERBRIDGE_ACCESS_AUDIT=PASS")
 print("P72_WEBVIEW_METHOD_FLAGS_AND_CALLS="+json.dumps(r,sort_keys=True))
 print("P72_REAL_USER_NO_REPLY_ROOT_CAUSE=NOT_YET_PROVEN")
 print("P72_ORIGINAL_BROWSER_PROFILE_AND_COOKIE_DATA_READ=NO")
 print("P72_FIXED_SIGNED_V139=BLOCKED")
