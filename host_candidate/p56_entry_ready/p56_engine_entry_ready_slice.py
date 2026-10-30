#!/usr/bin/env python3
"""P56 exact original startup/READY structural slice, read only.
Never prints original strings, filenames, argv, env, cwd or JS code.
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

BASE = pathlib.Path(__file__).resolve().parents[1]
for directory in (BASE, BASE / "p54_engine_tree", BASE / "p55_runtime_imports"):
    sys.path.insert(0, str(directory))
from p35_original_engine_spawn_contract import inspect as p35_inspect
from p54_immutable_tar_audit import exact_engine
from p55_exact_original_import_audit import EXPECTED_TREE_SHA

TARGET = "Lcom/dsh/android/EngineManager$start$2;"
PC = 3912
CODE_OFF = 3163260
INVOKE = re.compile(r"(L[^\s,;]+;)->([^\s(,]+)\(([^)]*)\)")
CALLS = {
    "Ljava/lang/ProcessBuilder;-><init>": "CONSTRUCTOR",
    "Ljava/lang/ProcessBuilder;->command": "COMMAND",
    "Ljava/lang/ProcessBuilder;->environment": "ENV",
    "Ljava/lang/ProcessBuilder;->directory": "CWD",
    "Ljava/lang/ProcessBuilder;->start": "START",
    "Ljava/lang/Process;->getInputStream": "STDOUT",
    "Ljava/lang/Process;->getErrorStream": "STDERR",
    "Ljava/lang/Process;->getOutputStream": "STDIN",
    "Ljava/lang/Process;->destroy": "DESTROY",
    "Ljava/util/concurrent/CountDownLatch;->await": "LATCH_WAIT",
    "Ljava/util/concurrent/CountDownLatch;->countDown": "LATCH_SIGNAL",
    "Ljava/util/regex/Pattern;->compile": "REGEX_COMPILE",
    "Ljava/util/regex/Matcher;->find": "REGEX_FIND",
    "Ljava/util/regex/Matcher;->matches": "REGEX_MATCH",
    "Lkotlin/text/Regex;->containsMatchIn": "KOTLIN_REGEX",
    "Lkotlinx/coroutines/flow/MutableStateFlow;->setValue": "STATEFLOW",
    "Ljava/lang/Thread;->start": "THREAD_START",
}
def require(ok, code):
    if not ok:
        raise ValueError("P56_BLOCKED_" + code)

def categories(value, assets):
    if not isinstance(value, str) or len(value) > 1024:
        return ()
    out = []
    if value in assets:
        out.append("EXACT_APK_ASSET_STRING")
    if value.endswith((".js", ".mjs", ".cjs")):
        out.append("JS_SHAPED")
    if value.endswith(".zip"):
        out.append("ZIP_SHAPED")
    if value == "engine.bin" or value.endswith("/engine.bin"):
        out.append("ENGINE_ARCHIVE_SHAPED")
    if re.search("ready|listening|started", value, flags=re.I):
        out.append("READY_STRING_HINT")
    return tuple(out)

def instruction_string(ins):
    if ins.get_name() not in ("const-string", "const-string/jumbo"):
        return None
    try:
        operands = ins.get_operands()
        if operands and len(operands[-1]) >= 3 and isinstance(operands[-1][-1], str):
            return operands[-1][-1]
    except (TypeError, IndexError, AttributeError, ValueError):
        pass
    return None

def asset_list(apk_zip):
    assets = set()
    counts = collections.Counter()
    for item in apk_zip.infolist():
        if not item.filename.startswith("assets/") or item.is_dir():
            continue
        require(len(assets) < 2000, "ASSET_CAP")
        require(item.filename not in assets, "ASSET_DUPLICATE")
        assets.add(item.filename)
        if item.filename.endswith((".js", ".mjs", ".cjs")):
            counts["js"] += 1
        if item.filename.endswith(".zip"):
            counts["zip"] += 1
    return assets, counts

def slice_methods(methods, assets):
    primary = [(cls, m) for cls, m in methods
               if cls == TARGET and m.get_name() == "invokeSuspend"]
    require(len(primary) == 1, "PRIMARY_METHOD_COUNT")
    target = primary[0][1]
    require(target.get_code_off() == CODE_OFF, "PRIMARY_CODE_OFFSET_DRIFT")
    counters = collections.Counter()
    direct = collections.Counter()
    literal_counts = collections.Counter()
    primary_lit = collections.Counter()
    family_assets = set()
    primary_assets = set()
    ready_signal_methods = set()
    regex_methods = set()
    starts = []
    total = 0
    for cls, method in methods:
        ident = cls + "->" + method.get_name()
        for pc, ins in method.get_instructions_idx():
            total += 1
            require(total <= 100000, "INSTRUCTION_CAP")
            name = ins.get_name()
            if name.startswith("invoke-"):
                match = INVOKE.search(ins.get_output())
                if match:
                    call = match.group(0)
                    for prefix, label in CALLS.items():
                        if call.startswith(prefix + "("):
                            counters[label] += 1
                            if method is target:
                                direct[label] += 1
                                if label == "START":
                                    starts.append(pc)
                            if label == "LATCH_SIGNAL":
                                ready_signal_methods.add(ident)
                            if label in ("REGEX_COMPILE", "REGEX_FIND",
                                         "REGEX_MATCH", "KOTLIN_REGEX"):
                                regex_methods.add(ident)
            elif name in ("const-string", "const-string/jumbo"):
                value = instruction_string(ins)
                if value is None:
                    literal_counts["UNDECODED_STRING"] += 1
                    continue
                for category in categories(value, assets):
                    literal_counts[category] += 1
                    if method is target and abs(pc - PC) <= 1500:
                        primary_lit[category] += 1
                if value in assets:
                    family_assets.add(value)
                    if method is target:
                        primary_assets.add(value)
    require(starts == [PC], "PRIMARY_START_DRIFT")
    require(direct["THREAD_START"] > 0, "ORIGINAL_READER_THREAD_DRIFT")
    require(direct["LATCH_WAIT"] > 0, "ORIGINAL_LATCH_DRIFT")
    require(direct["STATEFLOW"] > 0, "ORIGINAL_STATEFLOW_DRIFT")
    return {
        "primary_process_and_ready_api_counts": dict(sorted(direct.items())),
        "start_family_process_and_ready_api_counts": dict(sorted(counters.items())),
        "start_family_literal_category_counts": dict(sorted(literal_counts.items())),
        "primary_near_start_literal_category_counts": dict(sorted(primary_lit.items())),
        "start_family_methods": len(methods),
        "primary_exact_asset_literal_matches": len(primary_assets),
        "family_exact_asset_literal_matches": len(family_assets),
        "nested_latch_signal_method_hints": len(ready_signal_methods),
        "nested_regex_method_hints": len(regex_methods),
        "actual_start_command_proven": False,
        "actual_runtime_ready_predicate_proven": False,
    }

def audit(original):
    tree = exact_engine(original)
    require(tree["tree_sha256"] == EXPECTED_TREE_SHA and tree["members"] == 30411,
            "ORIGINAL_ENGINE_TREE_DRIFT")
    p35 = p35_inspect(original)
    require(p35["primary_start_pc"] == PC and
            len(p35["post_spawn_required_lifecycle_api_edges"]) == 6,
            "ORIGINAL_PROCESS_LIFECYCLE_DRIFT")
    with zipfile.ZipFile(original) as z:
        assets, counts = asset_list(z)
        require("classes.dex" in z.namelist(), "MISSING_ORIGINAL_DEX")
        dex = DEX(z.read("classes.dex"))
        methods = []
        for klass in dex.get_classes():
            name = klass.get_name()
            if name != TARGET and not name.startswith(TARGET[:-1] + "$"):
                continue
            for method in klass.get_methods():
                if method.get_code() is not None:
                    require(len(methods) < 160, "METHOD_COUNT_CAP")
                    methods.append((name, method))
        result = slice_methods(methods, assets)
    return counts, result

def report(counts, result):
    print("P56_PINNED_ORIGINAL_SHA_AND_P54_FULL_TREE=PASS")
    print("P56_P35_EXACT_SPAWN_LIFECYCLE=PASS")
    print("P56_APK_JS_ASSETS=" + str(counts["js"]))
    print("P56_APK_ZIP_ASSETS=" + str(counts["zip"]))
    for key in ("primary_process_and_ready_api_counts",
                "start_family_process_and_ready_api_counts",
                "start_family_literal_category_counts",
                "primary_near_start_literal_category_counts"):
        print("P56_" + key.upper() + "=" +
              json.dumps(result[key], sort_keys=True, separators=(",", ":")))
    for key in ("start_family_methods", "primary_exact_asset_literal_matches",
                "family_exact_asset_literal_matches",
                "nested_latch_signal_method_hints", "nested_regex_method_hints"):
        print("P56_" + key.upper() + "=" + str(result[key]))
    print("P56_ORIGINAL_SOURCE_PATHS_JS_CONTENT_OR_STRINGS_EMITTED=NO")
    print("P56_ORIGINAL_PRODUCTION_STARTUP_ENTRY_PROVEN=NO")
    print("P56_ORIGINAL_READY_PROTOCOL_PROVEN=NO")
    print("P56_ORIGINAL_PRODUCTION_NODE_EXECUTED=NO")
    print("P56_P53_PROXY_WIRED_TO_ORIGINAL_ENGINE=NO")
    print("P56_FIXED_SIGNED_V139=BLOCKED")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("signed_original_v138_apk")
    args = parser.parse_args()
    report(*audit(pathlib.Path(args.signed_original_v138_apk)))
