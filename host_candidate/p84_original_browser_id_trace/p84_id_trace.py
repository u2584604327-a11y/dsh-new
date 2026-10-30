#!/usr/bin/env python3
"""P84 SHA-pinned native BrowserBridge request-id JSON local trace.
Categorical-only. Not a full CFG/SSA or production tool-result proof.
"""
import argparse,collections,io,json,pathlib,re,sys,zipfile
from loguru import logger
logger.disable("androguard")
from androguard.core.dex import DEX
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"p82_exact_kotlin_io"))
from audit_orig_mailbox_io import OWNER,ROOT_TAG,method_id,inspect_method
sys.path.insert(0,str(ROOT/"p80_native_original_mailbox"))
from audit_orig_dex_mailbox import PINNED_ORIGINAL,PINNED_P6,digest,method_features,exact_const_string
sys.path.insert(0,str(ROOT/"p70_browser_mailbox"))
from audit_native_browser_mailbox import get_files
FIELDS={"id":"ID","action":"ACTION","arguments":"ARGUMENTS","result":"RESULT",
        "error":"ERROR","ok":"OK","type":"TYPE","status":"STATUS",
        "success":"SUCCESS","message":"MESSAGE","data":"DATA","code":"CODE"}
BOUNDS=("if-","goto","packed-switch","sparse-switch","return",
        "throw","monitor-","move-exception")
DEST=("const","new-","iget","sget","aget","instance-of","array-length",
      "check-cast","add-","sub-","mul-","and-","or-","xor-","cmp","neg-","not-")
def registers(ins):
 try:args=ins.get_operands()
 except (AttributeError,TypeError,ValueError):return []
 return [p[1] for p in args
         if isinstance(p,tuple) and len(p)>1 and p[0]==0
         and type(p[1]) is int and 0<=p[1]<512]
def json_api(ins):
 if not ins.get_name().startswith("invoke-"):return None
 output=ins.get_output()
 if "Lorg/json/JSONObject;->" not in output:return None
 match=re.search(r"->([A-Za-z0-9_$]+)\(",output)
 if match is None:return "OTHER"
 name=match.group(1)
 if name in ("getString","optString","get","opt","getJSONObject","getJSONArray","has"):
  return "READ"
 if name=="put":return "PUT"
 if name=="toString":return "SERIALIZE"
 if name=="<init>":return "CONSTRUCTOR"
 return "OTHER"
def scan(ops,dex,cmd,res):
 tags={};pending=None;events=[];counts=collections.Counter()
 ops=list(ops)
 if not 1<=len(ops)<=260:raise ValueError("P84_INSTRUCTION_BOUND")
 for pc,ins in ops:
  name=ins.get_name();rr=registers(ins)
  if name.startswith(BOUNDS):
   tags.clear();pending=None;counts["CONTROL_BARRIER"]+=1
  if name.startswith("const-string"):
   value=exact_const_string(ins,dex)
   category="CMD_FILE" if value==cmd else "REPLY_FILE" if value==res else FIELDS.get(value)
   if rr:
    tags.pop(rr[0],None)
    if category:tags[rr[0]]=("KEY",category)
   if category:events.append({"pc":pc,"event":"CONST","category":category})
  elif name.startswith(("move-object","move/from","move/16")) and len(rr)>=2:
   tags.pop(rr[0],None)
   if rr[1] in tags:tags[rr[0]]=tags[rr[1]]
  elif name=="move-result-object":
   if rr:
    tags.pop(rr[0],None)
    if pending is not None:tags[rr[0]]=pending
   pending=None
  elif name.startswith("move") and rr:
   tags.pop(rr[0],None)
  elif name.startswith("invoke-"):
   operation=json_api(ins);pending=None
   if operation:
    counts["JSON_"+operation]+=1
    is_range=name.endswith("/range")
    if is_range:counts["RANGE_ARGUMENT_ENCODING_UNKNOWN"]+=1
    key=None
    if not is_range and len(rr)>=2 and tags.get(rr[1],("?",))[0]=="KEY":
     key=tags[rr[1]][1]
    if operation in ("PUT","READ"):
     counts[operation+"_FIELD_"+(key or "UNKNOWN")]+=1
    reused=(operation=="PUT" and key=="ID" and
            not is_range and len(rr)>=3 and tags.get(rr[2])==("VALUE","ID"))
    if reused:counts["LOCAL_ID_READ_TO_REPLY_PUT"]+=1
    events.append({"pc":pc,"event":"JSON_"+operation,
                   "field_category":key or "UNKNOWN",
                   "same_block_id_value_proven":bool(reused)})
    if operation=="READ" and key:pending=("VALUE",key)
  elif name.startswith(DEST) and rr:
   tags.pop(rr[0],None);pending=None
  if len(tags)>256:raise ValueError("P84_TAINT_BOUND")
 return events,counts
def audit(original,p6):
 if digest(original)!=PINNED_ORIGINAL or digest(p6)!=PINNED_P6:
  raise ValueError("P84_ORIGINAL_P6_SHA_MISMATCH")
 cmd,res=get_files(p6);roots=[]
 with zipfile.ZipFile(io.BytesIO(original)) as z:
  if z.testzip() is not None:raise ValueError("P84_ORIGINAL_CRC")
  for name in z.namelist():
   if not re.fullmatch(r"classes\d*\.dex",name):continue
   dex=DEX(z.read(name))
   for cl in dex.get_classes():
    if cl.get_name()!=OWNER:continue
    for method in cl.get_methods():
     if method.get_code() is None:continue
     tokens,_,count=method_features(method,dex,cmd,res)
     if tokens=={"CMD","RESULT"}:roots.append((method,dex,count))
 if len(roots)!=1:raise ValueError("P84_NOT_EXACT_ROOT")
 method,dex,count=roots[0]
 if count!=107 or method_id(method)!=ROOT_TAG:
  raise ValueError("P84_ORIGINAL_ROOT_DRIFT")
 io_steps=inspect_method(method,dex,cmd,res)
 reads=[x["code_offset"] for x in io_steps if x["kind"]=="READ_TEXT"]
 writes=[x["code_offset"] for x in io_steps if x["kind"]=="WRITE_TEXT"]
 if len(reads)!=1 or len(writes)!=1 or reads[0]>=writes[0]:
  raise ValueError("P84_READ_WRITE_SEQUENCE_CHANGED")
 timeline,stats=scan(method.get_instructions_idx(),dex,cmd,res)
 return {"original_method_instructions":count,"original_read_before_write":True,
         "json_category_counts":dict(sorted(stats.items())),
         "json_event_categories":timeline,
         "local_request_id_into_reply_put":bool(stats["LOCAL_ID_READ_TO_REPLY_PUT"]),
         "interprocedural_id_equivalence":False,
         "webview_callback_proven":False,
         "p6_node_reply_consumption_proven":False,
         "model_continuation_proven":False}
class Instruction:
 def __init__(self,name,rr=(),ref=None,out=""):
  self.name=name;self.rr=rr;self.ref=ref;self.out=out
 def get_name(self):return self.name
 def get_operands(self):return [(0,r) for r in self.rr]
 def get_ref_kind(self):return self.ref
 def get_output(self):return self.out
class TestDex:
 def get_cm_string(self,k):return {1:"id",2:"p6-command",3:"p6-result"}[k]
def selftest():
 op=[
 (0,Instruction("const-string",(2,),1)),
 (2,Instruction("invoke-virtual",(1,2),out="v1,v2,Lorg/json/JSONObject;->getString(Ljava/lang/String;)Ljava/lang/String;")),
 (4,Instruction("move-result-object",(7,))),
 (6,Instruction("const-string",(8,),1)),
 (8,Instruction("invoke-virtual",(3,8,7),out="v3,v8,v7,Lorg/json/JSONObject;->put(Ljava/lang/String;Ljava/lang/Object;)Lorg/json/JSONObject;")),
 (10,Instruction("if-eqz",(0,))),
 (12,Instruction("invoke-virtual",(3,8,7),out="v3,v8,v7,Lorg/json/JSONObject;->put(Ljava/lang/String;Ljava/lang/Object;)Lorg/json/JSONObject;")),
 (14,Instruction("const-string",(9,),2)),
 (16,Instruction("const-string",(10,),3))]
 events,c=scan(op,TestDex(),"p6-command","p6-result")
 assert c["LOCAL_ID_READ_TO_REPLY_PUT"]==1
 assert c["CONTROL_BARRIER"]==1 and c["PUT_FIELD_UNKNOWN"]==1
 assert sum(e["category"]=="CMD_FILE" for e in events if e["event"]=="CONST")==1
 _,c=scan([(0,Instruction("const-string",(1,),1)),
           (2,Instruction("invoke-virtual/range",(1,2,3),out="v1..v3,Lorg/json/JSONObject;->put(Ljava/lang/String;Ljava/lang/Object;)Lorg/json/JSONObject;"))],TestDex(),"p6-command","p6-result")
 assert c["RANGE_ARGUMENT_ENCODING_UNKNOWN"]==1
 assert not c["LOCAL_ID_READ_TO_REPLY_PUT"]
 print("P84_LOCAL_ID_TRACE_BRANCH_AND_RANGE_FAIL_CLOSED=PASS")
if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--original");p.add_argument("--p6");p.add_argument("--selftest",action="store_true")
 a=p.parse_args()
 if a.selftest:selftest()
 else:
  if not a.original or not a.p6:p.error("original/P6 required")
  result=audit(pathlib.Path(a.original).read_bytes(),pathlib.Path(a.p6).read_bytes())
  print("P84_EXACT_ORIGINAL_REQUEST_ID_JSON_TRACE=PASS")
  print("P84_CATEGORICAL_ONLY="+json.dumps(result,sort_keys=True))
  print("P84_ORIGINAL_MODEL_TOOL_RESULT_CONTINUATION=NOT_PROVEN")
