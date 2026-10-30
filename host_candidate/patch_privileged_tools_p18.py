"""P18 deny legacy AI privileged shell/root tool registration in exact v138.
These original optional tools bypass app sandbox via adbd uid2000 or su uid0.
Only nested lib/index.js changed; do not rewrite built-in normal bash or
ordinary user-selected attachments. This is NOT full Node UID isolation.
"""
import argparse,copy,hashlib,io,json,pathlib,zipfile
BASE={
"assets/shell-tool.zip":"f34284d3518c1b5c5cd800b44db50b448bd844492a13e15d380b14b6448f2611",
"assets/root-tool.zip":"d67301442216463dcf340d5c549b203d9c5ec3a7ebb07e8d25c54f1af24b95c1",
}
START="export function apply(ctx) {"
EXECUTE="async execute(args, exec) {"
def hash_(blob):return hashlib.sha256(blob).hexdigest()
def patch(name,blob):
 if name not in BASE or hash_(blob)!=BASE[name]:
  raise ValueError("SIGNED_V138_PRIVILEGED_TOOL_PREIMAGE_CHANGED")
 with zipfile.ZipFile(io.BytesIO(blob)) as zip_:
  if zip_.testzip() or set(zip_.namelist())!={"package.json","lib/index.js"}:
   raise ValueError("UNEXPECTED_TOOL_ARCHIVE_LAYOUT")
  src=zip_.read("lib/index.js").decode()
  if src.count(START)!=1 or src.count(EXECUTE)!=1:
   raise ValueError("NOT_EXACT_PRIVILEGED_TOOL_ENTRYPOINTS")
  # Backstop: even if a forgotten module creates this plugin's Tool object
  # directly rather than through apply(), execute must not reach the old
  # adbd/su runner. Its registered API remains disabled until a native broker.
  src=src.replace(EXECUTE,EXECUTE+"""
            return {card:'terminal',output:'已拒绝：高权限 Shell/Root 需要经可信原生能力代理逐次批准，目前尚未接入。',exitCode:77};
""",1)
  src=src.replace(START,START+"""
    // P18 default deny: legacy adbd (uid2000) / su (uid0) bypass the
    // sandbox. Registration cannot be re-enabled by environment variables.
    ctx?.logger?.warn?.('[DSH-P18] Privileged tool unavailable until native broker');
    return;
""",1)
  if src.count("ctx.tools.register(")!=1:
   raise ValueError("REGISTRATION_SITE_SHAPE_CHANGED")
  out=io.BytesIO()
  with zipfile.ZipFile(out,"w") as result:
   result.comment=zip_.comment
   for entry in zip_.infolist():
    result.writestr(copy.copy(entry),src.encode()
                    if entry.filename=="lib/index.js" else zip_.read(entry.filename))
 new=out.getvalue()
 with zipfile.ZipFile(io.BytesIO(new)) as verify,zipfile.ZipFile(io.BytesIO(blob)) as orig:
  if verify.testzip() or verify.namelist()!=orig.namelist():
   raise ValueError("PATCHED_PRIVILEGED_ZIP_CRC_OR_SCOPE")
  if verify.read("package.json")!=orig.read("package.json"):
   raise ValueError("PRIVILEGED_TOOL_PACKAGE_METADATA_CHANGED")
 return new,src
def patch_both(original):
 return {name:patch(name,original[name]) for name in BASE}
if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--shell",required=True);p.add_argument("--root",required=True)
 p.add_argument("--out",required=True)
 a=p.parse_args()
 out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=True)
 for path in (a.shell,a.root):
  name="assets/shell-tool.zip" if path==a.shell else "assets/root-tool.zip"
  blob,js=patch(name,pathlib.Path(path).read_bytes())
  leaf=name.removeprefix("assets/")
  (out/leaf).write_bytes(blob)
  (out/(leaf+".js")).write_text(js)
  print(json.dumps({"file":name,"sha256":hash_(blob),
    "legacy_privileged_tool_registered":"NO",
    "ordinary_bash_tool":"NOT_MODIFIED_BY_P18",
    "generic_node_file_network":"NOT_ISOLATED",
    "APK":"NOT_BUILT"}))
