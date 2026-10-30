#!/usr/bin/env python3
"""P21: exact signed-v138 ARM64 Node + full ELF dependency graph packaging.

Only produces temporary native-lib candidate bytes. DOES NOT RUN NODE.
Never publish a production APK or include private original artifacts in PRs.
"""
import argparse,hashlib,io,json,pathlib,re,subprocess,tempfile,zipfile
APK_SHA="3ca56655d79afc57431636e340823e7071bc830615ca615c485b0b9a30b6e3e5"
NODE_ZIP_SHA="ba16f7f4d0cc0b0272700effe06dc0d3682206afe1b54af75ca530a3e5c0d3bf"
BOOT_ZIP_SHA="b3739c14a2eb7421243b908e2fe2b9e54cbdf8477d210d09e8ac4452d864cad9"
NODE_ELF_SHA="a0d21a1589312919114b24a5cc520c30ab7f26f9985b3f0c643c153172ebd1e6"
ANDROID_PLATFORM=frozenset(("libc.so","libm.so","libdl.so","liblog.so","libandroid.so"))
EXEC_NAME="libdshnode_p21_exec.so"
def hash_(b):return hashlib.sha256(b).hexdigest()
def elf_data(b):
 if b[:4]!=b"\x7fELF" or b[4]!=2 or b[5]!=1 or int.from_bytes(b[18:20],"little")!=183:
  raise ValueError("INVALID_ARM64_ELF")
 with tempfile.TemporaryDirectory(prefix="p21-static-readelf-") as td:
  p=pathlib.Path(td)/"binary";p.write_bytes(b)
  r=subprocess.run(["readelf","-d","-l","-W",str(p)],capture_output=True,text=True,check=True,timeout=30)
 o=r.stdout
 load_alignments=[int(line.split()[-1],16) for line in o.splitlines()
                  if line.strip().startswith("LOAD")]
 if not load_alignments or any(a<16384 or a%16384 for a in load_alignments):
  raise ValueError("ORIGINAL_ELF_NOT_16KB_PT_LOAD_ALIGNED")
 needed=sorted(set(re.findall(r"Shared library: \[([^\]]+)\]",o)))
 paths=re.findall(r"Library (?:runpath|rpath): \[([^\]]+)\]",o)
 interp=re.search(r"Requesting program interpreter:\s*([^\]]+)\]",o)
 return needed,paths,(interp.group(1) if interp else "")
def checked_zip(data):
 if len(data)>80*1024*1024:raise ValueError("OVERSIZE_NESTED_ZIP")
 z=zipfile.ZipFile(io.BytesIO(data))
 entries=z.infolist()
 if len(entries)>3000 or len(entries)!=len(set(i.filename for i in entries)):
  raise ValueError("DUPLICATE_OR_EXCESSIVE_ZIP_MEMBERS")
 for e in entries:
  p=pathlib.PurePosixPath(e.filename)
  if p.is_absolute() or ".." in p.parts or e.file_size>128*1024*1024:
   raise ValueError("ZIP_MEMBER_UNSAFE")
 if z.testzip() is not None:raise ValueError("ZIP_CRC_FAIL")
 return z
def main():
 p=argparse.ArgumentParser();p.add_argument("apk")
 p.add_argument("--out-native-dir",required=True);p.add_argument("--report",required=True);a=p.parse_args()
 original=pathlib.Path(a.apk).read_bytes()
 if hash_(original)!=APK_SHA:raise ValueError("ORIGINAL_APK_SHA_MISMATCH")
 with zipfile.ZipFile(io.BytesIO(original)) as outer:
  node_archive=outer.read("assets/node-runtime.bin")
  boot_archive=outer.read("assets/bootstrap-aarch64.zip")
 if hash_(node_archive)!=NODE_ZIP_SHA or hash_(boot_archive)!=BOOT_ZIP_SHA:
  raise ValueError("ORIGINAL_RUNTIME_ASSET_HASH_MISMATCH")
 with checked_zip(node_archive) as node,checked_zip(boot_archive) as boot:
  exe=node.read("bin/node")
  if hash_(exe)!=NODE_ELF_SHA:raise ValueError("ORIGINAL_ARM64_NODE_HASH_MISMATCH")
  n_names=set(node.namelist());b_names=set(boot.namelist());links={}
  for row in node.read("LINKS.txt").decode("ascii").splitlines():
   left,right=row.split()
   if not left.startswith("lib/") or "/" in right or not right.startswith("lib"):
    raise ValueError("UNEXPECTED_NODE_SONAME_ALIAS")
   links[left[4:]]="lib/"+right
  def resolve(name):
   if "/" in name or name.startswith(".") or not name.startswith("lib") or ".so" not in name:
    raise ValueError("INVALID_ELF_NEEDED_NAME")
   full="lib/"+name
   if full in n_names:return "node",node.read(full)
   alias=links.get(name)
   if alias is not None:
    if alias in n_names:return "node-alias",node.read(alias)
    if alias in b_names:return "bootstrap-alias",boot.read(alias)
    raise ValueError("REQUIRED_LINK_TARGET_NOT_FOUND_"+name)
   if full in b_names:return "bootstrap",boot.read(full)
   raise ValueError("NEEDED_LIBRARY_NOT_FOUND_"+name)
  needed,runpath,interp=elf_data(exe)
  if interp!="/system/bin/linker64" or "/data/data/com.termux/files/usr/lib" not in runpath:
   raise ValueError("ORIGINAL_ELF_LOADER_LAYOUT_CHANGED")
  dest=pathlib.Path(a.out_native_dir)
  if dest.exists() and any(dest.iterdir()):raise ValueError("DESTINATION_NOT_EMPTY")
  dest.mkdir(parents=True,exist_ok=True)
  (dest/EXEC_NAME).write_bytes(exe)
  queue=list(needed);seen=set();origins={};sizes={}
  while queue:
   name=queue.pop(0)
   if name in ANDROID_PLATFORM or name in seen:continue
   if len(seen)>=40:raise ValueError("UNEXPECTED_LIBRARY_GRAPH_SIZE")
   seen.add(name)
   origin,lib=resolve(name)
   deps,_,_=elf_data(lib)
   (dest/name).write_bytes(lib)
   origins[name]=origin;sizes[name]=len(lib)
   for need in deps:
    if need not in seen and need not in ANDROID_PLATFORM:queue.append(need)
  report={
    "type":"P21_ARM64_NATIVE_LIBRARY_CANDIDATE_STATIC_ONLY",
    "original_apk_sha256":APK_SHA,"original_node_sha256":NODE_ELF_SHA,
    "node_apk_path":"lib/arm64-v8a/"+EXEC_NAME,
    "interpreter":interp,"original_termux_runpath_present":True,
    "library_closure":sorted(seen),"library_source_archives":origins,
    "library_sizes_bytes":sizes,
    "all_original_elf_pt_load_alignments_16k":True,
    "native_lib_file_count":len(seen)+1,
    "api35_extractNativeLibs_unextractable_sonames":sorted(
      name for name in seen if not name.endswith(".so")),
    "api35_versioned_library_installation":"BLOCKED_IN_DEFAULT_EXTRACT_NATIVE_LIBS",
    "original_dt_needed_sonames_unmodified":True,
    "actual_android_isolated_node_execution":"NOT_TESTED",
    "original_dsh_engine_migration":"NO","release":"BLOCKED"}
  pathlib.Path(a.report).parent.mkdir(parents=True,exist_ok=True)
  pathlib.Path(a.report).write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
  print("P21_EXACT_SIGNED_V138_ELF=PASS")
  print("P21_RECURSIVE_LIBRARY_CLOSURE=PASS_"+str(len(seen)))
  print("P21_API35_VERSIONED_LIBRARY_AUTO_EXTRACTION=BLOCKED")
  print("P21_ARM64_ANDROID_NODE_EXECUTION=NOT_TESTED")
  print("P21_PRODUCTION_DSH_NODE_ISOLATED=NO")
if __name__=="__main__":main()
