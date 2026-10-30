#!/usr/bin/env python3
"""P64 list mutation categories and conservative branch control regression."""
import pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from p64_list_builder_mutations import classify_any,safe_file_api,mutation_record,summarize
n=0
def check(x,label):
    global n
    n+=1
    if not x:raise AssertionError("P64_SYNTHETIC_"+label)
class I:
    def __init__(self,name,out="",r=(),off=None):
        self.name,self.out,self.r,self.off=name,out,list(r),off
    def get_name(self):return self.name
    def get_output(self):return self.out
    def get_operands(self):return self.r
    def get_ref_off(self):return self.off
class M:
    def __init__(self,ops):self.ops=ops
    def get_instructions_idx(self):return iter(self.ops)
def r(n):return (0,n)
def call(owner,name,desc,ret,reg_list,form="invoke-interface"):
    value=owner+"->"+name+"("+desc+")"+ret
    return I(form,"{v}, "+value,[r(i) for i in reg_list]+[(256,0,value)])
kotlin="Lkotlin/collections/CollectionsKt;"
java="Ljava/util/List;"
create=call(kotlin,"createListBuilder","","Ljava/util/List;",[],"invoke-static")
build=call(kotlin,"build","Ljava/util/List;","Ljava/util/List;",[4],"invoke-static")
add=call(java,"add","Ljava/lang/Object;","Z",[4,7])
ops=[
 (0,create),(2,I("move-result-object",r=[r(4)])),
 (4,I("const-string",r=[r(7),(256,0,"synthetic_start.js")])),
 (6,add),(8,build),(10,I("move-result-object",r=[r(8)])),
 (12,I("return-object",r=[r(8)]))
]
x=summarize(M(ops),set(),False)
check([x for x in x["detected_public_kotlin_builder_call_order"]]==["createListBuilder","build"],"api_order")
check(x["mutator_calls"][0]["operation"]=="add","mutation_detect")
check(x["mutator_calls"][0]["bounded_element_input_categories"].get("CONST_JS_SHAPED")==1,"literal_category_only")
check(x["build_input_bounded_origin"]["original_build_list_input_origin"]=="OPAQUE_INVOKE_RESULT","builder_origin_opaque")
check(x["mutator_calls"][0]["bounded_element_producer_families"].get("DIRECT_CONST_JS_SHAPED")==1,"literal_producer_category")
check(safe_file_api(call("Ljava/io/File;","getAbsolutePath","","Ljava/lang/String;",[3],"invoke-virtual"))=="FILE_ABSOLUTE_PATH","safe_file_public_api")
check(safe_file_api(call("Lcom/dsh/android/Secret;","getAbsolutePath","","Ljava/lang/String;",[3]))=="NOT_FILESYSTEM_HELPER","dont_expose_app_method")
check(x["original_argv_elements_and_order_proven"]==False,"no_runtime_claim")
branched=ops[:3]+[(5,I("if-eqz",r=[r(0)],off=3))]+ops[3:]
y=summarize(M(branched),set(),False)
check(y["mutator_calls"][0]["bounded_element_input_categories"].get("UNKNOWN_CONTROL_BOUNDARY")==1,"branch_barrier")
check(classify_any(call("Lcom/dsh/android/EngineManager;","private","", "V",[]))=="DSH_INTERNAL_HELPER","private_no_names")
check(classify_any(call(java,"clear","","V",[4]))=="LIST_MUTATOR","clear")
print("P64_SYNTHETIC_LIST_BUILDER_MUTATIONS=PASS assertions="+str(n))
print("P64_SYNTHETIC_ORIGINAL_APK_READ=NO")
