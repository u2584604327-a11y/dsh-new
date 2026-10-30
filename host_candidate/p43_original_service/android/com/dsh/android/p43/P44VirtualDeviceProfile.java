package com.dsh.android.p43;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.regex.Pattern;

/**
 * Opt-in simulated device VIEW for DSH-controlled code only.
 * Does not change Build.*, WebView, actual device sensors, kernel, UID or attestation.
 * No permission or capability can be granted by a profile.
 */
public final class P44VirtualDeviceProfile {
  private static final Pattern ID=Pattern.compile("[a-z][a-z0-9-]{1,31}");
  private static final Pattern LOCALE=Pattern.compile("[a-z]{2}-[A-Z]{2}");
  private static final Pattern ZONE=Pattern.compile("[A-Za-z_]{2,32}(?:/[A-Za-z_]{2,32}){0,2}|UTC");
  public static final String VERSION="p44-1";
  public final String id;
  public final int width;
  public final int height;
  public final String locale;
  public final String timezone;
  public final String networkPolicy;
  public final String storagePolicy;

  public P44VirtualDeviceProfile(String id,int width,int height,String locale,
                                String timezone,String networkPolicy,String storagePolicy) {
    if(id==null||!ID.matcher(id).matches() || width<240 || width>3840 ||
       height<240 || height>3840 || locale==null || !LOCALE.matcher(locale).matches() ||
       timezone==null || !ZONE.matcher(timezone).matches() ||
       !("deny".equals(networkPolicy) || "broker-approved".equals(networkPolicy)) ||
       !"broker-only".equals(storagePolicy)) {
      throw new IllegalArgumentException("P44_PROFILE_REJECTED");
    }
    this.id=id;this.width=width;this.height=height;this.locale=locale;
    this.timezone=timezone;this.networkPolicy=networkPolicy;
    this.storagePolicy=storagePolicy;
  }

  public static P44VirtualDeviceProfile syntheticDemo() {
    return new P44VirtualDeviceProfile("sandbox-a",390,844,
        "en-US","UTC","deny","broker-only");
  }
  public String wire() {
    return VERSION+"|"+id+"|"+width+"|"+height+"|"+
        locale+"|"+timezone+"|"+networkPolicy+"|"+storagePolicy;
  }
  public static P44VirtualDeviceProfile parse(String wire) {
    if(wire==null || wire.length()>180 || wire.indexOf('\n')>=0 ||
        wire.indexOf('\r')>=0 || wire.indexOf('\0')>=0)
      throw new IllegalArgumentException("P44_WIRE_REJECTED");
    String[] fields=wire.split("\\|",-1);
    if(fields.length!=8 || !VERSION.equals(fields[0])) {
      throw new IllegalArgumentException("P44_WIRE_VERSION_OR_FIELDS");
    }
    try {
      P44VirtualDeviceProfile p=new P44VirtualDeviceProfile(fields[1],
        Integer.parseInt(fields[2]),Integer.parseInt(fields[3]),
        fields[4],fields[5],fields[6],fields[7]);
      if(!p.wire().equals(wire))throw new IllegalArgumentException("P44_WIRE_NOT_CANONICAL");
      return p;
    } catch(NumberFormatException bad) {
      throw new IllegalArgumentException("P44_WIRE_INVALID_NUMBER",bad);
    }
  }
  public String fingerprint() {
    try {
      byte[] d=MessageDigest.getInstance("SHA-256")
          .digest(wire().getBytes(StandardCharsets.US_ASCII));
      StringBuilder result=new StringBuilder(d.length*2);
      for(byte b:d) result.append(String.format(java.util.Locale.ROOT,"%02x",b&255));
      return result.toString();
    }catch(Exception e){throw new IllegalStateException(e);}
  }
  public boolean canMakeSystemVirtualMachine(){return false;}
  public boolean altersRealHardwareIdentity(){return false;}
  public boolean grantsNetworkOrFilesystemAccess(){return false;}
  public boolean hasIndependentKernel(){return false;}
}
