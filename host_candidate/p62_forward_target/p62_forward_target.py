#!/usr/bin/env python3
"""P62 read-only exact original v138 follow of generated List forwarding wrapper.
Only categorical structure; never print proprietary method names, scripts, paths
or executable bytes. No Node or original app execution.
"""
import collections,json,pathlib,re,sys,zipfile
from loguru import logger
logger.disable("androguard")
from androguard.core.dex import DEX
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"p61_bridge"))
from p61_original_bridge import audit as audit_p61,ref,producer_index,body,range_data
sys.path.insert(0,str(ROOT/"p59_backward_slice"))
from p59_backward_slice import call_info,constructor_mode
sys.path.insert(0,str(ROOT/"p57_engine_local_dataflow"))
from p57_engine_local_dataflow import regs,TARGET,CODE_OFF
sys.path.insert(0,str(ROOT/"p56_entry_ready"))
from p56_engine_entry_ready_slice import asset_list,require
def exact_def(classes,reference):
    if reference is None:return []
    owner,name,params,ret=reference
    want="("+ "".join(params.split()) +")"+ret
    found=[]
    for cl in classes:
        if cl.get_name()!=owner:continue
        for m in cl.get_methods():
            if m.get_name()==name and "".join(m.get_descriptor().split())==want:
                found.append(m)
    require(len(found)<=1,"DUPLICATE_METHOD_DEFINITION")
    return found
def forwarded_reference(bridge):
    if bridge is None or bridge.get_code() is None:return None,"UNKNOWN_NO_CODE"
    ops=list(bridge.get_instructions_idx())
    if len(ops)!=3:return None,"UNKNOWN_NOT_THREE_INSTRUCTIONS"
    invokes=[(i,ins) for i,(_,ins) in enumerate(ops)
             if ins.get_name().startswith("invoke-")]
    returns=[ins for _,ins in ops if ins.get_name()=="return-object"]
    if len(invokes)!=1 or len(returns)!=1:return None,"UNKNOWN_WRAPPER_SHAPE"
    idx,ins=invokes[0]
    candidate=ref(ins)
    if candidate is None:return None,"UNKNOWN_INVOKE_REFERENCE"
    if not candidate[0].startswith("Lcom/dsh/android/"):
        return None,"UNKNOWN_NON_APP_CALLEE"
    if idx+1>=len(ops) or ops[idx+1][1].get_name()!="move-result-object":
        return None,"UNKNOWN_RETURN_DEFUSE"
    reg_result=regs(ops[idx+1][1])
    reg_return=regs(ops[-1][1])
    if not reg_result or not reg_return or reg_result[0]!=reg_return[0]:
        return None,"UNKNOWN_RETURN_REGISTER"
    return candidate,"EXACT_FORWARDING_CALL"
def callee_structure(m):
    if m is None or m.get_code() is None:return {"has_body":False}
    ops=list(m.get_instructions_idx())
    require(len(ops)<=30000,"CALLEE_INSTRUCTION_CAP")
    c=collections.Counter()
    for _,ins in ops:
        name=ins.get_name()
        if name.startswith("invoke-"):
            call=ref(ins)
            if not call:c["UNPARSED_CALL"]+=1
            elif call[0].startswith("Lkotlin/collections/"):c["KOTLIN_COLLECTION_CALL"]+=1
            elif call[0] in ("Ljava/util/Arrays;","Ljava/util/Collections;"):
                c["JAVA_COLLECTION_CALL"]+=1
            elif call[0].startswith("Lcom/dsh/android/"):c["DSH_INTERNAL_CALL"]+=1
            elif call[0]=="Ljava/lang/StringBuilder;":c["STRING_BUILDER_CALL"]+=1
            elif call[0]=="Ljava/util/ArrayList;":c["JAVA_ARRAYLIST_CALL"]+=1
            else:c["OTHER_CALL"]+=1
        if name=="return-object":c["RETURN_OBJECT"]+=1
        if name=="new-instance" and "Ljava/util/ArrayList;" in ins.get_output():
            c["ALLOC_ARRAYLIST"]+=1
        if name.startswith(("new-array","filled-new-array")):c["ALLOC_ARRAY"]+=1
        if name in ("const-string","const-string/jumbo"):c["STRING_LITERAL_COUNT"]+=1
        if name.startswith(("if-","goto","packed-switch","sparse-switch")):
            c["BRANCH"]+=1
    return {"has_body":True,"instruction_count":len(ops),
            "calls_and_allocations":dict(sorted(c.items()))}
def audit(original):
    p=audit_p61(original)
    require(p["exact_method_definition_found"],"P61_EXACT_BRIDGE_NOT_FOUND")
    require(p["method_body"]["instructions"]==3,"P61_WRAPPER_CHANGED")
    with zipfile.ZipFile(original) as z:
        dexes=[DEX(z.read(n)) for n in sorted(z.namelist())
               if re.fullmatch(r"classes\d*\.dex",n)]
        require(1<=len(dexes)<=5,"DEX_COUNT")
        classes=[c for dex in dexes for c in dex.get_classes()]
        original_main=[m for c in dexes[0].get_classes() if c.get_name()==TARGET
                       for m in c.get_methods() if m.get_name()=="invokeSuspend"
                       and m.get_code() is not None]
        require(len(original_main)==1 and original_main[0].get_code_off()==CODE_OFF,
                "ORIGINAL_PRIMARY_DRIFT")
        primary_ops=list(original_main[0].get_instructions_idx())
        ctors=[(i,ins) for i,(_,ins) in enumerate(primary_ops)
               if constructor_mode(call_info(ins))=="LIST"]
        require(len(ctors)==1 and len(regs(ctors[0][1]))==2,
                "PROCESS_CTOR_DRIFT")
        idx=producer_index(primary_ops,ctors[0][0],regs(ctors[0][1])[1])
        require(idx is not None,"PROCESS_LIST_PRODUCER_DRIFT")
        first=ref(primary_ops[idx][1])
        bridge=exact_def(classes,first)
        require(len(bridge)==1,"EXACT_GENERATED_BRIDGE_UNRESOLVED")
        nextref,status=forwarded_reference(bridge[0])
        require(status=="EXACT_FORWARDING_CALL",
                "BRIDGE_IS_NOT_SAFE_FORWARDING_RETURN")
        targets=exact_def(classes,nextref)
        target=targets[0] if len(targets)==1 else None
        return {
          "wrapper_to_internal_call_resolved":True,
          "forwarding_callee_definition_found":target is not None,
          "callee_body":callee_structure(target),
          "callee_access_static":bool(target.get_access_flags()&0x8) if target else None,
          "confirmed_full_argv":False,
          "confirmed_ready_lifecycle":False,
          "confirmed_isolated_engine_launch":False,
        }
def report(x):
    print("P62_EXACT_PINNED_SIGNED_V138_AND_P61_CHAIN=PASS")
    print("P62_CATEGORICAL_CALLEE_STRUCTURE="+json.dumps(x,sort_keys=True,separators=(",",":")))
    print("P62_ORIGINAL_SYMBOLS_PATHS_ARGV_AND_VALUES_EMITTED=NO")
    print("P62_ORIGINAL_SCRIPT_OR_NODE_EXECUTED=NO")
    print("P62_FIXED_SIGNING_KEY_USED=NO")
    print("P62_FORMAL_SIGNED_V139=BLOCKED")
if __name__=="__main__":
    import argparse
    a=argparse.ArgumentParser();a.add_argument("original_signed_v138")
    report(audit(pathlib.Path(a.parse_args().original_signed_v138)))
