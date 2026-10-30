package com.dsh.android.p43;
import java.nio.charset.StandardCharsets;
/** P46 synthetic, public, never-executed test fixture ONLY. */
public final class P46FixtureData {
  private P46FixtureData(){}
  public static byte[] bytes(int i) {
    if(i==0)return "/* P46 FIXTURE: NOT EXECUTED */".getBytes(StandardCharsets.US_ASCII);
    if(i==1)return "{\"p46\":\"synthetic\",\"active\":false}".getBytes(StandardCharsets.US_ASCII);
    throw new IllegalArgumentException("P46_UNKNOWN_FIXTURE");
  }
}
