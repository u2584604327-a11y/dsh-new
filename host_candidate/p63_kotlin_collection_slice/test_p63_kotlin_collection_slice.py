#!/usr/bin/env python3
"""P63 public Kotlin methods, operand validation and conservative return path."""
import pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from p63_kotlin_collection_slice import safe_api,safe_public_kotlin_method,ret_type,encoded_arguments,analyze_callee
n=0
def check(ok,label):
    global n
    n+=1
    if not ok:raise AssertionError("P63_SYNTHETIC_"+label)
class I:
    def __init__(self,name,out="",operands=(),off=None):
        self.name,self.out,self.operands,self.off=name,out,list(operands),off
    def get_name(self):return self.name
    def get_output(self):return self.out
    def get_operands(self):return self.operands
    def get_ref_off(self):return self.off
class M:
    def __init__(self,ops):self.ops=ops
    def get_code(self):return object()
    def get_instructions_idx(self):return iter(self.ops)
def reg(n):return (0,n)
def inv(name,regs,form="invoke-static",owner="Lkotlin/collections/CollectionsKt;"):
    value=owner+"->"+name+"(Ljava/lang/Object;)Ljava/util/List;"
    return I(form,"{v}, "+value,[reg(i) for i in regs]+[(256,0,value)])
def literal(r,s):return I("const-string","",[reg(r),(256,0,s)])
check(safe_api("Lkotlin/collections/CollectionsKt;","listOf")=="LIST_OF","safe_public")
check(safe_api("Lcom/dsh/android/Private;","listOf")=="NOT_KOTLIN_COLLECTION","no_private")
check(ret_type("Ljava/util/List;")=="LIST","return_category")
check(safe_public_kotlin_method("Lkotlin/collections/CollectionsKt;","listOf")=="listOf","public_method")
check(safe_public_kotlin_method("Lcom/dsh/android/Secret;","secret")=="NON_KOTLIN_OWNER","only_std")
check(safe_public_kotlin_method("Lkotlin/collections/CollectionsKt;","bad/slash")=="UNSAFE_PUBLIC_SYMBOL_FORMAT","symbol_allowlist")
known=inv("listOf",[2])
check(encoded_arguments(known,("Lkotlin/collections/CollectionsKt;","listOf","Ljava/lang/Object;"))["status"]=="ARG_REGISTERS_DECODED","one_register")
missing=inv("listOf",[])
check(encoded_arguments(missing,("Lkotlin/collections/CollectionsKt;","listOf","Ljava/lang/Object;"))["status"]=="UNKNOWN_REGISTER_DECODING","missing")
zero=I("invoke-static","{}, Lkotlin/collections/CollectionsKt;->emptyList()Ljava/util/List;",[])
check(encoded_arguments(zero,("Lkotlin/collections/CollectionsKt;","emptyList",""))["status"]=="ARG_REGISTERS_DECODED","zero_arg_static_valid")
check(encoded_arguments(zero,("Lkotlin/collections/CollectionsKt;","emptyList",""))["argument_regs"]==[],"zero_arg_regs_empty")
mismatch=inv("listOf",[2,3])
check(encoded_arguments(mismatch,("Lkotlin/collections/CollectionsKt;","listOf","Ljava/lang/Object;"))["status"]=="UNKNOWN_REGISTER_COUNT_MISMATCH","mismatch")
range_call=inv("listOf",[2],form="invoke-static/range")
check(encoded_arguments(range_call,("Lkotlin/collections/CollectionsKt;","listOf","Ljava/lang/Object;"))["status"]=="UNKNOWN_RANGE_REGISTER_MAPPING","range_fail_closed")
ops=[
 (0,literal(2,"example.js")),(2,known),
 (4,I("move-result-object","",[reg(4)])),
 (6,I("return-object","",[reg(4)]))
]
data=analyze_callee(M(ops),set(),enforce_original=False)
check(data["kotlin_collection_calls"][0]["public_api_category"]=="LIST_OF","list_call")
check(data["kotlin_collection_calls"][0]["bounded_argument_provenance"].get("CONST_JS_SHAPED")==1,"local_provenance")
check(data["return_same_block_producer_categories"].get("DIRECT_KOTLIN_RESULT_SAME_BLOCK")==1,"direct_return")
branch_ops=[(0,literal(2,"example.js")),(2,known),
            (4,I("move-result-object","",[reg(4)])),
            (6,I("if-eqz","",[reg(0)],off=2)),
            (8,I("return-object","",[reg(4)]))]
result=analyze_callee(M(branch_ops),set(),enforce_original=False)
check(result["return_same_block_producer_categories"].get("UNKNOWN_CROSS_BRANCH_OR_NON_INVOKE")==1,"return_branch_barrier")
check(result["actual_process_argv_list_elements_verified"] is False,"no_runtime_claim")
print("P63_SYNTHETIC_KOTLIN_LIST_SLICE=PASS assertions="+str(n))
print("P63_SYNTHETIC_ORIGINAL_APK_READ=NO")
