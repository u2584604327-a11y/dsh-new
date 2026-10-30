#!/usr/bin/env python3
"""P74 alter test-compiled P47 Java gate ONLY in disposable P51 CI, never git source."""
import argparse,pathlib
OLD='throw new IOException("P47_ISOLATED_SUPERVISOR_UNAVAILABLE_NO_HOST_FALLBACK");'
NEW='return com.dsh.android.p74.P74OriginalEngineFixtureHandoff.startOrDeny(builder);'
def transform(src,dst):
 original=pathlib.Path(src).read_text("utf-8")
 if original.count(OLD)!=1:
  raise RuntimeError("P74_P47_GATE_UNEXPECTED_SOURCE")
 changed=original.replace(OLD,NEW)
 if changed.replace(NEW,OLD)!=original:
  raise RuntimeError("P74_SCOPE_NOT_ONE_LINE")
 out=pathlib.Path(dst);out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(changed,"utf-8")
 print("P74_DISPOSABLE_P47_GATE_DELEGATES_TO_ONE_SHOT_ISOLATED_PROXY=PASS")
 print("P74_P47_SOURCE_IN_REPOSITORY_UNCHANGED=YES")
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("source");p.add_argument("candidate");a=p.parse_args()
 transform(a.source,a.candidate)
