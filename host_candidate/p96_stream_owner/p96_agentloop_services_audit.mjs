/**
 * Read-only original service dependency/export survey. The only execution is
 * dynamic import of SHA-locked original DSH node_modules. No ctx/plugin/agent
 * start, no browser, credentials or model requests.
 */
const specs=[
 ['agents','@deepseek-ai/dsh-agent'],
 ['sessions','@deepseek-ai/dsh-session'],
 ['llm','@deepseek-ai/dsh-llm'],
 ['tools','@deepseek-ai/dsh-tools'],
 ['systemPrompt','@deepseek-ai/dsh-system-prompt'],
 ['sessionProjections','@deepseek-ai/dsh-session-projection'],
 ['sessionPersistence','@deepseek-ai/dsh-session-persistence']
];
const safe=n=>/^[A-Za-z0-9@/._-]{1,90}$/.test(n);
for(const [service,pkg] of specs) {
 try{
  const imported=await import(pkg);
  const named=Object.entries(imported).filter(([key,val])=>
    /^[A-Z][A-Za-z0-9]{1,80}$/.test(key)&&typeof val==='function'
  );
  const candidates=named.filter(([key,val])=>
    key.toLowerCase().includes(service.toLowerCase().replace('projections','projection'))
      || /^(Session|Agent|Model|Llm|SystemPrompt|Tools|Projection)/.test(key)
  ).slice(0,16);
  process.stdout.write('P96_AGENT_SERVICE_PACKAGE='+service+' MODULE=IMPORTED'
   +' CANDIDATES='+JSON.stringify(candidates.map(([key,val])=>({
    export:key,
    dependencyKeys:Array.isArray(val.inject)?val.inject.slice(0,15)
      :val.inject&&typeof val.inject==='object'?Object.keys(val.inject).slice(0,15):[]
   })))+'\n');
 }catch(e){
  const err=String(e?.message||'');
  const spec=err.match(/Cannot find (?:package|module) '([^']{1,140})'/)?.[1];
  process.stdout.write('P96_AGENT_SERVICE_PACKAGE='+service+
    ' MODULE=NOT_IMPORTED'+' ERROR='+(e?.code||e?.name||'UNKNOWN')+
    ' MISSING='+((spec&&safe(spec))?spec:'UNKNOWN')+'\n');
 }
}
process.stdout.write('P96_AGENT_SERVICE_DEPENDENCY_AUDIT=PASS\n');
process.stdout.write('P96_ORIGINAL_AGENT_LOOP_RUNTIME_READY=NOT_PROVEN\n');
