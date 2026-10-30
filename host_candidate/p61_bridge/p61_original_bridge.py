#!/usr/bin/env python3
"""P61: original v138 DEX generated bridge definition, only categorical output."""
import pathlib,sys,re,json,zipfile,collections
from loguru import logger
logger.disable("androguard")
from androguard.core.dex import DEX
BASE=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/"p60_return_producer"))
from p60_return_producer import audit as previous_audit,inspect_primary
sys.path.insert(0,str(BASE/"p59_backward_slice"))
from p59_backward_slice import call_info,constructor_mode,target_pcs,BRANCH,MOVE,SOURCE
sys.path.insert(0,str(BASE/"p57_engine_local_dataflow"))
from p57_engine_local_dataflow import regs,TARGET,CODE_OFF
sys.path.insert(0,str(BASE/"p56_entry_ready"))
from p56_engine_entry_ready_slice import asset_list,require
PAT=re.compile(r"(L[^,;\s]+;)->([^\s(,]+)\(([^)]*)\)(\[*[VZBCSIJFD]|\[*L[^;\s,]+;)")
def ref(ins):
    m=PAT.search(ins.get_output()) if ins.get_name().startswith("invoke-") else None
    return m.groups() if m else None
def arity(desc):
    desc="".join(desc.split())
    i=0;n=0
    while i<len(desc):
        while i<len(desc) and desc[i]=="[":i+=1
        if i>=len(desc):return None
        if desc[i]=="L":
            e=desc.find(";",i)
            if e<0:return None
            i=e+1
        elif desc[i] in "ZBCDFIJS":i+=1
        else:return None
        n+=1
        if n>48:return None
    return n
def flags(value):
    return {"synthetic":bool(value&0x1000),"bridge":bool(value&0x40),
            "static":bool(value&0x8)}
def range_data(ins):
    if not ins.get_name().endswith("/range"):
        return {"range":False,"interval_validated":False}
    f=getattr(ins,"get_AA",None)
    try:count=f() if callable(f) else None
    except (ValueError,TypeError,AttributeError):count=None
    rr=regs(ins)
    return {"range":True,"encoded_words":count,
            "decoded_operands":len(rr),
            "interval_validated":bool(type(count) is int and count>0 and
                len(rr)==count and rr==list(range(rr[0],rr[0]+len(rr))))}
def producer_index(ops,at,r):
    targets,_=target_pcs(ops)
    visited=set()
    for _ in range(12):
        if (at,r) in visited:return None
        visited.add((at,r))
        copied=False
        for j in range(at-1,max(-1,at-257),-1):
            pc,ins=ops[j];name=ins.get_name()
            if pc in targets or name.startswith(BRANCH):return None
            rs=regs(ins)
            if not rs or rs[0]!=r:continue
            if name.startswith(MOVE):
                if len(rs)<2:return None
                at,r=j,rs[1];copied=True;break
            if name.startswith("move-result"):
                return j-1 if j>0 and ops[j-1][1].get_name().startswith("invoke-") else None
            if name.startswith(SOURCE):return None
        if not copied:return None
    return None
def family(ins):
    call=ref(ins)
    if call is None:return "UNPARSED"
    owner=call[0]
    if owner.startswith("Lkotlin/collections/"):return "KOTLIN_COLLECTIONS"
    if owner in ("Ljava/util/Arrays;","Ljava/util/Collections;"):return "JAVA_COLLECTIONS"
    if owner=="Ljava/util/ArrayList;":return "ARRAY_LIST"
    if owner=="Ljava/lang/StringBuilder;":return "STRING_BUILDER"
    if owner.startswith("Lcom/dsh/android/"):return "DSH_INTERNAL"
    return "OTHER"
def body(m):
    if m is None or m.get_code() is None:return {"has_code":False}
    ops=list(m.get_instructions_idx())
    require(len(ops)<=30000,"PRODUCER_INSTRUCTION_CAP")
    c=collections.Counter()
    for _,ins in ops:
        name=ins.get_name()
        if name.startswith("invoke-"):c["INVOKE_"+family(ins)]+=1
        if name=="return-object":c["RETURN_OBJECT"]+=1
        if name.startswith(("if-","goto","packed-switch","sparse-switch")):c["BRANCH"]+=1
        if name=="new-instance" and "Ljava/util/ArrayList;" in ins.get_output():
            c["ALLOC_LIST"]+=1
        if name.startswith(("new-array","filled-new-array")):c["ALLOC_ARRAY"]+=1
    return {"has_code":True,"instructions":len(ops),"shape":dict(sorted(c.items()))}
def analyze(primary,classes,assets):
    checked=inspect_primary(primary,assets)
    require(checked["same_method_return_producer"]["status"]=="EXACT_LOCAL_RESULT_INVOKE","P60_DRIFT")
    ops=list(primary.get_instructions_idx())
    constructors=[(i,ins) for i,(_,ins) in enumerate(ops)
                  if constructor_mode(call_info(ins))=="LIST"]
    require(len(constructors)==1,"PROCESS_CTOR_DRIFT")
    at,ctor=constructors[0]
    rr=regs(ctor)
    require(len(rr)==2,"CTOR_REGISTER_DRIFT")
    idx=producer_index(ops,at,rr[1])
    require(idx is not None,"PRODUCER_INDEX_NOT_PROVEN")
    ins=ops[idx][1]
    info=ref(ins)
    require(info is not None,"PRODUCER_FULL_REF_NOT_PARSED")
    owner,name,params,ret=info
    require(owner.startswith("Lcom/dsh/android/"),"P60_OWNER_DRIFT")
    require(name.startswith(("access$","lambda$")),"P60_GENERATED_PATTERN_DRIFT")
    require(ret=="Ljava/util/List;","P60_LIST_RETURN_DRIFT")
    cl=[c for c in classes if c.get_name()==owner]
    require(len(cl)<=1,"CLASS_DUPLICATED")
    same_name=[]
    exact=[]
    return_match=[]
    if cl:
        for candidate in cl[0].get_methods():
            if candidate.get_name()!=name:
                continue
            same_name.append(candidate)
            desc="".join(candidate.get_descriptor().split())
            if desc.endswith(")"+ret):
                return_match.append(candidate)
            if desc=="("+"".join(params.split())+")"+ret:
                exact.append(candidate)
    require(len(exact)<=1,"METHOD_DUPLICATED")
    m=exact[0] if exact else None
    # Candidate classes may contain an overload, but an unmatched name is NOT
    # proof of a resolved original method. Inspect alternative matches only
    # as candidates, never as production command evidence.
    candidate=same_name[0] if len(same_name)==1 else None
    return {
      "generated_name_match":True,
      "owner_class_definition_found":bool(cl),
      "same_name_candidate_count":len(same_name),
      "same_name_and_return_descriptor_count":len(return_match),
      "exact_method_definition_found":m is not None,
      "access_flags":flags(m.get_access_flags()) if m else None,
      "candidate_only_access_flags":flags(candidate.get_access_flags()) if candidate and not m else None,
      "method_descriptor_argument_types":arity(params),
      "invoke_range":range_data(ins),
      "method_body":body(m),
      "candidate_only_method_body":body(candidate) if candidate and not m else None,
      "list_elements_proven":False,
      "node_argv_proven":False,
      "ready_contract_proven":False
    }
def audit(path):
    p=previous_audit(path)
    require(p["same_method_return_producer"]["owner_category"]=="DSH_APP","P60_OWNER_CHANGED")
    with zipfile.ZipFile(path) as z:
        assets,_=asset_list(z)
        dexes=[DEX(z.read(name)) for name in sorted(z.namelist())
               if re.fullmatch(r"classes\d*\.dex",name)]
        require(1<=len(dexes)<=5,"DEX_COUNT_UNEXPECTED")
        classes=[c for dex in dexes for c in dex.get_classes()]
        main=[m for c in dexes[0].get_classes() if c.get_name()==TARGET
              for m in c.get_methods()
              if m.get_name()=="invokeSuspend" and m.get_code() is not None]
        require(len(main)==1 and main[0].get_code_off()==CODE_OFF,"EXACT_MAIN_DRIFT")
        return analyze(main[0],classes,assets)
def report(r):
    print("P61_EXACT_SIGNED_V138_P60_TO_P35_CHAIN=PASS")
    print("P61_GENERATED_PRODUCER_CATEGORICAL="+json.dumps(r,sort_keys=True,separators=(",",":")))
    print("P61_RAW_ORIGINAL_METHOD_VALUES_EMITTED=NO")
    print("P61_ORIGINAL_SCRIPT_EXECUTED=NO")
    print("P61_P53_PRODUCTION_WIRED=NO")
    print("P61_V139_FORMAL_APK=BLOCKED")
if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("signed_original_v138")
    report(audit(pathlib.Path(p.parse_args().signed_original_v138)))
