#!/usr/bin/env python3
"""Read-only audit for an actual AiBrowserView.currentWebView IllegalAccessError.
No guessing: inspect original v138 class flags and every method call opcode.
Does not change any APK or Java access level.
"""
import argparse,hashlib,json,pathlib,struct,zipfile
from androguard.core.dex import DEX
from patch_deny import EXPECTED_APK,sha
TARGET_CLASS="Lcom/dsh/android/browser/AiBrowserView;"
TARGET_METHOD="currentWebView"
BRIDGE_CLASS="Lcom/dsh/android/browser/BrowserBridge;"
def inspect(apk):
    if sha(pathlib.Path(apk).read_bytes()) != EXPECTED_APK:
        raise ValueError("UNVERIFIED_BASELINE")
    with zipfile.ZipFile(apk) as z:
        if z.testzip():raise ValueError("APK_CRC_FAILED")
        dex_data=[(n,z.read(n)) for n in sorted(z.namelist())
                  if n=="classes.dex" or n=="classes2.dex"]
    if len(dex_data)!=2:raise ValueError("UNEXPECTED_DEX_COUNT")
    result={"dex_hashes":[{"name":n,"sha256":sha(raw)} for n,raw in dex_data],
            "currentWebView_methods":[],"calls":[],"status":"READ_ONLY"}
    for dex_name,data in dex_data:
      dex=DEX(data)
      for c in dex.get_classes():
          if c.get_name()==TARGET_CLASS:
              result["class_flags"]=hex(c.get_access_flags())
              for m in c.get_methods():
                  if m.get_name()==TARGET_METHOD:
                      result["currentWebView_methods"].append({
                          "descriptor":m.get_descriptor(),
                          "method_idx":m.get_method_idx(),
                          "access_flags":hex(m.get_access_flags()),
                          "private":bool(m.get_access_flags()&2),
                          "public":bool(m.get_access_flags()&1),
                          "code_off":m.get_code_off(),
                      })
          for m in c.get_methods():
              if not m.get_code():continue
              for off,ins in m.get_instructions_idx():
                  if not ins.get_name().startswith("invoke-"):continue
                  text=ins.get_output()
                  if TARGET_CLASS+"->"+TARGET_METHOD+"(" in text:
                      result["calls"].append({
                          "caller_class":m.get_class_name(),
                          "caller_name":m.get_name(),
                          "opcode":ins.get_name(),
                          "pc":off,
                          "caller_is_bridge":m.get_class_name()==BRIDGE_CLASS
                      })
    if not result["currentWebView_methods"]:raise ValueError("TARGET_METHOD_NOT_FOUND")
    result["bridge_call_sites"]=sum(bool(x["caller_is_bridge"]) for x in result["calls"])
    result["invoke_direct_sites"]=sum(x["opcode"].startswith("invoke-direct") for x in result["calls"])
    result["potential_safe_flag_upgrade"]=(
        len(result["currentWebView_methods"])==1 and
        result["currentWebView_methods"][0]["private"] and
        result["bridge_call_sites"]>0 and
        result["invoke_direct_sites"]==0
    )
    result["ART_ACCESS_PROOF"]="NOT_VERIFIED"
    return result
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("v138");p.add_argument("--report",required=True)
    a=p.parse_args();r=inspect(a.v138)
    pathlib.Path(a.report).write_text(json.dumps(r,indent=2)+"\n")
    print(json.dumps(r,indent=2))
