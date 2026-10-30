package com.dsh.android.p43;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
public final class P46ResourceBundleTest {
  private static int assertions=0;
  private static void yes(boolean ok,String why) {
    assertions++;if(!ok)throw new AssertionError(why);
  }
  private static void reject(String s) {
    assertions++;
    try {P46ResourceBundle.parse(s);}
    catch(IllegalArgumentException expected){return;}
    throw new AssertionError("malformed manifest accepted");
  }
  private static void rejectFixture(byte[] a,byte[] b) {
    assertions++;
    try{P46ResourceBundle.fromFixture(a,b);}
    catch(IllegalArgumentException expected){return;}
    throw new AssertionError("fixture accepted against length limits");
  }
  public static void main(String[] args) throws IOException {
    byte[] a=P46FixtureData.bytes(0),b=P46FixtureData.bytes(1);
    P46ResourceBundle p=P46ResourceBundle.fromFixture(a,b);
    P46ResourceBundle parsed=P46ResourceBundle.parse(p.wire());
    yes(p.fingerprint().equals(parsed.fingerprint()),"canonical round trip");
    yes(p.fingerprint().matches("[0-9a-f]{64}"),"digest form");
    yes(parsed.parts.length==2,"count exact");
    yes(parsed.parts[0].name.equals("fixture/bootstrap.js"),"label0");
    yes(parsed.parts[1].name.equals("fixture/settings.json"),"label1");
    yes(P46ResourceBundle.verifyPart(new ByteArrayInputStream(a),parsed.parts[0]),"valid 0");
    yes(P46ResourceBundle.verifyPart(new ByteArrayInputStream(b),parsed.parts[1]),"valid 1");
    yes(!P46ResourceBundle.verifyPart(new ByteArrayInputStream(new byte[0]),parsed.parts[0]),"short");
    yes(!P46ResourceBundle.verifyPart(new ByteArrayInputStream(Arrays.copyOf(a,a.length+1)),parsed.parts[0]),"long");
    byte[] changed=a.clone();changed[0]^=1;
    yes(!P46ResourceBundle.verifyPart(new ByteArrayInputStream(changed),parsed.parts[0]),"tampered");
    yes(!P46ResourceBundle.verifyPart(null,parsed.parts[0]),"null stream");
    yes(!P46ResourceBundle.verifyPart(new ByteArrayInputStream(a),null),"null part");
    reject(null);
    reject("");
    reject(p.wire()+"|extra");
    reject(p.wire().replace("p46-1","p46-2"));
    reject(p.wire().replace("fixture/bootstrap.js","../../files/token"));
    reject(p.wire().replace("fixture/bootstrap.js","fixture/settings.json"));
    reject(p.wire().replace("fixture/settings.json","fixture/bootstrap.js"));
    reject(p.wire().replace(","+a.length+",",",0"+a.length+","));
    reject(p.wire().replace(","+a.length+",",",0,"));
    reject(p.wire().replace(","+a.length+",",",4097,"));
    reject(p.wire().replace(","+a.length+",",",-1,"));
    reject(p.wire().replace(","+a.length+",",",99999999999,"));
    reject(p.wire().replace(",",";"));
    reject(p.wire().toUpperCase(java.util.Locale.ROOT));
    reject(p.wire()+"\n");
    reject(p.wire()+"\u0000");
    reject(p.wire().substring(0,p.wire().length()-1));
    rejectFixture(new byte[0],b);
    rejectFixture(new byte[4097],b);
    rejectFixture(a,null);
    System.out.println("P46_CONTENT_ADDRESSED_BUNDLE_JVM_TESTS=PASS assertions="+assertions);
    System.out.println("P46_FIXTURE_ONLY_ACTUAL_NODE_SCRIPTS=NO");
    System.out.println("P46_REAL_ENGINE_ISOLATION=BLOCKED");
  }
}
