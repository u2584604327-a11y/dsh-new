package com.dsh.android.p93;
import java.util.ArrayList;
import java.util.List;
public final class P93TurnMessageStateTest {
    private static void ok(boolean yes,String why){if(!yes)throw new AssertionError(why);}
    public static void main(String[] ignored){
        List<P93TurnMessageState.Frame> frames=new ArrayList<>();
        P93TurnMessageState m=new P93TurnMessageState("turn_p93_123456",1,frames::add);
        m.reasoning();
        ok(frames.get(1).phase==P93TurnMessageState.Phase.THINKING &&
           frames.get(1).content.isEmpty() && !frames.get(1).terminal,
           "thinking cannot complete or become body");
        m.content("你");
        ok(frames.get(2).content.equals("你") &&
           frames.get(2).phase==P93TurnMessageState.Phase.STREAMING &&
           !frames.get(2).terminal,
           "first text is visible before DONE");
        m.content("好");
        m.tools(2);
        ok(m.snapshot().content.equals("你好") && m.snapshot().toolFragments==2 &&
           m.snapshot().phase==P93TurnMessageState.Phase.TOOLS,
           "tools must not pollute content");
        m.done();
        ok(m.snapshot().terminal && m.snapshot().phase==P93TurnMessageState.Phase.COMPLETE,
           "explicit done");
        ok(frames.get(frames.size()-1).content.equals("你好"),"final text unchanged");
        boolean rejected=false;try{m.content("重复");}catch(IllegalStateException ex){rejected=true;}
        ok(rejected,"no extra data after terminal");
        List<P93TurnMessageState.Frame> broken=new ArrayList<>();
        P93TurnMessageState n=new P93TurnMessageState("turn_p93_123457",2,broken::add);
        n.content("已显示");
        n.closedWithoutDone();
        ok(n.snapshot().phase==P93TurnMessageState.Phase.TRUNCATED &&
           n.snapshot().content.equals("已显示"),"early EOF retains content and marks failure");
        long last=-1;
        for(P93TurnMessageState.Frame f:frames){
            ok(f.revision>last,"strict revision increase");
            last=f.revision;
        }
        ok(!m.snapshot().turnId.equals(n.snapshot().turnId),"distinct turn identities");
        List<P93TurnMessageState.Frame> tooLong=new ArrayList<>();
        P93TurnMessageState bound=new P93TurnMessageState("turn_p93_123458",3,tooLong::add);
        bound.content(new String(new char[600001]).replace('\0','A'));
        ok(bound.snapshot().phase==P93TurnMessageState.Phase.FAILED &&
           bound.snapshot().content.isEmpty(),"huge text must not be stored");
        System.out.println("P93_FIRST_BODY_FRAME_BEFORE_DONE=PASS");
        System.out.println("P93_THINKING_SEPARATE_TOOL_FRAGMENTS_NO_TEXT_POLLUTION=PASS");
        System.out.println("P93_EOF_NOT_COMPLETE_AND_MONOTONIC_TURN_REVISIONS=PASS");
        System.out.println("P93_CONTENT_CAP_AND_LATE_FRAME_REJECTION=PASS");
    }
}
