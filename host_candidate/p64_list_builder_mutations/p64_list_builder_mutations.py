#!/usr/bin/env python3
"""P64 original-v138 bounded ListBuilder append/mutation argument audit.

No original command values, script/path names, DSH method names, user data,
signing secrets or binaries are printed. A statically detected add() is not
proof of actual argv nor of a branch executing at runtime.
"""
import collections,json,pathlib,re,sys,zipfile
from loguru import logger
logger.disable("androguard")
from androguard.core.dex import DEX

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"p63_kotlin_collection_slice"))
from p63_kotlin_collection_slice import audit as audit_p63,analyze_callee,safe_public_kotlin_method,encoded_arguments
sys.path.insert(0,str(ROOT/"p62_forward_target"))
from p62_forward_target import exact_def,forwarded_reference
sys.path.insert(0,str(ROOT/"p61_bridge"))
from p61_original_bridge import ref,producer_index,arity
sys.path.insert(0,str(ROOT/"p59_backward_slice"))
from p59_backward_slice import call_info,constructor_mode,target_pcs,trace_arg
sys.path.insert(0,str(ROOT/"p60_return_producer"))
from p60_return_producer import follow_local_return
sys.path.insert(0,str(ROOT/"p57_engine_local_dataflow"))
from p57_engine_local_dataflow import regs,TARGET,CODE_OFF
sys.path.insert(0,str(ROOT/"p56_entry_ready"))
from p56_engine_entry_ready_slice import asset_list,require

MUTATION_METHODS=("add","addAll","set","remove","clear")
def is_mutable_list_owner(owner):
    return (owner in ("Ljava/util/List;","Ljava/util/Collection;",
                      "Ljava/util/ArrayList;","Ljava/util/AbstractList;") or
            owner.startswith("Lkotlin/collections/builders/ListBuilder;"))
PUBLIC_FILESYSTEM_APIS={
 "getAbsolutePath":"FILE_ABSOLUTE_PATH",
 "getCanonicalPath":"FILE_CANONICAL_PATH",
 "getPath":"FILE_PATH",
 "getName":"FILE_NAME",
 "getParent":"FILE_PARENT",
 "getParentFile":"FILE_PARENT_OBJECT",
 "toPath":"FILE_TO_PATH",
 "resolve":"FILE_RESOLVE",
 "resolveSibling":"FILE_RESOLVE_SIBLING",
 "exists":"FILE_EXISTS",
 "mkdirs":"FILE_MKDIRS",
 "readBytes":"FILE_READ_BYTES",
 "writeBytes":"FILE_WRITE_BYTES"
}
def safe_file_api(ins):
    info=ref(ins)
    if info is None:return "UNPARSED_FILE_CALL"
    owner,name,_,_=info
    if owner.startswith("Ljava/io/File;") or owner.startswith("Lkotlin/io/"):
        return PUBLIC_FILESYSTEM_APIS.get(name,"OTHER_FILE_HELPER")
    return "NOT_FILESYSTEM_HELPER"
def classify_any(ins):
    found=ref(ins)
    if found is None:return "INVOKE_UNPARSED"
    owner,name,params,ret=found
    if is_mutable_list_owner(owner):
        return "LIST_MUTATOR" if name in MUTATION_METHODS else "LIST_OTHER"
    if owner.startswith("Lkotlin/collections/"):
        return "KOTLIN_LIST_FACTORY"
    if owner.startswith("Ljava/io/File;") or owner.startswith("Lkotlin/io/"):
        return "FILESYSTEM_HELPER"
    if owner in ("Ljava/lang/StringBuilder;","Ljava/lang/StringBuffer;"):
        return "STRING_BUILDER"
    if owner.startswith("Ljava/lang/String;"):
        return "STRING_HELPER"
    if owner.startswith("Lcom/dsh/android/"):
        return "DSH_INTERNAL_HELPER"
    return "OTHER_INVOKE"
def mutation_record(ops,idx,assets,targets):
    ins=ops[idx][1]
    found=ref(ins)
    require(found is not None,"MUTATOR_REF_REQUIRED")
    owner,name,params,ret=found
    require(is_mutable_list_owner(owner) and name in MUTATION_METHODS,
            "NOT_LIST_MUTATOR")
    encode=encoded_arguments(ins,(owner,name,params))
    evidence=collections.Counter()
    producer=collections.Counter()
    if encode["status"]=="ARG_REGISTERS_DECODED":
        for reg in encode["argument_regs"]:
            evidence[trace_arg(ops,idx,reg,targets,assets)]+=1
            detail=follow_local_return(ops,idx,reg,targets,assets)
            status=detail.get("status","UNKNOWN")
            if status=="EXACT_LOCAL_RESULT_INVOKE":
                category="INVOKE_"+detail["owner_category"]+"_"+detail["method_category"]+"_"+detail["return_descriptor_category"]
            elif status=="NON_INVOKE_DEFINITION":
                category="DIRECT_"+detail.get("source_category","OPAQUE")
            else:
                category=status
            producer[category]+=1
    else:
        evidence["UNKNOWN_MUTATOR_ARGUMENT_ENCODING"]+=1
        producer["UNKNOWN_MUTATOR_ARGUMENT_ENCODING"]+=1
    return {
       "operation":name,
       "callee_owner_class":"LIST_OR_COLLECTION_INTERFACE" if owner in
         ("Ljava/util/List;","Ljava/util/Collection;") else "CONCRETE_OR_KOTLIN_LIST",
       "formal_argument_types":arity(params),
       "invoke_form":"RANGE" if ins.get_name().endswith("/range") else "NON_RANGE",
       "decoded_call_register_count":len(regs(ins)),
       "argument_decode_status":encode["status"],
       "bounded_element_input_categories":dict(sorted(evidence.items())),
       "bounded_element_producer_families":dict(sorted(producer.items())),
       "receiver_object_identity_proven":False
    }
def summarize(method,assets,enforce_original=True):
    ops=list(method.get_instructions_idx())
    require(0<len(ops)<=30000,"BODY_SIZE_LIMIT")
    if enforce_original:require(len(ops)==43,"ORIGINAL_43_INSTRUCTION_DRIFT")
    targets,unresolved=target_pcs(ops)
    collection_calls=[]
    mutators=[]
    other=collections.Counter()
    filesystem_calls=collections.Counter()
    for i,(_,ins) in enumerate(ops):
        if not ins.get_name().startswith("invoke-"):continue
        kind=classify_any(ins)
        other[kind]+=1
        if kind=="FILESYSTEM_HELPER":
            filesystem_calls[safe_file_api(ins)]+=1
        reference=ref(ins)
        if reference and reference[0].startswith("Lkotlin/collections/"):
            symbol=safe_public_kotlin_method(reference[0],reference[1])
            if symbol in ("createListBuilder","build"):
                collection_calls.append((i,symbol))
        if kind=="LIST_MUTATOR":
            mutators.append(mutation_record(ops,i,assets,targets))
    if enforce_original:
        require([kind for _,kind in collection_calls]==["createListBuilder","build"],
                "EXACT_KOTLIN_BUILDER_API_ORDER_DRIFT")
    build_args={}
    if len(collection_calls)==2:
        i,api=collection_calls[1]
        found=ref(ops[i][1])
        encode=encoded_arguments(ops[i][1],(found[0],found[1],found[2]))
        if encode["status"]=="ARG_REGISTERS_DECODED" and len(encode["argument_regs"])==1:
            build_args["original_build_list_input_origin"]=trace_arg(
                ops,i,encode["argument_regs"][0],targets,assets)
        else:
            build_args["original_build_list_input_origin"]="UNKNOWN_ARGUMENT_REGISTERS"
    return {
       "body_instruction_count":len(ops),
       "detected_public_kotlin_builder_call_order":[name for _,name in collection_calls],
       "mutator_calls":mutators,
       "filesystem_helper_public_api_families":dict(sorted(filesystem_calls.items())),
       "non_mutator_call_families":dict(sorted(other.items())),
       "build_input_bounded_origin":build_args,
       "known_branch_targets":len(targets),
       "unresolved_simple_branch_targets":unresolved,
       "original_argv_elements_and_order_proven":False,
       "real_argv_script_and_ready_proven":False,
       "host_process_fallback_removed":False
    }
def resolve(original):
    with zipfile.ZipFile(original) as z:
        assets,_=asset_list(z)
        names=[name for name in sorted(z.namelist()) if re.fullmatch(r"classes\d*\.dex",name)]
        require(1<=len(names)<=5,"DEX_COUNT")
        dex=[DEX(z.read(name)) for name in names]
        all_classes=[c for d in dex for c in d.get_classes()]
        primary=[m for cl in dex[0].get_classes() if cl.get_name()==TARGET
                 for m in cl.get_methods() if m.get_name()=="invokeSuspend"
                 and m.get_code() is not None]
        require(len(primary)==1 and primary[0].get_code_off()==CODE_OFF,"P35_PRIMARY_DRIFT")
        operations=list(primary[0].get_instructions_idx())
        ctor=[(i,ins) for i,(_,ins) in enumerate(operations)
              if constructor_mode(call_info(ins))=="LIST"]
        require(len(ctor)==1 and len(regs(ctor[0][1]))==2,"CTOR_REG_DRIFT")
        source=producer_index(operations,ctor[0][0],regs(ctor[0][1])[1])
        require(source is not None,"P60_LIST_SOURCE_DRIFT")
        wrapper=exact_def(all_classes,ref(operations[source][1]))
        require(len(wrapper)==1,"P61_WRAPPER_NOT_FOUND")
        forward,status=forwarded_reference(wrapper[0])
        require(status=="EXACT_FORWARDING_CALL","P62_WRAPPER_CHANGED")
        inner=exact_def(all_classes,forward)
        require(len(inner)==1,"P62_CALLEE_UNRESOLVED")
        return summarize(inner[0],assets,True)
def audit(original):
    prev=audit_p63(original)
    require(prev["method_instructions"]==43,"P63_BODY_CHANGED")
    found=[x["public_kotlin_std_method"] for x in prev["kotlin_collection_calls"]]
    require(found==["createListBuilder","build"],"P63_PUBLIC_BUILDER_APIS_CHANGED")
    return resolve(original)
def report(data):
    print("P64_SIGNED_ORIGINAL_V138_P63_P35_HASH_CHAIN=PASS")
    print("P64_EXACT_BUILDER_MUTATION_CATEGORIES="+json.dumps(
        data,sort_keys=True,separators=(",",":")))
    print("P64_ORIGINAL_SCRIPT_PATH_VALUES_AND_SECRETS_EMITTED=NO")
    print("P64_PRODUCTION_JS_NATIVE_ADDONS_EXECUTED=NO")
    print("P64_ORIGINAL_P53_RUNTIME_WIRED=NO")
    print("P64_FIXED_SIGNED_V139=BLOCKED")
if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("exact_original_v138")
    report(audit(pathlib.Path(p.parse_args().exact_original_v138)))
