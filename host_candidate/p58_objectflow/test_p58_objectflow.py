#!/usr/bin/env python3
"""P58 synthetic-only builder/list/array and ready provenance and kill tests."""
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from p58_objectflow import simulate
assertions = 0
def check(ok, label):
    global assertions
    assertions += 1
    if not ok:
        raise AssertionError("P58_FAIL_" + label)
class Inst:
    def __init__(self, name, output="", operands=None, off=None):
        self.name, self.output, self.operands, self.off = name, output, operands or [], off
    def get_name(self): return self.name
    def get_output(self): return self.output
    def get_operands(self): return self.operands
    def get_ref_off(self): return self.off
class Method:
    def __init__(self, sequence): self.sequence = sequence
    def get_instructions_idx(self): return iter(self.sequence)
def reg(n): return (0,n)
def literal(n,v): return Inst("const-string", operands=[reg(n),(256,0,v)])
def new(n,cls): return Inst("new-instance", output="v%d, %s"%(n,cls),operands=[reg(n),(256,0,cls)])
def invoke(cls,fun,reg_list,desc="()V"):
    method = cls+"->"+fun+desc
    return Inst("invoke-virtual","{v}, "+method,[reg(n) for n in reg_list]+[(256,1,method)])
def moveto(d,s):return Inst("move-object",operands=[reg(d),reg(s)])
def mresult(n):return Inst("move-result-object",operands=[reg(n)])
builder="Ljava/lang/StringBuilder;"
list_="Ljava/util/ArrayList;"
process="Ljava/lang/ProcessBuilder;"
js="private_fake_entry.js"
ready="READY"
source=[
    (0,new(1,builder)), (2,invoke(builder,"<init>",[1])),
    (4,literal(2,js)), (6,invoke(builder,"append",[1,2],"(Ljava/lang/String;)Ljava/lang/StringBuilder;")),
    (8,invoke(builder,"toString",[1],"()Ljava/lang/String;")),
    (10,mresult(3)), (12,new(4,list_)),
    (14,invoke(list_,"<init>",[4])), (16,invoke(list_,"add",[4,3],"(Ljava/lang/Object;)Z")),
    (18,invoke(process,"<init>",[5,4],"(Ljava/util/List;)V")),
    (20,literal(7,ready)),
    (22,invoke("Ljava/lang/String;","equals",[6,7],"(Ljava/lang/Object;)Z")),
    (24,mresult(8)),
    (26,Inst("if-eqz",operands=[reg(8)],off=3)),
]
found=simulate(Method(source),set())
check(found["BUILDER_APPEND_SOURCE_JS_SHAPED"]==1,"builder_append")
check(found["BUILDER_TOSTRING_TAGGED_JS_SHAPED"]==1,"to_string")
check(found["LIST_ADD_SOURCE_JS_SHAPED"]==1,"list_aggregate")
check(found["PROCESS_ARG_LOCAL_TAG_JS_SHAPED"]==1,"constructor_arg")
check(found["READY_LITERAL_AT_STRING_COMPARE"]==1,"ready_compare")
check(found["READY_COMPARE_RESULT_REGISTER"]==1,"comparison_result")
# A later overwrite invalidates the prior string before the add.
overwrite=source[:7]+[(15,literal(3,"overwritten_not_javascript"))]+source[7:]
bad=simulate(Method(overwrite),set())
check(bad.get("PROCESS_ARG_LOCAL_TAG_JS_SHAPED",0)==0,"register_overwrite")
# Jump target and branch kills object alias; must not carry through opaque CFG.
branched=source[:9]+[(17,Inst("if-eqz",operands=[reg(4)],off=3))]+source[9:]
bad2=simulate(Method(branched),set())
check(bad2.get("PROCESS_ARG_LOCAL_TAG_JS_SHAPED",0)==0,"branch_barrier")
# Opaque mutation of list kills its provenance.
opaque=source[:9]+[(17,invoke("Lsynthetic/Opaque;","change",[4]))]+source[9:]
bad3=simulate(Method(opaque),set())
check(bad3.get("PROCESS_ARG_LOCAL_TAG_JS_SHAPED",0)==0,"opaque_mutation_invalidation")
check(bad3.get("OPAQUE_OBJECT_INVALIDATION",0)>=1,"opaque_counter")
# Values don't cross a method boundary or become "production ready".
check("READY_LITERAL_AS_STATEFLOW_ARGUMENT" not in found,"no_fabricated_stateflow")
check("PROCESS_ARG_LOCAL_TAG_READY_STRING_HINT" not in found,"no_fake_ready_command")
print("P58_OBJECT_PROVENANCE_SYNTHETIC_TESTS=PASS assertions="+str(assertions))
print("P58_SYNTHETIC_ONLY_ORIGINAL_BINARY_NEVER_USED=YES")
