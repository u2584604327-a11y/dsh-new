#!/usr/bin/env python3
"""P66: finite SCC, reachability and dominator audit of original-v138 ListBuilder.

Only classifies CFG callsites. Does NOT execute DSH Node or expose original argv,
script names, file paths, literals, environment or original DSH private methods.
Dominance is structural on modelled normal-flow edges, not proof of runtime
branch feasibility, heap identity, contents, READY/exit or engine isolation.
"""
import collections
import json
import pathlib
import sys
from loguru import logger
logger.disable("androguard")
HERE=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE/"p65_cfg_builder_alias"))
from p65_cfg_builder_alias import (
    audit as audit_p65, branch_map, exception_status, call_id,
    is_mutable_list_owner, resolve_original, require,
)
# P65's original method selection is internal to resolve_original(). To avoid
# copying a second independent DEX scanner, obtain the method through a
# source-only visitor with the same exact constructor + wrapper anchor.
import re
import zipfile
from androguard.core.dex import DEX
sys.path.insert(0,str(HERE/"p62_forward_target"))
from p62_forward_target import exact_def,forwarded_reference
sys.path.insert(0,str(HERE/"p61_bridge"))
from p61_original_bridge import ref,producer_index
sys.path.insert(0,str(HERE/"p59_backward_slice"))
from p59_backward_slice import call_info,constructor_mode
sys.path.insert(0,str(HERE/"p57_engine_local_dataflow"))
from p57_engine_local_dataflow import regs,TARGET,CODE_OFF

MAX_INSTRUCTIONS=256
MAX_GRAPH_STATES=4096

def graph(method):
    ops=list(method.get_instructions_idx())
    require(0<len(ops)<=MAX_INSTRUCTIONS,"METHOD_SIZE_DRIFT")
    split,unknown=branch_map(ops)
    ends=set()
    succ={}
    for i,(_,inst) in enumerate(ops):
        name=inst.get_name()
        if name.startswith(("return","throw")):
            succ[i]=[]
            if name.startswith("return"):ends.add(i)
        elif i in split:
            succ[i]=list(split[i])
        elif i+1<len(ops):
            succ[i]=[i+1]
        else:
            unknown.append("NONTERMINAL_END")
            succ[i]=[]
    # Switch/payload edges remain blocked and do not constitute a valid CFG.
    ex=exception_status(method)
    if ex!="NO_EXCEPTION_HANDLERS":unknown.append(ex)
    return ops,succ,ends,sorted(set(unknown)),ex

def reach(succ,root,ban=None):
    if root is None or root==ban:return set()
    visited=set()
    stack=[root]
    while stack:
        u=stack.pop()
        if u==ban or u in visited:continue
        visited.add(u)
        if len(visited)>MAX_GRAPH_STATES:
            raise ValueError("P66_BLOCKED_REACHABILITY_CAP")
        stack.extend(v for v in succ[u] if v!=ban and v not in visited)
    return visited

def sccs(succ,allowed):
    seq=0
    indices={}
    lows={}
    stack=[]
    active=set()
    groups=[]
    def dfs(v):
        nonlocal seq
        indices[v]=lows[v]=seq
        seq+=1
        stack.append(v);active.add(v)
        for w in succ[v]:
            if w not in allowed:continue
            if w not in indices:
                dfs(w);lows[v]=min(lows[v],lows[w])
            elif w in active:lows[v]=min(lows[v],indices[w])
        if lows[v]==indices[v]:
            group=[]
            while True:
                w=stack.pop();active.remove(w);group.append(w)
                if w==v:break
            groups.append(frozenset(group))
    for i in sorted(allowed):
        if i not in indices:dfs(i)
    return groups

def categorise(ops,i):
    ins=ops[i][1]
    if not ins.get_name().startswith("invoke-"):return "OTHER"
    call=call_id(ins)
    if not call:return "OPAQUE_CALL"
    cls,name,_,_=call
    if is_mutable_list_owner(cls) and name=="add":return "ADD"
    if cls.startswith("Lkotlin/collections/") and name=="createListBuilder":
        return "CREATE_BUILDER"
    if cls.startswith("Lkotlin/collections/") and name=="build":return "BUILD"
    if cls.startswith("Ljava/io/File;"):return "FILE_HELPER"
    if cls.startswith("Lcom/dsh/android/"):return "APP_INTERNAL_CALL"
    return "OTHER_CALL"

def analyze(method,strict_original=False):
    ops,succ,return_sites,unknown,exception=graph(method)
    if strict_original:require(len(ops)==43,"ORIGINAL_43_INSTRUCTIONS_DRIFT")
    visited=reach(succ,0)
    available_returns=sorted(return_sites & visited)
    # Reverse reachability from all modelled returns (without mutation).
    pred={i:[] for i in succ}
    for u,targets in succ.items():
        for v in targets:pred[v].append(u)
    can_return=set()
    work=list(available_returns)
    while work:
        v=work.pop()
        if v in can_return:continue
        can_return.add(v);work.extend(pred[v])
    component=sccs(succ,visited)
    cyclic=[g for g in component if len(g)>1 or any(v in succ[v] for v in g)]
    static_add={i for i in range(len(ops)) if categorise(ops,i)=="ADD"}
    reachable_add=static_add&visited
    cyclic_add=set().union(*(static_add&c for c in cyclic)) if cyclic else set()
    cycle_shapes=[]
    for c in sorted(cyclic,key=lambda s:min(s)):
        categories=collections.Counter(categorise(ops,i) for i in c)
        exits=[v for u in c for v in succ[u] if v not in c]
        cycle_shapes.append({
            "instruction_count":len(c),
            "add_calls_in_cycle":categories["ADD"],
            "builder_creation_calls_in_cycle":categories["CREATE_BUILDER"],
            "builder_build_calls_in_cycle":categories["BUILD"],
            "app_internal_calls_in_cycle":categories["APP_INTERNAL_CALL"],
            "filesystem_calls_in_cycle":categories["FILE_HELPER"],
            "exit_edge_count":len(exits),
            "has_exit_path_to_return":any(v in can_return for v in exits),
        })
    # Dominance for every REACHABLE normal return, independent of loop
    # iteration count. If any edge/exception is unresolved, suppress proof.
    complete_edges=not unknown
    mandatory=set()
    if complete_edges and available_returns:
        for i in reachable_add:
            if all(target not in reach(succ,0,ban=i)
                   for target in available_returns):
                mandatory.add(i)
    no_unreachable_exit=bool(available_returns and
        all(i in can_return for i in visited))
    return {
        "method_instruction_count":len(ops),
        "modelled_cfg_edges_complete":complete_edges,
        "modelled_edge_blockers":unknown,
        "exception_edge_status":exception,
        "reachable_instruction_count":len(visited),
        "reachable_return_site_count":len(available_returns),
        "cyclic_scc_count":len(cyclic),
        "cyclic_scc_structures":cycle_shapes,
        "static_add_call_sites":len(static_add),
        "reachable_add_call_sites":len(reachable_add),
        "add_call_sites_in_cycles":len(cyclic_add),
        "add_call_sites_outside_cycles":len(reachable_add-cyclic_add),
        "mandatory_add_sites_on_all_modelled_terminating_paths":
           len(mandatory) if complete_edges and available_returns else None,
        "add_sites_not_mandatory_on_all_modelled_terminating_paths":
           len(reachable_add-mandatory) if complete_edges and available_returns else None,
        "all_reachable_instructions_have_exit_path":no_unreachable_exit,
        "iteration_count_and_actual_argv_order_proven":False,
        "builder_object_alias_and_heap_contents_proven":False,
        "original_engine_ready_and_p53_wiring_proven":False,
        "fixed_signed_production_apk_eligible":False,
    }

def exact_method(apk):
    with zipfile.ZipFile(apk) as z:
        names=[x for x in sorted(z.namelist())
               if re.fullmatch(r"classes\d*\.dex",x)]
        require(1<=len(names)<=5,"DEX_COUNT_DRIFT")
        dex=[DEX(z.read(n)) for n in names]
        classes=[cl for d in dex for cl in d.get_classes()]
        original=[m for cl in dex[0].get_classes() if cl.get_name()==TARGET
                  for m in cl.get_methods() if m.get_name()=="invokeSuspend"
                  and m.get_code() is not None]
        require(len(original)==1 and original[0].get_code_off()==CODE_OFF,
                "ORIGINAL_MAIN_METHOD_CHANGED")
        ops=list(original[0].get_instructions_idx())
        ctor=[(i,ins) for i,(_,ins) in enumerate(ops)
              if constructor_mode(call_info(ins))=="LIST"]
        require(len(ctor)==1 and len(regs(ctor[0][1]))==2,"CTOR_DRIFT")
        source=producer_index(ops,ctor[0][0],regs(ctor[0][1])[1])
        require(source is not None,"LIST_PRODUCER_UNRESOLVED")
        wrapper=exact_def(classes,ref(ops[source][1]))
        require(len(wrapper)==1,"WRAPPER_NOT_FOUND")
        target,status=forwarded_reference(wrapper[0])
        require(status=="EXACT_FORWARDING_CALL","BRIDGE_CHANGED")
        inner=exact_def(classes,target)
        require(len(inner)==1,"CALLEE_NOT_FOUND")
        return analyze(inner[0],strict_original=True)

def audit(apk):
    previous=audit_p65(apk)
    require(previous["method_instruction_count"]==43,"P65_METHOD_DRIFT")
    require(previous["static_add_calls"]==9,"P65_ADD_COUNT_DRIFT")
    require(previous["partial_or_unmodelled_reasons"].get("LOOP_OR_REVISIT_UNMODELLED")==1,
            "P65_REVISIT_COUNT_DRIFT")
    return exact_method(apk)

def report(value):
    print("P66_ORIGINAL_V138_P65_TO_P35_HASH_CHAIN=PASS")
    print("P66_SCC_DOMINATOR_CATEGORICAL="+json.dumps(value,sort_keys=True,separators=(",",":")))
    print("P66_RAW_ORIGINAL_METHODS_LITERALS_ARGV_AND_PATHS_LOGGED=NO")
    print("P66_ORIGINAL_ENGINE_NODE_AND_ADDONS_EXECUTED=NO")
    print("P66_P53_REAL_ENGINE_AND_READY_WIRED=NO")
    print("P66_FIXED_SIGNED_V139_RELEASE=BLOCKED")
if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("original_signed_v138")
    report(audit(pathlib.Path(p.parse_args().original_signed_v138)))
