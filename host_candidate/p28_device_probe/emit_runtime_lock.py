#!/usr/bin/env python3
"""P28 generate Android-on-device SHA lock from exact P25 original 11 ARM64 ELF.

The JSON is embedded in the locally signed test APK. Original binaries,
entire signed v138 APK and private signing materials are NEVER logged.
"""
import argparse, hashlib, json, pathlib, re

APK_SHA="3ca56655d79afc57431636e340823e7071bc830615ca615c485b0b9a30b6e3e5"
NODE_SHA="a0d21a1589312919114b24a5cc520c30ab7f26f9985b3f0c643c153172ebd1e6"
NODE="libdshnode_p21_exec.so"

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--p25-report",required=True)
    parser.add_argument("--native-dir",required=True)
    parser.add_argument("--out",required=True)
    args=parser.parse_args()
    root=pathlib.Path(args.native_dir)
    report=json.loads(pathlib.Path(args.p25_report).read_text())
    expected=report["original_library_sha256"]
    aliases=report["soname_to_installer_filename"]
    ordered=report["preload_dependency_first_order_versioned"]
    if report["original_node_sha256"]!=NODE_SHA:
        raise ValueError("NODE_SOURCE_IDENTITY_CHANGED")
    if report["original_missing_soname_exception"]!=["libsqlite3.so"]:
        raise ValueError("ORIGINAL_SQLITE_EXCEPTION_CHANGED")
    if report["original_libsqlite3_filename_fallback_runtime"]!="NOT_TESTED":
        raise ValueError("FALSE_SQLITE_RUNTIME_PASS")
    if len(aliases)!=10 or len(expected)!=10 or len(ordered)!=6:
        raise ValueError("UNEXPECTED_ORIGINAL_DEPENDENCY_GRAPH")
    if set(aliases)!=set(expected) or len(set(aliases.values()))!=10:
        raise ValueError("INVALID_UNIQUE_DEPENDENCY_NAMES")
    def hash_file(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    if hash_file(root/NODE)!=NODE_SHA:
        raise ValueError("ORIGINAL_NODE_SHA_CHANGED_BEFORE_APP_PACKAGING")
    entries=[]
    for original,alias in sorted(aliases.items()):
        if not re.fullmatch(r"lib[A-Za-z0-9_.+-]{1,70}\.so",alias) or ".." in alias:
            raise ValueError("INVALID_INSTALLER_LIBRARY_ALIAS")
        if hash_file(root/alias)!=expected[original]:
            raise ValueError("ORIGINAL_LIBRARY_BYTES_CHANGED")
        entries.append({"alias":alias,"sha256":expected[original]})
    preload=[]
    for original in ordered:
        if original not in aliases or original.endswith(".so"):
            raise ValueError("INVALID_VERSIONED_PRELOAD_SONAME")
        preload.append(aliases[original])
    if len(set(preload))!=6:
        raise ValueError("DUPLICATE_OR_MISSING_VERSIONED_ALIAS")
    lock={
       "gate":"P28_EXACT_V138_NODE_SHA_PIN",
       "source_apk_sha256":APK_SHA,
       "node_sha256":NODE_SHA,
       "libs":entries,
       "preload":preload,
       "runtime_node_execve":"NOT_TESTED_BUILD_ONLY",
       "client_network_and_private_file_attacks":"NOT_PERFORMED",
       "release":"BLOCKED",
    }
    target=pathlib.Path(args.out)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(lock,sort_keys=True,ensure_ascii=True,
                                 separators=(",",":"))+"\n")
    print("P28_LOCK_EXACT_ORIGINAL_11_ARM64_ELF=PASS_STATIC")
    print("P28_SIX_VERSIONED_PRELOAD_ALIASES=PASS_STATIC")
    print("P28_APK_PRIVATE_TEST_ONLY=YES")
if __name__=="__main__":main()
