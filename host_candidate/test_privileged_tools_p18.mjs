import assert from "node:assert/strict";
import fs from "node:fs";
import {pathToFileURL} from "node:url";
import path from "node:path";
const dir=path.resolve(process.argv[2]);
assert.ok(dir);
const envKeys=["DSH_PRIV_RUNNER","DSH_ROOT_RUNNER","DSH_HOME","DSH_ADB_HOME"];
const saved=Object.fromEntries(envKeys.map(k=>[k,process.env[k]]));
try {
  process.env.DSH_PRIV_RUNNER=process.execPath;
  process.env.DSH_ROOT_RUNNER=process.execPath;
  process.env.DSH_HOME=dir;
  process.env.DSH_ADB_HOME=dir;
  for(const item of ["shell","root"]) {
    const folder=path.join(dir,item);
    const js=fs.readFileSync(path.join(folder,"lib","index.js"),"utf8");
    assert.ok(js.includes("P18 default deny"));
    const start=js.indexOf("export function apply(ctx) {");
    assert.ok(start>=0);
    assert.ok(js.indexOf("return;",start)<js.indexOf("const runner",start),
      "P18 tool registration must be unreachable even with runner configured");
    assert.ok(js.includes("return {card:'terminal',output:'已拒绝"),
      "P18 direct execute failclose absent");
    const loaded=await import(pathToFileURL(path.join(folder,"lib","index.js")).href);
    let calls=0;
    const ctx={
      tools:{register(){calls++;throw new Error("forbidden privileged registration");}},
      shell:{execute(){throw new Error("forbidden privileged execution");}},
      logger:{warn(){},info(){}}
    };
    assert.equal(typeof loaded.apply,"function");
    loaded.apply(ctx);
    assert.equal(calls,0,item+": privileged registration bypass");
    console.log("P18_"+item.toUpperCase()+"_TOOL_REGISTRATION=DENIED");
  }
  console.log("P18_ADB_UID2000_AND_SU_UID0_MODEL_BYPASS=NOT_REGISTERED");
  console.log("P18_GENERIC_NODE_BASH_FS_NETWORK=NOT_ISOLATED");
}finally{
  for(const k of envKeys) {
    if(saved[k]===undefined)delete process.env[k];else process.env[k]=saved[k];
  }
}
