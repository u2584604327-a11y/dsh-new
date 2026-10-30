#!/usr/bin/env python3
"""P57 synthetic only: register-copy positive, branch/overwrite negatives."""
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from p57_engine_local_dataflow import local_trace, pc_buckets, inspect_methods, invoke_kind

n = 0
def check(value, why):
    global n
    n += 1
    if not value:
        raise AssertionError("P57_SYNTHETIC_" + why)
class I:
    def __init__(self, name, output="", operands=None, off=None):
        self.name, self.output, self.operands, self.off = name, output, operands or [], off
    def get_name(self): return self.name
    def get_output(self): return self.output
    def get_operands(self): return self.operands
    def get_ref_off(self): return self.off
class M:
    def __init__(self, ops, off=3163260):
        self.ops, self.off = ops, off
    def get_name(self): return "invokeSuspend"
    def get_code_off(self): return self.off
    def get_instructions_idx(self): return iter(self.ops)
def reg(k): return (0, k)
def const(k, value):
    return I("const-string", operands=[reg(k), (256, 0, value)])
def move(dest, src):
    return I("move-object", operands=[reg(dest), reg(src)])
def inv(kind, registers=()):
    return I("invoke-virtual", "{v1}, " + kind,
             [reg(k) for k in registers] + [(256, 3, kind)])
JS = "assets/fake_start.js"
READY = "READY"
ASSETS = {JS}
init = "Ljava/lang/ProcessBuilder;-><init>(Ljava/util/List;)V"
start = "Ljava/lang/ProcessBuilder;->start()Ljava/lang/Process;"
equals = "Ljava/lang/String;->equals(Ljava/lang/Object;)Z"
signal = "Ljava/util/concurrent/CountDownLatch;->countDown()V"
thread = "Ljava/lang/Thread;->start()V"
latch = "Ljava/util/concurrent/CountDownLatch;->await()V"
state = "Lkotlinx/coroutines/flow/MutableStateFlow;->setValue(Ljava/lang/Object;)V"
base = [
    (0, const(3, JS)),
    (2, move(4, 3)),
    (4, inv(init, (0, 4))),
    (6, const(5, READY)),
    (8, inv(equals, (6, 5))),
    (10, inv(signal, (1,))),
    (3912, inv(start, (0,))),
    (4010, inv(thread, (7,))),
    (4026, inv(latch, (1,))),
    (4674, inv(state, (8,))),
]
method = M(base)
result = local_trace(method, ASSETS)
check(result["SOURCE_JS_SHAPED"] == 1, "source_js")
check(result["SOURCE_READY_STRING_HINT"] == 1, "source_ready")
check(result["LINEAR_JS_SHAPED_AT_PROCESS_CONSTRUCTOR"] == 1, "direct_register_copy")
check(result["LINEAR_READY_STRING_HINT_AT_STRING_EQUALS"] == 1, "ready_equals")
check("LINEAR_JS_SHAPED_AT_PROCESS_START" not in result, "not_in_start")
near = pc_buckets(method, ASSETS)
check(near["READY_STRING_HINT_NEAR_STRING_EQUALS_LE32"] == 1,
      "near_ready_string_equals")
check(invoke_kind(inv("Lexample/Other;->foo()V", (4,))) is None,
      "unknown_sink")
# Overwrite the copy before constructor.
overwrite = M(base[:2] + [(3, const(4, "not-js"))] + base[2:])
summary = local_trace(overwrite, ASSETS)
check("LINEAR_JS_SHAPED_AT_PROCESS_CONSTRUCTOR" not in summary,
      "overwritten_register_must_not_reach")
# Any branch breaks linear implication across unproven paths.
br = I("if-eqz", operands=[reg(1)], off=3)
branch = M([(0, const(3, JS)), (2, br), (4, move(4, 3)),
            (6, inv(init, (0, 4)))])
brsum = local_trace(branch, ASSETS)
check("LINEAR_JS_SHAPED_AT_PROCESS_CONSTRUCTOR" not in brsum,
      "branch_must_reset")
check(brsum["CONTROL_BOUNDARY_RESET"] == 1, "branch_count")
# Structural baseline drift must fail closed.
try:
    inspect_methods([("Lcom/dsh/android/EngineManager$start$2;", M(base, off=333))],
                    ASSETS)
except ValueError as e:
    check("EXACT_ORIGINAL_ENTRY_DRIFT" in str(e), "code_offset_guard")
else:
    raise AssertionError("unanchored method accepted")
# The positive provenance is a static same-lineage hint only.
check("LINEAR_READY_STRING_HINT_AT_LATCH_SIGNAL" not in result,
      "no_ready_latch_fabrication")
print("P57_LOCAL_REGISTER_SYNTHETIC_TESTS=PASS assertions="+str(n))
print("P57_SYNTHETIC_ONLY_AND_ORIGINAL_STRINGS_EXCLUDED=YES")
