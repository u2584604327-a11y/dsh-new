#!/usr/bin/env python3
"""P25: create only SHA-preserving package-manager-extractable ARM64 aliases.

Input is P21 exact-v138 hash-pinned unpacked binary tree. Never executes,
disassembles/patches, signs, uploads, or mutates original Node bytes.
"""
import argparse,hashlib,json,pathlib,re,subprocess,tempfile

ORIGINAL_NODE_SHA="a0d21a1589312919114b24a5cc520c30ab7f26f9985b3f0c643c153172ebd1e6"
NODE="libdshnode_p21_exec.so"
ANDROID_PLATFORM={"libc.so","libm.so","libdl.so","liblog.so","libandroid.so"}
EXPECTED_NON_PLATFORM=10
EXPECTED_VERSIONED=6

def sha256(blob):return hashlib.sha256(blob).hexdigest()

def inspect(binary):
 if binary[:4]!=b"\x7fELF" or binary[4]!=2 or binary[5]!=1:
  raise ValueError("UNEXPECTED_ELF_FORMAT")
 if int.from_bytes(binary[18:20],"little")!=183:
  raise ValueError("NOT_ORIGINAL_ARM64")
 with tempfile.TemporaryDirectory(prefix="p25-readelf-") as temp:
  path=pathlib.Path(temp)/"binary";path.write_bytes(binary)
  run=subprocess.run(["readelf","-d","-W",str(path)],capture_output=True,
                     text=True,check=True,timeout=30)
 text=run.stdout
 sonames=re.findall(r"Library soname: \[([^\]]+)\]",text)
 needed=sorted(set(re.findall(r"Shared library: \[([^\]]+)\]",text)))
 return sonames,needed

def dependency_first_order(versioned, needs):
 state={};result=[]
 def visit(node):
  if state.get(node)==1:raise ValueError("VERSIONED_PRELOAD_DEPENDENCY_CYCLE")
  if state.get(node)==2:return
  state[node]=1
  for dependency in sorted(needs[node]):
   if dependency in versioned:visit(dependency)
  state[node]=2
  result.append(node)
 for item in sorted(versioned):visit(item)
 return result

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--p21-native-dir",required=True)
 p.add_argument("--out-native-dir",required=True)
 p.add_argument("--report",required=True)
 args=p.parse_args()
 source=pathlib.Path(args.p21_native_dir)
 destination=pathlib.Path(args.out_native_dir)
 if not source.is_dir() or destination.resolve()==source.resolve():
  raise ValueError("BAD_P21_SOURCE_DESTINATION")
 if destination.exists() and any(destination.iterdir()):
  raise ValueError("DESTINATION_MUST_BE_EMPTY")
 names={p.name for p in source.iterdir() if p.is_file()}
 if NODE not in names or len(names)!=EXPECTED_NON_PLATFORM+1:
  raise ValueError("P21_CLOSURE_FILE_COUNT_CHANGED")
 original_executable=(source/NODE).read_bytes()
 if sha256(original_executable)!=ORIGINAL_NODE_SHA:
  raise ValueError("ORIGINAL_NODE_BYTES_CHANGED")
 expected=names-{NODE}
 if len(expected)!=EXPECTED_NON_PLATFORM:raise ValueError("LIBRARY_COUNT_CHANGED")
 original_meta={}
 soname_mismatches=[]
 original_missing_sonames=[]
 for name in sorted(expected):
  if not re.fullmatch(r"lib[A-Za-z0-9_.+-]+\.so(?:\.[0-9][0-9.]*)?",name):
   raise ValueError("BAD_ORIGINAL_NEEDED_SONAME")
  blob=(source/name).read_bytes()
  sonames,needed=inspect(blob)
  if len(sonames)!=1 or sonames[0]!=name:
   # Exact original v138 exception: libsqlite3.so has no DT_SONAME.
   # Bionic may use basename fallback, but actual ARM64 resolution is NOT PROVEN.
   if name=="libsqlite3.so" and len(sonames)==0:
    original_missing_sonames.append(name)
   else:
    observed=sonames[0] if len(sonames)==1 else "MISSING_OR_MULTIPLE"
    soname_mismatches.append({"needed_name":name,"actual_soname":observed})
  if any(dep not in expected and dep not in ANDROID_PLATFORM for dep in needed):
   raise ValueError("TRANSITIVE_NEEDED_NOT_PRESENT_"+name)
  original_meta[name]={"sha256":sha256(blob),"needed":needed}
 # This prints bounded pinned binary *metadata only*, no runtime bytes or paths.
 if soname_mismatches:
  print("P25_ORIGINAL_SONAME_VS_NEEDED_MISMATCH_COUNT="+str(len(soname_mismatches)))
  for item in soname_mismatches:
   print("P25_ORIGINAL_SONAME_MISMATCH="+
         item["needed_name"]+"|"+item["actual_soname"])
  raise ValueError("ORIGINAL_SONAME_REQUIRES_EXPLICIT_RESOLUTION_PLAN")
 root_soname,root_needs=inspect(original_executable)
 if root_soname:raise ValueError("ORIGINAL_NODE_UNEXPECTED_SHARED_SONAME")
 if any(n not in expected and n not in ANDROID_PLATFORM for n in root_needs):
  raise ValueError("ORIGINAL_NODE_UNRESOLVED_NEEDED")
 versioned={name for name in expected if not name.endswith(".so")}
 if len(versioned)!=EXPECTED_VERSIONED:
  raise ValueError("VERSIONED_DEPENDENCY_COUNT_CHANGED")
 preload=dependency_first_order(versioned,{
   n:original_meta[n]["needed"] for n in expected})
 alias={}
 for name in sorted(expected):
  if name in versioned:
   suffix=hashlib.sha256(name.encode("ascii")).hexdigest()[:12]
   alias[name]="libp25_"+suffix+".so"
  else:alias[name]=name
 if len(set(alias.values()))!=len(alias):
  raise ValueError("ALIAS_FILENAME_COLLISION")
 if NODE in set(alias.values()):
  raise ValueError("ALIAS_COLLIDES_WITH_EXECUTABLE")
 destination.mkdir(parents=True,exist_ok=True)
 (destination/NODE).write_bytes(original_executable)
 for name in sorted(expected):
  source_blob=(source/name).read_bytes()
  destination_name=alias[name]
  if not destination_name.startswith("lib") or not destination_name.endswith(".so"):
   raise ValueError("NOT_APK_INSTALLER_EXTRACTABLE")
  dest_path=destination/destination_name
  dest_path.write_bytes(source_blob)
  if sha256(dest_path.read_bytes())!=original_meta[name]["sha256"]:
   raise ValueError("ALIAS_COPY_CHANGED_ORIGINAL_ELF_BYTES")
  sonames,_=inspect(dest_path.read_bytes())
  if sonames!=[name] and not (name=="libsqlite3.so" and sonames==[]):
   raise ValueError("ALIAS_COPY_CHANGED_EMBEDDED_SONAME")
 if sha256((destination/NODE).read_bytes())!=ORIGINAL_NODE_SHA:
  raise ValueError("ORIGINAL_EXECUTABLE_BYTES_CHANGED_ON_ALIAS_STAGE")
 report={
  "gate":"P25_EXACT_V138_ARM64_ALIAS_STATIC_ONLY",
  "original_node_sha256":ORIGINAL_NODE_SHA,
  "original_node_ELF_unchanged":True,
  "dependency_library_count":len(expected),
  "versioned_soname_count":len(versioned),
  "all_alias_filenames_end_with_so":True,
  "all_dependency_ELF_bytes_and_internal_sonames_preserved":True,
  "original_missing_soname_exception":original_missing_sonames,
  "original_libsqlite3_filename_fallback_runtime":"NOT_TESTED",
  "soname_to_installer_filename":alias,
  "original_library_sha256":{n:original_meta[n]["sha256"] for n in sorted(expected)},
  "preload_dependency_first_order_versioned":preload,
  "original_node_runpath_termux_cleanup":"NOT_ATTEMPTED_UNMODIFIED",
  "multi_library_android_linker_preload_success":"NOT_TESTED",
  "actual_original_arm64_node_execve_in_isolated_uid":"NOT_TESTED",
  "actual_original_node_egress_file_isolation":"NOT_TESTED",
  "original_dsh_host_runtime_migrated":False,
  "release":"BLOCKED",
 }
 report_path=pathlib.Path(args.report)
 report_path.parent.mkdir(parents=True,exist_ok=True)
 report_path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
 print("P25_ORIGINAL_ARM64_NODE_BYTES_UNCHANGED=PASS")
 print("P25_ORIGINAL_10_LIBRARY_BYTES_SONAMES_PRESERVED=PASS")
 print("P25_ANDROID_INSTALLER_EXTRACTABLE_ALIAS_NAMES=PASS_10")
 print("P25_ORIGINAL_LIBSQLITE3_HAS_NO_SONAME=STATIC_EXCEPTION_RUNTIME_BLOCKED")
 print("P25_VERSIONED_DEPENDENCY_PRELOAD_PLAN=STATIC_PASS_6")
 print("P25_ORIGINAL_ARM64_NODE_ISOLATED_BOOT=NOT_TESTED")
if __name__=="__main__":main()
