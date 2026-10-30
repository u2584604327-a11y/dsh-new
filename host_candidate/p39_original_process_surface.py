#!/usr/bin/env python3
"""P39 read-only exact signed-v138 DEX Process interposition feasibility audit.

Only code offsets, method signatures and API categories are processed.
Never print or persist DEX literals, Node configuration, private dirs,
original APK, original ELF or user-data. Ephemeral CI report destroyed.
No APK patching, decompilation source export, signing or release.
"""
import argparse
import collections
import hashlib
import json
import pathlib
import re
import zipfile

from loguru import logger
logger.disable("androguard")
from androguard.core.dex import DEX

V138 = "3ca56655d79afc57431636e340823e7071bc830615ca615c485b0b9a30b6e3e5"
TARGET = "Lcom/dsh/android/EngineManager$start$2;->invokeSuspend(Ljava/lang/Object;)"
CODE_OFF = 3163260
START_PC = 3912
INVOKE = re.compile(r"(L[^\s,;]+;)->([^\s(,]+)\(([^)]*)\)")
LIFECYCLE = {
    3924: "Lcom/dsh/android/EngineManager;->access$setProcess$p(",
    3980: "Lcom/dsh/android/EngineManager$start$2",
    3986: "Ljava/lang/Thread;-><init>(",
    4010: "Ljava/lang/Thread;->start(",
    4026: "Ljava/util/concurrent/CountDownLatch;->await(",
    4674: "Lkotlinx/coroutines/flow/MutableStateFlow;->setValue(",
}
PROCESS_APIS = {
    "getInputStream", "getErrorStream", "getOutputStream", "destroy",
    "destroyForcibly", "waitFor", "isAlive", "exitValue", "pid",
    "toHandle", "onExit", "supportsNormalTermination", "children",
    "descendants", "info",
}
BUILDER_APIS = {"start", "environment", "directory", "redirectErrorStream",
                "redirectInput", "redirectOutput", "redirectError", "command",
                "inheritIO"}
STOP_APIS = {"stop", "shutdown", "restart", "requestRestart", "probeBoot",
             "preflight", "runDumpConfig"}

def sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(2 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def method_id(m):
    return m.get_class_name() + "->" + m.get_name() + m.get_descriptor().split(")", 1)[0] + ")"

def bounded_api(s):
    if len(s) <= 300:
        return s
    return s[:240] + "#hash:" + hashlib.sha256(s.encode()).hexdigest()[:16]

def inspect(original):
    if sha_file(original) != V138:
        raise ValueError("P39_EXACT_SIGNED_V138_SHA_MISMATCH")
    with zipfile.ZipFile(original) as apk:
        if apk.testzip() is not None:
            raise ValueError("P39_ZIP_CRC_MISMATCH")
        dex_names = sorted(n for n in apk.namelist()
                           if re.fullmatch(r"classes(?:[2-9][0-9]*)?\.dex", n))
        if "classes.dex" not in dex_names:
            raise ValueError("P39_MAIN_DEX_MISSING")
        dex = [(n, DEX(apk.read(n))) for n in dex_names]
    selected = []
    found_target = None
    for dex_name, d in dex:
        for cls in d.get_classes():
            cls_name = cls.get_name()
            if not cls_name.startswith("Lcom/dsh/android/"):
                continue
            # EngineManager + coroutine reader / listener closures.
            if "EngineManager" not in cls_name:
                continue
            for m in cls.get_methods():
                if m.get_code() is None:
                    continue
                ident = method_id(m)
                if ident == TARGET:
                    if found_target:
                        raise ValueError("P39_DUPLICATE_PRIMARY_COROUTINE")
                    found_target = (dex_name, m)
                selected.append((dex_name, m, ident))
    if found_target is None:
        raise ValueError("P39_TARGET_MISSING")
    if found_target[0] != "classes.dex" or found_target[1].get_code_off() != CODE_OFF:
        raise ValueError("P39_ENGINE_COROUTINE_CODE_OFFSET_DRIFT")
    observed = {}
    callsites = []
    method_summaries = []
    for dex_name, m, ident in selected:
        calls = []
        categories = collections.Counter()
        for pc, instruction in m.get_instructions_idx():
            if not instruction.get_name().startswith("invoke-"):
                continue
            parsed = INVOKE.search(instruction.get_output())
            if not parsed:
                continue
            cls, fun, params = parsed.groups()
            api = parsed.group(0)
            if ident == TARGET:
                observed[pc] = api
            category = None
            if cls == "Ljava/lang/Process;" and fun in PROCESS_APIS:
                category = "PROCESS_API"
            elif cls == "Ljava/lang/ProcessBuilder;" and fun in BUILDER_APIS:
                category = "PROCESSBUILDER_API"
            elif "EngineManager" in cls and (fun in STOP_APIS or "process" in fun.lower()):
                category = "ENGINE_LIFECYCLE"
            elif cls in ("Ljava/lang/Thread;", "Ljava/util/concurrent/CountDownLatch;"):
                category = "THREAD_OR_LATCH"
            elif cls == "Ljava/io/InputStream;" or cls == "Ljava/io/OutputStream;":
                category = "STREAM_BASE_API"
            elif cls == "Ljava/lang/ProcessHandle;":
                category = "PROCESS_HANDLE"
            if not category:
                continue
            row = {
                "method": bounded_api(ident), "dex": dex_name,
                "code_off": m.get_code_off(), "pc": pc,
                "opcode": instruction.get_name(),
                "category": category, "callee": bounded_api(api),
            }
            callsites.append(row)
            calls.append(row)
            categories[category] += 1
        if calls:
            method_summaries.append({
                "method": bounded_api(ident), "dex": dex_name,
                "code_off": m.get_code_off(),
                "category_counts": dict(sorted(categories.items())),
            })
    if observed.get(START_PC) != "Ljava/lang/ProcessBuilder;->start()":
        raise ValueError("P39_PROCESSBUILDER_START_DRIFT")
    for pc, expected in LIFECYCLE.items():
        if not observed.get(pc, "").startswith(expected):
            raise ValueError("P39_ORIGINAL_ENGINE_LIFECYCLE_DRIFT_" + str(pc))
    starts = [c for c in callsites if c["callee"] == "Ljava/lang/ProcessBuilder;->start()"]
    primary_starts = [c for c in starts
                      if c["method"] == TARGET and c["pc"] == START_PC]
    if len(primary_starts) != 1:
        raise ValueError("P39_PRIMARY_ENGINE_SPAWN_ANCHOR_NOT_UNIQUE")
    # P35 proved one start in a selected coroutine, NOT in all EngineManager
    # closures. Preserve all other starts as separate hard-blocked callsites.
    callsites.sort(key=lambda c: (c["method"], c["pc"]))
    # Focus: exact Java Process methods needed by original engine, not all app.
    needed = sorted({c["callee"] for c in callsites
                     if c["category"] in ("PROCESS_API", "PROCESS_HANDLE", "STREAM_BASE_API")})
    result = {
        "gate": "P39_EXACT_READ_ONLY_ORIGINAL_ENGINE_PROCESS_SURFACE",
        "baseline_apk_sha256": V138,
        "primary_start_code_off": CODE_OFF,
        "primary_start_pc": START_PC,
        "primary_start_opcode": starts[0]["opcode"],
        "p35_lifecycle_edges_pinned": True,
        "engine_family_methods_inspected": len(selected),
        "engine_family_methods_with_process_calls": len(method_summaries),
        "direct_interesting_callsite_count": len(callsites),
        "engine_family_processbuilder_start_sites_total": len(starts),
        "other_engine_family_processbuilder_start_sites": [
            c for c in starts if c["method"] != TARGET or c["pc"] != START_PC
        ][:40],
        "other_engine_start_sites_must_not_be_globally_hooked": True,
        "original_java_process_and_stream_apis": needed,
        "engine_method_summaries": method_summaries[:100],
        "exact_direct_callsites": callsites[:250],
        "methods_truncated": len(method_summaries) > 100,
        "calls_truncated": len(callsites) > 250,
        "process_builder_start_patch_verified": False,
        "process_supervisor_adapter": "NOT_IMPLEMENTED_IN_ORIGINAL_DSH",
        "process_handle_compatibility": "STATIC_DIRECT_CALLS_ONLY",
        "kotlin_reflection_jni_invoke_dynamic": "NOT_COVERED",
        "environment_and_worker_private_data": "NOT_TRANSFERRED",
        "real_original_app_installed_overwritten": False,
        "v139_release": "BLOCKED",
    }
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument("exact_signed_original_v138")
    p.add_argument("--report", required=True)
    args = p.parse_args()
    r = inspect(args.exact_signed_original_v138)
    pathlib.Path(args.report).write_text(json.dumps(r, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "P39_EXACT_SIGNED_V138_SHA": "PASS",
        "P39_PRIMARY_PROCESS_START_PC": r["primary_start_pc"],
        "P39_PRIMARY_PROCESS_START_OPCODE": r["primary_start_opcode"],
        "P39_ENGINE_FAMILY_METHODS_SCANNED": r["engine_family_methods_inspected"],
        "P39_PROCESS_SURFACE_CALLSITES": r["direct_interesting_callsite_count"],
        "P39_ENGINE_FAMILY_PROCESSBUILDER_START_SITES": r["engine_family_processbuilder_start_sites_total"],
        "P39_OTHER_PROCESSBUILDER_START_SITES": r["other_engine_family_processbuilder_start_sites"],
        "P39_REQUIRED_JAVA_PROCESS_METHODS": r["original_java_process_and_stream_apis"],
        "P39_SOURCE_ONLY_NO_ART_DEX_PATCH": "YES",
        "P39_NATIVE_DSH_HOST_WIRING": "NOT_IMPLEMENTED",
        "P39_V139_RELEASE": "BLOCKED",
    }, indent=2))

if __name__ == "__main__":
    main()
