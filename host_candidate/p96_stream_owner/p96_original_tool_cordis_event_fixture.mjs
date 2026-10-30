/**
 * Real Cordis event delivery for original ToolRuntime.notifyResult.
 * Does not execute any tool, model, WebView, or Android native code.
 */
import assert from 'node:assert/strict';
import {Context} from '@deepseek-ai/cordis';
import {ToolRuntime} from '@deepseek-ai/dsh-tools';

assert.equal(typeof Context,'function');
const ctx=new Context();
const observed=[];
ctx.on('tools/result',(exec,result)=> {
  observed.push({exec,result});
});
const fakeRuntime={ctx};
const exec={name:'fixture_read_only',callId:'call_fixture12345',agent:null};
const result=Object.freeze({ok:true,code:'SYNTHETIC_ONLY'});
try{
  ToolRuntime.prototype.notifyResult.call(fakeRuntime,exec,result);
  assert.equal(observed.length,1,'real Cordis must dispatch exactly once');
  assert.equal(observed[0].exec,exec,'correlation envelope must be same object');
  assert.equal(observed[0].result,result,'result must be passed unchanged');
  assert.equal(Object.isFrozen(exec),true);
  process.stdout.write('P96_ORIGINAL_TOOL_RUNTIME_TO_REAL_CORDIS_EVENT=PASS\n');
  process.stdout.write('P96_ORIGINAL_TOOL_RESULT_EVENT=tools/result\n');
  process.stdout.write('P96_ORIGINAL_CORDIS_TO_AGENT_MODEL_CONTINUATION=NOT_TESTED\n');
}catch(e) {
  process.stdout.write('P96_ORIGINAL_TOOL_CORDIS_EVENT_OBSERVER=BLOCKED_'+
    (e?.code||e?.name||'UNKNOWN')+'\n');
  process.exitCode=2;
}finally{
  // Standalone synthetic scope only, never app lifecycle.
  if(typeof ctx.dispose==='function')await ctx.dispose();
}
