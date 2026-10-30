#!/usr/bin/env python3
"""P65 bounded path-sensitive CFG + DEX register alias audit on original 43 ops.
This is a read-only local provenance proof, NOT command argv, filesystem semantics,
real engine READY/exit, host runtime isolation or production release evidence.
No proprietary values, raw register lists or original symbols are emitted.
"""
import collections,json,pathlib,re,sys,zipfile
from loguru import logger
logger.disable("androguard")
from androguard.core.dex import DEX
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"p64_list_builder_mutations"))
from p64_list_builder_mutations import audit as p64_audit,is_mutable_list_owner
sys.path.insert(0,str(ROOT/"p62_forward_target"))
from p62_forward_target import exact_def,forwarded_reference
sys.path.insert(0,str(ROOT/"p61_bridge"))
from p61_original_bridge import ref,producer_index
sys.path.insert(0,str(ROOT/"p59_backward_slice"))
from p59_backward_slice import call_info,constructor_mode
sys.path.insert(0,str(ROOT/"p57_engine_local_dataflow"))
from p57_engine_local_dataflow import regs,TARGET,CODE_OFF
sys.path.insert(0,str(ROOT/"p56_entry_ready"))
from p56_engine_entry_ready_slice import require

MAX_STATES=1024
MAX_COMPLETED=256
MAX_PATH_INSTRUCTIONS=256
MAX_REGISTER_ENTRIES=256
TRACKED={"B","BUILT"}
WRITES=("const","new-instance","new-array","move-exception","move-result",
        "iget","sget","aget","instance-of","array-length","cmp","neg","not",
        "add-","sub-","mul-","div-","rem-","rsub-","and-","or-","xor-",
        "shl-","shr-","ushr-","int-to-","long-to-","float-to-","double-to-",
        "filled-new-array")
RETURNS=("return","throw")
def call_id(ins):
    out=ref(ins)
    return (out[0],out[1],out[2],out[3]) if out else None
def branch_map(ops):
    pc_index={pc:i for i,(pc,_) in enumerate(ops)}
    require(len(pc_index)==len(ops),"DUPLICATE_PC")
    branch={}
    unknown=[]
    for i,(pc,ins) in enumerate(ops):
        name=ins.get_name()
        if name.startswith(("if-","goto")):
            fn=getattr(ins,"get_ref_off",None)
            try:delta=fn() if callable(fn) else None
            except (TypeError,ValueError,AttributeError):delta=None
            target=(pc+2*delta) if type(delta) is int else None
            if target not in pc_index:
                unknown.append("UNRESOLVED_BRANCH_TARGET")
                branch[i]=[]
                continue
            goto=bool(name.startswith("goto"))
            successors=[pc_index[target]] if goto else [i+1,pc_index[target]]
            if any(j>=len(ops) for j in successors):
                unknown.append("OFF_END_FALLTHROUGH")
                branch[i]=[]
                continue
            branch[i]=list(dict.fromkeys(successors))
        elif name.startswith(("packed-switch","sparse-switch","fill-array-data")):
            unknown.append("UNMODELLED_SWITCH_OR_PAYLOAD")
            branch[i]=[]
    return branch,unknown
def exception_status(method):
    code=method.get_code()
    fn=getattr(code,"get_tries_size",None)
    if not callable(fn):return "UNKNOWN_EXCEPTION_TABLE"
    try:v=fn()
    except (ValueError,TypeError,AttributeError):return "UNKNOWN_EXCEPTION_TABLE"
    return "NO_EXCEPTION_HANDLERS" if v==0 else "EXCEPTION_HANDLERS_UNMODELLED"
def trace_paths(method):
    ops=list(method.get_instructions_idx())
    require(0<len(ops)<=30000,"METHOD_INSTRUCTION_LIMIT")
    edges,edge_unknown=branch_map(ops)
    status=exception_status(method)
    results=[]
    incomplete=collections.Counter()
    if edge_unknown:
        incomplete.update(edge_unknown)
    if status!="NO_EXCEPTION_HANDLERS":
        incomplete[status]+=1
    seen_states=0
    # pc-index, register aliases, prior-invoke result, added site indices,
    # builder-escaped, original create count, visited instruction indices,
    # matched build receiver counts
    pending=[(0,{},None,(),False,0,frozenset(),0)]
    while pending:
        if seen_states>=MAX_STATES or len(results)>=MAX_COMPLETED:
            incomplete["STATE_OR_PATH_LIMIT"]+=1
            break
        i,values,last,adds,escaped,creates,visited,builds=pending.pop()
        seen_states+=1
        if len(visited)>=MAX_PATH_INSTRUCTIONS:
            incomplete["PATH_LENGTH_LIMIT"]+=1
            continue
        if i>=len(ops):
            incomplete["OFF_END"]+=1
            continue
        if i in visited:
            incomplete["LOOP_OR_REVISIT_UNMODELLED"]+=1
            continue
        visited=visited|{i}
        pc,ins=ops[i]
        name=ins.get_name()
        rr=regs(ins)
        vals=values.copy()
        next_result=None
        next_adds=adds
        next_escaped=escaped
        next_creates=creates
        next_builds=builds
        if name.startswith("move-result"):
            if rr:
                vals[rr[0]]=last if last in TRACKED else "UNKNOWN"
            else:
                incomplete["UNDECODED_RESULT_REGISTER"]+=1
            last=None
        elif name.startswith("move"):
            if name.startswith(("move-object","move/from","move/16","move-wide","move-exception")):
                if len(rr)>=2:
                    vals[rr[0]]=vals.get(rr[1],"UNKNOWN")
                elif rr:
                    vals[rr[0]]="UNKNOWN"
                    incomplete["UNDECODED_MOVE_REGISTER"]+=1
            last=None
        elif name=="check-cast":
            last=None
        elif name.startswith("invoke-"):
            call=call_id(ins)
            if call is None:
                incomplete["INVOKE_REF_UNPARSED"]+=1
                if any(vals.get(r)=="B" for r in rr):
                    next_escaped=True
                next_result=None
            else:
                owner,method_name,params,ret=call
                if owner.startswith("Lkotlin/collections/") and method_name=="createListBuilder":
                    if ins.get_name().endswith("/range") or rr or params:
                        incomplete["CREATE_LIST_ENCODING_UNTRUSTED"]+=1
                    else:
                        next_result="B"
                        next_creates+=1
                elif owner.startswith("Lkotlin/collections/") and method_name=="build":
                    if ins.get_name().endswith("/range") or len(rr)!=1 or params!="Ljava/util/List;":
                        incomplete["BUILD_ENCODING_UNTRUSTED"]+=1
                    elif vals.get(rr[0])=="B" and not escaped:
                        next_result="BUILT"
                        next_builds+=1
                    else:
                        next_result=None
                elif is_mutable_list_owner(owner) and method_name=="add":
                    if ins.get_name().endswith("/range") or len(rr)!=2:
                        incomplete["ADD_RECEIVER_ENCODING_UNTRUSTED"]+=1
                    elif vals.get(rr[0])=="B" and not escaped:
                        next_adds=adds+(i,)
                    else:
                        incomplete["ADD_RECEIVER_NOT_PROVEN_BUILDER"]+=1
                elif any(vals.get(r)=="B" for r in rr):
                    # An opaque callee could store/rebind/mutate the list.
                    # Never treat the builder as a unique unescaped object
                    # after such a call, even if it appears read-only.
                    next_escaped=True
            # result is only carried by IMMEDIATELY following move-result.
        elif name.startswith(WRITES):
            if rr:
                vals[rr[0]]="UNKNOWN"
            last=None
        else:
            last=None
            if name.startswith(("iput","sput","aput")) and rr and vals.get(rr[0])=="B":
                next_escaped=True
            # Non-register-writing structural instructions are ignored.
        if len(vals)>MAX_REGISTER_ENTRIES:
            incomplete["REGMAP_CAP"]+=1
            continue
        if name=="return-object":
            is_built=bool(rr and vals.get(rr[0])=="BUILT")
            results.append({"adds":next_adds,"is_built":is_built,
                            "escaped":next_escaped,"creates":next_creates,
                            "builds":next_builds})
            continue
        if name.startswith(RETURNS):
            results.append({"adds":next_adds,"is_built":False,
                            "escaped":next_escaped,"creates":next_creates,
                            "builds":next_builds})
            continue
        if i in edges:
            neighbors=edges[i]
            if not neighbors:
                incomplete["NO_VALID_BRANCH_EDGE"]+=1
                continue
        else:
            neighbors=[i+1]
        for nxt in neighbors:
            pending.append((nxt,vals.copy(),next_result,next_adds,
                            next_escaped,next_creates,visited,next_builds))
    all_add_sites={i for i,(_,ins) in enumerate(ops)
                   if (call_id(ins) is not None and
                       is_mutable_list_owner(call_id(ins)[0]) and
                       call_id(ins)[1]=="add")}
    path_adds=[set(item["adds"]) for item in results]
    touched=set().union(*path_adds) if path_adds else set()
    mandatory=set.intersection(*path_adds) if path_adds else set()
    full_graph=not incomplete
    every_return_proven=bool(results and full_graph and all(
        x["is_built"] and not x["escaped"] and x["creates"]==1 and
        x["builds"]==1 for x in results))
    return {
        "method_instruction_count":len(ops),
        "path_enumeration_completed":full_graph,
        "exception_edge_status":status,
        "path_endings_explored":len(results),
        "partial_or_unmodelled_reasons":dict(sorted(incomplete.items())),
        "static_add_calls":len(all_add_sites),
        "add_sites_reached_on_explored_paths":len(touched),
        "add_sites_present_on_each_explored_path":len(mandatory),
        "add_sites_conditional_across_explored_paths":len(touched-mandatory),
        "add_sites_unreached_in_explored_paths":len(all_add_sites-touched),
        "all_paths_return_original_builder_build_result_proven":every_return_proven,
        "no_opaque_builder_escape_on_every_path_proven":bool(
            results and full_graph and all(not x["escaped"] for x in results)),
        "known_add_receivers_on_explored_paths_count":sum(len(x["adds"]) for x in results),
        "complete_original_argv_values_and_order_proven":False,
        "ready_and_exit_protocol_proven":False,
        "isolated_original_engine_running":False
    }
def resolve_original(original):
    with zipfile.ZipFile(original) as z:
        names=[n for n in sorted(z.namelist()) if re.fullmatch(r"classes\d*\.dex",n)]
        require(1<=len(names)<=5,"ORIGINAL_DEX_COUNT")
        dexes=[DEX(z.read(n)) for n in names]
        classes=[c for d in dexes for c in d.get_classes()]
        main=[m for cl in dexes[0].get_classes() if cl.get_name()==TARGET
              for m in cl.get_methods() if m.get_name()=="invokeSuspend"
              and m.get_code() is not None]
        require(len(main)==1 and main[0].get_code_off()==CODE_OFF,"P35_MAIN_DRIFT")
        ops=list(main[0].get_instructions_idx())
        ctors=[(i,ins) for i,(_,ins) in enumerate(ops)
               if constructor_mode(call_info(ins))=="LIST"]
        require(len(ctors)==1 and len(regs(ctors[0][1]))==2,"P59_CTOR_DRIFT")
        producer=producer_index(ops,ctors[0][0],regs(ctors[0][1])[1])
        require(producer is not None,"P60_LIST_DRIFT")
        bridges=exact_def(classes,ref(ops[producer][1]))
        require(len(bridges)==1,"P61_BRIDGE_DRIFT")
        nxt,status=forwarded_reference(bridges[0])
        require(status=="EXACT_FORWARDING_CALL","P62_BRIDGE_FORWARD_DRIFT")
        callee=exact_def(classes,nxt)
        require(len(callee)==1,"P62_CALLEE_DRIFT")
        return trace_paths(callee[0])
def audit(original):
    prior=p64_audit(original)
    require(prior["body_instruction_count"]==43,"P64_BODY_DRIFT")
    require(len(prior["mutator_calls"])==9,"P64_MUTATION_COUNT_DRIFT")
    require(prior["detected_public_kotlin_builder_call_order"]==
            ["createListBuilder","build"],"P64_BUILDER_APIS_DRIFT")
    return resolve_original(original)
def report(r):
    print("P65_SIGNED_V138_P64_TO_P35_PROVENANCE=PASS")
    print("P65_BOUNDED_CFG_ALIAS_SUMMARY="+json.dumps(r,sort_keys=True,separators=(",",":")))
    print("P65_ORIGINAL_ARGV_PATH_AND_SCRIPT_VALUES_EMITTED=NO")
    print("P65_NATIVE_NODE_OR_ORIGINAL_ENGINE_EXECUTED=NO")
    print("P65_P53_PRODUCTION_INTEGRATION=NO")
    print("P65_FORMAL_SIGNED_V139_APK=BLOCKED")
if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("signed_original_v138")
    report(audit(pathlib.Path(p.parse_args().signed_original_v138)))
