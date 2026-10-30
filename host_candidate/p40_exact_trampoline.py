#!/usr/bin/env python3
"""Exact-v138 *offline* EngineManager launch-site trampoline experiment.

This is NOT isolation, a permission broker, a complete v139 patch, or
a production signer. Never install an output into the user's DSH app.
"""
import argparse
import hashlib
import json
import pathlib
import re
import sys
import zipfile

from androguard.core.dex import DEX
from p35_original_engine_spawn_contract import EXPECTED, TARGET, inspect as p35_inspect

CLASS = "Lcom/dsh/android/p40/P40ProcessBridge;"
ORIGINAL = "Ljava/lang/ProcessBuilder;->start()"
TRAMPOLINE = CLASS + "->start(Ljava/lang/ProcessBuilder;)"
TARGET_FILENAME = "EngineManager$start$2.smali"
BRIDGE = """.class public final Lcom/dsh/android/p40/P40ProcessBridge;
.super Ljava/lang/Object;

# This method deliberately preserves the legacy ProcessBuilder semantics.
# It DOES NOT isolate Node, grant permissions or change environment variables.
.method public static start(Ljava/lang/ProcessBuilder;)Ljava/lang/Process;
    .registers 2
    .param p0, "builder"  # Ljava/lang/ProcessBuilder;

    invoke-virtual {p0}, Ljava/lang/ProcessBuilder;->start()Ljava/lang/Process;
    move-result-object v0
    return-object v0
.end method
"""
CALL = re.compile(r'(?m)^([ \t]*)invoke-virtual[ \t]+\{([vp][0-9]+)\},[ \t]+'
                  r'Ljava/lang/ProcessBuilder;->start\(\)Ljava/lang/Process;[ \t]*$')
RUNTIME = re.compile(r'(L[^\s,;]+;)->([^\s(,]+)\(([^)]*)\)')

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def require(condition, why):
    if not condition:
        raise RuntimeError("P40_BLOCKED_" + why)

def safe_path(root, *parts):
    candidate = root.joinpath(*parts)
    require(root.is_dir() and not root.is_symlink(), "OUTPUT_NOT_DIRECTORY")
    require(root.resolve() in candidate.resolve().parents, "PATH_ESCAPE")
    require(not candidate.is_symlink(), "SYMLINK")
    return candidate

def patch(apk, decoded, report):
    p35 = p35_inspect(apk)
    require(p35["primary_start_pc"] == 3912, "P35_PC_DRIFT")
    require(p35["post_spawn_required_lifecycle_api_edges"], "P35_LIFECYCLE_MISSING")
    root = pathlib.Path(decoded)
    target = safe_path(root, "smali", "com", "dsh", "android", TARGET_FILENAME)
    another = safe_path(root, "smali", "com", "dsh", "android", "EngineManager.smali")
    output = safe_path(root, "smali", "com", "dsh", "android", "p40", "P40ProcessBridge.smali")
    require(target.is_file() and another.is_file(), "ENGINE_MAIN_DEX_SMALI_MISSING")
    require(not output.exists(), "BRIDGE_ALREADY_EXISTS")
    target_bytes = target.read_bytes()
    another_bytes = another.read_bytes()
    require(len(target_bytes) < 3_000_000, "SMALI_TOO_LARGE")
    orig = target_bytes.decode("utf-8")
    match = list(CALL.finditer(orig))
    require(len(match) == 1, "TARGET_VIRTUAL_CALL_NOT_UNIQUE")
    require(".method" in orig and "invokeSuspend" in orig, "INVOKE_SUSPEND_NOT_FOUND")
    require(another_bytes.count(b"Ljava/lang/ProcessBuilder;->start()Ljava/lang/Process;") == 2,
            "OTHER_ENGINE_START_SITES_DRIFT")
    reg = match[0].group(2)
    # Keep exact register and instruction (35c) arity: receiver becomes static arg.
    patched = CALL.sub(lambda m:
        m.group(1) + "invoke-static {" + m.group(2) + "}, " +
        TRAMPOLINE + "Ljava/lang/Process;", orig)
    require(patched != orig, "NO_REWRITE")
    require(patched.count(TRAMPOLINE) == 1, "TRAMPOLINE_NOT_UNIQUE")
    require(ORIGINAL not in patched, "ORIGINAL_CALL_STILL_IN_TARGET")
    require(another.read_bytes() == another_bytes, "PROBE_DUMPCONFIG_MUTATED")
    output.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(patched, encoding="utf-8")
    output.write_text(BRIDGE, encoding="utf-8")
    require(another.read_bytes() == another_bytes, "OTHER_ENGINE_CALLSITE_DRIFT")
    payload = {
        "gate": "P40_OFFLINE_PINNED_TRAMPOLINE_SOURCE_ONLY",
        "original_signed_v138_sha256": EXPECTED,
        "target": TARGET,
        "target_original_pc": 3912,
        "invoke_register": reg,
        "original_engine_smali_sha256": digest(target_bytes),
        "patched_engine_smali_sha256": digest(target.read_bytes()),
        "other_engine_smali_sha256_unchanged": digest(another.read_bytes()),
        "other_engine_start_calls_preserved": 2,
        "trampoline_added": CLASS,
        "trampoline_behaviour": "CALLS_ORIGINAL_PROCESSBUILDER_START",
        "binder_worker_isolation": "NOT_IMPLEMENTED",
        "original_signed_apk_modified": False,
        "v139_release": "BLOCKED",
    }
    pathlib.Path(report).write_text(json.dumps(payload, indent=2) + "\n")
    print("P40_OFFLINE_EXACT_SITE_TRAMPOLINE=PASS_SMALI_SOURCE")
    print("P40_ORIGINAL_PROBEBOOT_AND_DUMPCONFIG=UNCHANGED")
    print("P40_ORIGINAL_PROCESS_SEMANTICS=UNCHANGED_BY_DESIGN_NOT_RUNTIME_TESTED")
    print("P40_V139_RELEASE=BLOCKED")

def find_methods(apk):
    out = {}
    with zipfile.ZipFile(apk) as archive:
        dex_files = [n for n in archive.namelist()
                     if re.fullmatch(r"classes(?:[2-9][0-9]*)?\.dex", n)]
        require("classes.dex" in dex_files, "REBUILT_PRIMARY_DEX_MISSING")
        for dex_name in dex_files:
            d = DEX(archive.read(dex_name))
            for cls in d.get_classes():
                if cls.get_name() not in ("Lcom/dsh/android/EngineManager$start$2;",
                                          "Lcom/dsh/android/EngineManager;", CLASS):
                    continue
                for m in cls.get_methods():
                    if m.get_code() is None:
                        continue
                    ident = cls.get_name() + "->" + m.get_name()
                    if ident not in (
                        "Lcom/dsh/android/EngineManager$start$2;->invokeSuspend",
                        "Lcom/dsh/android/EngineManager;->probeBoot",
                        "Lcom/dsh/android/EngineManager;->runDumpConfig",
                        CLASS + "->start",
                    ):
                        continue
                    calls = []
                    for pc, insn in m.get_instructions_idx():
                        if not insn.get_name().startswith("invoke-"):
                            continue
                        found = RUNTIME.search(insn.get_output())
                        if found and ("ProcessBuilder;" in found.group(0) or CLASS in found.group(0)):
                            calls.append((insn.get_name(), found.group(0)))
                    out[ident] = {"dex": dex_name, "calls": calls}
    return out

def verify_rebuilt(apk):
    methods = find_methods(apk)
    target = "Lcom/dsh/android/EngineManager$start$2;->invokeSuspend"
    probe = "Lcom/dsh/android/EngineManager;->probeBoot"
    dump = "Lcom/dsh/android/EngineManager;->runDumpConfig"
    bridge = CLASS + "->start"
    for name in (target, probe, dump, bridge):
        require(name in methods, "MISSING_METHOD_" + name.split("->")[-1])
    require(methods[target]["dex"] == "classes.dex", "TARGET_RELOCATED_OUT_OF_PRIMARY_DEX")
    require(methods[bridge]["dex"] == "classes.dex", "TRAMPOLINE_RELOCATED_OUT_OF_PRIMARY_DEX")
    # Other ProcessBuilder APIs (environment, directory, redirects) are
    # essential original startup semantics and must remain in this method.
    # Only the single ProcessBuilder.start() invocation is redirected.
    primary_calls = methods[target]["calls"]
    require(primary_calls.count(("invoke-static", TRAMPOLINE)) == 1,
            "TRAMPOLINE_NOT_PRESENT_EXACTLY_ONCE")
    require(("invoke-virtual", ORIGINAL) not in primary_calls,
            "ORIGINAL_START_REMAINS_IN_PRIMARY")
    for name in (probe, dump, bridge):
        require(methods[name]["calls"].count(("invoke-virtual", ORIGINAL)) == 1,
                "OTHER_START_BROKEN_" + name.split("->")[-1])
    original_calls = sum(v["calls"].count(("invoke-virtual", ORIGINAL))
                         for v in methods.values())
    require(original_calls == 3, "UNEXPECTED_BUILDER_START_TOTAL")
    print("P40_REBUILT_DEX_TRAMPOLINE_METHOD=PASS")
    print("P40_REBUILT_DEX_PROBEBOOT_AND_DUMPCONFIG=PASS")
    print("P40_TRAMPOLINE_IS_NOT_ISOLATION=CONFIRMED")
    print("P40_ORIGINAL_SIGNATURE_PRESERVED=NO")
    print("P40_V139_RELEASE=BLOCKED")

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="op", required=True)
    a = sub.add_parser("patch")
    a.add_argument("exact_v138_apk")
    a.add_argument("decoded_apk_dir")
    a.add_argument("--report", required=True)
    b = sub.add_parser("verify")
    b.add_argument("rebuilt_unsigned_apk")
    args = parser.parse_args()
    if args.op == "patch":
        patch(args.exact_v138_apk, args.decoded_apk_dir, args.report)
    else:
        verify_rebuilt(args.rebuilt_unsigned_apk)

if __name__ == "__main__":
    main()
