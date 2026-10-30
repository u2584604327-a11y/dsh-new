#!/usr/bin/env python3
"""P66 synthetic CFG SCC/return dominance and conservative unknown-edge tests."""
import pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from p66_loop_scc_dominators import analyze
count=0
def check(ok,label):
    global count
    count+=1
    if not ok:raise AssertionError("P66_TEST_"+label)
class I:
    def __init__(self,name,out="",registers=(),delta=None):
        self.name,self.out,self.registers,self.delta=name,out,list(registers),delta
    def get_name(self):return self.name
    def get_output(self):return self.out
    def get_operands(self):return self.registers
    def get_ref_off(self):return self.delta
class C:
    def __init__(self,tries):self.tries=tries
    def get_tries_size(self):return self.tries
class M:
    def __init__(self,items,tries=0):self.items,self.code=items,C(tries)
    def get_code(self):return self.code
    def get_instructions_idx(self):return iter(self.items)
def R(i):return (0,i)
def call(owner,name,params,ret,rs,op="invoke-interface"):
    ref=owner+"->"+name+"("+params+")"+ret
    return I(op,"{fixture}, "+ref,[R(r) for r in rs]+[(256,0,ref)])
add=call("Ljava/util/List;","add","Ljava/lang/Object;","Z",[4,7])
build=call("Lkotlin/collections/CollectionsKt;","build","Ljava/util/List;","Ljava/util/List;",[4],"invoke-static")
# Loop at pc4--pc8: an optional add can happen 0..N times.
loop=[
    (0,I("nop")),
    (2,I("nop")),
    (4,I("if-eqz",registers=[R(0)],delta=5)),
    (6,add),
    (8,I("goto",delta=-2)),
    (10,I("nop")),
    (12,I("nop")),
    (14,build),
    (16,I("move-result-object",registers=[R(8)])),
    (18,I("return-object",registers=[R(8)])),
]
x=analyze(M(loop))
check(x["modelled_cfg_edges_complete"],"complete_edges")
check(x["cyclic_scc_count"]==1,"one_loop")
check(x["add_call_sites_in_cycles"]==1,"add_in_loop")
check(x["reachable_return_site_count"]==1,"one_return")
check(x["mandatory_add_sites_on_all_modelled_terminating_paths"]==0,"optional_loop_add")
check(x["cyclic_scc_structures"][0]["has_exit_path_to_return"],"loop_exit")
check(not x["iteration_count_and_actual_argv_order_proven"],"never_claim_argv")
# An unconditional add after any loop exit dominates the return.
with_common=loop[:7]+[(14,add),(16,build),
                         (18,I("move-result-object",registers=[R(8)])),
                         (20,I("return-object",registers=[R(8)]))]
y=analyze(M(with_common))
check(y["static_add_call_sites"]==2,"two_add_sites")
check(y["mandatory_add_sites_on_all_modelled_terminating_paths"]==1,"mandatory_post_loop")
check(y["add_call_sites_in_cycles"]==1,"loop_still_one_site")
# A jump into unknown territory must void dominance proof.
invalid=loop[:4]+[(8,I("goto",delta=1000))]+loop[5:]
z=analyze(M(invalid))
check(not z["modelled_cfg_edges_complete"],"unknown_edge_rejected")
check(z["mandatory_add_sites_on_all_modelled_terminating_paths"] is None,"no_false_dominance")
# Exceptions omitted -> no complete normal-CFG all-path claim.
e=analyze(M(loop,tries=1))
check(not e["modelled_cfg_edges_complete"],"exception_block")
# Unreachable cycle must NOT pollute reachable add counts.
unreachable=[
 (0,I("goto",delta=5)),
 (2,add),
 (4,I("goto",delta=-1)),
 (6,I("nop")),
 (8,I("nop")),
 (10,I("return-object",registers=[R(1)])),
]
u=analyze(M(unreachable))
check(u["cyclic_scc_count"]==0,"unreachable_loop_suppressed")
check(u["reachable_add_call_sites"]==0,"unreachable_add_suppressed")
# Standalone infinite loop with no return is NOT a complete return proof.
infinite=analyze(M([(0,I("goto",delta=0)),(2,I("return-object",registers=[R(1)]))]))
check(infinite["reachable_return_site_count"]==0,"infinite_no_return")
check(infinite["mandatory_add_sites_on_all_modelled_terminating_paths"] is None,"no_vacuous_proof")
print("P66_SYNTHETIC_SCC_DOMINATORS=PASS assertions="+str(count))
print("P66_SYNTHETIC_NO_ORIGINAL_APK_USED=YES")
