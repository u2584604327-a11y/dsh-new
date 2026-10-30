import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

const js=process.argv[2];
if(!js)throw new Error('need patched JS');
const home=fs.mkdtempSync(path.join(os.tmpdir(),'dsh-p11-counter-only-'));
process.env.DSH_HOME=home;
const loaded=await import(pathToFileURL(path.resolve(js)).href);
let tool=null;
loaded.apply({tools:{register(entry){tool=entry;}},logger:{warn(){},info(){}}});
assert.ok(tool?.execute && tool.output?.render,'logs plugin must register');
assert.deepEqual(tool.parameters.properties.action.enum,['summary']);
const cmd=path.join(home,'logs-cmd.json');
const reply=path.join(home,'logs-result.json');

function render(a,v){return JSON.stringify(tool.output.render(a,v));}
try {
  for(const action of ['read','crashes','export','unknown']){
    const result=await tool.execute({action,query:'CANARY_READ',crashFile:'private-crash.txt'});
    assert.equal(result.ok,false);
    assert.equal(fs.existsSync(cmd),false,'blocked raw action may not write native mailbox');
    assert.equal(render({action},result).includes('private-crash'),false);
  }
  let processed=-1;
  const responder=setInterval(()=>{
    if(!fs.existsSync(cmd))return;
    let request;try{request=JSON.parse(fs.readFileSync(cmd,'utf8'));}catch{return;}
    if(request.id===processed)return;
    processed=request.id;
    assert.equal(request.action,'summary','only summary may go native');
    fs.writeFileSync(reply,JSON.stringify({
      id:request.id,ok:true,headline:'CANARY_SECRET_HEADLINE',
      lastExit:'CANARY_SECRET_EXIT',message:'CANARY_SECRET_MESSAGE',
      counts:{total:7,warn:2,error:1,crash:3,pending:0,
        scope:'CANARY_SECRET_SCOPE',userSupplied:'CANARY_SECRET'},
      logText:'CANARY_SECRET_LOG',sceneText:'CANARY_SECRET_CRASH',
      bundlePath:'/private/CANARY_SECRET_ZIP',
      details:{token:'CANARY_SECRET_TOKEN'}
    }));
  },10);
  try {
    const result=await tool.execute({action:'summary'});
    assert.equal(result.ok,true);
    assert.deepEqual(Object.keys(result).sort(),['ok','headline','counts','message'].sort());
    assert.equal(result.counts.warn,2);
    assert.equal(result.counts.error,1);
    assert.equal(result.counts.crash,3);
    const visible=JSON.stringify(result)+render({action:'summary'},result);
    assert.equal(visible.includes('CANARY_SECRET'),false);
    assert.equal(visible.includes('/private/'),false);
    const native=JSON.parse(fs.readFileSync(cmd,'utf8'));
    assert.deepEqual(Object.keys(native).sort(),['action','id'].sort());
  }finally{clearInterval(responder);}
  console.log('P11_RAW_READ_CRASH_EXPORT_DENY_BEFORE_MAILBOX=PASS');
  console.log('P11_SUMMARY_NUMERIC_WHITELIST=PASS');
  console.log('P11_CANARY_SECRET_NONDISCLOSURE=PASS');
  console.log('P11_NODE_GENERIC_FILESYSTEM_BYPASS=NOT_SOLVED');
}finally{fs.rmSync(home,{recursive:true,force:true});}
