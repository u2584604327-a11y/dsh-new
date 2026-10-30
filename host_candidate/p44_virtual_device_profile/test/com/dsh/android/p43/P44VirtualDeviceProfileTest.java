package com.dsh.android.p43;

public final class P44VirtualDeviceProfileTest {
  private static int assertions=0;
  private static void check(boolean ok,String label) {
    assertions++;
    if(!ok)throw new AssertionError(label);
  }
  private static void reject(String wire) {
    assertions++;
    try {P44VirtualDeviceProfile.parse(wire);}
    catch(IllegalArgumentException expected){return;}
    throw new AssertionError("unexpectedly accepted invalid virtual profile");
  }
  private static void rejectProfile(String name,int width,int height,String lang,
                                   String zone,String net,String storage) {
    assertions++;
    try {new P44VirtualDeviceProfile(name,width,height,lang,zone,net,storage);}
    catch(IllegalArgumentException expected){return;}
    throw new AssertionError("accepted invalid profile");
  }
  public static void main(String[] args) {
    P44VirtualDeviceProfile p=P44VirtualDeviceProfile.syntheticDemo();
    String wire=p.wire();
    check(wire.equals("p44-1|sandbox-a|390|844|en-US|UTC|deny|broker-only"),
          "stable canonical protocol");
    check(p.fingerprint().matches("[a-f0-9]{64}"),"SHA256 canonical digest");
    check(P44VirtualDeviceProfile.parse(wire).fingerprint().equals(p.fingerprint()),
          "round trip digest");
    check(!p.canMakeSystemVirtualMachine(),"VM unavailable");
    check(!p.altersRealHardwareIdentity(),"physical identity unmodified");
    check(!p.grantsNetworkOrFilesystemAccess(),"profile cannot grant capabilities");
    check(!p.hasIndependentKernel(),"not kernel virtualization");
    reject("");
    reject(null);
    reject(wire+"|extra");
    reject(wire.replace("p44-1","p44-2"));
    reject(wire.replace("sandbox-a","../secret"));
    reject(wire.replace("390","0390"));
    reject(wire.replace("390","-1"));
    reject(wire.replace("844","100000"));
    reject(wire.replace("en-US","zz.invalid"));
    reject(wire.replace("UTC","../root"));
    reject(wire.replace("|deny|","|unrestricted|"));
    reject(wire.replace("broker-only","host-private-all"));
    reject(wire+"\n");
    reject(wire+"\u0000");
    rejectProfile("a",390,844,"en-US","UTC","deny","broker-only");
    rejectProfile("sandbox-a",0,844,"en-US","UTC","deny","broker-only");
    rejectProfile("sandbox-a",390,844,"en-US","UTC","all","broker-only");
    rejectProfile("sandbox-a",390,844,"en-US","UTC","deny","/");
    System.out.println("P44_VIRTUAL_DEVICE_PROFILE_JVM_TESTS=PASS assertions="+assertions);
    System.out.println("P44_REAL_KERNEL_VM=NO");
    System.out.println("P44_GLOBAL_DEVICE_SPOOF=NO");
    System.out.println("P44_PRODUCTION_DSH_ENGINE_ISOLATION=BLOCKED");
  }
}
