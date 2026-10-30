#!/usr/bin/env python3
"""P57: bounded, original v138 DEX JS/READY literal-register and callsite hints.
READ ONLY. Does not evaluate scripts, execute Node, disclose strings/paths,
claim CFG-proven dataflow, patch DEX or grant sandbox permissions.
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
sys.path.insert(0, str(BASE / "p56_entry_ready"))
from p56_engine_entry_ready_slice import (
    audit as audit_p56, asset_list, categories, instruction_string, TARGET,
    CODE_OFF, PC, INVOKE, require
)
MAX_METHODS = 160
MAX_INSTRUCTIONS = 120000
MAX_CALLS = 30000
MAX_STRINGS = 20000
MAX_REGISTERS = 512

# Each label is a literal API interaction, NOT evidence of network or READINESS.
CALL_KINDS = {
    "Ljava/lang/ProcessBuilder;-><init>": "PROCESS_CONSTRUCTOR",
    "Ljava/lang/ProcessBuilder;->command": "PROCESS_COMMAND",
    "Ljava/lang/ProcessBuilder;->start": "PROCESS_START",
    "Ljava/util/ArrayList;->add": "LIST_ADD",
    "Ljava/util/List;->add": "LIST_ADD",
    "Ljava/util/Arrays;->asList": "LIST_AS_LIST",
    "Ljava/lang/StringBuilder;->append": "STRING_APPEND",
    "Ljava/lang/String;->equals": "STRING_EQUALS",
    "Ljava/lang/String;->contains": "STRING_CONTAINS",
    "Ljava/lang/String;->startsWith": "STRING_STARTS_WITH",
    "Ljava/lang/String;->matches": "STRING_MATCHES",
    "Lkotlin/text/StringsKt;->contains": "KOTLIN_CONTAINS",
    "Lkotlin/text/Regex;->containsMatchIn": "KOTLIN_REGEX",
    "Ljava/util/concurrent/CountDownLatch;->countDown": "LATCH_SIGNAL",
    "Ljava/util/concurrent/CountDownLatch;->await": "LATCH_WAIT",
    "Lkotlinx/coroutines/flow/MutableStateFlow;->setValue": "STATEFLOW_SET",
}
HINTS = ("JS_SHAPED", "READY_STRING_HINT", "EXACT_APK_ASSET_STRING")
SINKS = ("PROCESS_CONSTRUCTOR", "PROCESS_COMMAND", "PROCESS_START",
         "LIST_ADD", "LIST_AS_LIST", "STRING_APPEND", "STRING_EQUALS",
         "STRING_CONTAINS", "STRING_STARTS_WITH", "STRING_MATCHES",
         "KOTLIN_CONTAINS", "KOTLIN_REGEX", "LATCH_SIGNAL", "LATCH_WAIT",
         "STATEFLOW_SET")
BOUNDARY_PREFIX = ("if-", "goto", "packed-switch", "sparse-switch",
                   "return", "throw", "monitor-enter", "monitor-exit")
DEST_WRITE_PREFIX = ("const", "new-instance", "new-array", "filled-new-array",
                     "move-result", "move-exception", "iget", "sget", "aget",
                     "instance-of", "array-length", "cmp", "neg", "not",
                     "add-", "sub-", "mul-", "div-", "rem-", "rsub-",
                     "and-", "or-", "xor-", "shl-", "shr-", "ushr-",
                     "int-to-", "long-to-", "float-to-", "double-to-")

def regs(ins):
    """Actual DEX register operands. Do not parse original literal text."""
    result = []
    try:
        parts = ins.get_operands()
    except (AttributeError, ValueError, TypeError):
        return []
    for p in parts:
        if isinstance(p, tuple) and len(p) >= 2 and p[0] == 0 and type(p[1]) is int:
            if 0 <= p[1] < MAX_REGISTERS:
                result.append(p[1])
    return result

def invoke_kind(ins):
    if not ins.get_name().startswith("invoke-"):
        return None
    found = INVOKE.search(ins.get_output())
    if found is None:
        return None
    target = found.group(0)
    for prefix, kind in CALL_KINDS.items():
        if target.startswith(prefix + "("):
            return kind
    # Kotlin generated String helpers may differ across library builds.
    if found.group(1).startswith("Lkotlin/text/StringsKt") and found.group(2) == "contains":
        return "KOTLIN_CONTAINS"
    return None

def group_hint(value, assets):
    cats = set(categories(value, assets))
    # A literal may be both a JS string and an asset match; do not
    # log the literal even when its contents look ordinary.
    return tuple(c for c in HINTS if c in cats)

def pc_buckets(method, assets):
    """PC separation only; same-method proximity is NOT register dataflow."""
    ops = list(method.get_instructions_idx())
    strings = []
    sinks = collections.defaultdict(list)
    for pc, ins in ops:
        if ins.get_name() in ("const-string", "const-string/jumbo"):
            value = instruction_string(ins)
            for cat in group_hint(value, assets):
                strings.append((pc, cat))
        kind = invoke_kind(ins)
        if kind in SINKS:
            sinks[kind].append(pc)
    counters = collections.Counter()
    for pc, cat in strings:
        for kind, pcs in sinks.items():
            d = min(abs(k - pc) for k in pcs)
            band = "LE32" if d <= 32 else "LE128" if d <= 128 else "GT128"
            counters[cat + "_NEAR_" + kind + "_" + band] += 1
    return counters

def local_trace(method, assets):
    """Straight-line register-copy hints; resets at branches and target offsets.
    Not a complete CFG/SSA analysis and cannot prove runtime argv or READY.
    """
    ops = list(method.get_instructions_idx())
    require(len(ops) <= MAX_INSTRUCTIONS, "METHOD_INSTRUCTION_CAP")
    # Conservative jump-target reset where the instruction exposes offset.
    branch_targets = set()
    unresolved_branches = 0
    for pc, ins in ops:
        name = ins.get_name()
        if name.startswith(("if-", "goto")):
            ref = getattr(ins, "get_ref_off", None)
            try:
                delta = ref() if callable(ref) else None
            except (TypeError, ValueError, AttributeError):
                delta = None
            if type(delta) is int and delta != 0:
                branch_targets.add(pc + 2 * delta)
            else:
                unresolved_branches += 1
    taint = {}
    counts = collections.Counter()
    string_total = 0
    invoke_total = 0
    for pc, ins in ops:
        if pc in branch_targets:
            taint.clear()
            counts["JUMP_TARGET_STATE_RESET"] += 1
        name = ins.get_name()
        r = regs(ins)
        if name in ("const-string", "const-string/jumbo"):
            string_total += 1
            require(string_total <= MAX_STRINGS, "STRING_INSTRUCTION_CAP")
            if r:
                tags = group_hint(instruction_string(ins), assets)
                taint.pop(r[0], None)
                if tags:
                    taint[r[0]] = frozenset(tags)
                    for tag in tags:
                        counts["SOURCE_" + tag] += 1
            else:
                counts["CONST_STRING_WITHOUT_REGISTER"] += 1
        elif name.startswith(("move-object", "move/from", "move/16")) and len(r) >= 2:
            # Copy only a known taint. Unknown moves invalidate the dest.
            taint.pop(r[0], None)
            if r[1] in taint:
                taint[r[0]] = taint[r[1]]
        elif name.startswith("move") and len(r) >= 1:
            taint.pop(r[0], None)
        elif name.startswith("invoke-"):
            invoke_total += 1
            require(invoke_total <= MAX_CALLS, "INVOKE_CAP")
            kind = invoke_kind(ins)
            if kind:
                counts["INVOKE_" + kind] += 1
                tags = set().union(*(taint.get(reg, ()) for reg in r))
                for tag in tags:
                    counts["LINEAR_" + tag + "_AT_" + kind] += 1
                if not r:
                    counts["SINK_WITHOUT_DECODED_REGISTERS"] += 1
        elif name.startswith(DEST_WRITE_PREFIX) and r:
            taint.pop(r[0], None)
        if name.startswith(BOUNDARY_PREFIX):
            taint.clear()
            counts["CONTROL_BOUNDARY_RESET"] += 1
        require(len(taint) <= MAX_REGISTERS, "TAINT_REGISTER_CAP")
    counts["UNRESOLVED_BRANCH_OFFSETS"] = unresolved_branches
    counts["KNOWN_BRANCH_TARGETS"] = len(branch_targets)
    return counts

def inspect_methods(methods, assets):
    require(0 < len(methods) <= MAX_METHODS, "FAMILY_METHOD_LIMIT")
    primary = [m for cls, m in methods if cls == TARGET and m.get_name() == "invokeSuspend"]
    require(len(primary) == 1 and primary[0].get_code_off() == CODE_OFF,
            "EXACT_ORIGINAL_ENTRY_DRIFT")
    total = collections.Counter()
    proximity = collections.Counter()
    for cls, method in methods:
        local = local_trace(method, assets)
        near = pc_buckets(method, assets)
        total.update(local)
        proximity.update(near)
    # Reconfirm unique primary ProcessBuilder.start anchor from original DEX.
    starts = [(pc, invoke_kind(ins)) for pc, ins in primary[0].get_instructions_idx()
              if invoke_kind(ins) == "PROCESS_START"]
    require(starts == [(PC, "PROCESS_START")], "PRIMARY_SPAWN_ANCHOR_DRIFT")
    return {
        "start_family_method_count": len(methods),
        "bounded_local_register_counters": dict(sorted(total.items())),
        "within_method_pc_proximity_counters": dict(sorted(proximity.items())),
        "script_to_process_constructor_confirmed": False,
        "ready_literal_controls_latch_or_stateflow_confirmed": False,
        "complete_cfg_and_coroutine_dataflow": False,
        "live_original_engine_ready": False,
    }

def audit(original):
    counts, p56 = audit_p56(original)
    require(p56["start_family_methods"] == 9, "P56_METHOD_COUNT_DRIFT")
    with zipfile.ZipFile(original) as z:
        assets, _ = asset_list(z)
        dex = DEX(z.read("classes.dex"))
        methods = []
        for cls in dex.get_classes():
            name = cls.get_name()
            if name != TARGET and not name.startswith(TARGET[:-1] + "$"):
                continue
            for m in cls.get_methods():
                if m.get_code() is not None:
                    methods.append((name, m))
    data = inspect_methods(methods, assets)
    require(data["start_family_method_count"] == 9,
            "P56_ORIGINAL_NESTED_CALLBACK_FAMILY_DRIFT")
    return data

def print_report(r):
    print("P57_P56_EXACT_SIGNED_V138_AND_FULL_TAR_HASH=PASS")
    print("P57_PRIMARY_ENGINE_SPAWN_OFFSET=PASS")
    print("P57_START_FAMILY_METHODS=" + str(r["start_family_method_count"]))
    for key in ("bounded_local_register_counters", "within_method_pc_proximity_counters"):
        print("P57_" + key.upper() + "=" + json.dumps(
            r[key], sort_keys=True, separators=(",", ":")))
    print("P57_ORIGINAL_JS_PATH_AND_READY_LITERAL_CONTENTS_PRINTED=NO")
    print("P57_DIRECT_LOCAL_REGISTER_HINTS_NOT_FULL_CFG=YES")
    print("P57_EXECUTABLE_PRODUCTION_SCRIPT_RESOLVED=NO")
    print("P57_RUNTIME_READY_CONDITION_PROVED=NO")
    print("P57_P53_PROCESS_PROXY_CONNECTED=NO")
    print("P57_PRODUCTION_SCRIPTS_EXECUTED=NO")
    print("P57_FIXED_SIGNED_V139=BLOCKED")

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("signed_original_v138_apk")
    args = p.parse_args()
    print_report(audit(pathlib.Path(args.signed_original_v138_apk)))
