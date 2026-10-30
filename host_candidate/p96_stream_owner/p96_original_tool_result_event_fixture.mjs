/**
 * Exact original ToolRuntime notifyResult observer contract test.
 * Calls only the original method body against synthetic in-memory ctx.
 * Does not register, dispatch, execute or retry a tool, and does not call a model.
 */
import assert from 'node:assert/strict';
import {ToolRuntime} from '@deepseek-ai/dsh-tools';

const accepted=[];
const fakeRuntime={
  ctx:{
    events:{
      dispatch(kind,args){
        accepted.push({kind,args});
        return [];
      }
    },
    logger:{warn(){}}
  }
};
const exec={name:'fixture_read_only',callId:'call_fixture12345',agent:null};
const result=Object.freeze({ok:true,code:'SYNTHETIC_ONLY'});
assert.equal(typeof ToolRuntime.prototype.notifyResult,'function');
ToolRuntime.prototype.notifyResult.call(fakeRuntime,exec,result);

assert.equal(Object.isFrozen(exec),true,'original dispatcher must freeze execution envelope');
assert.equal(accepted.length,1,'one original tools/result emission only');
const event=accepted[0];
assert.equal(event.kind,'emit');
assert.equal(event.args[1],'tools/result');
assert.equal(event.args[2],exec);
assert.equal(event.args[3],result);

process.stdout.write('P96_ORIGINAL_TOOL_RUNTIME_REAL_NOTIFYRESULT_EMIT=PASS\n');
process.stdout.write('P96_ORIGINAL_TOOL_RESULT_EVENT_NAME=tools/result\n');
process.stdout.write('P96_ORIGINAL_TOOL_NATIVE_BROWSER_EXECUTION=NOT_TESTED\n');
process.stdout.write('P96_ORIGINAL_AGENT_LOOP_CONSUMPTION=NOT_TESTED\n');
