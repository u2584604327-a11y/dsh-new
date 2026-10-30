#!/usr/bin/env python3
"""P70 passive original v138 browser mailbox/native responder and WebView state audit.

No user cookies or browsing data are accessed. No original JS, URL, host
private method names, credentials or original strings printed. File basenames
are matched in-memory only against pinned P6/DEX. Static evidence only.
"""
import argparse,collections,hashlib,io,json,pathlib,re,sys,zipfile
from androguard.core.dex import DEX
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"p69_browser_reply"))
from audit_browser_reply import ORIGINAL,P6,zip_entries,digest

STORAGE_API = {
 "setAcceptCookie":"COOKIE_ACCEPT_CONFIG",
 "setAcceptThirdPartyCookies":"THIRD_PARTY_COOKIE_CONFIG",
 "removeAllCookies":"COOKIE_ALL_DELETE",
 "removeSessionCookies":"COOKIE_SESSION_DELETE",
 "flush":"COOKIE_FLUSH",
 "getCookie":"COOKIE_GET",
 "setCookie":"COOKIE_SET",
 "clearCache":"WEBVIEW_CLEAR_CACHE",
 "clearHistory":"WEBVIEW_CLEAR_HISTORY",
 "deleteAllData":"WEBSTORAGE_DELETE_ALL",
 "setDomStorageEnabled":"DOM_STORAGE_CONFIG",
 "setDatabaseEnabled":"DATABASE_STORAGE_CONFIG",
 "setDataDirectorySuffix":"WEBVIEW_DATA_DIRECTORY_SUFFIX",
 "destroy":"WEBVIEW_DESTROY",
 "loadUrl":"WEBVIEW_NAVIGATION",
 "evaluateJavascript":"WEBVIEW_EVALUATION"
}
def get_files(p6):
 with zipfile.ZipFile(io.BytesIO(p6)) as outer:
  overlay=outer.read("output/DSH_V139_P6_ASSET_OVERLAY_NOT_APK.zip")
 with zipfile.ZipFile(io.BytesIO(overlay)) as stage:
  inner=stage.read("assets/browser-tool.zip")
 with zipfile.ZipFile(io.BytesIO(inner)) as browser:
  js=browser.read("lib/index.js").decode("utf-8")
 def string(name):
  match=re.search(r'\bconst '+re.escape(name)+r'\s*=\s*([\'"])([^\'"]+)\1\s*;',js)
  if not match:raise ValueError("ORIGINAL_MAILBOX_FILE_LITERAL_NOT_FOUND:"+name)
  return match.group(2)
 return string("CMD_FILE"),string("RESULT_FILE")
def main(apk,p6):
 a=pathlib.Path(apk).read_bytes();b=pathlib.Path(p6).read_bytes()
 if digest(a)!=ORIGINAL or digest(b)!=P6:raise ValueError("BAD_SIGNED_ORIGINAL_OR_P6_HASH")
 cmd,res=get_files(b)
 with zipfile.ZipFile(io.BytesIO(a)) as z:
  dex_names=[s for s in z.namelist() if re.fullmatch(r"classes\d*\.dex",s)]
  dexes=[DEX(z.read(n)) for n in dex_names]
 counts=collections.Counter()
 mailbox={"command_literal_found":False,"result_literal_found":False}
 browser_classes=0
 browser_methods=0
 dsh_bridge_invokes=collections.Counter()
 for dex in dexes:
  for string in dex.get_strings():
   if string==cmd:mailbox["command_literal_found"]=True
   if string==res:mailbox["result_literal_found"]=True
  for cl in dex.get_classes():
   name=cl.get_name()
   # BrowserBridge, AiBrowserView and browser child classes only.
   if not (name.startswith("Lcom/dsh/android/browser/") or
           name.startswith("Lcom/dsh/android/MainActivity;")):continue
   browser_classes+=1
   for method in cl.get_methods():
    if method.get_code() is None:continue
    browser_methods+=1
    for _,ins in method.get_instructions_idx():
     if not ins.get_name().startswith("invoke-"):continue
     text=ins.get_output()
     match=re.search(r"(L[^;\s,]+;)->([^\s(,]+)\(",text)
     if not match:continue
     owner,symbol=match.groups()
     if owner.startswith("Landroid/webkit/") and symbol in STORAGE_API:
      counts[STORAGE_API[symbol]]+=1
     if owner.startswith("Lcom/dsh/android/browser/"):
      dsh_bridge_invokes["APP_BROWSER_TO_BROWSER"]+=1
     if owner.startswith("Ljava/io/File;") or owner.startswith("Ljava/nio/file/"):
      dsh_bridge_invokes["APP_FILE_API_CALL"]+=1
     if "Landroid/webkit/WebView;->" in text:
      dsh_bridge_invokes["ANDROID_WEBVIEW_CALL"]+=1
 print("P70_SIGNED_ORIGINAL_V138_NATIVE_BROWSER_AUDIT=PASS")
 print("P70_NATIVE_BROWSER_CLASSES="+str(browser_classes))
 print("P70_NATIVE_BROWSER_METHODS="+str(browser_methods))
 print("P70_MAILBOX_NAMES_REFERENCED_EXACTLY_IN_DEX="+json.dumps(mailbox,sort_keys=True))
 print("P70_WEBVIEW_COOKIE_AND_STORAGE_CALL_CATEGORIES="+json.dumps(dict(counts),sort_keys=True))
 print("P70_BROWSER_NATIVE_INVOCATION_CATEGORIES="+json.dumps(dict(dsh_bridge_invokes),sort_keys=True))
 print("P70_NATIVE_BROWSER_COMMAND_DISPATCH_AND_REPLY_WRITER=NOT_PROVEN")
 print("P70_LOGIN_PERSISTENCE_ACROSS_PROCESS_RESTART=NOT_VERIFIED")
 print("P70_ORIGINAL_COOKIE_VALUES_OR_BROWSER_HISTORY_ACCESSED=NO")
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("original");p.add_argument("p6")
 args=p.parse_args();main(args.original,args.p6)
