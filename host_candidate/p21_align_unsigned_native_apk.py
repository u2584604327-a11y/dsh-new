#!/usr/bin/env python3
"""P21 installer-immutable APK ZIP ELF alignment. Candidate-only unsigned APK.

API >=23 Bionic linker supports page-aligned uncompressed ELF files in ZIPs.
Verifies 16 KB page alignment for VERSIONED .so.N files too; makes no runtime linker/UID claim.
"""
import argparse,copy,hashlib,json,pathlib,struct,zipfile
EXPECTED_NODE="a0d21a1589312919114b24a5cc520c30ab7f26f9985b3f0c643c153172ebd1e6"
VERSIONED={"libcrypto.so.3","libssl.so.3","libz.so.1",
           "libicui18n.so.78","libicuuc.so.78","libicudata.so.78"}
NATIVE_PREFIX="lib/arm64-v8a/"
def offset(m):
 return m.header_offset+30+len(m.filename.encode("utf-8"))+len(m.extra)
def main():
 a=argparse.ArgumentParser()
 a.add_argument("unsigned_input")
 a.add_argument("--out",required=True)
 a.add_argument("--report",required=True)
 p=a.parse_args();input_=pathlib.Path(p.unsigned_input);out=pathlib.Path(p.out)
 if input_.resolve()==out.resolve() or out.exists():
  raise ValueError("DESTINATION_EXISTING_OR_SAME_AS_INPUT")
 if input_.stat().st_size>240*1024*1024:raise ValueError("OVERLONG_UNSIGNED_APK")
 with zipfile.ZipFile(input_) as src:
  infos=src.infolist()
  if len(infos)>120 or len(infos)!=len(set(i.filename for i in infos)) or src.testzip():
   raise ValueError("INVALID_UNSIGNED_APK")
  entries=[i for i in infos if i.filename.startswith(NATIVE_PREFIX) and
           i.filename[len(NATIVE_PREFIX):].startswith("lib") and not i.is_dir()]
  if len(entries)!=11:raise ValueError("NOT_EXACT_11_ARM64_RUNTIME_ENTRIES")
  if not VERSIONED.issubset(set(i.filename[len(NATIVE_PREFIX):] for i in entries)):
   raise ValueError("VERSIONED_NEEDED_LIBS_MISSING")
  exe=src.read(NATIVE_PREFIX+"libdshnode_p21_exec.so")
  if hashlib.sha256(exe).hexdigest()!=EXPECTED_NODE:
   raise ValueError("ORIGINAL_EXE_SHA_MISMATCH")
  with zipfile.ZipFile(out,"w",allowZip64=True) as dest:
   for info in infos:
    if info.is_dir():continue
    data=src.read(info.filename)
    native=info.filename.startswith(NATIVE_PREFIX)
    if native and info.compress_type!=zipfile.ZIP_STORED:
     raise ValueError("NATIVE_ELF_MUST_BE_UNCOMPRESSED")
    item=copy.copy(info)
    item.extra=b""
    # New valid private ZIP extra field: length includes tag and size (4).
    alignment=16384 if native else (4 if info.compress_type==zipfile.ZIP_STORED else 1)
    pos=dest.fp.tell()
    name_bytes=item.filename.encode("utf-8")
    if alignment>1:
     pad=(-(pos+30+len(name_bytes)+4))%alignment
     item.extra=struct.pack("<HH",0xD521,pad)+bytes(pad)
    dest.writestr(item,data)
 with zipfile.ZipFile(out) as check:
  if check.testzip():raise ValueError("FINAL_ZIP_CRC_FAILURE")
  for entry in check.infolist():
   if entry.is_dir():continue
   native=entry.filename.startswith(NATIVE_PREFIX)
   required=16384 if native else (4 if entry.compress_type==0 else 1)
   if offset(entry)%required:raise ValueError("ZIP_PAGE_ALIGNMENT_BAD_"+entry.filename)
  if hashlib.sha256(check.read(NATIVE_PREFIX+"libdshnode_p21_exec.so")).hexdigest()!=EXPECTED_NODE:
   raise ValueError("ZIP_REWRITE_CHANGED_NODE_EXE")
  report={"P21_ZIP_NATIVE_LIB_ENTRIES":len(entries),
          "P21_VERSIONED_LIBS_ALIGNED_16384":len(VERSIONED),
          "P21_NATIVE_ELFS_STORED_UNCOMPRESSED":True,
          "P21_ORIGINAL_NODE_SHA256_RETAINED":True,
          "P21_ZIP_LD_LIBRARY_PATH_ANDROID_ISOLATED_UID":"NOT_TESTED",
          "P21_NODE_REAL_EXECUTION":"NOT_TESTED",
          "P21_RELEASE":"BLOCKED"}
  pathlib.Path(p.report).write_text(json.dumps(report,indent=2)+"\n")
 print("P21_ALL_11_REAL_ARM64_ELF_ZIP_16KB_ALIGNMENT=PASS")
 print("P21_VERSIONED_SONAMES_DIRECT_APK_LINKER_CANDIDATE=PACKAGED_NOT_EXECUTED")
if __name__=="__main__":main()
