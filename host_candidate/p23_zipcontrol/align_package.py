#!/usr/bin/env python3
"""P23: uncompressed/16KiB ZIP alignment for 4 identical-ELF loader controls.
Contains no original DSH/Node binaries and does not execute any ELF.
"""
import argparse,copy,hashlib,json,pathlib,struct,zipfile
LIBS={
  "lib/x86_64/libp23bridge.so",
  "lib/x86_64/libp22version.so.3",
  "assets/p23control.so",
  "assets/p23control.so.3",
}
EQUIV={
  "lib/x86_64/libp22version.so.3",
  "assets/p23control.so",
  "assets/p23control.so.3",
}
def loc(i):
  return i.header_offset+30+len(i.filename.encode("utf-8"))+len(i.extra)
def main():
  p=argparse.ArgumentParser()
  p.add_argument("input")
  p.add_argument("--out",required=True)
  p.add_argument("--report",required=True)
  a=p.parse_args()
  source=pathlib.Path(a.input);dest=pathlib.Path(a.out)
  if not source.is_file() or dest.exists() or source.resolve()==dest.resolve():
    raise ValueError("INVALID_SOURCE_OR_EXISTING_OUTPUT")
  with zipfile.ZipFile(source) as src:
    info=src.infolist()
    if len(info)>100 or len(info)!=len({i.filename for i in info}) or src.testzip():
      raise ValueError("UNEXPECTED_P23_ZIP_CONTENT")
    names={i.filename for i in info}
    if not LIBS.issubset(names) or any(n.startswith("lib/x86_64/") and n not in LIBS for n in names):
      raise ValueError("P23_NATIVE_EXPECTED_ELF_SET_CHANGED")
    contents={n:src.read(n) for n in LIBS}
    if len({hashlib.sha256(contents[n]).hexdigest() for n in EQUIV})!=1:
      raise ValueError("P23_THREE_LIBRARY_BYTES_NOT_IDENTICAL")
    with zipfile.ZipFile(dest,"w") as dst:
      for item in info:
        if item.is_dir():continue
        if item.file_size>16*1024*1024:raise ValueError("MEMBER_TOO_LARGE")
        new=copy.copy(item)
        new.extra=b""
        native=item.filename in LIBS
        if native and item.compress_type!=zipfile.ZIP_STORED:
          raise ValueError("P23_ELF_MUST_BE_STORED")
        align=16384 if native else (4 if item.compress_type==0 else 1)
        if align>1:
          pad=(-(dst.fp.tell()+30+len(new.filename.encode("utf-8"))+4))%align
          new.extra=struct.pack("<HH",0xD523,pad)+bytes(pad)
        dst.writestr(new,src.read(item.filename))
  with zipfile.ZipFile(dest) as check:
    if check.testzip():raise ValueError("REPACK_CRC_FAIL")
    for i in check.infolist():
      if i.filename in LIBS and (loc(i)%16384 or i.compress_type!=zipfile.ZIP_STORED):
        raise ValueError("P23_NATIVE_ELF_ZIP_16K_STORED_GATE")
    if len({hashlib.sha256(check.read(n)).hexdigest() for n in EQUIV})!=1:
      raise ValueError("P23_REPACK_CHANGED_MATCHING_ELF_BYTES")
  pathlib.Path(a.report).write_text(json.dumps({
    "P23_FOUR_ZIP_ELF_ENTRIES_STORED_16K":True,
    "P23_THREE_IDENTICAL_ELF_LIBRARY_CONTENTS":True,
    "P23_ANDROID35_ISOLATED_DLOPEN":"NOT_TESTED",
    "P23_ORIGINAL_DSH_ARM64_NODE":"NOT_EXECUTED",
  },indent=2)+"\n")
  print("P23_ALL_4_TEST_ELF_APK_ZIP_STORED_16K=PASS_STATIC")
if __name__=="__main__":main()
