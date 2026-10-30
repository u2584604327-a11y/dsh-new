/**
 * Real original AgentLoop.create single synthetic-session probe.
 * Uses original Cordis, AgentLoop, SessionStore, AgentRegistry, LlmRuntime,
 * ToolRuntime, SystemPrompt and SessionProjectionRegistry from exact APK.
 * No prompt, registered agent, real model or tool is supplied.
 * Outbound fetch/HTTP/TCP are fail-closed, and the attempt is one-shot.
 * Result is diagnostic, NEVER proof of an Android session.
 */
import {Context} from '@deepseek-ai/cordis';
import {AgentRegistry} from '@deepseek-ai/dsh-agent';
import {SessionStore} from '@deepseek-ai/dsh-session';
import {LlmRuntime} from '@deepseek-ai/dsh-llm';
import {ToolRuntime} from '@deepseek-ai/dsh-tools';
import {SystemPrompt} from '@deepseek-ai/dsh-system-prompt';
import {SessionProjectionRegistry} from '@deepseek-ai/dsh-session-projection';
import {AgentLoop} from '@deepseek-ai/dsh-agent-loop';
import net from 'node:net';
import http from 'node:http';
import https from 'node:https';

let networkAttempts=0;
const deny=()=>{
  networkAttempts++;
  throw new Error('P98_NO_NETWORK_ALLOWED');
};
globalThis.fetch=deny;
net.Socket.prototype.connect=deny;
net.connect=deny;
net.createConnection=deny;
http.request=deny;
http.get=deny;
https.request=deny;
https.get=deny;

const log=(key,value)=>process.stdout.write('P98_ORIGINAL_SESSION_'+key+'='+String(value)+'\n');
const context=new Context();
const modules=[
  ['agents',AgentRegistry],
  ['sessions',SessionStore],
  ['llm',LlmRuntime],
  ['systemPrompt',SystemPrompt],
  ['tools',ToolRuntime],
  ['sessionProjections',SessionProjectionRegistry],
  ['agentLoop',AgentLoop]
];
let handle=null;
let outcome='UNSET';
try{
 for(const [key,Class] of modules){
   await context.plugin(Class,key==='tools'
     ? {mode:'native',maxParallelSubCalls:1}:{});
 }
 const loop=context.get('agentLoop');
 if(typeof loop?.create!=='function')throw new Error('ORIGINAL_AGENTLOOP_CREATE_MISSING');
 log('REAL_LOOP_CREATE_AVAILABLE','YES');
 const id='p98_nonexistent_fixture_agent_no_model';
 try{
   // Explicitly not a normal user prompt: this checks whether the original
   // runtime can create its own session from an otherwise empty registry.
   handle=await Promise.race([
      loop.create(id),
      new Promise((_,reject)=>setTimeout(
        ()=>reject(new Error('P98_CREATE_TIMEOUT')),2500))
   ]);
   outcome='CREATED_WITHOUT_USER_PROMPT';
   log('CREATE_RETURN_TYPE',typeof handle);
   log('CREATE_RETURN_KEYS',Object.keys(handle||{}).slice(0,15).join(','));
   log('SESSION_STORE_GET_TYPE',typeof context.get('sessions')?.get(id));
   const stored=context.get('sessions')?.get(id);
   if(!stored || typeof handle!=='object' || handle.id!==id)
      throw new Error('ORIGINAL_SESSION_NOT_CREATED_OR_PERSISTED');
   const ownFunctions=Object.entries(handle).filter(([key,value])=>
     typeof value==='function'&&/^[A-Za-z_$][A-Za-z0-9_$]{0,64}$/.test(key))
     .map(([key,value])=>({name:key,arity:value.length})).slice(0,45);
   log('ACTUAL_HANDLE_FUNCTIONS',JSON.stringify(ownFunctions));
   // Do not invoke session command methods: inspect names and arities only.
   function methods(object){
     if(!object || (typeof object!=='object' && typeof object!=='function'))return [];
     const prototype=Object.getPrototypeOf(object);
     return Object.getOwnPropertyNames(prototype||{}).filter(key=>
       key!=='constructor' && /^[a-zA-Z_$][a-zA-Z0-9_$]{0,64}$/.test(key)
       && typeof Object.getOwnPropertyDescriptor(prototype,key)?.value==='function'
     ).slice(0,35).map(name=>({
       name,arity:Object.getOwnPropertyDescriptor(prototype,name).value.length
     }));
   }
   function safeMethodContract(object,name){
     const method=Object.getPrototypeOf(object)?.[name];
     if(typeof method!=='function')return null;
     const source=Function.prototype.toString.call(method);
     const sig=source.match(/^[^(]*\(([^)]{0,360})\)/)?.[1]||'';
     const parameters=sig.split(',').map(x=>x.trim())
       .filter(x=>/^[A-Za-z_$][A-Za-z0-9_$]{0,64}$/.test(x)).slice(0,10);
     const fields=[...source.matchAll(/(?:this|message|request|options|input|signal|turn|session)\??\.([A-Za-z_$][A-Za-z0-9_$]{0,64})/g)]
       .map(x=>x[1]);
     const safeLiterals=[...source.matchAll(/['"]([A-Za-z_$][A-Za-z0-9_$-]{0,31})['"]/g)]
       .map(x=>x[1]).filter(x=>/^(?:nextTurn|nextStep|followup|steer|inject|user|assistant|tool|idle|running|aborted)$/.test(x));
     const sendMatch=source.match(/\.send\(\s*[^,]{1,120},\s*([^,)]{1,120}),\s*([^)\n]{1,120})\)/);
     const cleanExpr=(value)=>{
       const v=String(value||'').trim();
       return /^(?:true|false|[A-Za-z_$][A-Za-z0-9_$]*(?:\.[A-Za-z_$][A-Za-z0-9_$]*){0,4}|['"][A-Za-z_$][A-Za-z0-9_$-]{0,31}['"])$/.test(v)
         ? v : 'COMPLEX_OR_UNSAFE';
     };
     return {name,arity:method.length,parameters,
       referencedFields:[...new Set(fields)].slice(0,45),
       safeLiterals:[...new Set(safeLiterals)],
       sendTargetExpression:sendMatch?cleanExpr(sendMatch[1]):null,
       sendWakeupExpression:sendMatch?cleanExpr(sendMatch[2]):null,
       isAsync:method.constructor.name==='AsyncFunction'};
   }
   function safeOwnShape(object){
     if(!object || typeof object!=='object')return [];
     return Object.keys(object)
       .filter(key=>/^[A-Za-z_$][A-Za-z0-9_$]{0,64}$/.test(key))
       .slice(0,45).map(key=>{
         const value=object[key];
         return {
           key,
           type:Array.isArray(value)?'array':typeof value,
           length:Array.isArray(value)||typeof value==='string'?value.length:undefined,
           nullValue:value===null
         };
       });
   }
   log('HANDLE_PROTOTYPE_METHODS',JSON.stringify(methods(handle)));
   log('SEND_METHOD_CONTRACT',JSON.stringify(safeMethodContract(handle,'send')));
   log('FOLLOWUP_METHOD_CONTRACT',JSON.stringify(safeMethodContract(handle,'followup')));
   log('STEER_METHOD_CONTRACT',JSON.stringify(safeMethodContract(handle,'steer')));
   log('INJECT_METHOD_CONTRACT',JSON.stringify(safeMethodContract(handle,'inject')));
   const currentInbox=handle.inbox.current();
   log('INBOX_CURRENT_RETURN_TYPE',Array.isArray(currentInbox)?'array':typeof currentInbox);
   log('INBOX_CURRENT_RETURN_CONSTRUCTOR',
     /^[A-Za-z_$][A-Za-z0-9_$]{0,64}$/.test(currentInbox?.constructor?.name||'')
       ?currentInbox.constructor.name:'UNKNOWN');
   log('INBOX_CURRENT_RETURN_IS_MAP',currentInbox instanceof Map);
   log('INBOX_CURRENT_RETURN_IS_SET',currentInbox instanceof Set);
   log('INBOX_CURRENT_RETURN_SHAPE',JSON.stringify(
     currentInbox && typeof currentInbox==='object' ? safeOwnShape(currentInbox) : []));
   log('INBOX_CURRENT_RETURN_OWN_PROPERTY_NAMES',JSON.stringify(
     currentInbox && typeof currentInbox==='object'
       ?Object.getOwnPropertyNames(currentInbox)
          .filter(x=>/^[A-Za-z_$][A-Za-z0-9_$]{0,64}$/.test(x)).slice(0,45):[]));
   log('INBOX_CURRENT_RETURN_PROTOTYPE_METHODS',JSON.stringify(methods(currentInbox)));
   if(currentInbox instanceof Map){
     log('INBOX_CURRENT_RETURN_MAP_SIZE',currentInbox.size);
     log('INBOX_CURRENT_RETURN_MAP_SAFE_KEYS',JSON.stringify(
       [...currentInbox.keys()].filter(x=>typeof x==='string' &&
         /^[A-Za-z_$][A-Za-z0-9_$-]{0,64}$/.test(x)).slice(0,45)));
   }
   log('SESSION_APPEND_CONTRACT',JSON.stringify(safeMethodContract(handle.session,'append')));
   log('SESSION_COMMIT_CONTRACT',JSON.stringify(safeMethodContract(handle.session,'commit')));
   log('INBOX_PROTOTYPE_METHODS',JSON.stringify(methods(handle.inbox)));
   log('SESSION_PROTOTYPE_METHODS',JSON.stringify(methods(handle.session)));
   log('DISPATCH_PROTOTYPE_METHODS',JSON.stringify(methods(handle.dispatch)));
   for(const name of ['current','mutate','splice','append','push','shift','clear']){
     const contract=safeMethodContract(handle.inbox,name);
     if(contract)log('INBOX_'+name.toUpperCase()+'_CONTRACT',JSON.stringify(contract));
   }
   log('INBOX_OWN_SHAPE',JSON.stringify(safeOwnShape(handle.inbox)));
   const inboxCtor=Object.getPrototypeOf(handle.inbox)?.constructor;
   log('INBOX_CONSTRUCTOR_ARITY',typeof inboxCtor==='function'?inboxCtor.length:'MISSING');
   const projectionService=context.get('sessionProjections');
   log('SESSION_PROJECTION_SERVICE_TYPE',typeof projectionService);
   log('SESSION_PROJECTION_SERVICE_METHODS',JSON.stringify(methods(projectionService)));
   log('SESSION_PROJECTION_SERVICE_OWN_SHAPE',JSON.stringify(safeOwnShape(projectionService)));
   const registrations=projectionService?.registrations;
   const registrationCtor=registrations?.constructor?.name||'MISSING';
   const registrationIsMap=registrations instanceof Map;
   const registrationIsSet=registrations instanceof Set;
   const registrationSize=typeof registrations?.size==='number'
     ?registrations.size:Object.keys(registrations||{}).length;
   function safeRegistrationKey(value){
     if(typeof value==='string' && /^[A-Za-z0-9_.:/-]{1,100}$/.test(value))return value;
     if(typeof value==='symbol' && /^[A-Za-z0-9_.:/-]{1,100}$/.test(value.description||''))return 'symbol:'+value.description;
     return typeof value;
   }
   let registrationKeys=[];
   let registrationDefinitions=[];
   if(registrationIsMap){
     registrationKeys=[...registrations.keys()].slice(0,40).map(safeRegistrationKey);
     registrationDefinitions=[...registrations.entries()].slice(0,20).map(([key,def])=>({
       key:safeRegistrationKey(key),
       type:Array.isArray(def)?'array':typeof def,
       ownKeys:def&&typeof def==='object'
         ?Object.keys(def).filter(k=>/^[A-Za-z_$][A-Za-z0-9_$]{0,64}$/.test(k)).slice(0,24):[]
     }));
   }else if(registrations&&typeof registrations==='object'){
     registrationKeys=Object.keys(registrations)
       .filter(k=>/^[A-Za-z0-9_.:/-]{1,100}$/.test(k)).slice(0,40);
     registrationDefinitions=registrationKeys.slice(0,20).map(key=>{
       const def=registrations[key];
       return {key,type:Array.isArray(def)?'array':typeof def,
         ownKeys:def&&typeof def==='object'
          ?Object.keys(def).filter(k=>/^[A-Za-z_$][A-Za-z0-9_$]{0,64}$/.test(k)).slice(0,24):[]};
     });
   }
   log('SESSION_PROJECTION_REGISTRATIONS_CONSTRUCTOR',registrationCtor);
   log('SESSION_PROJECTION_REGISTRATIONS_IS_MAP',registrationIsMap);
   log('SESSION_PROJECTION_REGISTRATIONS_IS_SET',registrationIsSet);
   log('SESSION_PROJECTION_REGISTRATIONS_SIZE',registrationSize);
   log('SESSION_PROJECTION_REGISTRATION_KEYS',JSON.stringify(registrationKeys));
   log('SESSION_PROJECTION_REGISTRATION_DEFINITIONS',JSON.stringify(registrationDefinitions));
   log('INBOX_PROJECTIONS_SAME_SERVICE',handle.inbox?.projections===projectionService);
   for(const name of methods(projectionService).map(x=>x.name).slice(0,20)){
     const contract=safeMethodContract(projectionService,name);
     if(contract)log('SESSION_PROJECTION_'+name.toUpperCase()+'_CONTRACT',JSON.stringify(contract));
   }
   for(const field of ['session','inbox','dispatch','phase','ctx']){
     const obj=handle[field];
     log('ACTUAL_HANDLE_'+field.toUpperCase()+'_TYPE',typeof obj);
     if(obj && typeof obj==='object'){
       const keys=Object.keys(obj).filter(k=>/^[A-Za-z_$][A-Za-z0-9_$]{0,64}$/.test(k)).slice(0,30);
       log('ACTUAL_HANDLE_'+field.toUpperCase()+'_KEYS',JSON.stringify(keys));
     }
   }
   log('ACTUAL_SESSION_CREATED_AND_STORED','PASS');
 }catch(error){
   const code=String(error?.code||error?.name||'UNKNOWN')
     .replace(/[^a-zA-Z0-9_]/g,'').slice(0,80);
   const reason=String(error?.message||'').slice(0,140)
     .replace(/(?:\/[A-Za-z0-9._/-]+)|(?:Bearer [A-Za-z0-9._-]+)/g,'<REDACTED>');
   outcome='BLOCKED_'+code;
   log('CREATE_ERROR_TYPE',code);
   log('CREATE_ERROR_REASON',reason);
 }
} finally{
 if(handle){
    for(const method of ['close','dispose']){
      if(typeof handle[method]==='function'){
        try{await handle[method]();}catch{}
        break;
      }
    }
 }
 if(typeof context.dispose==='function'){
   try{await context.dispose();}catch{}
 }
}
log('CREATE_OUTCOME',outcome);
log('BLOCKED_NETWORK_ATTEMPTS',networkAttempts);
if(networkAttempts!==0){
  process.exitCode=2;
  log('NETWORK_SIDE_EFFECT_GATE','FAIL');
}else log('NETWORK_SIDE_EFFECT_GATE','PASS');
log('MODEL_POST_COUNT','NOT_OBSERVED_REAL_PROVIDER');
log('ORIGINAL_ANDROID_ENGINE_ATTACHED','NO');
log('ORIGINAL_AGENT_AUTOCONTINUATION','NOT_TESTED');
if(outcome!=='CREATED_WITHOUT_USER_PROMPT'){
  log('ACTUAL_SESSION_CREATED_AND_STORED','FAIL');
  process.exitCode=2;
}
log('SOURCE_LOCKED_ONE_SHOT_PROBE','PASS');
