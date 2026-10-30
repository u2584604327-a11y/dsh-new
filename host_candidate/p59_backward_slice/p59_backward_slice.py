#!/usr/bin/env python3
"""P59: targeted, bounded original-v138 ProcessBuilder constructor backward slice.

Only syntactic, same-basic-block def-use witnesses are recognized. A branch,
branch target, field, opaque result or out-of-window origin is UNKNOWN.
No original command, path, string, executable source or bytes are printed.
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
sys.path.insert(0,str(ROOT/"p58_objectflow"))
from p58_objectflow import audit as audit_p58
sys.path.insert(0,str(ROOT/"p57_engine_local_dataflow"))
from p57_engine_local_dataflow import regs,group_hint,TARGET,CODE_OFF,PC
sys.path.insert(0,str(ROOT/"p56_entry_ready"))
from p56_engine_entry_ready_slice import asset_list,require,INVOKE,instruction_string

MAX_OPS=40000
MAX_SCAN=256
MAX_DEPTH=8
MAX_ARGS=32
BRANCH=("if-","goto","packed-switch","sparse-switch","return","throw",
        "monitor-enter","monitor-exit")
SOURCE=("const","new-instance","new-array","filled-new-array","move-result",
        "move-exception","iget","sget","aget","instance-of","array-length",
        "cmp","neg","not","add-","sub-","mul-","div-","rem-","rsub-","and-",
        "or-","xor-","shl-","shr-","ushr-","int-to-","long-to-",
        "float-to-","double-to-")
MOVE=("move-object","move/from","move/16","move-object/from16",
      "move-object/16","move-wide","move-wide/from16","move-wide/16")
CALL=re.compile(r"(L[^,;\s]+;)->([^\s(,]+)\(([^)]*)\)")
DEX_TYPE=re.compile(r"L[A-Za-z0-9_/$]+;")
PRODUCERS={
 "Ljava/util/Arrays;->asList":"ARRAYS_AS_LIST",
 "Ljava/lang/StringBuilder;->toString":"BUILDER_TO_STRING",
 "Ljava/lang/StringBuffer;->toString":"BUILDER_TO_STRING",
 "Lkotlin/collections/CollectionsKt;->listOf":"KOTLIN_LIST",
}
def call_info(ins):
    if not ins.get_name().startswith("invoke-"):
        return None
    found=CALL.search(ins.get_output())
    return found.groups() if found else None

def constructor_mode(info):
    if info is None: return None
    cls,name,args=info
    if cls!="Ljava/lang/ProcessBuilder;" or name!="<init>":
        return None
    if args=="Ljava/util/List;": return "LIST"
    if args=="[Ljava/lang/String;": return "STRING_ARRAY"
    return "OTHER"

def source_kind(ins,assets):
    name=ins.get_name()
    if name in ("const-string","const-string/jumbo"):
        tags=group_hint(instruction_string(ins),assets)
        return "CONST_"+"_".join(tags) if tags else "CONST_OTHER"
    if name=="new-instance":
        out=ins.get_output()
        if "Ljava/util/ArrayList;" in out: return "ALLOC_ARRAYLIST_CONTENTS_UNKNOWN"
        if "Ljava/lang/StringBuilder;" in out: return "ALLOC_STRING_BUILDER_CONTENTS_UNKNOWN"
        if "Ljava/lang/ProcessBuilder;" in out: return "ALLOC_PROCESS_BUILDER"
        return "ALLOC_OTHER"
    if name in ("new-array","filled-new-array","filled-new-array/range"):
        return "ALLOC_ARRAY_CONTENTS_UNKNOWN"
    if name.startswith(("iget","sget","aget")): return "FIELD_OR_ARRAY_READ_OPAQUE"
    return "OTHER_DEFINITION_OPAQUE"

def producer_kind(ins):
    info=call_info(ins)
    if info is None: return "OPAQUE_INVOKE_RESULT"
    cls,name,_=info
    key=cls+"->"+name
    if key in PRODUCERS: return PRODUCERS[key]+"_CONTENTS_UNKNOWN"
    if cls.startswith("Lkotlin/collections/") and name in ("listOf","arrayListOf","mutableListOf"):
        return "KOTLIN_COLLECTION_CONTENTS_UNKNOWN"
    if cls=="Ljava/lang/StringBuilder;" and name=="append":
        return "BUILDER_ALIAS_CONTENTS_UNKNOWN"
    return "OPAQUE_INVOKE_RESULT"

def target_pcs(ops):
    result=set()
    unresolved=0
    for pc,ins in ops:
        if ins.get_name().startswith(("if-","goto")):
            fn=getattr(ins,"get_ref_off",None)
            try: delta=fn() if callable(fn) else None
            except (TypeError,ValueError,AttributeError): delta=None
            if type(delta) is int and delta:
                result.add(pc+delta*2)
            else: unresolved+=1
    return result,unresolved

def trace_arg(ops,at,register,targets,assets,depth=0,seen=None):
    """Last local register definition; no crossing control/exception barriers."""
    if seen is None:seen=set()
    if depth>=MAX_DEPTH or (at,register) in seen:
        return "UNKNOWN_DEPTH_OR_CYCLE"
    seen.add((at,register))
    floor=max(0,at-MAX_SCAN)
    for j in range(at-1,floor-1,-1):
        pc,ins=ops[j]
        name=ins.get_name()
        if pc in targets or name.startswith(BRANCH):
            return "UNKNOWN_CONTROL_BOUNDARY"
        if name.startswith("invoke-"):
            # An invoke can change heap contents but cannot directly write
            # ordinary register values; any allocation/list result is still
            # classified CONTENTS_UNKNOWN rather than trusted argv.
            continue
        r=regs(ins)
        if not r:continue
        if name=="check-cast":
            continue
        is_move=name.startswith(MOVE)
        writes=(name.startswith(SOURCE) or is_move)
        if not writes or r[0]!=register:
            continue
        if is_move and len(r)>=2:
            return trace_arg(ops,j,r[1],targets,assets,depth+1,seen)
        if name.startswith("move-result"):
            # Immediate preceding invoke, not an arbitrary earlier call.
            if j<1: return "UNKNOWN_RESULT_PRODUCER"
            p_name=ops[j-1][1].get_name()
            if p_name.startswith("invoke-"):
                return producer_kind(ops[j-1][1])
            if p_name.startswith("filled-new-array"):
                return "ARRAY_RESULT_CONTENTS_UNKNOWN"
            return "UNKNOWN_RESULT_PRODUCER"
        return source_kind(ins,assets)
    return "UNKNOWN_LIVEIN_OR_WINDOW"

def analyze_primary(method,assets):
    ops=list(method.get_instructions_idx())
    require(len(ops)<=MAX_OPS,"METHOD_OPS_LIMIT")
    targets,unresolved=target_pcs(ops)
    ctor=[]
    start=[]
    for i,(pc,ins) in enumerate(ops):
        info=call_info(ins)
        mode=constructor_mode(info)
        if mode is not None:
            ctor.append((i,pc,mode,ins))
        if info and info[0]=="Ljava/lang/ProcessBuilder;" and info[1]=="start":
            start.append(pc)
    require(len(ctor)==1,"CONSTRUCTOR_COUNT_DRIFT")
    require(start==[PC],"SPAWN_OFFSET_DRIFT")
    i,pc,mode,ins=ctor[0]
    regargs=regs(ins)
    # invoke/range encoding sometimes exposes a single start register. This
    # implementation MUST NOT misidentify that as a decoded arg register list.
    arg_encoding_supported=not ins.get_name().endswith("/range")
    categories=collections.Counter()
    if arg_encoding_supported and len(regargs)>1 and len(regargs)<=MAX_ARGS:
        for reg in regargs[1:]:
            categories[trace_arg(ops,i,reg,targets,assets)]+=1
    else:
        categories["UNKNOWN_ARGUMENT_REGISTER_ENCODING"]+=1
    return {
        "process_constructor_descriptor_class":mode,
        "process_constructor_register_count":len(regargs),
        "argument_register_encoding_supported":arg_encoding_supported,
        "parameter_backward_source_categories":dict(sorted(categories.items())),
        "branch_targets_count":len(targets),
        "unresolved_branch_targets":unresolved,
        "complete_argv_object_contents_proven":False,
    }

def ready_structure(methods,assets):
    count=collections.Counter()
    for _,method in methods:
        ops=list(method.get_instructions_idx())
        for i,(pc,ins) in enumerate(ops):
            if ins.get_name() not in ("const-string","const-string/jumbo"):
                continue
            tags=group_hint(instruction_string(ins),assets)
            if "READY_STRING_HINT" not in tags:
                continue
            count["READY_LITERAL_HITS"]+=1
            # Same basic block, up to 64 instructions; descriptive lexical
            # neighborhood only, not proof of a predicate or state transition.
            for _,other in ops[i+1:i+65]:
                if other.get_name().startswith(BRANCH):
                    count["READY_LOCAL_SCAN_HALTED_AT_BRANCH"]+=1
                    break
                info=call_info(other)
                if info:
                    cls,name,_=info
                    if cls=="Ljava/lang/String;" and name in ("equals","contains","startsWith"):
                        count["READY_NEAR_STRING_COMPARE"]+=1
                    if cls=="Ljava/util/concurrent/CountDownLatch;" and name=="countDown":
                        count["READY_NEAR_LATCH_SIGNAL"]+=1
                    if cls=="Lkotlinx/coroutines/flow/MutableStateFlow;" and name=="setValue":
                        count["READY_NEAR_STATEFLOW"]+=1
    return dict(sorted(count.items()))

def audit(original):
    previous=audit_p58(original)
    require(previous["PROCESS_CTOR_CALLS"]==1 and previous["PROCESS_START_CALLS"]==1,
            "P58_PROCESS_ANCHOR_DRIFT")
    with zipfile.ZipFile(original) as z:
        assets,_=asset_list(z)
        dex=DEX(z.read("classes.dex"))
        methods=[]
        for klass in dex.get_classes():
            cls=klass.get_name()
            if cls!=TARGET and not cls.startswith(TARGET[:-1]+"$"):
                continue
            for m in klass.get_methods():
                if m.get_code() is not None:
                    methods.append((cls,m))
        require(len(methods)==9,"P58_FAMILY_COUNT_DRIFT")
        matches=[m for cls,m in methods if cls==TARGET and m.get_name()=="invokeSuspend"]
        require(len(matches)==1 and matches[0].get_code_off()==CODE_OFF,
                "P35_EXACT_PRIMARY_DRIFT")
        primary=analyze_primary(matches[0],assets)
        ready=ready_structure(methods,assets)
    return {"primary":primary,"ready":ready}

def report(result):
    print("P59_P58_P57_P56_P54_EXACT_SIGNED_V138=PASS")
    print("P59_PRIMARY_PROCESSBUILDER_CONSTRUCTOR_ANCHORED=PASS")
    for k,v in result["primary"].items():
        print("P59_"+k.upper()+"="+(json.dumps(v,sort_keys=True,separators=(",",":"))
                                       if isinstance(v,(dict,list)) else str(v)))
    print("P59_READY_STATIC_LOCAL_NEIGHBORHOOD="+json.dumps(result["ready"],sort_keys=True,separators=(",",":")))
    print("P59_CONSTRUCTOR_ARGV_AND_DYNAMIC_READY_CONFIRMED=NO")
    print("P59_PRODUCTION_SCRIPT_OR_NATIVE_ADDON_EXECUTED=NO")
    print("P59_ORIGINAL_STRINGS_PATHS_ENV_OR_SCRIPT_EXPOSED=NO")
    print("P59_P53_PROCESS_PROXY_WIRED_TO_ORIGINAL_DSH=NO")
    print("P59_FIXED_SIGNED_V139=BLOCKED")
if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("original_signed_v138")
    args=parser.parse_args()
    report(audit(pathlib.Path(args.original_signed_v138)))
