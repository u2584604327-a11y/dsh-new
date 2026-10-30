#!/usr/bin/env python3
"""P65 synthetic branch enumeration and same-original-builder alias controls."""
import pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from p65_cfg_builder_alias import branch_map,trace_paths
checks=0
def check(x,label):
 global checks
 checks+=1
 if not x:raise AssertionError("P65_SYNTHETIC_"+label)
class I:
 def __init__(self,n,out="",regs=(),off=None):
  self.n,self.out,self.regs,self.off=n,out,list(regs),off
 def get_name(self):return self.n
 def get_output(self):return self.out
 def get_operands(self):return self.regs
 def get_ref_off(self):return self.off
class Code:
 def __init__(self,tries=0):self.tries=tries
 def get_tries_size(self):return self.tries
class Method:
 def __init__(self,ops,tries=0):self.ops,self.code=ops,Code(tries)
 def get_code(self):return self.code
 def get_instructions_idx(self):return iter(self.ops)
def reg(n):return (0,n)
def call(cls,name,params,ret,rs,opcode="invoke-static"):
 value=cls+"->"+name+"("+params+")"+ret
 return I(opcode,"{synthetic}, "+value,[reg(r) for r in rs]+[(256,0,value)])
owner="Lkotlin/collections/CollectionsKt;"
create=call(owner,"createListBuilder","","Ljava/util/List;",[])
build=call(owner,"build","Ljava/util/List;","Ljava/util/List;",[4])
add=call("Ljava/util/List;","add","Ljava/lang/Object;","Z",[4,7],"invoke-interface")
root=[
 (0,create),
 (2,I("move-result-object",regs=[reg(4)])),
 (4,I("const-string",regs=[reg(7),(256,0,"synthetic.js")])),
 (6,I("if-eqz",regs=[reg(0)],off=3)),
 (8,add),
 (10,I("goto",off=1)),
 (12,add),
 (14,build),
 (16,I("move-result-object",regs=[reg(8)])),
 (18,I("return-object",regs=[reg(8)]))
]
# One branch executes an optional add, then BOTH paths execute the final add.
result=trace_paths(Method(root))
check(result["path_enumeration_completed"],"complete_branches")
check(result["path_endings_explored"]==2,"two_routes")
check(result["static_add_calls"]==2,"static_add_sites")
check(result["add_sites_conditional_across_explored_paths"]==1,"conditional_site_count")
check(result["add_sites_present_on_each_explored_path"]==1,"one_common_add_site")
check(result["all_paths_return_original_builder_build_result_proven"],"built_alias")
check(result["no_opaque_builder_escape_on_every_path_proven"],"no_escape")
check(result["complete_original_argv_values_and_order_proven"] is False,"no_argv_claim")
# Unknown callee called with the builder invalidates the heap identity claim.
opaque=call("Lcom/dsh/android/Opaque;","mutate","Ljava/lang/Object;","V",[4])
with_escape=root[:3]+[(5,opaque)]+root[3:]
escaped=trace_paths(Method(with_escape))
check(not escaped["all_paths_return_original_builder_build_result_proven"],"escape_deny")
# Unknown goto target: do not silently assume fall-through.
bad=root[:5]+[(10,I("goto",off=999))]+root[6:]
missing=trace_paths(Method(bad))
check(not missing["path_enumeration_completed"],"bad_target_unmodelled")
check(not missing["all_paths_return_original_builder_build_result_proven"],"bad_target_no_proof")
# Catch edges not accounted for -> no complete all-path claim.
with_tries=trace_paths(Method(root,tries=1))
check(not with_tries["path_enumeration_completed"],"exception_edge_unmodelled")
# Synthetic register aliases remain same through move-object.
alias=root[:4]+[(7,I("move-object",regs=[reg(9),reg(4)]))]+[
 (8,call("Ljava/util/List;","add","Ljava/lang/Object;","Z",[9,7],"invoke-interface"))
]+root[5:]
aliased=trace_paths(Method(alias))
check(aliased["all_paths_return_original_builder_build_result_proven"],"move_alias")
print("P65_SYNTHETIC_CFG_ALIAS=PASS assertions="+str(checks))
print("P65_SYNTHETIC_NO_ORIGINAL_APK=YES")
