#!/usr/bin/env python3
"""Examine exact original v138 native diagnostic bundle export write site.
Read-only. Emits bounded opcode samples without raw strings or user data.
"""
import argparse,hashlib,json,pathlib,zipfile
from androguard.core.dex import DEX
from patch_deny import EXPECTED_APK,sha

TARGET_CLASS="Lcom/dsh/android/LogCommandBridge;"
def analyze(apk):
  if sha(pathlib.Path(apk).read_bytes())!=EXPECTED_APK:raise ValueError("BAD_V138_PREIMAGE")
  with zipfile.ZipFile(apk) as z:
    if z.testzip():raise ValueError("APK_CRC_FAIL")
    original=z.read("classes.dex")
  d=DEX(original)
  rows=[]
  for cls in d.get_classes():
    if cls.get_name()!=TARGET_CLASS:continue
    for m in cls.get_methods():
      if m.get_name() not in ("doExport","doSummary") and "export" not in m.get_name().lower():
        continue
      ins=list(m.get_instructions_idx())
      sites=[]
      for idx,(pc,op) in enumerate(ins):
        if op.get_name().startswith("const-string") and "bundlePath" in op.get_output():
          window=[]
          for at,(offset,instruction) in enumerate(ins[max(0,idx-6):idx+16]):
            text=instruction.get_output()
            if instruction.get_name().startswith("const-string"):
              text="BUNDLE_PATH_KEY" if "bundlePath" in text else "OTHER_CONST_STRING"
            elif instruction.get_name().startswith("invoke-"):
              # Static method names are harmless; no actual application data exposed.
              text=text.split(",",1)[-1] if "->" in text else "METHOD_REF"
            elif any(word in text for word in ("/data/","http:","https:","Authorization")):
              text="REDACTED_CONSTANT_OR_PATH"
            window.append({"pc":offset,"op":instruction.get_name(),"operands":text[:180]})
          sites.append({"key_instruction_index":idx,"pc":pc,"window":window})
      rows.append({"method":m.get_name(),"descriptor":m.get_descriptor(),
                   "code_off":m.get_code_off(),"insns_size":m.get_code().get_insns_size() if m.get_code() else 0,
                   "bundlePath_const_sites":sites})
  return {"original_dex_sha256":sha(original),"methods":rows,
          "bundlePath_key_site_total":sum(len(r["bundlePath_const_sites"]) for r in rows),
          "native_path_removal":"NOT_APPLIED","app_data_modified":"NO"}
if __name__=="__main__":
  ap=argparse.ArgumentParser();ap.add_argument("apk");ap.add_argument("--report",required=True)
  args=ap.parse_args();r=analyze(args.apk);pathlib.Path(args.report).write_text(json.dumps(r,indent=2)+"\n")
  print(json.dumps(r,indent=2))
