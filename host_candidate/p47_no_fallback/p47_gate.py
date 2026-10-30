#!/usr/bin/env python3
"""P47: only change the exact P40 generated *main* DEX trampoline.
Original unmodified EngineManager probeBoot and runDumpConfig are untouched.
Never produces a release or modifies the signed owner APK.
"""
import argparse
import pathlib
import re
import zipfile
from androguard.core.dex import DEX
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from p40_exact_trampoline import find_methods, TARGET, CLASS, ORIGINAL, TRAMPOLINE

BRIDGE_SOURCE = "invoke-virtual {p0}, Ljava/lang/ProcessBuilder;->start()Ljava/lang/Process;"
DENY = "Lcom/dsh/android/p47/P47LaunchGate;->startOrDeny(Ljava/lang/ProcessBuilder;)"
BRIDGE_REPLACEMENT = "invoke-static {p0}, " + DENY + "Ljava/lang/Process;"

def need(ok,label):
    if not ok:
        raise RuntimeError("P47_BLOCKED_" + label)

def patch(decoded):
    root=pathlib.Path(decoded)
    file=root / "smali/com/dsh/android/p40/P40ProcessBridge.smali"
    need(file.is_file() and not file.is_symlink(),"BRIDGE_MISSING")
    data=file.read_text(encoding="utf-8")
    need(data.count(BRIDGE_SOURCE)==1,"ORIGINAL_BRIDGE_START_DRIFT")
    need("P47LaunchGate" not in data,"BRIDGE_ALREADY_MODIFIED")
    modified=data.replace(BRIDGE_SOURCE,BRIDGE_REPLACEMENT)
    need(modified.count(BRIDGE_REPLACEMENT)==1,"DENY_NOT_UNIQUE")
    file.write_text(modified,encoding="utf-8")
    print("P47_EXACT_ORIGINAL_BRIDGE_INTERPOSED=PASS_STATIC")
    print("P47_DIRECT_HOST_PROCESSBUILDER_START=REMOVED_FROM_MAIN_ENGINE_BRIDGE")
    print("P47_OTHER_ORIGINAL_ENGINE_START_SITES=UNCHANGED")
    print("P47_REAL_PRODUCTION_NODE_ENGINE_ISOLATED=NO")

def verify(apk):
    m=find_methods(apk)
    target="Lcom/dsh/android/EngineManager$start$2;->invokeSuspend"
    bridge=CLASS+"->start"
    probe="Lcom/dsh/android/EngineManager;->probeBoot"
    dump="Lcom/dsh/android/EngineManager;->runDumpConfig"
    need(all(x in m for x in (target,bridge,probe,dump)),"REBUILT_CALLSITE_MISSING")
    need(m[target]["dex"]=="classes.dex","TARGET_MOVED")
    need(m[bridge]["dex"]=="classes.dex","BRIDGE_MOVED")
    need(m[target]["calls"].count(("invoke-static",TRAMPOLINE))==1,
         "PRIMARY_CALLSITE_NOT_EXACT")
    # P40's legacy scanner includes this invocation because the new static
    # signature contains ProcessBuilder as a *parameter*, even though the
    # callee is P47LaunchGate. Require the exact expected single call here.
    need(m[bridge]["calls"]==[("invoke-static",DENY)],
         "BRIDGE_CALLSITE_NOT_EXACT_NO_FALLBACK")
    need(("invoke-virtual",ORIGINAL) not in m[target]["calls"],
         "PRIMARY_STILL_SPAWNS_HOST")
    for x in (probe,dump):
        need(m[x]["calls"].count(("invoke-virtual",ORIGINAL))==1,
             "NON_TARGET_ORIGINAL_PROBE_CHANGED")
    need(sum(row["calls"].count(("invoke-virtual",ORIGINAL))
             for row in m.values())==2,"ORIGINAL_HOST_START_COUNT_DRIFT")
    with zipfile.ZipFile(apk) as z:
        main_dex=DEX(z.read("classes.dex"))
        exact_bridge_methods=[
            method for cls in main_dex.get_classes()
            if cls.get_name()==CLASS
            for method in cls.get_methods()
            if method.get_name()=="start"
        ]
        need(len(exact_bridge_methods)==1,"MAIN_DEX_BRIDGE_NOT_UNIQUE")
        bridge_invokes=[
            (inst.get_name(),inst.get_output())
            for _,inst in exact_bridge_methods[0].get_instructions_idx()
            if inst.get_name().startswith("invoke-")
        ]
        need(len(bridge_invokes)==1 and bridge_invokes[0][0]=="invoke-static"
             and DENY in bridge_invokes[0][1],
             "BRIDGE_NOT_EXACTLY_NO_FALLBACK")
        need(not any("Ljava/lang/ProcessBuilder;->start(" in value
                     for _,value in bridge_invokes),"BRIDGE_HOST_START_PRESENT")
        need("classes3.dex" in z.namelist(),"P47_GATE_DEX_MISSING")
        d=DEX(z.read("classes3.dex"))
        classes={c.get_name():c for c in d.get_classes()}
        gate="Lcom/dsh/android/p47/P47LaunchGate;"
        need(gate in classes,"P47_JAVA_GATE_MISSING")
        launch_methods=[method for method in classes[gate].get_methods()
                        if method.get_name()=="startOrDeny"]
        need(len(launch_methods)==1,"GATE_METHOD_NOT_UNIQUE")
        refs=[]
        for _,inst in launch_methods[0].get_instructions_idx():
            if not inst.get_name().startswith("invoke-"):
                continue
            refs.append(inst.get_output())
        need(not any("Ljava/lang/ProcessBuilder;->start(" in i for i in refs),
             "GATE_CALLS_HOST_START")
    print("P47_REBUILT_ORIGINAL_PRIMARY_ENGINE_BRIDGE_NO_HOST_START=PASS")
    print("P47_OTHER_ORIGINAL_PROBEBOOT_AND_DUMPCONFIG_PRESERVED=PASS")
    print("P47_GATE_SOURCE_COMPILED_TO_CLASSES3_DEX=PASS")
    print("P47_ALLOW_PRODUCTION_RELEASE=NO")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("mode",choices=["patch","verify"])
    p.add_argument("target")
    a=p.parse_args()
    patch(a.target) if a.mode=="patch" else verify(a.target)

if __name__=="__main__":
    main()
