#!/usr/bin/env python3
"""Read-only classification of exact original signed v138 DSH engine asset.

Do not print APK member paths, filenames, source lines, dynamic literals, env
values, user files, script bytes, credentials or command arguments. No write to
APK, no execution, no decompression to disk, no publishing original bytes.
"""
import argparse
import collections
import hashlib
import io
import pathlib
import zipfile
import gzip
import tarfile

ORIGINAL_SHA="3ca56655d79afc57431636e340823e7071bc830615ca615c485b0b9a30b6e3e5"
ENGINE="assets/engine.bin"
MAX_ASSET=128*1024*1024
MAX_MEMBERS=100000
MAX_UNWRAPPED_METADATA_BYTES=512*1024*1024

def require(ok,why):
    if not ok:raise RuntimeError("P53_RUNTIME_INTAKE_BLOCKED_"+why)

def sha256_file(path):
    digest=hashlib.sha256()
    with open(path,"rb") as fh:
        for b in iter(lambda:fh.read(2**20),b""):
            digest.update(b)
    return digest.hexdigest()

def classify(data):
    header=data[:16]
    if header.startswith(b"PK\x03\x04"): return "ZIP"
    if header.startswith(b"\x1f\x8b"): return "GZIP"
    if header.startswith(b"\xfd7zXZ\x00"):return "XZ"
    if header.startswith(b"BZh"):return "BZIP2"
    if header.startswith(b"\x28\xb5\x2f\xfd"):return "ZSTANDARD"
    if header.startswith(b"\x7fELF"):return "ELF"
    return "OPAQUE_UNKNOWN"

def inventory(path):
    apk=pathlib.Path(path)
    require(apk.is_file() and apk.stat().st_size==147341486,"WRONG_BASELINE_LENGTH")
    require(sha256_file(apk)==ORIGINAL_SHA,"WRONG_BASELINE_SHA")
    with zipfile.ZipFile(apk) as z:
        entries=z.namelist()
        require(entries.count(ENGINE)==1,"ENGINE_MISSING_OR_DUPLICATED")
        info=z.getinfo(ENGINE)
        require(info.file_size>0 and info.file_size<=MAX_ASSET,"ENGINE_ASSET_SIZE_INVALID")
        data=z.read(ENGINE)
    kind=classify(data)
    counts=collections.Counter()
    archive_members=0
    inner_kind="NOT_INSPECTED"
    if kind=="GZIP":
        # Inspect the *streamed* unwrapped header without writing scripts.
        # For TAR: skip member bytes, record only counts and bounded sizes.
        with gzip.GzipFile(fileobj=io.BytesIO(data),mode="rb") as gz:
            peek=gz.read(512)
        if len(peek)>=512 and peek[257:262]==b"ustar":
            inner_kind="TAR"
            unwrapped_total=0
            with gzip.GzipFile(fileobj=io.BytesIO(data),mode="rb") as gz:
                with tarfile.open(fileobj=gz,mode="r|") as archive:
                    for member in archive:
                        archive_members+=1
                        require(archive_members<=MAX_MEMBERS,"TAR_MEMBER_CAP")
                        name=member.name
                        from pathlib import PurePosixPath
                        parts=PurePosixPath(name)
                        require(not parts.is_absolute() and ".." not in parts.parts
                                and "\\" not in name,"TAR_UNSAFE_MEMBER")
                        require(member.size<=MAX_ASSET,"TAR_MEMBER_TOO_LARGE")
                        unwrapped_total+=member.size
                        require(unwrapped_total<=MAX_UNWRAPPED_METADATA_BYTES,
                                "TAR_TOTAL_DECLARED_CONTENT_TOO_LARGE")
                        if member.isdir():counts["directories"]+=1
                        elif member.issym() or member.islnk():counts["links"]+=1
                        elif name.endswith(".js"):counts["js"]+=1
                        elif name.endswith(".mjs"):counts["mjs"]+=1
                        elif name.endswith(".cjs"):counts["cjs"]+=1
                        elif name.endswith(".json"):counts["json"]+=1
                        elif name.endswith(".node"):counts["native_addon"]+=1
                        else:counts["other"]+=1
        else:
            inner_kind=classify(peek)
    if kind=="ZIP":
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            infos=z.infolist()
            require(len(infos)<=MAX_MEMBERS,"ENGINE_TOO_MANY_MEMBERS")
            require(len(infos)==len(set(i.filename for i in infos)),
                    "ENGINE_DUPLICATE_MEMBERS")
            archive_members=len(infos)
            for i in infos:
                # Filename strings stay in memory; no full paths or contents
                # are printed. This is classification only.
                from pathlib import PurePosixPath
                path=PurePosixPath(i.filename)
                require(not path.is_absolute() and ".." not in path.parts and
                        "\\" not in i.filename,"ENGINE_UNSAFE_MEMBER")
                require(i.file_size<=MAX_ASSET,"ENGINE_MEMBER_BOMB")
                if i.is_dir():counts["directories"]+=1
                elif i.filename.endswith(".js"):counts["js"]+=1
                elif i.filename.endswith(".mjs"):counts["mjs"]+=1
                elif i.filename.endswith(".cjs"):counts["cjs"]+=1
                elif i.filename.endswith(".json"):counts["json"]+=1
                elif i.filename.endswith(".node"):counts["native_addon"]+=1
                else:counts["other"]+=1
    print("P53_EXACT_SIGNED_V138_ENGINE_ASSET=PASS")
    print("P53_ENGINE_ASSET_CONTAINER_TYPE="+kind)
    print("P53_ENGINE_ASSET_GZIP_CONTAINER_OR_RAW_BYTES="+str(len(data)))
    print("P53_ENGINE_GZIP_INNER_CONTAINER_TYPE="+inner_kind)
    print("P53_ENGINE_ARCHIVE_MEMBER_COUNT="+str(archive_members))
    for name in ("js","mjs","cjs","json","native_addon","other","directories","links"):
        print("P53_ENGINE_MEMBER_CATEGORY_"+name.upper()+"="+str(counts[name]))
    print("P53_ENGINE_SCRIPT_CONTENT_EXTRACTED_OR_UPLOADED=NO")
    print("P53_PRODUCTION_STARTUP_COMMAND_AND_DIRECTORY=NOT_PROVEN")
    print("P53_ORIGINAL_DSH_ENGINE_MANAGER_WORKER_SCRIPT_BROKER=NOT_IMPLEMENTED")
    print("P53_V139_RELEASE=BLOCKED")

if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("exact_original_v138_apk")
    args=a.parse_args()
    inventory(args.exact_original_v138_apk)
