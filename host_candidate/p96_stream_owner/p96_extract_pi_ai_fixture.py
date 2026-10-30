#!/usr/bin/env python3
"""Prepare minimal on-runner original pi-ai dependencies for synthetic SSE E2E.

Exact original signed APK hash check; extract only package manager JS/JSON
files into ephemeral private CI workspace. Do not commit/archive extracted
original code or run Android original app. Hard limits prevent tar abuse.
"""
import argparse
import gzip
import io
import json
import os
import pathlib
import re
import tarfile
import zipfile
from p96_original_engine_owner import SOURCE_BYTES, SOURCE_SHA, file_hash, require

BASE_PACKAGES = ("@earendil-works/pi-ai",)
MAX_FILES = 7000
MAX_PACKAGE_GRAPH = 100
INCLUDE_PRESENT_PEERS = False
MAX_BYTES = 120 * 1024 * 1024
MAX_MEMBER = 8 * 1024 * 1024
EXTENSIONS = (".js", ".cjs", ".mjs", ".json")
SCOPE = "node_modules/"
NAME = re.compile(r"^[A-Za-z0-9._@+/-]{1,240}$")

def package_name(path):
    if not path.startswith(SCOPE):return None
    rest=path[len(SCOPE):].split("/")
    if rest[0].startswith("@") and len(rest)>=3:
        return "/".join(rest[:2])
    if len(rest)>=2:
        return rest[0]
    return None

def audit_extract(apk, out):
    require(apk.stat().st_size==SOURCE_BYTES, "APK_SIZE_CHANGED")
    require(file_hash(apk)==SOURCE_SHA, "APK_SHA_CHANGED")
    require(not out.exists(), "DESTINATION_EXISTS")
    out.mkdir(mode=0o700,parents=True)
    with zipfile.ZipFile(apk) as z:
        require(z.testzip() is None,"APK_CRC")
        raw=z.read("assets/engine.bin")
    require(raw[:2]==b"\x1f\x8b", "ENGINE_FORMAT")
    # First pass obtains only small package manifests for closure selection.
    packages={}
    def iterate(raw):
        return tarfile.open(fileobj=gzip.GzipFile(fileobj=io.BytesIO(raw)),mode="r|")
    count=0
    with iterate(raw) as tar:
        for item in tar:
            count+=1
            require(count<=50000,"TOO_MANY_TAR_MEMBERS")
            if not item.isfile() or not item.name.endswith("/package.json"):continue
            name=item.name
            if not name.startswith(SCOPE) or not NAME.fullmatch(name):continue
            pkg=package_name(name)
            if not pkg or name!=SCOPE+pkg+"/package.json":continue
            if item.size>256*1024:continue
            f=tar.extractfile(item)
            if f is None:continue
            try:
                m=json.loads(f.read(256*1024).decode("utf-8"))
            except (ValueError,UnicodeDecodeError):continue
            if isinstance(m,dict):
                packages[pkg]=m
    # Transitive first-party pi-ai dependencies, excluding optional and peer
    # libraries that do not participate in the OpenAI Completions transport.
    needed=set(BASE_PACKAGES)
    frontier=list(BASE_PACKAGES)
    while frontier:
        pkg=frontier.pop()
        manifest=packages.get(pkg,{})
        # First-party DSH's peer-declared Cordis services must also be
        # present when probing the actual original AgentLoop/ToolRuntime.
        dependencies=dict(manifest.get("dependencies",{}))
        if INCLUDE_PRESENT_PEERS:
            dependencies.update({
                name: value for name, value in manifest.get("peerDependencies",{}).items()
                if name in packages
            })
        for dep in dependencies:
            if dep not in needed:
                needed.add(dep);frontier.append(dep)
        require(len(needed)<=MAX_PACKAGE_GRAPH,"DEPENDENCY_GRAPH_TOO_WIDE")
    missing=sorted(x for x in needed if x not in packages)
    # Presence check rather than reaching the internet to npm install.
    require(not missing, "ORIGINAL_DEPENDENCY_PACKAGE_MISSING")
    extracted=0
    nbytes=0
    with iterate(raw) as tar:
        for item in tar:
            if not item.isfile():continue
            name=item.name
            if not NAME.fullmatch(name):continue
            pkg=package_name(name)
            if pkg not in needed:continue
            if not name.endswith(EXTENSIONS):continue
            require(item.size<=MAX_MEMBER, "DEPENDENCY_MEMBER_TOO_LARGE")
            require(extracted<MAX_FILES,"FILE_COUNT_EXCEEDED")
            require(nbytes+item.size<=MAX_BYTES, "BYTE_BUDGET_EXCEEDED")
            dest=out/name
            require(out.resolve() in dest.resolve().parents,"PATH_ESCAPE")
            dest.parent.mkdir(parents=True,exist_ok=True)
            # Exclusive new file; no symlinks and no overwrite.
            with dest.open("xb") as f:
                stream=tar.extractfile(item)
                require(stream is not None,"SOURCE_MISSING")
                b=stream.read(MAX_MEMBER+1)
                require(len(b)==item.size,"SOURCE_TRUNCATED")
                f.write(b)
            nbytes+=item.size;extracted+=1
    require(extracted>0 and (out/"node_modules/@earendil-works/pi-ai/package.json").is_file(),
            "PI_AI_PACKAGE_MISSING")
    print("P96_EXACT_ORIGINAL_PI_AI_ISOLATED_FIXTURE=PASS")
    print("P96_ORIGINAL_PACKAGE_CLOSURE_COUNT="+str(len(needed)))
    print("P96_SYNTHETIC_MODULE_COUNT="+str(extracted))
    print("P96_SYNTHETIC_MODULE_BYTES="+str(nbytes))
    print("P96_ORIGINAL_SOURCE_MODIFIED=NO")
if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--original",required=True)
    a.add_argument("--out",required=True)
    args=a.parse_args()
    audit_extract(pathlib.Path(args.original),pathlib.Path(args.out))
