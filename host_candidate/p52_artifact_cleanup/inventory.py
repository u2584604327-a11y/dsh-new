#!/usr/bin/env python3
"""Repo-only GitHub Actions artifact inventory; never delete by default."""
import collections
import datetime
import json
import pathlib
import sys

def normalized(raw):
    rows=[]
    seen=set()
    for a in raw:
        if not isinstance(a,dict):continue
        artifact_id=a.get("id")
        name=a.get("name","")
        size=a.get("size_in_bytes")
        if not isinstance(artifact_id,int) or artifact_id in seen:
            raise ValueError("INVALID_OR_DUPLICATE_ARTIFACT_ID")
        if not isinstance(size,int) or size<0 or not isinstance(name,str):
            raise ValueError("INVALID_ARTIFACT_METADATA")
        seen.add(artifact_id)
        rows.append({"id":artifact_id,"name":name,"bytes":size,
            "expired":bool(a.get("expired",False)),
            "created_at":str(a.get("created_at","")),
            "expires_at":str(a.get("expires_at","")),
            "run_id":(a.get("workflow_run") or {}).get("id")})
    return rows

def fmt(bytes_count):
    return f"{bytes_count/2**20:.2f} MiB"

def report(rows):
    rows=normalized(rows)
    total=sum(x["bytes"] for x in rows)
    names=collections.Counter(x["name"] for x in rows)
    print("P52_DSH_ACTIONS_ARTIFACT_INVENTORY=PASS_READ_ONLY")
    print(f"P52_DSH_ACTIONS_ARTIFACT_COUNT={len(rows)}")
    print(f"P52_DSH_ACTIONS_ARTIFACT_BYTES={total}")
    print(f"P52_DSH_ACTIONS_ARTIFACT_SIZE_MIB={total/2**20:.2f}")
    print("P52_DELETE_ACTION_PERFORMED=NO")
    print("ARTIFACTS_LARGEST_TOP_25:")
    for a in sorted(rows,key=lambda x:x["bytes"],reverse=True)[:25]:
        print(f" ID={a['id']} size={fmt(a['bytes'])} created={a['created_at']}"
              f" expired={a['expired']} name={a['name'][:100]!r}")
    print("DUPLICATE_NAME_BUCKETS_TOP_30:")
    for name,count in names.most_common(30):
        if count>1:
            total_name=sum(x["bytes"] for x in rows if x["name"]==name)
            print(f" count={count} total={fmt(total_name)} name={name[:100]!r}")
    return len(rows),total

if __name__=="__main__":
    args=sys.argv[1:]
    if len(args)!=1:raise SystemExit("usage: inventory.py JSON")
    data=json.loads(pathlib.Path(args[0]).read_text())
    report(data)
