import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import vm from "node:vm";
const file=process.argv[2];
assert(file,"patched browser JS required");
const source=fs.readFileSync(file,"utf8");
const from=source.indexOf("const P70_MAILBOX_BY_HOME = new Map();");
const to=source.indexOf("function writeJsonAtomic(file, value) {",from);
assert(from>=0&&to>from,"P70 actual sendCommand replacement missing");
const cmdFile=/const CMD_FILE = ["']([^"']+)["'];/.exec(source)?.[1];
const resFile=/const RESULT_FILE = ["']([^"']+)["'];/.exec(source)?.[1];
const pollMs=Number(/const POLL_INTERVAL_MS = ([0-9_]+);/.exec(source)?.[1]?.replaceAll("_",""));
assert(cmdFile&&resFile&&pollMs>0,"real original mailbox constants missing");
const context={fs,path,Promise,Date,Map,Number,Set,String,Array,Object,setTimeout,
  CMD_FILE:cmdFile,RESULT_FILE:resFile,POLL_INTERVAL_MS:pollMs,WAIT_TIMEOUT_MS:25000,
  writeJsonAtomic(file,value){
    const tmp=file+".tmp."+Math.random().toString(16).slice(2);
    fs.writeFileSync(tmp,JSON.stringify(value),"utf8");fs.renameSync(tmp,file);
  },
  readJson(file){try{return JSON.parse(fs.readFileSync(file,"utf8"));}catch{return null;}},
  sleep(ms){return new Promise(resolve=>setTimeout(resolve,ms));}
};
vm.createContext(context);
vm.runInContext(source.slice(from,to)+"\nglobalThis.testSendCommand=sendCommand;",context);
const send=context.testSendCommand;
const home=fs.mkdtempSync(path.join(os.tmpdir(),"p70-browser-"));
let tests=0;const check=(v,msg)=>{tests++;assert(v,msg);};
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const cmdPath=path.join(home,cmdFile),resPath=path.join(home,resFile);
function readCmd(){try{return JSON.parse(fs.readFileSync(cmdPath,"utf8"));}catch{return null;}}
function respond(ids,{wrongFirst=false}={}){
 const seen=new Set();
 const timer=setInterval(()=>{
   const cmd=readCmd();if(!cmd||seen.has(String(cmd.id)))return;
   seen.add(String(cmd.id));ids.push(cmd.id);
   if(wrongFirst){
     fs.writeFileSync(resPath,JSON.stringify({id:"wrong",ok:true}),"utf8");
     setTimeout(()=>fs.writeFileSync(resPath,JSON.stringify({id:cmd.id,ok:true,result:"success"}),"utf8"),45);
   }else {
     fs.writeFileSync(resPath,JSON.stringify({id:cmd.id,ok:true,result:"success"}),"utf8");
   }
 },7);
 return ()=>clearInterval(timer);
}
try{
 const order=[],stop=respond(order);
 const a=send(home,"a",{action:"read",id:"model-forged"},1200);
 const b=send(home,"b",{action:"scroll"},1200);
 const [ra,rb]=await Promise.all([a,b]);stop();
 check(ra.ok===true&&rb.ok===true,"two overlapping calls both receive actual replies");
 check(order.length===2&&order[0]==="a"&&order[1]==="b","real mailbox dispatch serialized");
 check(readCmd().id==="b","no wrong stale command survived");
 const order2=[],stop2=respond(order2,{wrongFirst:true});
 const rc=await send(home,"c",{action:"read"},1200);stop2();
 check(rc.ok===true&&rc.id==="c","stale mismatched id ignored until true reply");
 check(order2.length===1,"no duplicate side effect issued");
 const rd=await send(home,"lost",{action:"click"},130);
 check(rd.ok===false&&rd.code==="BROWSER_NO_REPLY_OUTCOME_UNKNOWN","real no reply explicit outcome unknown");
 check(rd.outcomeUnknown===true&&rd.retrySafe===false,"side effect never falsely safe to retry");
 const before=readCmd().id;
 const re=await send(home,"unsafe-next",{action:"click"},200);
 check(re.ok===false&&re.code==="BROWSER_MAILBOX_NEEDS_RESYNC","poisoned mailbox refuses further action");
 check(readCmd().id===before,"no extra command emitted after lost reply");
 const other=fs.mkdtempSync(path.join(os.tmpdir(),"p70-browser-independent-"));
 try{
  const otherSeen=[];let done=false;
  const interval=setInterval(()=>{
   let data;try{data=JSON.parse(fs.readFileSync(path.join(other,cmdFile),"utf8"));}catch{return;}
   if(done)return;done=true;otherSeen.push(data.id);
   fs.writeFileSync(path.join(other,resFile),JSON.stringify({id:data.id,ok:true}),"utf8");
  },6);
  const fresh=await send(other,"separate",{action:"read"},1000);clearInterval(interval);
  check(fresh.ok===true&&otherSeen.length===1,"other isolated home remains operable");
 }finally{fs.rmSync(other,{recursive:true,force:true});}
 const staleErr=await send(home,"still-blocked",{action:"read"},50);
 check(staleErr.code==="BROWSER_MAILBOX_NEEDS_RESYNC","quarantine persists until true resync");
 check(!source.includes("P70_AUTOMATIC_RETRY"),"no unsafe replay");
 console.log("P70_ACTUAL_PATCHED_JS_MAILBOX_TESTS=PASS assertions="+tests);
 console.log("P70_CONCURRENT_TWO_REQUESTS_SERIALIZED=PASS");
 console.log("P70_MISMATCHED_REPLY_DID_NOT_COMPLETE=PASS");
 console.log("P70_NO_REPLY_OUTCOME_UNKNOWN_FAIL_CLOSED=PASS");
 console.log("P70_AUTOMATIC_COMMENT_RETRY=NO");
 console.log("P70_ANDROID_NATIVE_EXECUTOR_E2E=NOT_TESTED");
}finally{fs.rmSync(home,{recursive:true,force:true});}
