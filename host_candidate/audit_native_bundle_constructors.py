#!/usr/bin/env python3
"""Identify all native diagnostic ZIP build callsites in exact original v138.

Read-only static invocation scan; does not read logs or diagnostic ZIP contents.
No code edits, signing, installation or data transfer.
"""
import argparse,hashlib,json,pathlib,re,zipfile
from androguard.core.dex import DEX
from patch_deny import EXPECTED_APK,sha
MATCHES=("Lcom/dsh/android/log/DiagnosticBundle;->build",
         "Lcom/dsh/android/log/DiagnosticBundle;->build$default")
def scan(apk):
  if sha(pathlib.Path(apk).read_bytes())!=EXPECTED_APK:raise ValueError("BAD_ORIGINAL_V138_HASH")
  rows=[];classes=[];all_sites=[]
  with zipfile.ZipFile(apk) as z:
    if z.testzip():raise ValueError("APK_ZIP_CRC_BAD")
    names=[n for n in ("classes.dex","classes2.dex") if n in z.namelist()]
    if names!=["classes.dex","classes2.dex"]:raise ValueError("UNEXPECTED_APK_DEX_LAYOUT")
    for name in names:
      d=DEX(z.read(name))
      for c in d.get_classes():
        for m in c.get_methods():
          if "DiagnosticBundle;" in c.get_name() and "build" in m.get_name():
            classes.append({"dex":name,"method":c.get_name()+"->"+m.get_name()+m.get_descriptor()})
          if not m.get_code():continue
          for pc,op in m.get_instructions_idx():
            if not op.get_name().startswith("invoke-"):continue
            value=op.get_output()
            if any(ref in value for ref in MATCHES):
              all_sites.append({"dex":name,"caller":m.get_class_name()+"->"+m.get_name()+m.get_descriptor(),
                                "code_off":m.get_code_off(),"pc":pc,
                                "opcode":op.get_name(),
                                "target":"build$default" if "build$default" in value else "build"})
  return {"exact_baseline_sha256":EXPECTED_APK,
          "builder_methods":classes,
          "all_builder_invocation_sites":all_sites,
          "builder_callsite_count":len(all_sites),
          "native_manual_export_also_calls_builder":
            any("LogViewerActivity;" in x["caller"] for x in all_sites),
          "static_only":True,
          "reflection_and_jni_paths":"NOT_VERIFIED",
          "all_diagnostic_zip_creation_default_denied":"NOT_VERIFIED",
          "APK_BUILT":"NO"}
if __name__=="__main__":
  a=argparse.ArgumentParser();a.add_argument("v138");a.add_argument("--report",required=True)
  o=a.parse_args();result=scan(o.v138)
  pathlib.Path(o.report).write_text(json.dumps(result,indent=2)+"\n")
  print(json.dumps(result,indent=2))
