package com.dsh.android.p53;

public final class P53StartOrderTest {
  private static int n;
  private static void check(boolean ok,String message) {
    ++n;if(!ok)throw new AssertionError(message);
  }
  private static void allow(P53StartOrder g,int what,long seq){
    check(g.accept(what,seq),"accept "+what+" seq "+seq);
  }
  private static void deny(P53StartOrder g,int what,long seq){
    check(!g.accept(what,seq),"deny "+what+" seq "+seq);
  }
  private static P53StartOrder hello(){
    P53StartOrder g=new P53StartOrder();
    allow(g,P53StartOrder.HELLO,0);return g;
  }
  public static void main(String[] args){
    P53StartOrder g=hello();
    check(!g.hasStartedChild(),"HELLO not started");
    deny(g,P53StartOrder.STDOUT,1);
    deny(g,P53StartOrder.EXIT,1);
    deny(g,P53StartOrder.CHILD_STARTED,2);
    deny(g,P53StartOrder.HELLO,0);
    allow(g,P53StartOrder.CHILD_STARTED,1);
    check(g.hasStartedChild(),"started");
    deny(g,P53StartOrder.CHILD_STARTED,2);
    allow(g,P53StartOrder.STDOUT,2);
    deny(g,P53StartOrder.STDERR,2);
    allow(g,P53StartOrder.STDERR,3);
    allow(g,P53StartOrder.EXIT,4);
    check(g.isTerminal(),"EXIT terminal");
    deny(g,P53StartOrder.STDOUT,5);
    deny(g,P53StartOrder.CHILD_STARTED,5);
    P53StartOrder fail=hello();
    allow(fail,P53StartOrder.FAIL,1);
    check(fail.isTerminal() && !fail.hasStartedChild(),"fail before spawn");
    deny(fail,P53StartOrder.CHILD_STARTED,2);
    P53StartOrder odd=new P53StartOrder();
    deny(odd,P53StartOrder.CHILD_STARTED,1);
    deny(odd,P53StartOrder.HELLO,1);
    allow(odd,P53StartOrder.HELLO,0);
    deny(odd,999,1);
    allow(odd,P53StartOrder.CHILD_STARTED,1);
    allow(odd,P53StartOrder.FAIL,2);
    check(odd.isTerminal(),"failure terminal even after spawn");
    P53StartOrder wrong=hello();
    deny(wrong,P53StartOrder.STDOUT,0);
    deny(wrong,P53StartOrder.EXIT,Long.MAX_VALUE);
    deny(wrong,P53StartOrder.CHILD_STARTED,-1);
    allow(wrong,P53StartOrder.CHILD_STARTED,1);
    allow(wrong,P53StartOrder.EXIT,2);
    System.out.println("P53_START_ORDER_JVM_NEGATIVE_CASES=PASS assertions="+n);
    System.out.println("P53_HELLO_NEVER_AUTHORIZES_PROCESS_HANDOFF=PASS");
    System.out.println("P53_CHILD_STARTED_REQUIRED_BEFORE_STREAM_OR_EXIT=PASS");
    System.out.println("P53_REAL_PRODUCTION_NODE_ENGINE=NOT_TESTED");
  }
}
