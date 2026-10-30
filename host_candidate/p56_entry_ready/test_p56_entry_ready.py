#!/usr/bin/env python3
"""P56 synthetic-only contract tests, no original binary or secrets."""
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from p56_engine_entry_ready_slice import categories, instruction_string, asset_list, slice_methods

checks = 0
def verify(value, tag):
    global checks
    checks += 1
    if not value:
        raise AssertionError("P56_SYNTHETIC_FAIL_" + tag)

ASSETS = {"assets/fake_boot.js", "assets/fake_bundle.zip"}
verify("EXACT_APK_ASSET_STRING" in categories("assets/fake_boot.js", ASSETS),
       "exact_asset")
verify("EXACT_APK_ASSET_STRING" not in categories("assets/not_here.js", ASSETS),
       "not_a_match")
verify("READY_STRING_HINT" in categories("READY", ASSETS), "ready_only_hint")
verify(categories("A" * 2000, ASSETS) == (), "oversized_skip")
class Ins:
    def __init__(self, op, content="", operands=None):
        self.op, self.content, self.operands = op, content, operands or []
    def get_name(self): return self.op
    def get_output(self): return self.content
    def get_operands(self): return self.operands
verify(instruction_string(Ins("const-string", operands=[(0, 0), (256, 4, "READY")])) ==
       "READY", "operand_decode")
verify(instruction_string(Ins("invoke-virtual")) is None, "no_nonstring")
class Method:
    def __init__(self, ops, off=3163260):
        self.ops, self.off = ops, off
    def get_name(self): return "invokeSuspend"
    def get_code_off(self): return self.off
    def get_instructions_idx(self): return iter(self.ops)
def invoke(method):
    return Ins("invoke-virtual", "{v0}, " + method)
base = [
    (2900, Ins("const-string", operands=[(0, 0), (256, 1, "assets/fake_boot.js")])),
    (3912, invoke("Ljava/lang/ProcessBuilder;->start()Ljava/lang/Process;")),
    (4010, invoke("Ljava/lang/Thread;->start()V")),
    (4026, invoke("Ljava/util/concurrent/CountDownLatch;->await()V")),
    (4674, invoke("Lkotlinx/coroutines/flow/MutableStateFlow;->setValue(Ljava/lang/Object;)V")),
]
target = Method(base)
result = slice_methods([("Lcom/dsh/android/EngineManager$start$2;",target)], ASSETS)
verify(result["primary_exact_asset_literal_matches"] == 1, "literal_equal_join")
verify(result["primary_process_and_ready_api_counts"]["START"] == 1, "real_spawn_anchor")
verify(result["actual_start_command_proven"] is False, "no_argv_claim")
verify(result["actual_runtime_ready_predicate_proven"] is False, "no_ready_claim")
try:
    drift = Method([(3910, base[1][1])] + base[2:])
    slice_methods([("Lcom/dsh/android/EngineManager$start$2;", drift)], ASSETS)
except ValueError as e:
    verify("PRIMARY_START_DRIFT" in str(e), "spawn_drift_denied")
else:
    raise AssertionError("spawn drift incorrectly allowed")
class Item:
    def __init__(self, filename): self.filename = filename
    def is_dir(self): return False
class Zip:
    def infolist(self):
        return [Item("assets/fake_boot.js"),Item("assets/fake_bundle.zip")]
names,counts = asset_list(Zip())
verify(names == ASSETS and counts["js"] == 1 and counts["zip"] == 1,
       "asset_classification")
print("P56_STATIC_SLICE_SYNTHETIC_TESTS=PASS assertions="+str(checks))
print("P56_SYNTHETIC_TESTS_CONTAIN_ONLY_FAKE_STRINGS=YES")
