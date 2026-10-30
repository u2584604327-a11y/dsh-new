#!/usr/bin/env python3
"""P49: embed SHA-pinned original v138 ARM64 Node + dependency ELF in the
ephemeral *original DSH APK*, without executing them or shipping an APK.

This does not expose or rewrite original app-private runtime directories.
"""
import argparse
import hashlib
import json
import pathlib
import struct
import subprocess
import sys
import zipfile

ORIGINAL_APK_SHA="3ca56655d79afc57431636e340823e7071bc830615ca615c485b0b9a30b6e3e5"
NODE_SHA="a0d21a1589312919114b24a5cc520c30ab7f26f9985b3f0c643c153172ebd1e6"
NODE="libdshnode_p21_exec.so"
LOCK_PATH="assets/p49-original-node-lock.json"
MAX_APK=512*1024*1024
BASE=pathlib.Path(__file__).resolve().parent

def fail(condition,why):
    if not condition:raise RuntimeError("P49_BLOCKED_"+why)
def hash_bytes(blob):
    return hashlib.sha256(blob).hexdigest()
def hash_file(path):
    h=hashlib.sha256()
    with pathlib.Path(path).open("rb") as handle:
        for block in iter(lambda:handle.read(65536),b""):
            h.update(block)
    return h.hexdigest()
def run(*args):
    subprocess.run([sys.executable,*map(str,args)],check=True,timeout=120)

def prepare(original,stage):
    original=pathlib.Path(original)
    stage=pathlib.Path(stage)
    fail(original.is_file() and original.stat().st_size==147341486,"BAD_ORIGINAL_SIZE")
    fail(hash_file(original)==ORIGINAL_APK_SHA,"SIGNED_V138_SOURCE_IDENTITY_CHANGED")
    fail(not stage.exists() or not any(stage.iterdir()),"NONEMPTY_STAGE_DIRECTORY")
    stage.mkdir(parents=True,exist_ok=True)
    first=stage/"p21";final=stage/"native";report=stage/"p25.json"
    run(BASE/"p21_real_arm64_loader_pack.py",original,
        "--out-native-dir",first,"--report",stage/"p21.json")
    run(BASE/"p25_original_node_alias_stager.py",
        "--p21-native-dir",first,"--out-native-dir",final,"--report",report)
    run(BASE/"p28_device_probe/emit_runtime_lock.py",
        "--p25-report",report,"--native-dir",final,
        "--out",stage/"p49-original-node-lock.json")
    lock=json.loads((stage/"p49-original-node-lock.json").read_text())
    fail(lock["source_apk_sha256"]==ORIGINAL_APK_SHA and
         lock["node_sha256"]==NODE_SHA and
         lock["gate"]=="P28_EXACT_V138_NODE_SHA_PIN","RUNTIME_LOCK_DRIFT")
    fail(len(lock["libs"])==10 and len(lock["preload"])==6,"LOCK_COUNTS_DRIFT")
    names={p.name for p in final.iterdir() if p.is_file()}
    expected={NODE}|{v["alias"] for v in lock["libs"]}
    fail(names==expected and len(names)==11,"REAL_ELF_SET_MISMATCH")
    fail(hash_file(final/NODE)==NODE_SHA,"NODE_BYTES_DRIFT")
    for lib in lock["libs"]:
        fail(hash_file(final/lib["alias"])==lib["sha256"],"LIBRARY_BYTES_DRIFT")
    print("P49_EXACT_ORIGINAL_NODE_ELF_SHA256=PASS")
    print("P49_ORIGINAL_TEN_ELF_DEPENDENCIES=PASS")
    print("P49_OWNED_ORIGINAL_V138_SOURCE=UNCHANGED")

def embed(candidate,stage):
    candidate=pathlib.Path(candidate)
    stage=pathlib.Path(stage)
    final=stage/"native"
    lock=json.loads((stage/"p49-original-node-lock.json").read_text())
    expected={NODE}|{v["alias"] for v in lock["libs"]}
    fail(candidate.is_file() and candidate.stat().st_size<MAX_APK,"BAD_CANDIDATE")
    fail({p.name for p in final.iterdir()}==expected,"STAGE_ELF_SET_DRIFT")
    names={"lib/arm64-v8a/"+name for name in expected}|{LOCK_PATH}
    with zipfile.ZipFile(candidate,"a",allowZip64=True) as z:
        current=z.namelist()
        fail(len(current)==len(set(current)),"DUPLICATE_BASE_MEMBERS")
        fail(not names.intersection(current),"COLLISION_WITH_ORIGINAL_PACKAGE")
        for name in sorted(expected):
            file=final/name
            fail(file.stat().st_size<128*1024*1024,"OVERSIZE_NATIVE_FILE")
            z.write(file,"lib/arm64-v8a/"+name,compress_type=zipfile.ZIP_STORED)
        z.write(stage/"p49-original-node-lock.json",LOCK_PATH,
                compress_type=zipfile.ZIP_DEFLATED)
    fail(candidate.stat().st_size<MAX_APK,"PACKAGED_APK_TOO_LARGE")
    print("P49_EXACT_ARM64_NODE_AND_10_LIBS_ADDED_TO_REAL_ORIGINAL_APK=PASS_STATIC")
    print("P49_ORIGINAL_ARM64_NODE_NOT_EXECUTED=YES")

def data_offset(apk,entry):
    with pathlib.Path(apk).open("rb") as f:
        f.seek(entry.header_offset)
        raw=f.read(30)
    fail(len(raw)==30 and raw[:4]==b"PK\x03\x04","BAD_ZIP_LOCAL_HEADER")
    fields=struct.unpack("<IHHHHHIIIHH",raw)
    return entry.header_offset+30+fields[-2]+fields[-1]

def verify(original,apk):
    original=pathlib.Path(original);apk=pathlib.Path(apk)
    fail(hash_file(original)==ORIGINAL_APK_SHA,"ORIGINAL_SHA_AFTER_STAGE_DRIFT")
    with zipfile.ZipFile(original) as orig,zipfile.ZipFile(apk) as derived:
        base={x.filename:hash_bytes(orig.read(x.filename))
              for x in orig.infolist() if x.filename.startswith(("lib/","assets/"))
              and not x.is_dir()}
        allnames=derived.namelist()
        fail(len(allnames)==len(set(allnames)),"DUPLICATE_OUTPUT_MEMBERS")
        fail(all(x in allnames and hash_bytes(derived.read(x))==digest
                 for x,digest in base.items()),"ORIGINAL_ASSETS_LIB_SHA_DRIFT")
        fail(LOCK_PATH in allnames and LOCK_PATH not in base,"STAGE_LOCK_MISSING")
        lock=json.loads(derived.read(LOCK_PATH))
        fail(lock["source_apk_sha256"]==ORIGINAL_APK_SHA and
             lock["node_sha256"]==NODE_SHA and
             lock["gate"]=="P28_EXACT_V138_NODE_SHA_PIN" and
             lock["runtime_node_execve"]=="NOT_TESTED_BUILD_ONLY" and
             lock["release"]=="BLOCKED","LOCK_CONTENT_DRIFT")
        fail(len(lock["libs"])==10 and len(lock["preload"])==6,"LOCK_LIBRARY_COUNT_DRIFT")
        required={"lib/arm64-v8a/"+NODE:NODE_SHA}
        for lib in lock["libs"]:
            alias=lib["alias"]
            fail(alias.startswith("lib") and alias.endswith(".so") and
                 "/" not in alias and ".." not in alias,"INVALID_ALIAS")
            required["lib/arm64-v8a/"+alias]=lib["sha256"]
        fail(len(required)==11,"REQUIRED_ELF_COUNT")
        installed={x for x in allnames if x.startswith("lib/arm64-v8a/") and
                   x not in base and not x.endswith("/")}
        fail(installed==set(required),"ADDITIONAL_ARM64_LIB_SET_CHANGED")
        fail({x for x in allnames if x.startswith(("lib/","assets/")) and
              x not in base and not x.endswith("/")}==
             set(required)|{LOCK_PATH},"UNAUTHORIZED_EXTRA_ASSET_OR_LIB")
        for name,digest in required.items():
            e=derived.getinfo(name)
            fail(e.compress_type==zipfile.ZIP_STORED,"NATIVE_ELF_COMPRESSED")
            fail(data_offset(apk,e)%16384==0,"NATIVE_ELF_NOT_16K_ZIP_ALIGNED")
            payload=derived.read(name)
            fail(hash_bytes(payload)==digest,"ORIGINAL_ELF_REWRITTEN")
            fail(payload[:4]==b"\x7fELF" and
                 int.from_bytes(payload[18:20],"little")==183,"NOT_ARM64_ELF")
        fail(derived.read(LOCK_PATH).endswith(b"\n"),"LOCK_NOT_FINAL_NEWLINE")
    print("P49_REAL_ORIGINAL_DSH_ASSETS_AND_LIBRARIES_BYTE_PRESERVED=PASS")
    print("P49_11_ADDITIONAL_ARM64_ELF_STORED_16K_AND_SHA=PASS")
    print("P49_ORIGINAL_NODE_SOURCE_SHA256_MATCH=PASS")
    print("P49_EXTRA_APK_MEMBERS_ALLOWLIST=PASS")
    print("P49_REAL_NODE_EXECUTED_IN_ORIGINAL_APK=NO")
    print("P49_V139_RELEASE=BLOCKED")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("mode",choices=["prepare","embed","verify"])
    p.add_argument("a");p.add_argument("b")
    args=p.parse_args()
    if args.mode=="prepare":prepare(args.a,args.b)
    elif args.mode=="embed":embed(args.a,args.b)
    else:verify(args.a,args.b)
