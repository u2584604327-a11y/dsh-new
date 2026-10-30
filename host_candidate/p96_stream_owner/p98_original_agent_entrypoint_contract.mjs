/**
 * Exact original agent/session entrypoint contract inventory.
 * Reflects imported SHA-pinned code without creating a session, executing
 * a tool, performing I/O or logging any code body / secrets.
 * Identifiers only; no original source file exported or archived.
 */
import {AgentLoop} from '@deepseek-ai/dsh-agent-loop';
import {SessionStore} from '@deepseek-ai/dsh-session';
import {AgentRegistry} from '@deepseek-ai/dsh-agent';
import {SessionController} from '@deepseek-ai/dsh-api-session-controller';
import * as SessionControllerModule from '@deepseek-ai/dsh-api-session-controller';
import {LlmRuntime} from '@deepseek-ai/dsh-llm';

const selected=[
  ['AgentLoop',AgentLoop,['create','resume','resumeWith','prepare']],
  ['SessionStore',SessionStore,['create','get','update','append','createSession']],
  ['AgentRegistry',AgentRegistry,['register','get','create']],
  ['SessionController',SessionController,['prompt','follow','liveProjections']],
  ['LlmRuntime',LlmRuntime,['stream','generate','create','get']]
];
const safe=(s)=>/^[A-Za-z_$][A-Za-z0-9_$]{0,70}$/.test(s);
function info(klass,method){
  const fn=klass.prototype?.[method];
  if(typeof fn!=='function')return null;
  const body=Function.prototype.toString.call(fn);
  const declared=body.match(/^[^(]*\(([^)]{0,450})\)/)?.[1]??'';
  const params=declared.split(',').map(x=>x.trim()).filter(safe).slice(0,12);
  const propertyNames=[...body.matchAll(/(?:this|args|options|input|params|session|turn|request|signal)\??\.([A-Za-z_$][A-Za-z0-9_$]{0,70})/g)]
    .map(x=>x[1]).filter(safe);
  const requestFields=[...body.matchAll(/request\??\.([A-Za-z_$][A-Za-z0-9_$]{0,70})/g)]
    .map(x=>x[1]).filter(safe);
  const calls=[...body.matchAll(/(?:this\.)?([A-Za-z_$][A-Za-z0-9_$]{0,70})\s*\(/g)]
    .map(x=>x[1]).filter(x=>safe(x)&&!['if','for','while','switch','catch'].includes(x));
  const memberCalls=[...body.matchAll(/([A-Za-z_$][A-Za-z0-9_$]{0,70}(?:\??\.[A-Za-z_$][A-Za-z0-9_$]{0,70}){1,4})\s*\(/g)]
    .map(x=>x[1].replaceAll('?.','.'))
    .filter(x=>x.split('.').every(safe));
  const safeLiterals=[...body.matchAll(/["']([A-Za-z0-9_.:/-]{1,90})["']/g)]
    .map(x=>x[1]).filter(x=>!/^(?:http|https):/i.test(x));
  return {
    method,arity:fn.length,params,
    propertyNames:[...new Set(propertyNames)].slice(0,40),
    requestFields:[...new Set(requestFields)].slice(0,40),
    calledIdentifiers:[...new Set(calls)].slice(0,45),
    memberCalls:[...new Set(memberCalls)].slice(0,45),
    safeLiterals:[...new Set(safeLiterals)].slice(0,45),
    isAsync:fn.constructor?.name==='AsyncFunction',
    sourceSize:body.length
  };
}
for(const [label,klass,focus] of selected){
  const methods=focus.map(x=>info(klass,x)).filter(Boolean);
  process.stdout.write('P98_ORIGINAL_ENTRYPOINT='+label+' '+JSON.stringify(methods)+'\n');
}
const moduleExports=Object.keys(SessionControllerModule).filter(safe).sort();
process.stdout.write('P98_ORIGINAL_SESSION_CONTROLLER_MODULE_EXPORTS='+JSON.stringify(moduleExports)+'\n');
for(const name of moduleExports){
  const value=SessionControllerModule[name];
  if(typeof value!=='function')continue;
  const proto=Object.getPrototypeOf(value.prototype||{})?value.prototype:null;
  const protoMethods=proto?Object.getOwnPropertyNames(proto)
    .filter(x=>x!=='constructor'&&safe(x)&&typeof Object.getOwnPropertyDescriptor(proto,x)?.value==='function')
    .slice(0,35).map(x=>({name:x,arity:Object.getOwnPropertyDescriptor(proto,x).value.length})):[];
  const staticKeys=Object.getOwnPropertyNames(value)
    .filter(x=>!['length','name','prototype'].includes(x)&&safe(x)).slice(0,30);
  process.stdout.write('P98_ORIGINAL_SESSION_CONTROLLER_EXPORT_CONTRACT='+JSON.stringify({
    name,arity:value.length,prototypeMethods:protoMethods,staticKeys
  })+'\n');
}
process.stdout.write('P98_ORIGINAL_ENTRYPOINT_SOURCE_ONLY=PASS\n');
process.stdout.write('P98_ORIGINAL_SESSION_CREATED=NO\n');
