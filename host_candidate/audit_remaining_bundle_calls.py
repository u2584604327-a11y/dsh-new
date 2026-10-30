#!/usr/bin/env python3
"""Read-only targeted native DiagnosticBundle build-call result handling audit."""
import argparse,json,pathlib,zipfile
from androguard.core.dex import DEX
from patch_deny import EXPECTED_APK,sha

TARGETS={
 ("Lcom/dsh/android/LogViewerActivity;","exportBundle$lambda$41"):64,
 ("Lcom/dsh/android/log/LogUploader;","collectCrashScenes"):442,
}
def audit(path):
 if sha(pathlib.Path(path).read_bytes())!=EXPECTED_APK:
  raise ValueError("NOT_EXACT_V138_APK")
 with zipfile.ZipFile(path) as z:
  d=DEX(z.read("classes.dex"))
 result=[]
 for c in d.get_classes():
  for m in c.get_methods():
   key=(c.get_name(),m.get_name())
   if key not in TARGETS:continue
   ins=list(m.get_instructions_idx())
   hit=next((i for i,(pc,x) in enumerate(ins) if pc==TARGETS[key]),None)
   if hit is None:raise ValueError("BUILDER_CALLSITE_NOT_FOUND")
   selected=[]
   for pc,x in ins[max(0,hit-9):hit+23]:
    output=x.get_output()
    if "const-string" in x.get_name(): output="REDACTED_LITERAL"
    elif "->" not in output and ("/" in output or "http" in output.lower()):output="REDACTED_VALUE"
    selected.append({"pc":pc,"op":x.get_name(),"length":x.get_length(),
                     "operands":output[:190]})
   result.append({"class":key[0],"method":key[1],"descriptor":m.get_descriptor(),
                  "code_off":m.get_code_off(),"registers":m.get_code().get_registers_size(),
                  "insns_size":m.get_code().get_insns_size(),
                  "tries_size":m.get_code().get_tries_size(),
                  "window":selected})
 if len(result)!=len(TARGETS):raise ValueError("MISSING_METHODS")
 return {"status":"READ_ONLY_BOUND_NATIVE_CALLER_CONTEXT","methods":result,
         "patch_applied":False,"ART":"NOT_VERIFIED"}
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("apk");p.add_argument("--report",required=True)
 a=p.parse_args();r=audit(a.apk)
 pathlib.Path(a.report).write_text(json.dumps(r,indent=2)+"\n")
 print(json.dumps(r,indent=2))
