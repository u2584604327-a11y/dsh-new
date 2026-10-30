package com.dsh.android.p78;
import java.io.IOException;

public final class P78ModuleSlotTest {
  private static int checks;
  private static final String SESSION="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
  private static void check(boolean b,String label){
    checks++;if(!b)throw new AssertionError("P78_"+label);
  }
  private static boolean rejected(Runnable fn){
    try{fn.run();return false;}
    catch(SecurityException expected){return true;}
  }
  public static void main(String[] args)throws Exception {
    boolean invalid=false;
    try{new P78ModuleSlot("not-session");}catch(SecurityException e){invalid=true;}
    check(invalid,"session_format_rejected");
    P78ModuleSlot slot=new P78ModuleSlot(SESSION);
    check(rejected(slot::opaqueId),"unverified_id_denied");
    check(rejected(slot::moduleSha),"unverified_sha_denied");
    check(rejected(()->slot.takeOnce(SESSION,"deadbeef")),"unverified_take_denied");
    check(!slot.begin("pkg/native.node",false,13),"native_addon_excluded");
    check(!slot.begin("pkg/big.js",false,P78ModuleSlot.MAX_JS_BYTES+1L),"oversize_denied");
    check(!slot.begin("pkg/dir.js",true,2),"directory_denied");
    invalid=false;
    try{slot.begin("../private.js",false,3);}catch(IOException e){invalid=true;}
    check(invalid,"traversal_denied");
    check(slot.begin("pkg/index.js",false,3),"first_valid_source_selected");
    invalid=false;
    try{slot.accept(new byte[4],0,4);}catch(IOException e){invalid=true;}
    check(invalid,"out_of_bounds_write_denied");
    slot.accept(new byte[]{'1'},0,1);
    invalid=false;
    try{slot.endMember();}catch(IOException e){invalid=true;}
    check(invalid,"short_member_denied");
    slot.accept(new byte[]{'2','3'},0,2);
    slot.endMember();
    check(!slot.begin("pkg/second.mjs",false,3),"second_module_ignored");
    invalid=false;
    try{slot.sealOriginal(null);}catch(IOException e){invalid=true;}
    check(invalid,"synthetic_cannot_seal_as_original");
    check(!slot.isReady(),"untrusted_source_not_readable");
    check(rejected(()->slot.takeOnce(SESSION,"ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff")),"raw_unsealed_module_denied");
    System.out.println("P78_SYNTHETIC_MODULE_SLOT_SECURITY=PASS assertions="+checks);
    System.out.println("P78_SYNTHETIC_ORIGINAL_MODULE_BYTES_LEAKED=NO");
  }
}
