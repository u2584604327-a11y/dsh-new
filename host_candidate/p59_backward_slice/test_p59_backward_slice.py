#!/usr/bin/env python3
"""P59 synthetic-only constructor def-use and barrier negative tests."""
import pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from p59_backward_slice import trace_arg,analyze_primary,ready_structure
n=0
def ok(v,label):
    global n
    n+=1
    if not v: raise AssertionError("P59_SYNTHETIC_"+label)
class I:
    def __init__(self,n,out="",operands=(),off=None):
        self.n,self.out,self.operands,self.off=n,out,list(operands),off
    def get_name(self): return self.n
    def get_output(self): return self.out
    def get_operands(self): return self.operands
    def get_ref_off(self): return self.off
class M:
    def __init__(self,ops,offset=3163260):
        self.ops,self.offset=ops,offset
    def get_code_off(self): return self.offset
    def get_name(self): return "invokeSuspend"
    def get_instructions_idx(self): return iter(self.ops)
def reg(n):return (0,n)
def string(r,s):return I("const-string",operands=[reg(r),(256,0,s)])
def mov(d,s):return I("move-object",operands=[reg(d),reg(s)])
def new(r,cls):return I("new-instance","v0, "+cls,[reg(r),(256,0,cls)])
def invoke(cls,name,desc,regs=()):
    value=cls+"->"+name+"("+desc+")V"
    return I("invoke-direct","{registers}, "+value,[reg(x) for x in regs]+[(256,0,value)])
ctor=invoke("Ljava/lang/ProcessBuilder;","<init>","Ljava/util/List;",[1,4])
start=invoke("Ljava/lang/ProcessBuilder;","start","",[1])
base=[
    (0,new(4,"Ljava/util/ArrayList;")),
    (2,mov(5,4)),
    (4,mov(4,5)),
    (6,ctor),
    (3912,start)
]
r=analyze_primary(M(base),set())
ok(r["process_constructor_descriptor_class"]=="LIST","list_descriptor")
ok(r["parameter_backward_source_categories"]["ALLOC_ARRAYLIST_CONTENTS_UNKNOWN"]==1,"new_list_origin")
ok(not r["complete_argv_object_contents_proven"],"no_claim")
# register overwrite takes precedence over earlier allocation
overwrite=base[:3]+[(5,string(4,"synthetic.js"))]+base[3:]
r=analyze_primary(M(overwrite),set())
ok(r["parameter_backward_source_categories"]["CONST_JS_SHAPED"]==1,"overwrite")
# Branch prevents treating def from a different path as producer.
barrier=base[:3]+[(5,I("if-eqz",operands=[reg(0)],off=3))]+base[3:]
r=analyze_primary(M(barrier),set())
ok(r["parameter_backward_source_categories"]["UNKNOWN_CONTROL_BOUNDARY"]==1,"branch")
# move-result immediately follows producer, but list elements are not proven.
listcall=invoke("Ljava/util/Arrays;","asList","[Ljava/lang/Object;",[2])
out=[
    (0,listcall),(2,I("move-result-object",operands=[reg(4)])),
    (4,ctor),(3912,start)
]
r=analyze_primary(M(out),set())
ok(r["parameter_backward_source_categories"]["ARRAYS_AS_LIST_CONTENTS_UNKNOWN"]==1,"factory")
# opaque field-load must stay unknown and never become an APK argv assertion
field=[(0,I("iget-object",operands=[reg(4),reg(0),(256,0,"Lfake/Foo;->bar")])),
       (2,ctor),(3912,start)]
r=analyze_primary(M(field),set())
ok(r["parameter_backward_source_categories"]["FIELD_OR_ARRAY_READ_OPAQUE"]==1,"field")
# Within-method proximity to READY is not a proven conditional.
ready=M([(0,string(5,"READY")),(2,invoke("Ljava/lang/String;","equals","Ljava/lang/Object;",[0,5])),
         (4,I("if-eqz",operands=[reg(3)],off=4)),
         (6,invoke("Ljava/util/concurrent/CountDownLatch;","countDown","",[0]))])
near=ready_structure([("Lfake/Callback;",ready)],set())
ok(near["READY_LITERAL_HITS"]==1,"ready_literal")
ok(near["READY_NEAR_STRING_COMPARE"]==1,"ready_lexical")
ok("READY_NEAR_LATCH_SIGNAL" not in near,"branch_halting")
# Misleading invoke/range single start-register must be marked UNKNOWN
range_ctor=I("invoke-direct/range",
"{v1 .. v4}, Ljava/lang/ProcessBuilder;-><init>(Ljava/util/List;)V",
[reg(1),(256,0,"Ljava/lang/ProcessBuilder;")])
r=analyze_primary(M([(0,new(4,"Ljava/util/ArrayList;")),(6,range_ctor),(3912,start)]),set())
ok(r["parameter_backward_source_categories"]["UNKNOWN_ARGUMENT_REGISTER_ENCODING"]==1,
   "range_must_be_unknown")
print("P59_BACKWARD_SLICE_SYNTHETIC_TESTS=PASS assertions="+str(n))
print("P59_SYNTHETIC_ORIGINAL_BYTES_USED=NO")
