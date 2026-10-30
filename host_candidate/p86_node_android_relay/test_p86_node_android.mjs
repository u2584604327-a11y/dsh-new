import assert from "node:assert/strict";
import fs from "node:fs";import os from "node:os";import path from "node:path";import vm from "node:vm";
import {execFileSync} from "node:child_process";
const [file,cmdName,resName]=process.argv.slice(2);
assert(file&&cmdName&&resName);
const source=fs.readFileSync(file,"utf8");
const start=source.indexOf("const P70_MAILBOX_BY_HOME = new Map();");
const end=source.indexOf("function writeJsonAtomic(file, value) {",start);
assert(start>=0&&end>start,"pinned P6 sendCommand not found");
const pinned=n=>new RegExp("const "+n+" = [\"']([^\"']+)[\"'];").exec(source)?.[1];
assert.equal(cmdName,pinned("CMD_FILE"));assert.equal(resName,pinned("RESULT_FILE"));
const scope={fs,path,Promise,Date,Map,Number,Set,String,Array,Object,setTimeout,
 CMD_FILE:cmdName,RESULT_FILE:resName,POLL_INTERVAL_MS:25,WAIT_TIMEOUT_MS:15000,
 writeJsonAtomic(target,record){const tmp=target+".pending";fs.writeFileSync(tmp,JSON.stringify(record));fs.renameSync(tmp,target);},
 readJson(target){try{return JSON.parse(fs.readFileSync(target,"utf8"));}catch{return null;}},
 sleep(ms){return new Promise(r=>setTimeout(r,ms));}};
vm.createContext(scope);vm.runInContext(source.slice(start,end)+"\nglobalThis.send=sendCommand;",scope);
const home=fs.mkdtempSync(path.join(os.tmpdir(),"p86-original-p6-"));
const command=path.join(home,cmdName),reply=path.join(home,resName);
const component="com.dsh.p51.isolatedprobe/com.dsh.android.p43.P43ProbeActivity";
const safe=new Set(["read","scroll","locate","draft","status","postComment"]);
const seen=new Set(),waiting=new Set();let stopping=false,failure=null,count=0;
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
function adb(args){return execFileSync("adb",args,{encoding:"utf8",timeout:15000,maxBuffer:256*1024});}
function result(id){
 const log=adb(["logcat","-d","-v","tag","-s","P86_NATIVE_REPLY:I","*:S"]);
 for(const line of log.split("\n")){
  const m=/P86_NATIVE_REPLY(?:\([^)]*\))?:\s+(p86[a-z0-9]{2,24})\|(0|1)\|([A-Z][A-Z0-9_]{1,63})/.exec(line);
  if(m&&m[1]===id)return {id,ok:m[2]==="1",code:m[3],outcomeUnknown:false,retrySafe:false,
    result:m[2]==="1"?"synthetic_native_callback":null};
 }
 return null;
}
async function relay(){
 while(!stopping){
  try{
   let call=null;try{call=JSON.parse(fs.readFileSync(command,"utf8"));}catch{}
   if(call&&!seen.has(call.id)){
    assert(typeof call.id==="string"&&/^p86[a-z0-9]{2,24}$/.test(call.id));
    assert(safe.has(call.action));
    seen.add(call.id);waiting.add(call.id);
    adb(["shell","am","start","-f","0x20000000","-n",component,
      "--es","p86_id",call.id,"--es","p86_action",call.action]);
    count++;
   }
   for(const id of [...waiting]){
    const answer=result(id);
    if(answer){fs.writeFileSync(reply,JSON.stringify(answer));waiting.delete(id);}
   }
  }catch(e){failure=e;stopping=true;break;}
  await sleep(60);
 }
}
const task=relay();
try{
 const steps=["read","scroll","locate","draft","status","postComment"];
 for(const action of steps){
  if(failure)throw failure;
  const id="p86"+action.toLowerCase()+"01";
  const answer=await scope.send(home,id,{action,id:"forged-by-model"},14000);
  if(answer.id!==id){
   const safeCode=String(answer?.code||"MISSING_CODE").replace(/[^A-Z0-9_]/g,"").slice(0,80);
   console.error("P86_TEST_REPLY_ID_MISMATCH_CATEGORY="+safeCode);
   console.error("P86_TEST_ADB_RELAY_FAILURE="+(failure?"YES":"NO"));
   throw new Error("P86_NODE_REPLY_ID_NOT_RETURNED");
  }
  if(action==="postComment"){
    assert.equal(answer.ok,false);assert.equal(answer.code,"NATIVE_USER_CONFIRMATION_REQUIRED");
  }else{
    assert.equal(answer.ok,true,action);assert.equal(answer.code,"OK");
  }
  assert.equal(answer.outcomeUnknown,false);
 }
 assert.equal(count,steps.length);assert.equal(waiting.size,0);assert.equal(failure,null);
 console.log("P86_PINNED_P6_NODE_TO_REAL_ANDROID_WEBVIEW_CALLBACK=PASS");
 console.log("P86_NODE_REQUEST_ID_CORRELATION_AND_USER_CONSENT=PASS");
 console.log("P86_TEST_ONLY_ADB_RELAY_NOT_PRODUCTION=YES");
 console.log("P86_ORIGINAL_DSH_MODEL_CONTINUATION=NOT_WIRED");
}finally{stopping=true;await task;fs.rmSync(home,{recursive:true,force:true});}
