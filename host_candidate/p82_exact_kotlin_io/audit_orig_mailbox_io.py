#!/usr/bin/env python3
"""P82 original BrowserBridge exact Kotlin command/result file IO audit.
Never prints literal filenames, source bytes, method names or private values.
"""
import argparse,hashlib,io,json,pathlib,re,sys,zipfile
from androguard.core.dex import DEX
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"p80_native_original_mailbox"))
from audit_orig_dex_mailbox import (
 PINNED_ORIGINAL,PINNED_P6,digest,exact_const_string,method_features)
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"p70_browser_mailbox"))
from audit_native_browser_mailbox import get_files
OWNER="Lcom/dsh/android/browser/BrowserBridge;"
ROOT_TAG="d55c5289f8a4"
def method_id(method):
 return digest((method.get_class_name()+"::"+method.get_name()+
                method.get_descriptor()).encode())[:12]
def kotlin_io_kind(output):
 if "Lkotlin/io/FilesKt" not in output and "Ljava/nio/file/Files;" not in output:
  return None
 match=re.search(r"->([A-Za-z][A-Za-z0-9_$]*)\(",output)
 if match is None:return "UNKNOWN_KOTLIN_IO"
 name=match.group(1).split('$',1)[0]
 mapping={"readText":"READ_TEXT","writeText":"WRITE_TEXT",
          "readBytes":"READ_BYTES","writeBytes":"WRITE_BYTES",
          "appendText":"APPEND_TEXT","copyTo":"COPY_FILE",
          "readLines":"READ_LINES","forEachLine":"READ_LINES",
          "move":"MOVE_FILE","write":"WRITE_NIO","read":"READ_NIO"}
 return mapping.get(name,"OTHER_KOTLIN_IO")
def inspect_method(method,dex,cmd,res):
 row=[]
 for pc,ins in method.get_instructions_idx():
  name=ins.get_name()
  if name.startswith("const-string"):
   literal=exact_const_string(ins,dex)
   if literal==cmd:row.append({"code_offset":pc,"kind":"CMD_CONST"})
   if literal==res:row.append({"code_offset":pc,"kind":"RESULT_CONST"})
  if not name.startswith("invoke-"):continue
  text=ins.get_output()
  kind=kotlin_io_kind(text)
  if kind is not None:row.append({"code_offset":pc,"kind":kind})
  if "Lorg/json/JSONObject;->" in text:
   if "->put(" in text:kind="JSON_PUT"
   elif "->toString(" in text:kind="JSON_SERIALIZE"
   elif any(x in text for x in ("->get(", "->opt(", "->getString(", "->optString(")):
    kind="JSON_READ"
   else:kind="JSON_OTHER"
   row.append({"code_offset":pc,"kind":kind})
  if "Landroid/os/Handler;->" in text:
   row.append({"code_offset":pc,"kind":"HANDLER_DISPATCH"})
  if "Landroid/webkit/WebView;->evaluateJavascript(" in text:
   row.append({"code_offset":pc,"kind":"WEBVIEW_EVAL"})
 return sorted(row,key=lambda r:r["code_offset"])
def audit(original,p6):
 if digest(original)!=PINNED_ORIGINAL or digest(p6)!=PINNED_P6:
  raise ValueError("P82_ORIGINAL_OR_P6_HASH_MISMATCH")
 cmd,res=get_files(p6)
 with zipfile.ZipFile(io.BytesIO(original)) as archive:
  if archive.testzip() is not None:raise ValueError("P82_BAD_ORIGINAL_APK_CRC")
  blobs=[archive.read(n) for n in archive.namelist()
         if re.fullmatch(r"classes\d*\.dex",n)]
 roots=[]
 for blob in blobs:
  dex=DEX(blob)
  for cl in dex.get_classes():
   if cl.get_name()!=OWNER:continue
   for m in cl.get_methods():
    if m.get_code() is None:continue
    tokens,_,count=method_features(m,dex,cmd,res)
    if tokens=={"CMD","RESULT"}:roots.append((m,dex,count))
 if len(roots)!=1:raise ValueError("P82_ORIGINAL_MAILBOX_ROOT_NOT_UNIQUE")
 m,dex,count=roots[0]
 if method_id(m)!=ROOT_TAG or count!=107:
  raise ValueError("P82_P80_P81_ROOT_ID_OR_OPCODE_DRIFT")
 steps=inspect_method(m,dex,cmd,res)
 kinds=[s["kind"] for s in steps]
 if kinds.count("CMD_CONST")!=1 or kinds.count("RESULT_CONST")!=1:
  raise ValueError("P82_CMD_RESULT_NOT_UNIQUE_WITHIN_ROOT")
 return {"root_instructions":count,"opaque_root_id":ROOT_TAG,
         "steps":steps,
         "kotlin_read_text_present":"READ_TEXT" in kinds,
         "kotlin_write_text_present":"WRITE_TEXT" in kinds,
         "kotlin_nio_operations":[x for x in kinds if x.endswith("_TEXT") or
                                  x in ("READ_BYTES","WRITE_BYTES","WRITE_NIO","READ_NIO","OTHER_KOTLIN_IO")],
         "full_command_to_reply_control_flow_proven":False,
         "model_tool_result_continuation_proven":False}
def selftest():
 assert kotlin_io_kind('v0, Lkotlin/io/FilesKt;->readText(Ljava/io/File;)Ljava/lang/String;')=="READ_TEXT"
 assert kotlin_io_kind('v0, Lkotlin/io/FilesKt__FileReadWriteKt;->writeText(Ljava/io/File;Ljava/lang/String;)V')=="WRITE_TEXT"
 assert kotlin_io_kind('v0, Lkotlin/io/FilesKt;->readText$default(Ljava/io/File;)Ljava/lang/String;')=="READ_TEXT"
 assert kotlin_io_kind('v0, Lkotlin/io/FilesKt__FileReadWriteKt;->writeText$default(Ljava/io/File;Ljava/lang/String;)V')=="WRITE_TEXT"
 assert kotlin_io_kind('v0, Ljava/io/FileOutputStream;->write([B)V') is None
 assert kotlin_io_kind('v0, Ljava/nio/file/Files;->write(Ljava/nio/file/Path;[B)V')=="WRITE_NIO"
 print("P82_SYNTHETIC_KOTLIN_IO_LITERAL_CLASSIFIER=PASS")
if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--original");p.add_argument("--p6");p.add_argument("--selftest",action="store_true")
 a=p.parse_args()
 if a.selftest:selftest()
 else:
  if not a.original or not a.p6:p.error("original and P6 required")
  result=audit(pathlib.Path(a.original).read_bytes(),pathlib.Path(a.p6).read_bytes())
  print("P82_EXACT_ORIGINAL_MAILBOX_FILE_IO_OPCODE_AUDIT=PASS")
  print("P82_NO_LITERAL_OR_PRIVATE_CODE_PRINTED=YES")
  print("P82_CATEGORICAL_ONLY="+json.dumps(result,sort_keys=True))
  print("P82_ORIGINAL_BROWSER_RESULT_TO_MODEL_CONTINUATION=NOT_PROVEN")
