#!/usr/bin/env python3
"""P72 exactly one private AiBrowserView.currentWebView accessor visibility fix.
Only for disposable P51 test APK, NEVER original user's installed app.
"""
import argparse,pathlib,re,zipfile
from androguard.core.dex import DEX
CLASS="Lcom/dsh/android/browser/AiBrowserView;"
METHOD="currentWebView"
DESCRIPTOR="()Landroid/webkit/WebView;"
def patch(root):
 root=pathlib.Path(root)
 file=root/"smali/com/dsh/android/browser/AiBrowserView.smali"
 if not file.is_file() or file.is_symlink():
  raise RuntimeError("P72_ORIGINAL_MAIN_DEX_METHOD_FILE_MISSING")
 data=file.read_text("utf-8")
 pattern=re.compile(r"(?m)^\.method[ \t]+(?P<flags>(?:(?:[A-Za-z-]+)[ \t]+)+)currentWebView\(\)Landroid/webkit/WebView;[ \t]*$")
 found=list(pattern.finditer(data))
 if len(found)!=1:raise RuntimeError("P72_EXACT_METHOD_HEADER_COUNT_DRIFT")
 flags=found[0].group("flags").split()
 if flags.count("private")!=1 or "public" in flags or "protected" in flags:
  raise RuntimeError("P72_ACCESS_VISIBILITY_NOT_EXACT_PRIVATE")
 rewrite=found[0].group(0).replace("private","public",1)
 new=data[:found[0].start()]+rewrite+data[found[0].end():]
 if new.count(".method")!=data.count(".method"):
  raise RuntimeError("P72_METHOD_COUNT_CHANGED")
 if new.replace(rewrite,found[0].group(0),1)!=data:
  raise RuntimeError("P72_UNAUTHORIZED_SOURCE_MODIFICATION")
 file.write_text(new,"utf-8")
 print("P72_ORIGINAL_ACCESSOR_PRIVATE_TO_PUBLIC_ONLY=PASS")
 print("P72_ORIGINAL_ACCESSOR_BODY_PRESERVED=YES")
def verify(apk):
 with zipfile.ZipFile(apk) as z:
  if z.testzip() is not None:raise RuntimeError("P72_BAD_REBUILT_ZIP_CRC")
  d=DEX(z.read("classes.dex"))
  matching=[m for c in d.get_classes() if c.get_name()==CLASS
            for m in c.get_methods() if m.get_name()==METHOD
            and m.get_descriptor()==DESCRIPTOR]
  if len(matching)!=1 or not (matching[0].get_access_flags()&1):
   raise RuntimeError("P72_METHOD_NOT_PUBLIC_OR_DRIFT")
 print("P72_REBUILT_MAIN_DEX_CURRENT_WEBVIEW_IS_PUBLIC=PASS")
 print("P72_ORIGINAL_PHONE_AND_LOGIN_PROFILE_UNCHANGED=YES")
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("mode",choices=("patch","verify"))
 p.add_argument("target");args=p.parse_args()
 patch(args.target) if args.mode=="patch" else verify(args.target)
