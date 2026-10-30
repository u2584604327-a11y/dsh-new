#!/usr/bin/env python3
"""P60 exact v138: source of the List returned to ProcessBuilder(List).

Bounded local-register def-use only, fail closed across branches, field
dereferences and unsupported invoke/range forms. No original values output;
not a runnable command, READY proof or complete interprocedural CFG.
"""
import collections
import json
import pathlib
import re
import sys
import zipfile
from loguru import logger
logger.disable("androguard")
from androguard.core.dex import DEX

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"p59_backward_slice"))
from p59_backward_slice import (
    audit as audit_p59, analyze_primary, call_info, constructor_mode,
    trace_arg, target_pcs, BRANCH, SOURCE, MOVE, MAX_SCAN, MAX_DEPTH, MAX_ARGS,
)
sys.path.insert(0,str(ROOT/"p57_engine_local_dataflow"))
from p57_engine_local_dataflow import regs, TARGET, CODE_OFF, PC
sys.path.insert(0,str(ROOT/"p56_entry_ready"))
from p56_engine_entry_ready_slice import asset_list,require

# Strictly finite categories; no dynamically copied owner or method names.
KNOWN_FACTORY_NAMES={
 "listOf":"LIST_OF","listOfNotNull":"LIST_OF_NOT_NULL",
 "mutableListOf":"MUTABLE_LIST_OF","arrayListOf":"ARRAY_LIST_OF",
 "singletonList":"SINGLETON_LIST","emptyList":"EMPTY_LIST",
 "unmodifiableList":"UNMODIFIABLE_LIST","asList":"AS_LIST",
 "toList":"TO_LIST","toMutableList":"TO_MUTABLE_LIST",
 "plus":"COLLECTION_PLUS","filter":"COLLECTION_FILTER",
 "filterNotNull":"FILTER_NOT_NULL","flatten":"FLATTEN",
 "map":"COLLECTION_MAP","mapNotNull":"MAP_NOT_NULL",
 "take":"TAKE","drop":"DROP",
}
def owner_category(owner):
    if owner.startswith("Lkotlin/collections/"):return "KOTLIN_COLLECTIONS"
    if owner.startswith("Lkotlin/"):return "KOTLIN_OTHER"
    if owner.startswith("Ljava/util/Collections;"):return "JAVA_COLLECTIONS"
    if owner.startswith("Ljava/util/Arrays;"):return "JAVA_ARRAYS"
    if owner.startswith("Ljava/util/"):return "JAVA_UTIL_OTHER"
    if owner.startswith("Ljava/lang/"):return "JAVA_LANG"
    if owner.startswith("Lcom/dsh/android/"):return "DSH_APP"
    if owner.startswith("Landroid/"):return "ANDROID_FRAMEWORK"
    if owner.startswith("Lcom/"):return "OTHER_COM_NAMESPACE"
    return "OTHER_NAMESPACE"

def method_category(owner,name):
    if name in KNOWN_FACTORY_NAMES and (
      owner_category(owner) in ("KOTLIN_COLLECTIONS","JAVA_COLLECTIONS","JAVA_ARRAYS")
    ):
        return KNOWN_FACTORY_NAMES[name]
    if name in ("<init>","<clinit>"):return "INITIALIZER"
    if name.endswith("$default"):return "KOTLIN_DEFAULT_WRAPPER"
    if name.startswith(("access$","lambda$")):return "GENERATED_BRIDGE"
    return "OTHER_OR_APP_METHOD"

def return_category(instruction):
    # This is a descriptor SHAPE, not an actual returned class or runtime type.
    text=instruction.get_output()
    m=re.search(r"\)[ ]*(\[*[VZBCSIJFD]|(?:\[*L[^;\s,]+;))",text)
    if not m:return "UNPARSED"
    ret=m.group(1)
    if ret=="Ljava/util/List;":return "JAVA_UTIL_LIST"
    if ret in ("Ljava/util/ArrayList;","Ljava/util/LinkedList;"):
        return "CONCRETE_JAVA_LIST"
    if ret.startswith("["):return "ARRAY"
    if ret=="Ljava/lang/Object;":return "OBJECT"
    if ret=="V":return "VOID"
    if ret.startswith("L"):return "OTHER_REFERENCE"
    return "PRIMITIVE"

def arg_descriptor_count(info):
    # Count types in JVM-style parameter descriptors; bounded, no values exposed.
    if not info:return None
    desc=info[2]
    count=0
    i=0
    while i<len(desc):
        if count>64:return None
        while i<len(desc) and desc[i]=="[":i+=1
        if i>=len(desc):return None
        if desc[i]=="L":
            end=desc.find(";",i)
            if end<0:return None
            i=end+1
        elif desc[i] in "ZBCSIJFD":i+=1
        else:return None
        count+=1
    return count

def producer_from_move_result(ops,j,assets,targets):
    if j<=0:return {"status":"UNKNOWN_MISSING_RESULT_PRODUCER"}
    call_pc,call=ops[j-1]
    info=call_info(call)
    if info is None:return {"status":"UNKNOWN_RESULT_NOT_INVOKE"}
    owner,name,desc=info
    args=regs(call)
    member=not call.get_name().startswith("invoke-static")
    range_form=call.get_name().endswith("/range")
    # Do not treat a start register as a full argument vector.
    decoded=(not range_form and len(args)<=MAX_ARGS and (bool(args) or not member))
    if decoded:
        sources=collections.Counter()
        for r in args[1 if member else 0:]:
            sources[trace_arg(ops,j-1,r,targets,assets)]+=1
        source_counts=dict(sorted(sources.items()))
    else:source_counts={"UNKNOWN_INVOKE_ARGUMENT_ENCODING":1}
    return {
       "status":"EXACT_LOCAL_RESULT_INVOKE",
       "owner_category":owner_category(owner),
       "method_category":method_category(owner,name),
       "return_descriptor_category":return_category(call),
       "invoke_opcode_category":("STATIC" if not member else "INSTANCE_OR_DIRECT"),
       "invoke_range_encoding":range_form,
       "decoded_argument_register_count":len(args),
       "descriptor_parameter_count":arg_descriptor_count(info),
       "producer_input_origin_categories":source_counts,
       "complete_list_elements_proven":False,
    }

def follow_local_return(ops,at,reg,targets,assets,depth=0,seen=None):
    if seen is None:seen=set()
    if depth>=MAX_DEPTH or (at,reg) in seen:return {"status":"UNKNOWN_DEPTH_OR_CYCLE"}
    seen.add((at,reg))
    for j in range(at-1,max(-1,at-MAX_SCAN-1),-1):
        pc,ins=ops[j]
        name=ins.get_name()
        if pc in targets or name.startswith(BRANCH):
            return {"status":"UNKNOWN_CONTROL_BARRIER"}
        if name=="check-cast":continue
        r=regs(ins)
        if not r or r[0]!=reg:continue
        if name.startswith(MOVE):
            if len(r)<2:return {"status":"UNKNOWN_MOVE_REGISTER_ENCODING"}
            return follow_local_return(ops,j,r[1],targets,assets,depth+1,seen)
        if name.startswith("move-result"):
            return producer_from_move_result(ops,j,assets,targets)
        if name.startswith(SOURCE):
            return {"status":"NON_INVOKE_DEFINITION",
                    "source_category":trace_arg(ops,at,reg,targets,assets)}
    return {"status":"UNKNOWN_REGISTER_LIVEIN_OR_WINDOW"}

def inspect_primary(method,assets):
    ops=list(method.get_instructions_idx())
    # Reuse P59 anchor and exact original signature gates.
    prev=analyze_primary(method,assets)
    require(prev["process_constructor_descriptor_class"]=="LIST",
            "LIST_SIGNATURE_DRIFT")
    require(prev["process_constructor_register_count"]==2,
            "PROCESS_CTOR_REGISTER_COUNT_DRIFT")
    require(prev["argument_register_encoding_supported"],
            "PROCESS_CTOR_RANGE_UNSUPPORTED")
    ctor=[(i,pc,ins) for i,(pc,ins) in enumerate(ops)
          if constructor_mode(call_info(ins)) is not None]
    require(len(ctor)==1,"CONSTRUCTOR_COUNT_DRIFT")
    i,pc,ins=ctor[0]
    require(constructor_mode(call_info(ins))=="LIST","CONSTRUCTOR_DESCRIPTOR_DRIFT")
    args=regs(ins)
    require(len(args)==2,"DECODED_ARGUMENTS_DRIFT")
    targets,unresolved=target_pcs(ops)
    origin=follow_local_return(ops,i,args[1],targets,assets)
    require(origin["status"]=="EXACT_LOCAL_RESULT_INVOKE",
            "OPAQUE_RETURN_SOURCE_CHANGED")
    # Raw class, method, registers and PC are deliberately excluded.
    return {
      "process_constructor_mode":"LIST",
      "same_method_return_producer":origin,
      "unresolved_branch_offsets":unresolved,
      "fully_resolved_list_contents":False,
      "actual_argv_or_script_entry_proven":False,
    }

def audit(original):
    prev=audit_p59(original)
    require(prev["primary"]["parameter_backward_source_categories"]==
            {"OPAQUE_INVOKE_RESULT":1},"P59_BASELINE_CHANGED")
    with zipfile.ZipFile(original) as z:
        assets,_=asset_list(z)
        dex=DEX(z.read("classes.dex"))
        matched=[]
        for c in dex.get_classes():
            if c.get_name()!=TARGET:continue
            for m in c.get_methods():
                if m.get_name()=="invokeSuspend" and m.get_code() is not None:
                    matched.append(m)
        require(len(matched)==1 and matched[0].get_code_off()==CODE_OFF,
                "ORIGINAL_SUSPEND_METHOD_DRIFT")
        return inspect_primary(matched[0],assets)

def report(result):
    print("P60_P59_P58_P57_P56_P54_SIGNED_V138_PROVENANCE=PASS")
    print("P60_CONSTRUCTOR_LIST_PRODUCER_LOCAL_SLICE=PASS")
    print("P60_CATEGORICAL_ONLY_PRODUCER="+json.dumps(
        result["same_method_return_producer"],sort_keys=True,separators=(",",":")))
    print("P60_UNRESOLVED_SIMPLE_BRANCH_OFFSETS="+str(
        result["unresolved_branch_offsets"]))
    print("P60_LIST_ELEMENTS_AND_REAL_ARGV_PROVEN=NO")
    print("P60_READY_LATCH_AND_STATEFLOW_CONDITION_PROVEN=NO")
    print("P60_ORIGINAL_CLASS_METHOD_JS_PATH_ARGV_ENV_VALUES_EMITTED=NO")
    print("P60_REAL_PRODUCTION_ENGINE_SCRIPT_EXECUTED=NO")
    print("P60_P53_ORIGINAL_PROCESS_PROXY_CONNECTED=NO")
    print("P60_FIXED_SIGNED_V139=BLOCKED")

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("original_signed_v138")
    args=p.parse_args()
    report(audit(pathlib.Path(args.original_signed_v138)))
