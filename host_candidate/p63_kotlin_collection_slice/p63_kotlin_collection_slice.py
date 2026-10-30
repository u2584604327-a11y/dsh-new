#!/usr/bin/env python3
"""P63 original v138: exact collection calls inside verified 43-instruction callee.
Source-only analysis; categorizes public Kotlin API calls and bounded def-use.
Never print original literal values, private DEX class/method names, argv or env.
"""
import collections,json,pathlib,re,sys,zipfile
from loguru import logger
logger.disable("androguard")
from androguard.core.dex import DEX

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"p62_forward_target"))
from p62_forward_target import audit as previous_audit,exact_def,forwarded_reference
sys.path.insert(0,str(ROOT/"p61_bridge"))
from p61_original_bridge import ref,producer_index,arity
sys.path.insert(0,str(ROOT/"p59_backward_slice"))
from p59_backward_slice import call_info,constructor_mode,target_pcs,trace_arg
sys.path.insert(0,str(ROOT/"p57_engine_local_dataflow"))
from p57_engine_local_dataflow import regs,TARGET,CODE_OFF
sys.path.insert(0,str(ROOT/"p56_entry_ready"))
from p56_engine_entry_ready_slice import asset_list,categories,instruction_string,require

PUBLIC_API_NAMES={
 "listOf":"LIST_OF","listOfNotNull":"LIST_OF_NOT_NULL",
 "emptyList":"EMPTY_LIST","mutableListOf":"MUTABLE_LIST_OF",
 "arrayListOf":"ARRAY_LIST_OF","toList":"TO_LIST",
 "toMutableList":"TO_MUTABLE_LIST","plus":"PLUS",
 "filter":"FILTER","filterNotNull":"FILTER_NOT_NULL",
 "map":"MAP","mapNotNull":"MAP_NOT_NULL",
 "take":"TAKE","drop":"DROP","flatten":"FLATTEN",
 "single":"SINGLE","first":"FIRST","last":"LAST",
 "joinToString":"JOIN_TO_STRING",
}
def safe_api(owner,name):
    if not owner.startswith("Lkotlin/collections/"):
        return "NOT_KOTLIN_COLLECTION"
    return PUBLIC_API_NAMES.get(name,"OTHER_KOTLIN_COLLECTION_API")
def safe_public_kotlin_method(owner,name):
    # Only symbols from Kotlin's public collections namespace, never DSH
    # classes, private member symbols, strings, asset paths or payload data.
    if not owner.startswith("Lkotlin/collections/"):
        return "NON_KOTLIN_OWNER"
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$-]{0,63}", name):
        return "UNSAFE_PUBLIC_SYMBOL_FORMAT"
    return name
def ret_type(ret):
    if ret=="Ljava/util/List;":return "LIST"
    if ret=="Ljava/lang/String;":return "STRING"
    if ret in ("Ljava/lang/Object;","Ljava/lang/Iterable;"):return "OBJECT_OR_ITERABLE"
    if ret.startswith("["):return "ARRAY"
    if ret.startswith("L"):return "OTHER_REFERENCE"
    if ret=="V":return "VOID"
    return "PRIMITIVE_OR_UNPARSED"
def encoded_arguments(ins,info):
    rs=regs(ins)
    if ins.get_name().endswith("/range"):
        return {"status":"UNKNOWN_RANGE_REGISTER_MAPPING","raw_register_operand_count":len(rs)}
    if not ins.get_name().startswith("invoke-"):
        return {"status":"UNKNOWN_REGISTER_DECODING","raw_register_operand_count":len(rs)}
    member=not ins.get_name().startswith("invoke-static")
    formal=arity(info[2])
    # A synthetic fixture or DEX instruction may have library metadata as
    # non-register operands. Only decoded registers count here.
    if formal is None:
        return {"status":"UNKNOWN_FORMAL_ARITY","raw_register_operand_count":len(rs)}
    if not rs and (member or formal>0):
        return {"status":"UNKNOWN_REGISTER_DECODING","raw_register_operand_count":len(rs)}
    input_regs=rs[1:] if member else rs
    if len(input_regs)!=formal:
        return {"status":"UNKNOWN_REGISTER_COUNT_MISMATCH","raw_register_operand_count":len(rs)}
    return {"status":"ARG_REGISTERS_DECODED","raw_register_operand_count":len(rs),
            "argument_regs":input_regs}
def call_summary(ops,idx,assets,targets):
    pc,ins=ops[idx]
    info=ref(ins)
    require(info is not None and info[0].startswith("Lkotlin/collections/"),
            "CALLEE_NOT_COLLECTION_CALL")
    owner,name,params,ret=info
    encode=encoded_arguments(ins,(owner,name,params))
    raw=encode["raw_register_operand_count"]
    result={"public_api_category":safe_api(owner,name),
            "public_kotlin_std_method":safe_public_kotlin_method(owner,name),
            "return_descriptor_category":ret_type(ret),
            "formal_parameter_types":arity(params),
            "invoke_form":"RANGE" if ins.get_name().endswith("/range") else "NON_RANGE",
            "decoded_register_operands":raw,
            "argument_decode_status":encode["status"]}
    if encode["status"]=="ARG_REGISTERS_DECODED":
        evidence=collections.Counter()
        for r in encode["argument_regs"]:
            evidence[trace_arg(ops,idx,r,targets,assets)]+=1
        result["bounded_argument_provenance"]=dict(sorted(evidence.items()))
    else:
        result["bounded_argument_provenance"]={"UNKNOWN_ARGUMENTS":1}
    return result
def analyze_callee(m,assets,enforce_original=True):
    require(m.get_code() is not None,"NO_CALLEE_BODY")
    ops=list(m.get_instructions_idx())
    require(len(ops)<=30000,"CALLEE_INSTRUCTION_LIMIT")
    if enforce_original:require(len(ops)==43,"ORIGINAL_CALLEE_INSTRUCTION_COUNT_DRIFT")
    targets,unknown=target_pcs(ops)
    apis=[]
    count=collections.Counter()
    returns=[]
    for i,(pc,ins) in enumerate(ops):
        name=ins.get_name()
        if name.startswith("invoke-"):
            info=ref(ins)
            if info and info[0].startswith("Lkotlin/collections/"):
                apis.append(call_summary(ops,i,assets,targets))
        if name=="return-object":returns.append(i)
        if name in ("const-string","const-string/jumbo"):
            count["LITERAL_SITES"]+=1
            value=instruction_string(ins)
            for cat in categories(value,assets):
                if cat in ("JS_SHAPED","READY_STRING_HINT","EXACT_APK_ASSET_STRING"):
                    count["LITERAL_CATEGORY_"+cat]+=1
        if name.startswith(("if-","goto","packed-switch","sparse-switch")):
            count["BRANCH_SITES"]+=1
    if enforce_original:
        require(len(apis)==2,"ORIGINAL_TWO_KOTLIN_CALLS_DRIFT")
        require(len(returns)==1,"ORIGINAL_RETURN_COUNT_DRIFT")
        require(count["LITERAL_SITES"]==5,"ORIGINAL_LITERAL_COUNT_DRIFT")
        require(count["BRANCH_SITES"]==3,"ORIGINAL_BRANCH_COUNT_DRIFT")
    ret_origin=collections.Counter()
    for j in returns:
        reg=regs(ops[j][1])
        if not reg:
            ret_origin["UNKNOWN_RETURN_REGISTER"]+=1
            continue
        producer=producer_index(ops,j,reg[0])
        if producer is None:
            ret_origin["UNKNOWN_CROSS_BRANCH_OR_NON_INVOKE"]+=1
            continue
        method=ref(ops[producer][1])
        if method is None:
            ret_origin["UNKNOWN_PRODUCER_REFERENCE"]+=1
        elif method[0].startswith("Lkotlin/collections/"):
            ret_origin["DIRECT_KOTLIN_RESULT_SAME_BLOCK"]+=1
        else:
            ret_origin["DIRECT_OTHER_INVOKE_RESULT_SAME_BLOCK"]+=1
    return {"method_instructions":len(ops),
            "kotlin_collection_calls":apis,
            "branch_target_count":len(targets),
            "unresolved_simple_branch_targets":unknown,
            "literal_and_branch_counts":dict(sorted(count.items())),
            "return_same_block_producer_categories":dict(sorted(ret_origin.items())),
            "actual_process_argv_list_elements_verified":False,
            "ready_and_exit_protocol_verified":False}
def find_callee(original):
    with zipfile.ZipFile(original) as z:
        assets,_=asset_list(z)
        dex_files=[n for n in sorted(z.namelist()) if re.fullmatch(r"classes\d*\.dex",n)]
        require(1<=len(dex_files)<=5,"DEX_COUNT")
        dexes=[DEX(z.read(n)) for n in dex_files]
        classes=[c for d in dexes for c in d.get_classes()]
        primary=[m for c in dexes[0].get_classes() if c.get_name()==TARGET
                 for m in c.get_methods()
                 if m.get_name()=="invokeSuspend" and m.get_code() is not None]
        require(len(primary)==1 and primary[0].get_code_off()==CODE_OFF,
                "PRIMARY_ORIGINAL_DRIFT")
        ops=list(primary[0].get_instructions_idx())
        constructors=[(i,ins) for i,(_,ins) in enumerate(ops)
                      if constructor_mode(call_info(ins))=="LIST"]
        require(len(constructors)==1,"PROCESS_CTOR_COUNT_DRIFT")
        i,ctor=constructors[0]
        rr=regs(ctor)
        require(len(rr)==2,"PROCESS_CTOR_ARGUMENT_DRIFT")
        producer=producer_index(ops,i,rr[1])
        require(producer is not None,"P60_PRODUCER_DRIFT")
        wrapper=exact_def(classes,ref(ops[producer][1]))
        require(len(wrapper)==1,"P61_WRAPPER_UNRESOLVED")
        callee,status=forwarded_reference(wrapper[0])
        require(status=="EXACT_FORWARDING_CALL","P62_FORWARDING_DRIFT")
        matches=exact_def(classes,callee)
        require(len(matches)==1,"P62_CALLEE_MISSING")
        return analyze_callee(matches[0],assets,enforce_original=True)
def audit(original):
    prev=previous_audit(original)
    require(prev["callee_body"]["instruction_count"]==43,
            "P62_ORIGINAL_CALLEE_CHANGED")
    require(prev["callee_body"]["calls_and_allocations"].get("KOTLIN_COLLECTION_CALL")==2,
            "P62_TWO_COLLECTION_CALLS_CHANGED")
    return find_callee(original)
def report(data):
    print("P63_SIGNED_V138_P62_P61_P60_HASH_CHAIN=PASS")
    print("P63_EXACT_COLLECTION_SLICE="+json.dumps(data,sort_keys=True,separators=(",",":")))
    print("P63_ORIGINAL_COMMAND_LITERAL_VALUES_AND_SOURCE_EMITTED=NO")
    print("P63_REAL_SCRIPT_OR_NODE_EXECUTED=NO")
    print("P63_ORIGINAL_ENGINE_P53_WIRED=NO")
    print("P63_FIXED_SIGNED_V139=BLOCKED")
if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("signed_original_v138")
    report(audit(pathlib.Path(p.parse_args().signed_original_v138)))
