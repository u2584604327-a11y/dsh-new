/**
 * Read-only source contract scanner for the exact SHA-locked original
 * dsh-api-session-controller package extracted transiently in CI.
 * Prints identifiers/contracts only; never emits original source text.
 */
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const safeId=s=>/^[A-Za-z_$][A-Za-z0-9_$]{0,80}$/.test(s);
const safeLiteral=s=>/^[A-Za-z0-9_.:/-]{1,100}$/.test(s) && !/^(?:http|https):/i.test(s);

function packageRoot(entry){
  let dir=path.dirname(entry);
  for(let i=0;i<8;i++){
    const p=path.join(dir,'package.json');
    if(fs.existsSync(p))return dir;
    const next=path.dirname(dir);
    if(next===dir)break;
    dir=next;
  }
  throw new Error('PACKAGE_ROOT_NOT_FOUND');
}

function filesUnder(root){
  const out=[];
  const stack=[root];
  while(stack.length){
    const dir=stack.pop();
    for(const ent of fs.readdirSync(dir,{withFileTypes:true})){
      const p=path.join(dir,ent.name);
      if(ent.isDirectory())stack.push(p);
      else if(ent.isFile() && /\.(?:js|mjs|cjs)$/.test(ent.name)){
        const st=fs.statSync(p);
        if(st.size<=3_000_000)out.push(p);
      }
    }
  }
  return out.slice(0,250);
}

function findClassBlock(source,name){
  const re=new RegExp('class\\s+'+name+'\\b');
  const m=re.exec(source);
  if(!m)return null;
  const open=source.indexOf('{',m.index);
  if(open<0)return null;
  let depth=0, quote=null, esc=false, line=false, block=false;
  for(let i=open;i<source.length;i++){
    const ch=source[i], nx=source[i+1];
    if(line){ if(ch==='\n')line=false; continue; }
    if(block){ if(ch==='*'&&nx==='/'){block=false;i++;} continue; }
    if(quote){
      if(esc){esc=false;continue;}
      if(ch==='\\'){esc=true;continue;}
      if(ch===quote){quote=null;continue;}
      continue;
    }
    if(ch==='/'&&nx==='/'){line=true;i++;continue;}
    if(ch==='/'&&nx==='*'){block=true;i++;continue;}
    if(ch==="'"||ch==='"'||ch==='\`'){quote=ch;continue;}
    if(ch==='{')depth++;
    else if(ch==='}'){
      depth--;
      if(depth===0)return source.slice(open+1,i);
    }
  }
  return null;
}

function balancedMethod(classBody,name){
  const re=new RegExp('(?:^|[^A-Za-z0-9_$])'+name+'\\s*\\(([^)]{0,500})\\)\\s*\\{','g');
  const m=re.exec(classBody);
  if(!m)return null;
  const open=classBody.indexOf('{',m.index);
  let depth=0, quote=null, esc=false, line=false, block=false;
  for(let i=open;i<classBody.length;i++){
    const ch=classBody[i], nx=classBody[i+1];
    if(line){ if(ch==='\n')line=false; continue; }
    if(block){ if(ch==='*'&&nx==='/'){block=false;i++;} continue; }
    if(quote){
      if(esc){esc=false;continue;}
      if(ch==='\\'){esc=true;continue;}
      if(ch===quote){quote=null;continue;}
      continue;
    }
    if(ch==='/'&&nx==='/'){line=true;i++;continue;}
    if(ch==='/'&&nx==='*'){block=true;i++;continue;}
    if(ch==="'"||ch==='"'||ch==='\`'){quote=ch;continue;}
    if(ch==='{')depth++;
    else if(ch==='}'){
      depth--;
      if(depth===0)return {params:m[1],body:classBody.slice(open+1,i)};
    }
  }
  return null;
}

function callArgumentSummary(body,callee){
  const needle=callee+'(';
  const start=body.indexOf(needle);
  if(start<0)return null;
  const open=start+callee.length;
  let depth=0, quote=null, esc=false, line=false, block=false, end=-1;
  for(let i=open;i<body.length;i++){
    const ch=body[i], nx=body[i+1];
    if(line){if(ch==='\n')line=false;continue;}
    if(block){if(ch==='*'&&nx==='/'){block=false;i++;}continue;}
    if(quote){
      if(esc){esc=false;continue;}
      if(ch==='\\'){esc=true;continue;}
      if(ch===quote){quote=null;continue;}
      continue;
    }
    if(ch==='/'&&nx==='/'){line=true;i++;continue;}
    if(ch==='/'&&nx==='*'){block=true;i++;continue;}
    if(ch==="'"||ch==='"'||ch==='\`'){quote=ch;continue;}
    if(ch==='(')depth++;
    else if(ch===')'){
      depth--;
      if(depth===0){end=i;break;}
    }
  }
  if(end<0)return {callee,balanced:false};
  const args=body.slice(open+1,end);
  const identifiers=[...args.matchAll(/\b([A-Za-z_$][A-Za-z0-9_$]{0,80})\b/g)]
    .map(x=>x[1]).filter(x=>safeId(x)&&!['true','false','null','undefined','new','await','return'].includes(x));
  const memberRefs=[...args.matchAll(/([A-Za-z_$][A-Za-z0-9_$]{0,80}(?:\??\.[A-Za-z_$][A-Za-z0-9_$]{0,80}){1,5})/g)]
    .map(x=>x[1].replaceAll('?.','.')).filter(x=>x.split('.').every(safeId));
  const literals=[...args.matchAll(/["']([^"'\n\r]{1,100})["']/g)]
    .map(x=>x[1]).filter(safeLiteral);
  let topCommas=0, p=0,b=0,s=0,q=null,e=false;
  for(const ch of args){
    if(q){if(e){e=false;continue;}if(ch==='\\'){e=true;continue;}if(ch===q)q=null;continue;}
    if(ch==="'"||ch==='"'||ch==='\`'){q=ch;continue;}
    if(ch==='(')p++; else if(ch===')')p--;
    else if(ch==='{')b++; else if(ch==='}')b--;
    else if(ch==='[')s++; else if(ch===']')s--;
    else if(ch===','&&p===0&&b===0&&s===0)topCommas++;
  }
  const objectPropertyKeys=[...args.matchAll(/(?:^|[,{])\s*([A-Za-z_$][A-Za-z0-9_$]{0,80})\s*:/g)]
    .map(x=>x[1]).filter(safeId);
  const spreads=[...args.matchAll(/\.\.\.([A-Za-z_$][A-Za-z0-9_$]{0,80}(?:\.[A-Za-z_$][A-Za-z0-9_$]{0,80}){0,4})/g)]
    .map(x=>x[1]).filter(x=>x.split('.').every(safeId));
  return {callee,balanced:true,argCount:args.trim()?topCommas+1:0,
    identifiers:[...new Set(identifiers)].slice(0,35),
    memberRefs:[...new Set(memberRefs)].slice(0,35),
    objectPropertyKeys:[...new Set(objectPropertyKeys)].slice(0,35),
    spreadRefs:[...new Set(spreads)].slice(0,20),
    safeLiterals:[...new Set(literals)].slice(0,30)};
}

function contract(name,method){
  if(!method)return {name,present:false};
  const body=method.body;
  const params=method.params.split(',').map(x=>x.trim())
    .filter(safeId).slice(0,12);
  const requestFields=[...body.matchAll(/request\??\.([A-Za-z_$][A-Za-z0-9_$]{0,80})/g)]
    .map(x=>x[1]).filter(safeId);
  const thisFields=[...body.matchAll(/this\??\.([A-Za-z_$][A-Za-z0-9_$]{0,80})/g)]
    .map(x=>x[1]).filter(safeId);
  const memberCalls=[...body.matchAll(/([A-Za-z_$][A-Za-z0-9_$]{0,80}(?:\??\.[A-Za-z_$][A-Za-z0-9_$]{0,80}){1,5})\s*\(/g)]
    .map(x=>x[1].replaceAll('?.','.'))
    .filter(x=>x.split('.').every(safeId));
  const literals=[...body.matchAll(/["']([^"'\n\r]{1,100})["']/g)]
    .map(x=>x[1]).filter(safeLiteral);
  const called=[...body.matchAll(/([A-Za-z_$][A-Za-z0-9_$]{0,80})\s*\(/g)]
    .map(x=>x[1]).filter(x=>safeId(x)&&!['if','for','while','switch','catch'].includes(x));
  const callTargets=[...new Set(memberCalls)].filter(x=>
    ['this.ctx.agents.create','this.ctx.agents.resume','this.createAgent','this.createMinted',
     'this.composeAgent','this.claim','this.inOrder','this.created','agent.session.append',
     'agent.followup','agent.steer'].includes(x));
  const callArguments=callTargets.map(x=>callArgumentSummary(body,x)).filter(Boolean);
  return {
    name,present:true,arity:params.length,params,
    requestFields:[...new Set(requestFields)].slice(0,50),
    thisFields:[...new Set(thisFields)].slice(0,50),
    memberCalls:[...new Set(memberCalls)].slice(0,60),
    memberCallArguments:callArguments,
    safeLiterals:[...new Set(literals)].slice(0,80),
    calledIdentifiers:[...new Set(called)].slice(0,60),
    sourceSize:body.length
  };
}

const entry=fileURLToPath(import.meta.resolve('@deepseek-ai/dsh-api-session-controller'));
const root=packageRoot(entry);
let found=null, foundPath=null;
for(const file of filesUnder(root)){
  const source=fs.readFileSync(file,'utf8');
  if(!source.includes('SessionCommandController'))continue;
  const block=findClassBlock(source,'SessionCommandController');
  if(block){found=block;foundPath=file;break;}
}
if(!found)throw new Error('SESSION_COMMAND_CONTROLLER_CLASS_NOT_FOUND');

const methods=['constructor','create','prompt','updateQueue','cancel','attachment'];
const contracts=methods.map(name=>contract(name,balancedMethod(found,name)));
const classLiterals=[...found.matchAll(/["']([^"'\n\r]{1,100})["']/g)]
  .map(x=>x[1]).filter(safeLiteral);
const classThisFields=[...found.matchAll(/this\??\.([A-Za-z_$][A-Za-z0-9_$]{0,80})/g)]
  .map(x=>x[1]).filter(safeId);

process.stdout.write('P98_SESSION_COMMAND_SOURCE_FILE_BASENAME='+path.basename(foundPath)+'\n');
process.stdout.write('P98_SESSION_COMMAND_CLASS_FIELDS='+JSON.stringify([...new Set(classThisFields)].slice(0,80))+'\n');
process.stdout.write('P98_SESSION_COMMAND_CLASS_SAFE_LITERALS='+JSON.stringify([...new Set(classLiterals)].slice(0,100))+'\n');
process.stdout.write('P98_SESSION_COMMAND_METHOD_CONTRACTS='+JSON.stringify(contracts)+'\n');
let agentFound=null, agentFoundPath=null;
for(const file of filesUnder(root)){
  const source=fs.readFileSync(file,'utf8');
  if(!source.includes('ApiSessionAgentController'))continue;
  const block=findClassBlock(source,'ApiSessionAgentController');
  if(block){agentFound=block;agentFoundPath=file;break;}
}
if(!agentFound)throw new Error('API_SESSION_AGENT_CONTROLLER_CLASS_NOT_FOUND');

const agentMethods=['constructor','createSession','created','createMinted','composeAgent','inOrder','claim','createAgent','reuseLive','reuseSetup','agentOptions','resolveAgent','selectionFor','serializeImageAdmission'];
const agentContracts=agentMethods.map(name=>contract(name,balancedMethod(agentFound,name)));
const agentLiterals=[...agentFound.matchAll(/["']([^"'\n\r]{1,100})["']/g)]
  .map(x=>x[1]).filter(safeLiteral);
const agentFields=[...agentFound.matchAll(/this\??\.([A-Za-z_$][A-Za-z0-9_$]{0,80})/g)]
  .map(x=>x[1]).filter(safeId);

process.stdout.write('P98_API_SESSION_AGENT_SOURCE_FILE_BASENAME='+path.basename(agentFoundPath)+'\n');
process.stdout.write('P98_API_SESSION_AGENT_CLASS_FIELDS='+JSON.stringify([...new Set(agentFields)].slice(0,80))+'\n');
process.stdout.write('P98_API_SESSION_AGENT_CLASS_SAFE_LITERALS='+JSON.stringify([...new Set(agentLiterals)].slice(0,100))+'\n');
process.stdout.write('P98_API_SESSION_AGENT_METHOD_CONTRACTS='+JSON.stringify(agentContracts)+'\n');
process.stdout.write('P98_SESSION_COMMAND_SOURCE_CONTRACT=PASS\n');
process.stdout.write('P98_SESSION_COMMAND_SOURCE_TEXT_EXPORTED=NO\n');
