#!/usr/bin/env python3
"""P58 exact signed-v138 startup: bounded, conservative local object flow.

Read-only DEX analysis. No source strings, original paths, argv, env, code,
application data or original bytes are printed/persisted. No JS/ELF execution.
Object tags are only *within branch-free, same-method* structural witnesses.
No claim of complete CFG, process argv, READY, callbacks or runtime execution.
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

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "p57_engine_local_dataflow"))
from p57_engine_local_dataflow import audit as audit_p57, group_hint, regs
from p57_engine_local_dataflow import invoke_kind, TARGET, CODE_OFF, PC
sys.path.insert(0, str(ROOT / "p56_entry_ready"))
from p56_engine_entry_ready_slice import asset_list, require, INVOKE

MAX_METHODS = 160
MAX_INSTRUCTIONS = 120000
MAX_HEAP_OBJECTS = 4000
MAX_COUNTER = 100000
TAGS = {"JS_SHAPED", "READY_STRING_HINT", "EXACT_APK_ASSET_STRING"}
BUILDER_CLASSES = ("Ljava/lang/StringBuilder;", "Ljava/lang/StringBuffer;")
LIST_CLASSES = ("Ljava/util/ArrayList;", "Ljava/util/List;")
ARRAY_FACTORIES = ("Ljava/util/Arrays;",)
KNOWN_FACTORY = ("Lkotlin/collections/CollectionsKt", "Lkotlin/collections/CollectionsKt__")
RE_BRANCH = ("if-", "goto", "packed-switch", "sparse-switch",
             "return", "throw", "monitor-enter", "monitor-exit")
DEST_WRITE = ("const", "new-instance", "new-array", "filled-new-array",
              "move-result", "move-exception", "iget", "sget", "aget",
              "instance-of", "array-length", "cmp", "neg", "not",
              "add-", "sub-", "mul-", "div-", "rem-", "rsub-",
              "and-", "or-", "xor-", "shl-", "shr-", "ushr-",
              "int-to-", "long-to-", "float-to-", "double-to-")
RE_TYPE = re.compile(r"(L[A-Za-z0-9_/$]+;)")
RE_RANGE = re.compile(r"^(?:move-object|move/from|move/16|move-object/from16|move-object/16)$")

def method_call(ins):
    if not ins.get_name().startswith("invoke-"):
        return (None, None)
    m = INVOKE.search(ins.get_output())
    return (m.group(1), m.group(2)) if m else (None, None)

def kind_of_new(ins):
    if ins.get_name() == "new-instance":
        t = RE_TYPE.search(ins.get_output())
        if t:
            if t.group(1) in BUILDER_CLASSES:
                return "BUILDER"
            if t.group(1) == "Ljava/util/ArrayList;":
                return "LIST"
    if ins.get_name() in ("new-array", "filled-new-array",
                          "filled-new-array/range"):
        return "ARRAY"
    return None

def safe_static_branch_targets(ops):
    targets = set()
    unknown = 0
    for pc, ins in ops:
        name = ins.get_name()
        if name.startswith(("if-", "goto")):
            fn = getattr(ins, "get_ref_off", None)
            try:
                off = fn() if callable(fn) else None
            except (ValueError, TypeError, AttributeError):
                off = None
            if type(off) is int and off:
                targets.add(pc + 2 * off)
            else:
                unknown += 1
        # Switch payload dataflow and exception handler edges are not
        # resolved here. Treat every switch as an opaque barrier.
    return targets, unknown

def simulate(method, assets):
    ops = list(method.get_instructions_idx())
    require(len(ops) <= MAX_INSTRUCTIONS, "INSTRUCTION_LIMIT")
    jump_targets, unresolved = safe_static_branch_targets(ops)
    counts = collections.Counter()
    regmap = {}           # r -> ("STRING",frozenset) or ("OBJECT",object_id)
    heap = {}             # id -> {"kind": category, "tags": frozenset}
    next_id = 1
    pending = None        # only consumed by immediately following move-result
    last_compare = None   # ("READY" tag set), consumed by move-result
    total_created = 0

    def tags(value):
        if value is None:
            return frozenset()
        if value[0] == "STRING":
            return value[1]
        if value[0] == "OBJECT" and value[1] in heap:
            return heap[value[1]]["tags"]
        return frozenset()

    def allocate(kind, source=frozenset()):
        nonlocal next_id, total_created
        total_created += 1
        require(total_created <= MAX_HEAP_OBJECTS, "OBJECT_LIMIT")
        oid = next_id
        next_id += 1
        heap[oid] = {"kind": kind, "tags": frozenset(source)}
        return ("OBJECT", oid)

    def clear():
        regmap.clear()
        heap.clear()

    for pc, ins in ops:
        name = ins.get_name()
        r = regs(ins)
        if pc in jump_targets:
            clear()
            pending = None
            last_compare = None
            counts["TARGET_STATE_KILLED"] += 1
        if name.startswith("move-result"):
            if r:
                regmap.pop(r[0], None)
                if pending is not None:
                    regmap[r[0]] = pending
                    counts["RESULT_PROVENANCE_CARRIED"] += 1
                    if last_compare and "READY_STRING_HINT" in last_compare:
                        counts["READY_COMPARE_RESULT_REGISTER"] += 1
            pending = None
            last_compare = None
            continue
        pending = None
        last_compare = None
        if name in ("const-string", "const-string/jumbo"):
            if r:
                from p56_engine_entry_ready_slice import instruction_string
                v = instruction_string(ins)
                hint = frozenset(t for t in group_hint(v, assets) if t in TAGS)
                regmap.pop(r[0], None)
                if hint:
                    regmap[r[0]] = ("STRING", hint)
                    for tag in hint:
                        counts["ORIGINAL_LITERAL_" + tag] += 1
            else:
                counts["UNDECODED_LITERAL_REGISTER"] += 1
        elif RE_RANGE.match(name) and len(r) >= 2:
            regmap.pop(r[0], None)
            if r[1] in regmap:
                regmap[r[0]] = regmap[r[1]]
        elif name == "move-object" and len(r) >= 2:
            regmap.pop(r[0], None)
            if r[1] in regmap:
                regmap[r[0]] = regmap[r[1]]
        elif name.startswith("new-instance") and r:
            kind = kind_of_new(ins)
            regmap.pop(r[0], None)
            if kind:
                regmap[r[0]] = allocate(kind)
                counts["NEW_" + kind] += 1
        elif name.startswith("new-array") and r:
            regmap.pop(r[0], None)
            regmap[r[0]] = allocate("ARRAY")
            counts["NEW_ARRAY"] += 1
        elif name.startswith("aput-object") and len(r) >= 3:
            src, arr = regmap.get(r[0]), regmap.get(r[2])
            if arr and arr[0] == "OBJECT" and arr[1] in heap:
                obj = heap[arr[1]]
                if obj["kind"] == "ARRAY":
                    obj["tags"] |= tags(src)
                    if tags(src):
                        counts["TAGGED_ARRAY_STORE"] += 1
        elif name.startswith("invoke-"):
            cls, method_name = method_call(ins)
            counts["CALLS_SEEN"] += 1
            if cls is None:
                counts["INVOKE_UNDECODED"] += 1
                clear()
                continue
            arg_values = [regmap.get(k) for k in r]
            arg_tags = [tags(v) for v in arg_values]
            receiver = arg_values[0] if arg_values else None
            obj = heap.get(receiver[1]) if receiver and receiver[0] == "OBJECT" else None
            union_arg = frozenset().union(*arg_tags[1:]) if len(arg_tags) > 1 else frozenset()
            # Preserve receiver aliases only when the invoked API is fully
            # whitelisted; an unknown method might mutate the object.
            known = False
            if cls in BUILDER_CLASSES and obj and obj["kind"] == "BUILDER":
                if method_name == "<init>":
                    obj["tags"] |= union_arg
                    known = True
                elif method_name == "append":
                    obj["tags"] |= union_arg
                    pending = receiver
                    known = True
                    counts["BUILDER_APPEND_CALLS"] += 1
                    for tag in union_arg:
                        counts["BUILDER_APPEND_SOURCE_" + tag] += 1
                elif method_name == "toString":
                    pending = ("STRING", obj["tags"])
                    known = True
                    counts["BUILDER_TOSTRING_CALLS"] += 1
                    for tag in obj["tags"]:
                        counts["BUILDER_TOSTRING_TAGGED_" + tag] += 1
            elif cls in LIST_CLASSES and obj and obj["kind"] == "LIST":
                if method_name == "<init>":
                    obj["tags"] |= union_arg
                    known = True
                elif method_name == "add":
                    obj["tags"] |= union_arg
                    known = True
                    counts["LIST_ADD_CALLS"] += 1
                    for tag in union_arg:
                        counts["LIST_ADD_SOURCE_" + tag] += 1
            elif cls in ARRAY_FACTORIES and method_name == "asList":
                pending = allocate("LIST", frozenset().union(*arg_tags))
                known = True
                counts["ARRAY_TO_LIST_CALLS"] += 1
            elif (cls and cls.startswith(KNOWN_FACTORY) and
                  method_name in ("listOf", "mutableListOf", "arrayListOf")):
                pending = allocate("LIST", frozenset().union(*arg_tags))
                known = True
                counts["KOTLIN_LIST_FACTORY_CALLS"] += 1
            elif cls == "Ljava/lang/ProcessBuilder;" and method_name in ("<init>", "command"):
                known = True
                counts["PROCESS_" + ("CTOR" if method_name == "<init>" else "COMMAND") + "_CALLS"] += 1
                # Only actual invoke argument tags, not nearby literals or
                # shared object names, can count as this local witness.
                for tag in union_arg:
                    counts["PROCESS_ARG_LOCAL_TAG_" + tag] += 1
                if not r:
                    counts["PROCESS_ARG_REGISTERS_UNDECODED"] += 1
            elif cls == "Ljava/lang/String;" and method_name in ("equals", "contains", "startsWith", "matches"):
                known = True
                if "READY_STRING_HINT" in frozenset().union(*arg_tags):
                    counts["READY_LITERAL_AT_STRING_COMPARE"] += 1
                    last_compare = frozenset().union(*arg_tags)
                    # Comparison returns boolean, not object; track the
                    # following move-result as a categorical fact only.
                    pending = ("STRING", last_compare)
            elif cls == "Lkotlinx/coroutines/flow/MutableStateFlow;" and method_name == "setValue":
                known = True
                if "READY_STRING_HINT" in union_arg:
                    counts["READY_LITERAL_AS_STATEFLOW_ARGUMENT"] += 1
            elif cls == "Ljava/util/concurrent/CountDownLatch;" and method_name == "countDown":
                known = True
                counts["LATCH_SIGNAL_CALLS"] += 1
            elif cls == "Ljava/lang/ProcessBuilder;" and method_name == "start":
                known = True
                counts["PROCESS_START_CALLS"] += 1
            if not known:
                # Invalidate object provenance if an opaque invocation
                # receives it. Does not fabricate writes or proof of safety.
                for value in arg_values:
                    if value and value[0] == "OBJECT" and value[1] in heap:
                        heap.pop(value[1], None)
                        counts["OPAQUE_OBJECT_INVALIDATION"] += 1
        elif name.startswith(DEST_WRITE) and r:
            regmap.pop(r[0], None)

        if name.startswith("if-"):
            if any("READY_STRING_HINT" in tags(regmap.get(k)) for k in r):
                counts["READY_TAG_NEAR_CONDITIONAL_DIRECT"] += 1
        if name.startswith(RE_BRANCH):
            clear()
            pending = None
            last_compare = None
            counts["CONTROL_FLOW_KILL"] += 1
        require(len(regmap) <= 512, "REGMAP_SIZE_CAP")

    counts["BRANCH_TARGETS_SEEN"] = len(jump_targets)
    counts["UNRESOLVED_BRANCH_TARGETS"] = unresolved
    return counts

def audit(original):
    prev = audit_p57(original)
    require(prev["start_family_method_count"] == 9, "P57_PRECONDITION_DRIFT")
    with zipfile.ZipFile(original) as z:
        assets, _ = asset_list(z)
        dex = DEX(z.read("classes.dex"))
        methods = []
        for klass in dex.get_classes():
            name = klass.get_name()
            if name != TARGET and not name.startswith(TARGET[:-1] + "$"):
                continue
            for method in klass.get_methods():
                if method.get_code():
                    methods.append((name, method))
    require(len(methods) == 9, "START_FAMILY_COUNT_DRIFT")
    target = [m for n,m in methods if n == TARGET and m.get_name() == "invokeSuspend"]
    require(len(target) == 1 and target[0].get_code_off() == CODE_OFF,
            "EXACT_COROUTINE_ANCHOR_DRIFT")
    starts = [(pc, invoke_kind(i)) for pc,i in target[0].get_instructions_idx()
              if invoke_kind(i) == "PROCESS_START"]
    require(starts == [(PC,"PROCESS_START")], "EXACT_PROCESS_START_DRIFT")
    result = collections.Counter()
    for _, method in methods:
        result.update(simulate(method, assets))
    return result

def report(r):
    print("P58_PINNED_P57_P56_P54_V138_CHAIN=PASS")
    print("P58_ORIGINAL_ENGINE_PROCESS_SPAWN_ANCHOR=PASS")
    print("P58_LOCAL_OBJECT_FLOW_COUNTS="+json.dumps(dict(sorted(r.items())),
                                                    sort_keys=True, separators=(",", ":")))
    print("P58_DIRECT_OBJECT_FLOW_ONLY_NOT_CFG_SSA=YES")
    print("P58_ORIGINAL_ARGV_VALUES_AND_JS_PATHS_EMITTED=NO")
    print("P58_ORIGINAL_SCRIPT_ENTRY_PROVEN=NO")
    print("P58_READY_SIGNAL_CONDITION_PROVEN=NO")
    print("P58_REAL_NODE_PRODUCTION_SCRIPT_EXECUTED=NO")
    print("P58_ORIGINAL_DSH_P53_PROCESS_PROXY_WIRED=NO")
    print("P58_SIGNED_V139_APK=BLOCKED")

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("original_signed_v138")
    a = p.parse_args()
    report(audit(pathlib.Path(a.original_signed_v138)))
