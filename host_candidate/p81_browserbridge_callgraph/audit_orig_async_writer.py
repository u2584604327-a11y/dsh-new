#!/usr/bin/env python3
"""P81 exact SHA-pinned original BrowserBridge closure/dataflow map.
Original method/code names and private string literals never printed.
Only categorization: a call edge is not executable control-flow proof.
"""
import argparse,collections,hashlib,io,json,pathlib,re,sys,zipfile
from androguard.core.dex import DEX
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"p80_native_original_mailbox"))
from audit_orig_dex_mailbox import PINNED_ORIGINAL,PINNED_P6,digest,owner_bucket,method_features
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"p70_browser_mailbox"))
from audit_native_browser_mailbox import get_files
BRIDGE="Lcom/dsh/android/browser/BrowserBridge;"
ROOT_TAG="d55c5289f8a4"
MAX_METHODS=160
MAX_DEPTH=3
CALL=re.compile(r"(L[^;\s,]+;)->([^\s(,]+)\(([^)]*)\)\s*([^\s,]*)")
OWNER_RE=re.compile(r"(Lcom/dsh/android/browser/[^;\s,]+;)")
KOTLIN_IO=("Lkotlin/io/FilesKt","Lkotlin/io/FilesKt__","Ljava/nio/file/Files;->write",
           "Ljava/nio/file/Files;->move")
DIRECT_WRITE=("Ljava/io/FileOutputStream;->","Ljava/io/FileWriter;->",
              "Landroid/util/AtomicFile;->","Ljava/io/Writer;->write")
READ=("Ljava/io/FileInputStream;->","Ljava/io/FileReader;->",
      "Ljava/nio/file/Files;->read","Lkotlin/io/FilesKt")
EVAL=("Landroid/webkit/WebView;->evaluateJavascript","->evaluateJavascript(")
CLOSURE_METHODS={"invoke","invokeSuspend","run","accept","call","onSuccess",
                 "onFailure","onPageFinished","onReceiveValue","handleMessage"}
def ident(method):
 return (method.get_class_name(),method.get_name(),
         re.sub(r"\s+","",method.get_descriptor()))
def tag(key):
 return digest((key[0]+"::"+key[1]+key[2]).encode())[:12]
def resolved(output):
 m=CALL.search(output)
 if not m:return None
 owner,name,params,ret=m.groups()
 if not ret:return None
 return (owner,name,"("+re.sub(r"\s+","",params)+")"+ret.strip())
def classify(method):
 result=collections.Counter()
 for _,ins in method.get_instructions_idx():
  n=ins.get_name()
  if not n.startswith("invoke-"):continue
  s=ins.get_output()
  if any(t in s for t in DIRECT_WRITE):result["DIRECT_FILE_WRITE"]+=1
  if any(t in s for t in KOTLIN_IO):result["KOTLIN_OR_NIO_IO"]+=1
  if any(t in s for t in READ):result["FILE_READ"]+=1
  if any(t in s for t in EVAL):result["WEBVIEW_EVALUATION"]+=1
  if "Lorg/json/JSONObject;" in s:result["JSON_PROCESSING"]+=1
  if "Landroid/os/Handler;" in s or "Ljava/lang/Thread;" in s:
   result["ASYNC_DISPATCH"]+=1
  if "Lcom/dsh/android/browser/" in s:result["APP_BROWSER_INVOKE"]+=1
 return result
def discover(method):
 invoked=set();closure_owners=set()
 if method.get_code() is None:return invoked,closure_owners
 for _,ins in method.get_instructions_idx():
  s=ins.get_output()
  if ins.get_name().startswith("invoke-"):
   parsed=resolved(s)
   if parsed and parsed[0].startswith("Lcom/dsh/android/"):
    invoked.add(parsed)
  if ins.get_name()=="new-instance" or ins.get_name()=="const-class":
   for owner in OWNER_RE.findall(s):
    if owner.startswith(BRIDGE[:-1]+"$"):
     closure_owners.add(owner)
 return invoked,closure_owners
def audit(original,p6):
 if digest(original)!=PINNED_ORIGINAL or digest(p6)!=PINNED_P6:
  raise ValueError("P81_SOURCE_SHA_MISMATCH")
 command,result=get_files(p6)
 with zipfile.ZipFile(io.BytesIO(original)) as archive:
  if archive.testzip() is not None:raise ValueError("P81_APK_CRC")
  blobs=[archive.read(name) for name in archive.namelist()
         if re.fullmatch(r"classes\d*\.dex",name)]
 defs={}
 for raw in blobs:
  d=DEX(raw)
  for cl in d.get_classes():
   if not cl.get_name().startswith("Lcom/dsh/android/"):continue
   for m in cl.get_methods():
    if m.get_code() is not None:
     defs[ident(m)]=(m,d)
 roots=[]
 for k,(m,d) in defs.items():
  if k[0]!=BRIDGE:continue
  tokens,_,_=method_features(m,d,command,result)
  if tokens=={"CMD","RESULT"}:roots.append(k)
 if len(roots)!=1 or tag(roots[0])!=ROOT_TAG:
  raise ValueError("P81_EXACT_ROOT_OR_P80_METHOD_ID_DRIFT")
 queue=collections.deque([(roots[0],0,"ROOT")])
 visited=set();rows=[];unresolved=0;closures=0
 while queue:
  key,depth,via=queue.popleft()
  if key in visited:continue
  if len(visited)>=MAX_METHODS:raise ValueError("P81_BOUND_REACHED")
  visited.add(key)
  item=defs.get(key)
  if item is None:
   unresolved+=1;continue
  m,d=item
  features=classify(m)
  calls,owners=discover(m)
  rows.append({
   "opaque_method_id":tag(key),
   "owner_category":owner_bucket(key[0]),
   "depth":depth,"edge_category":via,
   "instruction_count":sum(1 for _ in m.get_instructions_idx()),
   "api_categories":{k:v for k,v in sorted(features.items()) if v},
   "is_direct_file_writer_candidate":features["DIRECT_FILE_WRITE"]>0,
   "is_webview_executor_candidate":features["WEBVIEW_EVALUATION"]>0
  })
  if depth>=MAX_DEPTH:continue
  for dest in sorted(calls):
   if dest not in visited and dest[0].startswith("Lcom/dsh/android/"):
    queue.append((dest,depth+1,"DIRECT_CALL"))
  for owner in sorted(owners):
   candidates=[k for k in defs
               if k[0]==owner and k[1] in CLOSURE_METHODS]
   closures+=len(candidates)
   if len(candidates)>24:raise ValueError("P81_TOO_MANY_CLOSURE_METHODS")
   for candidate in sorted(candidates):
    if candidate not in visited:
     queue.append((candidate,depth+1,"CLOSURE_OBJECT"))
 rows.sort(key=lambda x:(x["depth"],x["opaque_method_id"]))
 return {
  "root_exact_unique":True,
  "root_method_instructions":rows[0]["instruction_count"] if rows else None,
  "reachable_method_count":len(rows),
  "unresolved_member_refs":unresolved,
  "closure_invocation_candidates":closures,
  "direct_file_writer_candidates":sum(x["is_direct_file_writer_candidate"] for x in rows),
  "webview_executor_candidates":sum(x["is_webview_executor_candidate"] for x in rows),
  "categories":collections.Counter(x["owner_category"] for x in rows),
  "methods":[x for x in rows if x["api_categories"] or x["depth"]==0],
  "original_tool_result_delivery_proven":False,
  "original_model_continuation_proven":False
 }
def selftest():
 class Mock:
  def get_output(self):return "v0, Lcom/dsh/android/browser/BrowserBridge;->foo(Ljava/lang/String;)V"
 assert resolved(Mock().get_output())==(
  "Lcom/dsh/android/browser/BrowserBridge;","foo","(Ljava/lang/String;)V")
 assert resolved("v0, Landroid/webkit/WebView;->evaluateJavascript(Ljava/lang/String;Landroid/webkit/ValueCallback;)V")
 assert tag((BRIDGE,"example","()V"))!=ROOT_TAG
 print("P81_SYNTHETIC_DESCRIPTOR_AND_CLASSIFIER=PASS")
if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--original");p.add_argument("--p6");p.add_argument("--selftest",action="store_true")
 a=p.parse_args()
 if a.selftest:selftest()
 else:
  if not a.original or not a.p6:p.error("original/P6 required")
  data=audit(pathlib.Path(a.original).read_bytes(),pathlib.Path(a.p6).read_bytes())
  data["categories"]=dict(data["categories"])
  print("P81_ORIGINAL_BROWSERBRIDGE_CALL_GRAPH_CATEGORY_AUDIT=PASS")
  print("P81_CATEGORICAL_ONLY="+json.dumps(data,sort_keys=True))
  print("P81_ORIGINAL_TOOL_RESULT_TO_MODEL=NOT_WIRED")
