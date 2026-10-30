#!/usr/bin/env python3
"""P22 align actual versioned x86_64 ELF in unsigned disposable APK.
The source contents are test-only NDK C code; never original DSH binary.
"""
import argparse,copy,json,pathlib,struct,zipfile
ABI="lib/x86_64/"
EXPECTED={ABI+"libp22probe_exec.so",ABI+"libp22version.so.3",
          ABI+"libp22bridge.so"}
ALIGN=16384
def pos(i):
 return i.header_offset+30+len(i.filename.encode("utf-8"))+len(i.extra)
def main():
 p=argparse.ArgumentParser()
 p.add_argument("source")
 p.add_argument("--out",required=True)
 p.add_argument("--report",required=True)
 a=p.parse_args()
 source=pathlib.Path(a.source);dest=pathlib.Path(a.out)
 if not source.is_file() or dest.exists() or source.resolve()==dest.resolve():
  raise ValueError("INVALID_SOURCE_OR_EXISTING_OUTPUT")
 with zipfile.ZipFile(source) as zin:
  infos=zin.infolist()
  if len(infos)>100 or len(infos)!=len(set(x.filename for x in infos)) or zin.testzip():
   raise ValueError("INVALID_ARCHIVE")
  native={x.filename for x in infos if x.filename.startswith(ABI)}
  if native!=EXPECTED:raise ValueError("EXPECTED_TWO_ELF_MISSING")
  with zipfile.ZipFile(dest,"w") as zout:
   for info in infos:
    if info.is_dir():continue
    if info.file_size>16*1024*1024:raise ValueError("OVERSIZE_TEST_INPUT")
    contents=zin.read(info.filename)
    selected=info.filename in EXPECTED
    if selected and info.compress_type!=zipfile.ZIP_STORED:
     raise ValueError("ELF_COMPRESSED")
    new=copy.copy(info)
    new.extra=b""
    alignment=ALIGN if selected else (4 if info.compress_type==0 else 1)
    if alignment>1:
     # ZIP "private extra field" length includes tag+size; pads payload start.
     need=(-((zout.fp.tell()+30+len(new.filename.encode("utf-8")))+4))%alignment
     new.extra=struct.pack("<HH",0xD522,need)+bytes(need)
    zout.writestr(new,contents)
 with zipfile.ZipFile(dest) as check:
  if check.testzip():raise ValueError("REPACK_CRC_FAIL")
  for item in check.infolist():
   if item.filename in EXPECTED:
    if pos(item)%ALIGN:raise ValueError("NOT_16K_ALIGNED")
    if item.compress_type!=zipfile.ZIP_STORED:raise ValueError("NOT_STORED")
  output={"P22_ZIP_16K_ALIGNED_ELF_COUNT":3,
          "P22_VERSIONED_SONAME_PRESERVED":True,
          "P22_ACTUAL_ANDROID35_EXECVE":"NOT_TESTED",
          "P22_FIXED_JNI_BIONIC_ZIP_DLOPEN":"NOT_TESTED"}
  pathlib.Path(a.report).write_text(json.dumps(output,indent=2)+"\n")
 print("P22_16KB_ELF_APK_ZIP_OFFSET=PASS")
if __name__=="__main__":main()
