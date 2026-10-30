package com.dsh.android.p43;
import android.os.Bundle;
import android.os.ParcelFileDescriptor;
import java.io.IOException;
import java.io.InputStream;

/** P46 PFD receipt with strict manifest/digest/size validation only. */
public final class P46WorkerBundle {
  private P46WorkerBundle(){}
  public static String verifyFixture(Bundle data){
    try {
      if(data==null || data.getInt("p46_fd_count",-1)!=P46ResourceBundle.COUNT)
        return null;
      P46ResourceBundle pkg=P46ResourceBundle.parse(data.getString("p46_manifest"));
      P46ResourceBundle expected=P46ResourceBundle.fromFixture(
          P46FixtureData.bytes(0),P46FixtureData.bytes(1));
      // Authorize exactly the known, public, synthetic test package.
      // Never interpret this as a production user-approved file capability.
      if(!expected.fingerprint().equals(pkg.fingerprint()))return null;
      ParcelFileDescriptor first=(ParcelFileDescriptor)data.getParcelable("p46_fd_0");
      ParcelFileDescriptor second=(ParcelFileDescriptor)data.getParcelable("p46_fd_1");
      if(first==null || second==null)return null;
      try (InputStream a=new ParcelFileDescriptor.AutoCloseInputStream(first);
           InputStream b=new ParcelFileDescriptor.AutoCloseInputStream(second)) {
        if(!P46ResourceBundle.verifyPart(a,pkg.parts[0]))return null;
        if(!P46ResourceBundle.verifyPart(b,pkg.parts[1]))return null;
      }
      return pkg.fingerprint();
    }catch(IOException | RuntimeException invalid){
      return null;
    }
  }
}
