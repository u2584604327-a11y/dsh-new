/**
 * P94: one-shot tool_result envelope to the ORIGINAL model dispatcher, not
 * a substitute model/provider. The caller must supply a trusted live-turn
 * validator and the original dispatcher. This module NEVER invokes a tool.
 */
export class P94ToolResultRelay {
  #turn;
  #generation;
  #registered = new Map();
  #isCurrent;
  #dispatch;
  constructor({turnId,generation,isCurrentOriginalTurn,dispatchOriginalToolResult}) {
    if(!/^[A-Za-z0-9_-]{8,128}$/.test(turnId||"")||
       !Number.isSafeInteger(generation)||generation<1||
       typeof isCurrentOriginalTurn!=="function" ||
       typeof dispatchOriginalToolResult!=="function")
      throw new Error("P94_MISSING_TRUSTED_ORIGINAL_TURN_ADAPTER");
    this.#turn=turnId;
    this.#generation=generation;
    this.#isCurrent=isCurrentOriginalTurn;
    this.#dispatch=dispatchOriginalToolResult;
  }
  register({toolCallId,brokerRequestId}) {
    if(!/^[A-Za-z0-9_-]{6,256}$/.test(toolCallId||"")||
       !/^[A-Za-z0-9_-]{6,256}$/.test(brokerRequestId||""))
      throw new Error("P94_INVALID_ID");
    if(this.#registered.has(toolCallId))
      throw new Error("P94_DUPLICATE_TOOL_CALL");
    for(const c of this.#registered.values())
      if(c.requestId===brokerRequestId)throw new Error("P94_DUPLICATE_BROKER_REQUEST");
    if(this.#registered.size>=16)throw new Error("P94_TOOL_LIMIT");
    this.#registered.set(toolCallId,{requestId:brokerRequestId,state:"AWAITING_BROKER",
                                    envelope:null,continuation:false});
  }
  /** trustedBrokerTerminal MUST come from verified P85 native broker journal,
   * never directly from model output, a web page, or a JS string.
   */
  acceptTrustedBrokerTerminal({toolCallId,brokerRequestId,terminal,
                               outcomeUnknown,ok,code,result}) {
    const item=this.#registered.get(toolCallId);
    if(!item||item.requestId!==brokerRequestId)throw new Error("P94_RESULT_ID_MISMATCH");
    if(item.state!=="AWAITING_BROKER")throw new Error("P94_RESULT_ALREADY_CONSUMED");
    if(!terminal||outcomeUnknown){
      item.state="BLOCKED_UNKNOWN_OUTCOME";
      return false;
    }
    if(typeof ok!=="boolean" || typeof code!=="string"||
       !/^[A-Z0-9_]{2,80}$/.test(code))
      throw new Error("P94_INVALID_TRUSTED_BROKER_RESULT");
    // A denied action is an error tool_result so the model can continue
    // without trying to silently self-approve the side effect.
    const safeResult={ok,code,result:ok ? result ?? null : null};
    const content=JSON.stringify(safeResult);
    if(content.length>65536)throw new Error("P94_TOOL_RESULT_SIZE_LIMIT");
    item.envelope={role:"tool",tool_call_id:toolCallId,content};
    item.state="READY_TO_DISPATCH";
    return true;
  }
  async deliverExactlyOnce(toolCallId) {
    const item=this.#registered.get(toolCallId);
    if(!item)throw new Error("P94_UNKNOWN_CALL");
    if(item.state!=="READY_TO_DISPATCH")return false;
    // Take the single-use slot before awaiting any cross-process transfer.
    // If transport fails after delivery, do NOT blindly send a duplicate.
    item.state="ACK_UNKNOWN";
    if(!(await this.#isCurrent(this.#turn,this.#generation))){
      item.state="BLOCKED_STALE_TURN";
      return false;
    }
    let receipt;
    try{
      receipt=await this.#dispatch({
        turnId:this.#turn,generation:this.#generation,
        message:Object.freeze({...item.envelope}),
      });
    }catch(_error){
      item.state="ACK_UNKNOWN";
      return false;
    }
    if(receipt?.accepted===true && receipt?.durable===true &&
       receipt?.turnId===this.#turn && receipt?.generation===this.#generation &&
       receipt?.toolCallId===toolCallId){
      item.state="DISPATCH_ACKNOWLEDGED";
      return true;
    }
    return false;
  }
  /** A dispatched tool_result does not prove the model continued. */
  markObservedOriginalModelContinuation(toolCallId,verifiedTurnId) {
    const item=this.#registered.get(toolCallId);
    if(!item || item.state!=="DISPATCH_ACKNOWLEDGED"||
       verifiedTurnId!==this.#turn)return false;
    item.continuation=true;
    item.state="CONTINUATION_OBSERVED";
    return true;
  }
  status(toolCallId) {
    const item=this.#registered.get(toolCallId);
    return item?Object.freeze({
      state:item.state,
      continuationObserved:item.continuation,
      canAutoRetry:false,
    }):null;
  }
}
