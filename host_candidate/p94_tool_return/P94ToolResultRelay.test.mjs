import assert from "node:assert/strict";
import {P94ToolResultRelay} from "./P94ToolResultRelay.mjs";
const sent=[];
const make=()=>new P94ToolResultRelay({
  turnId:"turn_p94_12345",generation:7,
  isCurrentOriginalTurn:async(id,gen)=>id==="turn_p94_12345"&&gen===7,
  dispatchOriginalToolResult:async(x)=>{
    sent.push(x);return {
      accepted:true,durable:true,turnId:x.turnId,generation:x.generation,
      toolCallId:x.message.tool_call_id,
    };
  },
});
const a=make();a.register({toolCallId:"call_read01",brokerRequestId:"p86read01"});
assert.equal(a.acceptTrustedBrokerTerminal({
  toolCallId:"call_read01",brokerRequestId:"p86read01",
  terminal:true,outcomeUnknown:false,ok:true,code:"OK",result:{text:"fixture"},
}),true);
assert.equal(await a.deliverExactlyOnce("call_read01"),true);
assert.equal(await a.deliverExactlyOnce("call_read01"),false);
assert.equal(sent.length,1);
assert.deepEqual(JSON.parse(sent[0].message.content),{
  ok:true,code:"OK",result:{text:"fixture"},
});
assert.equal(a.status("call_read01").continuationObserved,false);
assert.equal(a.markObservedOriginalModelContinuation("call_read01","wrongturn"),false);
assert.equal(a.markObservedOriginalModelContinuation("call_read01","turn_p94_12345"),true);
assert.equal(a.status("call_read01").continuationObserved,true);

const denial=make();
denial.register({toolCallId:"call_post01",brokerRequestId:"p86post01"});
denial.acceptTrustedBrokerTerminal({toolCallId:"call_post01",brokerRequestId:"p86post01",
  terminal:true,outcomeUnknown:false,ok:false,
  code:"NATIVE_USER_CONFIRMATION_REQUIRED",result:null});
assert.equal(await denial.deliverExactlyOnce("call_post01"),true);
assert.equal(JSON.parse(sent.at(-1).message.content).code,
  "NATIVE_USER_CONFIRMATION_REQUIRED");
assert.equal(JSON.parse(sent.at(-1).message.content).ok,false);
assert.throws(()=>denial.acceptTrustedBrokerTerminal({
  toolCallId:"call_post01",brokerRequestId:"p86post01",
  terminal:true,outcomeUnknown:false,ok:true,code:"OK"}),/ALREADY_CONSUMED/);

const unknown=make();unknown.register({toolCallId:"call_draft01",brokerRequestId:"p86draft01"});
assert.equal(unknown.acceptTrustedBrokerTerminal({
  toolCallId:"call_draft01",brokerRequestId:"p86draft01",
  terminal:false,outcomeUnknown:true,ok:false,code:"UNKNOWN",
}),false);
assert.equal(await unknown.deliverExactlyOnce("call_draft01"),false);
assert.equal(unknown.status("call_draft01").state,"BLOCKED_UNKNOWN_OUTCOME");

const duplicate=make();duplicate.register({toolCallId:"call_get01",brokerRequestId:"p86get01"});
assert.throws(()=>duplicate.register({toolCallId:"call_get01",brokerRequestId:"p86get02"}),/DUPLICATE/);
assert.throws(()=>duplicate.acceptTrustedBrokerTerminal({
 toolCallId:"call_get01",brokerRequestId:"mismatch",terminal:true,outcomeUnknown:false,
 ok:true,code:"OK",
}),/RESULT_ID_MISMATCH/);

let ambiguousDispatch=0;
const lost=new P94ToolResultRelay({
  turnId:"turn_p94_12345",generation:7,
  isCurrentOriginalTurn:async()=>true,
  dispatchOriginalToolResult:async()=>{ambiguousDispatch++;throw Error("network_lost_after_write");},
});
lost.register({toolCallId:"call_retry01",brokerRequestId:"p86retry01"});
lost.acceptTrustedBrokerTerminal({
  toolCallId:"call_retry01",brokerRequestId:"p86retry01",
  terminal:true,outcomeUnknown:false,ok:true,code:"OK",result:"ok",
});
assert.equal(await lost.deliverExactlyOnce("call_retry01"),false);
assert.equal(await lost.deliverExactlyOnce("call_retry01"),false);
assert.equal(ambiguousDispatch,1);
assert.equal(lost.status("call_retry01").state,"ACK_UNKNOWN");
assert.equal(lost.status("call_retry01").canAutoRetry,false);

console.log("P94_TOOL_RESULT_ID_AND_ORIGINAL_TURN_CORRELATION=PASS");
console.log("P94_DENIED_TOOL_RETURNS_ERROR_WITHOUT_EXECUTING=PASS");
console.log("P94_UNKNOWN_OUTCOME_AND_ACK_LOSS_NO_REPLAY=PASS");
console.log("P94_MODEL_CONTINUATION_NEEDS_OBSERVED_ORIGINAL_TURN=PASS");
