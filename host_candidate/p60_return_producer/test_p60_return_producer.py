#!/usr/bin/env python3
"""P60 synthetic only: real move-result producer; no unsafe cross-boundary claims."""
import pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from p60_return_producer import follow_local_return,producer_from_move_result,owner_category,method_category,return_category,inspect_primary
checks=0
def check(x,label):
    global checks
    checks+=1
    if not x:raise AssertionError("P60_SYNTHETIC_"+label)
class I:
    def __init__(self,n,out="",operands=(),off=None):
        self.n,self.out,self.operands,self.off=n,out,list(operands),off
    def get_name(self):return self.n
    def get_output(self):return self.out
    def get_operands(self):return self.operands
    def get_ref_off(self):return self.off
class M:
    def __init__(self,ops):self.ops=ops
    def get_instructions_idx(self):return iter(self.ops)
def r(x):return (0,x)
def call(cls,name,params,ret,regs,opcode="invoke-static"):
    value=cls+"->"+name+"("+params+")"+ret
    return I(opcode,"{synth}, "+value,[r(x) for x in regs]+[(256,0,value)])
def move(d,s):return I("move-object",operands=[r(d),r(s)])
def sconst(d,s):return I("const-string",operands=[r(d),(256,0,s)])
factory=call("Ljava/util/Collections;","singletonList","Ljava/lang/Object;","Ljava/util/List;",[2])
process=call("Ljava/lang/ProcessBuilder;","<init>","Ljava/util/List;","V",[0,4],"invoke-direct")
start=call("Ljava/lang/ProcessBuilder;","start","","Ljava/lang/Process;",[0],"invoke-virtual")
ops=[
 (0,sconst(2,"synthetic_entry.js")),
 (2,factory),(4,I("move-result-object",operands=[r(3)])),
 (6,move(4,3)),(8,process),(3912,start)
]
result=inspect_primary(M(ops),set())
p=result["same_method_return_producer"]
check(p["status"]=="EXACT_LOCAL_RESULT_INVOKE","producer")
check(p["owner_category"]=="JAVA_COLLECTIONS","owner")
check(p["method_category"]=="SINGLETON_LIST","factory")
check(p["return_descriptor_category"]=="JAVA_UTIL_LIST","return")
check(p["descriptor_parameter_count"]==1,"params")
check(p["producer_input_origin_categories"].get("CONST_JS_SHAPED")==1,"input")
check(result["fully_resolved_list_contents"] is False,"unknown_elements")
# Branch barrier before the definition prohibits cross-path inference.
branch=ops[:3]+[(5,I("if-eqz",operands=[r(0)],off=4))]+ops[3:]
o=follow_local_return(branch,5,4,{13},set())
check(o["status"]=="UNKNOWN_CONTROL_BARRIER","branch")
# Direct result of unknown method is described categorically only.
opaque=call("Lcom/dsh/android/MyHelper;","privateCommand","",
            "Ljava/util/List;",[],"invoke-static")
opaque_ops=[(0,opaque),(2,I("move-result-object",operands=[r(4)])),(4,process),(3912,start)]
o=follow_local_return(opaque_ops,2,4,set(),set())
check(o["owner_category"]=="DSH_APP","app_owner")
check(o["method_category"]=="OTHER_OR_APP_METHOD","name_hidden")
check(o["producer_input_origin_categories"]=={},"zero_arguments")
# invoke/range: no fake expanded register vector or argv.
range_call=call("Ljava/util/Arrays;","asList","[Ljava/lang/Object;",
                "Ljava/util/List;",[1],"invoke-static/range")
range_ops=[(0,range_call),(2,I("move-result-object",operands=[r(4)])),(4,process),(3912,start)]
o=follow_local_return(range_ops,2,4,set(),set())
check(o["invoke_range_encoding"] is True,"range_detected")
check(o["producer_input_origin_categories"]=={"UNKNOWN_INVOKE_ARGUMENT_ENCODING":1},
      "range_fails_closed")
# unknown producer cannot be normalized to an empty list.
n=I("move-result-object",operands=[r(4)])
check(follow_local_return([(0,n),(2,process)],1,4,set(),set())["status"]==
      "UNKNOWN_MISSING_RESULT_PRODUCER","unbacked_result")
check(owner_category("Lsecret/company/Payload;")=="OTHER_NAMESPACE","no_raw_owner")
print("P60_PRODUCER_SYNTHETIC_TESTS=PASS assertions="+str(checks))
print("P60_SYNTHETIC_ONLY_REAL_APK_NOT_READ=YES")
