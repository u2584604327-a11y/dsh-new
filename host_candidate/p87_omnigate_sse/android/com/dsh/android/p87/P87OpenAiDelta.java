package com.dsh.android.p87;
import org.json.JSONArray;
import org.json.JSONObject;
/** OpenAI Chat Completions streaming projection; never mixes reasoning/tool into assistant text. */
public final class P87OpenAiDelta {
 public final String content,reasoning,finishReason;
 public final int toolFragments;
 public final boolean done,error;
 private P87OpenAiDelta(String body,String think,int tools,String finish,boolean end,boolean bad){
  content=body;reasoning=think;toolFragments=tools;finishReason=finish;done=end;error=bad;
 }
 public static P87OpenAiDelta parse(P87SseDecoder.Event event){
  if(event.done)return new P87OpenAiDelta("","",0,"",true,false);
  if("error".equals(event.event))
   return new P87OpenAiDelta("","",0,"",false,true);
  try{
   JSONObject root=new JSONObject(event.data);
   if(root.has("error"))
    return new P87OpenAiDelta("","",0,"",false,true);
   JSONArray choices=root.optJSONArray("choices");
   if(choices==null||choices.length()==0)
    return new P87OpenAiDelta("","",0,"",false,false); // usage-only
   JSONObject c=choices.optJSONObject(0);
   if(c==null)return new P87OpenAiDelta("","",0,"",false,true);
   JSONObject delta=c.optJSONObject("delta");
   String text="",reason="";
   int tools=0;
   if(delta!=null){
    Object raw=delta.opt("content");
    if(raw instanceof String)text=(String)raw;
    else if(raw instanceof JSONArray){
     JSONArray parts=(JSONArray)raw;
     for(int i=0;i<parts.length();i++){
      JSONObject part=parts.optJSONObject(i);
      if(part!=null && "text".equals(part.optString("type","")))
       text+=part.optString("text","");
     }
    }
    reason=delta.optString("reasoning_content","");
    JSONArray calls=delta.optJSONArray("tool_calls");
    if(calls!=null)tools=calls.length();
   }
   String finish=c.isNull("finish_reason")?"":c.optString("finish_reason","");
   return new P87OpenAiDelta(text,reason,tools,finish,false,false);
  }catch(Exception ex){
   return new P87OpenAiDelta("","",0,"",false,true);
  }
 }
}
