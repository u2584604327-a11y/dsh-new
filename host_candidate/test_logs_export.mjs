import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

// Test runs ONLY against an isolated patched plugin directory on GitHub runner.
const pluginPath=process.argv[2];
if(!pluginPath)throw new Error('Expected patched plugin JS path');
const home=fs.mkdtempSync(path.join(os.tmpdir(),'dsh-p7-local-test-'));
process.env.DSH_HOME=home;
const plugin=await import(pathToFileURL(path.resolve(pluginPath)).href);
let tool=null;
plugin.apply({tools:{register(value){tool=value;}},logger:{warn(){},info(){}}});
assert.ok(tool?.execute && tool?.output?.render,'plugin still registers the logs tool');
let previous=-1;
const cmdPath=path.join(home,'logs-cmd.json'),replyPath=path.join(home,'logs-result.json');
const responder=setInterval(()=>{
  if(!fs.existsSync(cmdPath))return;
  let cmd;try{cmd=JSON.parse(fs.readFileSync(cmdPath,'utf8'));}catch{return;}
  if(cmd.id===previous)return;
  previous=cmd.id;
  let result;
  if(cmd.action==='export'){
    result=cmd.id===1?
      {id:cmd.id,ok:true,bundlePath:'/data/user/0/PRIVATE_DIAGNOSTIC.zip',
       bundleBytes:2345,details:{bundlePath:'/other/private.zip',secret:'CANARY_SECRET'},
       message:'CANARY_SECRET'}:
      {id:cmd.id,ok:false,bundlePath:'/data/FAILED_PRIVATE.zip',
       details:{secret:'CANARY_SECRET'},message:'CANARY_SECRET'};
  }else result={id:cmd.id,ok:true,message:'original summary preserved',count:4};
  fs.writeFileSync(replyPath,JSON.stringify(result));
},10);
try{
  const ok=await tool.execute({action:'export'});
  assert.equal(ok.ok,true);
  assert.equal(ok.needsNativeReview,true);
  assert.equal(ok.bundleBytes,2345);
  assert.deepEqual(Object.keys(ok).sort(),['bundleBytes','message','needsNativeReview','ok'].sort());
  for(const forbidden of ['PRIVATE_DIAGNOSTIC.zip','CANARY_SECRET','/data/user/0/']){
    assert.equal(JSON.stringify(ok).includes(forbidden),false,'export response cannot leak '+forbidden);
    assert.equal(JSON.stringify(tool.output.render({action:'export'},ok)).includes(forbidden),false,
      'render cannot leak '+forbidden);
  }
  const fail=await tool.execute({action:'export'});
  assert.equal(fail.ok,false);
  assert.equal(JSON.stringify(fail).includes('CANARY_SECRET'),false);
  assert.equal(JSON.stringify(fail).includes('FAILED_PRIVATE.zip'),false);
  const summary=await tool.execute({action:'summary'});
  assert.equal(summary.message,'original summary preserved');
  assert.equal(summary.count,4);
  console.log('P7_MODEL_VISIBLE_EXPORT_BOUNDARY=PASS');
  console.log('P7_SUMMARY_BACKCOMPAT=PASS');
  console.log('P7_NATIVE_MAILBOX_AND_GENERIC_NODE_EGRESS=NOT_VERIFIED');
}finally{
  clearInterval(responder);
  fs.rmSync(home,{recursive:true,force:true});
}
