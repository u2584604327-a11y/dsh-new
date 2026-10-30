#!/usr/bin/env python3
"""P80: original SHA-pinned native DEX mailbox command reader/result writer
control-surface discovery. Values and method identities remain private.
A per-method API cooccurrence is NEVER proof of execution/reply delivery.
"""
import argparse,collections,hashlib,json,pathlib,re,sys,zipfile
from androguard.core.dex import DEX
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"p70_browser_mailbox"))
from audit_native_browser_mailbox import get_files
PINNED_ORIGINAL="3ca56655d79afc57431636e340823e7071bc830615ca615c485b0b9a30b6e3e5"
PINNED_P6="3af586c2c83d1aea67d119357672559eb09371c77ef4e06900bb697c06d11fd5"
CALL=re.compile(r"(L[^;\s,]+;)->([^\s(,]+)\(")
GROUPS={
 "FILE_INPUT":("Ljava/io/FileInputStream;->","Ljava/io/FileReader;->"),
 "FILE_OUTPUT":("Ljava/io/FileOutputStream;->","Ljava/io/FileWriter;->"),
 "FILE_OP":("Ljava/io/File;->","Ljava/nio/file/Files;->"),
 "ATOMIC_FILE":("Landroid/util/AtomicFile;->",),
 "JSON":("Lorg/json/JSONObject;->",),
 "WEBVIEW_EVAL":("Landroid/webkit/WebView;->evaluateJavascript(",
                 "Lcom/dsh/android/browser/AiBrowserView;->"),
 "WEBVIEW_NATIVE":("Landroid/webkit/WebView;->",),
 "THREADING":("Landroid/os/Handler;->","Ljava/lang/Thread;->"),
}
def digest(b):return hashlib.sha256(b).hexdigest()
def owner_bucket(owner):
 if owner=="Lcom/dsh/android/browser/BrowserBridge;":return "ORIGINAL_BROWSER_BRIDGE"
 if owner=="Lcom/dsh/android/browser/AiBrowserView;":return "ORIGINAL_AI_BROWSER_VIEW"
 if owner.startswith("Lcom/dsh/android/browser/"):return "ORIGINAL_BROWSER_FAMILY"
 if owner.startswith("Lcom/dsh/android/MainActivity"):return "ORIGINAL_MAIN_ACTIVITY"
 if owner.startswith("Lcom/dsh/android/"):return "DSH_APP_OTHER"
 return "OTHER"
def exact_const_string(ins,dex):
 if not ins.get_name().startswith("const-string"):return None
 try:
  value=dex.get_cm_string(ins.get_ref_kind())
  if isinstance(value,str):return value
 except (AttributeError,TypeError,KeyError,IndexError,ValueError):pass
 # Fallback only if the complete literal appears as an exact double-quoted
 # constant operand. Never treat an arbitrary substring as a method match.
 output=ins.get_output()
 m=re.search(r',\s*"([^"\\]*)"\s*$',output)
 return m.group(1) if m else None
def method_features(method,dex,cmd,res):
 values=set();calls=collections.Counter();instructions=0
 if method.get_code() is None:return values,calls,instructions
 for _,ins in method.get_instructions_idx():
  instructions+=1
  v=exact_const_string(ins,dex)
  if v==cmd:values.add("CMD")
  if v==res:values.add("RESULT")
  if not ins.get_name().startswith("invoke-"):continue
  output=ins.get_output()
  for category,prefixes in GROUPS.items():
   if any(p in output for p in prefixes):calls[category]+=1
 return values,calls,instructions
def audit(original,p6):
 if digest(original)!=PINNED_ORIGINAL or digest(p6)!=PINNED_P6:
  raise ValueError("P80_ORIGINAL_OR_P6_SHA_MISMATCH")
 cmd,res=get_files(p6)
 if not cmd or not res or cmd==res:raise ValueError("P80_INVALID_PINNED_FILENAMES")
 import io
 with zipfile.ZipFile(io.BytesIO(original)) as archive:
  if archive.testzip() is not None:raise ValueError("P80_BAD_ORIGINAL_ZIP_CRC")
  dex_sources=[(n,archive.read(n)) for n in archive.namelist()
               if re.fullmatch(r"classes\d*\.dex",n)]
 counts=collections.Counter()
 findings=[]
 for dexname,raw in dex_sources:
  dex=DEX(raw)
  for klass in dex.get_classes():
   owner=klass.get_name()
   if not owner.startswith("Lcom/dsh/android/"):continue
   for method in klass.get_methods():
    found,calls,total=method_features(method,dex,cmd,res)
    if not found:continue
    counts["CMD" if found=={"CMD"} else
           "RESULT" if found=={"RESULT"} else "BOTH"]+=1
    category=owner_bucket(owner)
    method_tag=digest((owner+"::"+method.get_name()+
                      method.get_descriptor()).encode())[:12]
    # Classify but DO NOT claim a writer solely from API co-occurrence.
    has_file_write=bool(calls["FILE_OUTPUT"] or calls["ATOMIC_FILE"])
    has_file_read=bool(calls["FILE_INPUT"] or calls["FILE_OP"])
    findings.append({
      "dex_category":("PRIMARY" if dexname=="classes.dex" else "SECONDARY"),
      "owner_category":category,
      "anonymous_method_tag":method_tag,
      "literal_categories":sorted(found),
      "instruction_count":total,
      "api_categories":{k:int(v) for k,v in sorted(calls.items()) if v},
      "candidate_input":("CMD" in found and has_file_read),
      "candidate_result_writer":("RESULT" in found and has_file_write),
      "native_webview_invocation_in_same_method":bool(calls["WEBVIEW_EVAL"])
    })
 findings.sort(key=lambda x:(x["owner_category"],x["anonymous_method_tag"]))
 if len(findings)>32:
  raise ValueError("P80_TOO_MANY_UNBOUNDED_METHODS")
 return {
   "cmd_const_string_methods":counts["CMD"]+counts["BOTH"],
   "result_const_string_methods":counts["RESULT"]+counts["BOTH"],
   "both_in_one_method":counts["BOTH"],
   "candidate_command_reader_methods":sum(x["candidate_input"] for x in findings),
   "candidate_result_writer_methods":sum(x["candidate_result_writer"] for x in findings),
   "methods":findings,
   "P80_NATIVE_RESULT_DISPATCH_PROVEN":False,
   "P80_ORIGINAL_MODEL_CONTINUATION_PROVEN":False
 }
def test():
 class FakeIns:
  def __init__(self,name,kind,out):self.n=name;self.k=kind;self.o=out
  def get_name(self):return self.n
  def get_ref_kind(self):return self.k
  def get_output(self):return self.o
 class FakeDex:
  def get_cm_string(self,index):return {1:"cmd.json",2:"result.json"}[index]
 class FakeMethod:
  def get_code(self):return self
  def get_instructions_idx(self):
   return enumerate([
      FakeIns("const-string",1,'v0, "cmd.json"'),
      FakeIns("invoke-virtual",0,'v0, Ljava/io/FileInputStream;->read([B)I'),
      FakeIns("const-string",2,'v1, "result.json"'),
      FakeIns("invoke-virtual",0,'v1, Ljava/io/FileOutputStream;->write([B)V')])
 values,calls,_=method_features(FakeMethod(),FakeDex(),"cmd.json","result.json")
 assert values=={"CMD","RESULT"}
 assert calls["FILE_INPUT"]==1 and calls["FILE_OUTPUT"]==1
 assert exact_const_string(FakeIns("const-string",0,'v0, "different.json"'),
                           FakeDex())!="cmd.json"
 assert owner_bucket("Lcom/dsh/android/browser/BrowserBridge;")=="ORIGINAL_BROWSER_BRIDGE"
 assert owner_bucket("Lcom/dsh/android/browser/AiBrowserView;")=="ORIGINAL_AI_BROWSER_VIEW"
 print("P80_SYNTHETIC_EXACT_METHOD_LITERAL_AND_IO_CLASSIFIER=PASS")
if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--original");p.add_argument("--p6");p.add_argument("--selftest",action="store_true")
 a=p.parse_args()
 if a.selftest:test()
 else:
  if not a.original or not a.p6:p.error("original and P6 required")
  r=audit(pathlib.Path(a.original).read_bytes(),pathlib.Path(a.p6).read_bytes())
  print("P80_PINNED_ORIGINAL_DEX_TARGETED_MAILBOX_METHOD_AUDIT=PASS")
  print("P80_CATEGORICAL_NATIVE_MAILBOX_EVIDENCE="+json.dumps(r,sort_keys=True))
  print("P80_P6_FILE_BASENAMES_PRINTED=NO")
  print("P80_ORIGINAL_BROWSER_TOOL_RESULT_MODEL_RESUME=NOT_PROVEN")
