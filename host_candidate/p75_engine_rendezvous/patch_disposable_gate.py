#!/usr/bin/env python3
"""P75 changes ONLY P74's disposable scratch P47 gate delegation."""
import argparse,pathlib
OLD="return com.dsh.android.p74.P74OriginalEngineFixtureHandoff.startOrDeny(builder);"
NEW="return com.dsh.android.p75.P75EngineStartRendezvous.startOrDeny(builder);"
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("scratch_gate");a=p.parse_args()
 file=pathlib.Path(a.scratch_gate)
 source=file.read_text()
 if source.count(OLD)!=1 or NEW in source:
  raise RuntimeError("P75_TEST_GATE_PREIMAGE_MISMATCH")
 after=source.replace(OLD,NEW)
 if after.replace(NEW,OLD)!=source:raise RuntimeError("P75_SCOPE_EXCEEDED")
 file.write_text(after)
 print("P75_ONLY_TEST_P47_GATE_DELEGATES_TO_CROSS_THREAD_RENDEZVOUS=PASS")
