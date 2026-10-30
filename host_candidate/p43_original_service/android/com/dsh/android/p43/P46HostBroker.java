package com.dsh.android.p43;
import android.content.Context;
import android.os.Bundle;
import android.os.ParcelFileDescriptor;
import java.io.Closeable;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;

/**
 * P46 ONLY synthetic fixed-payload test broker: no arbitrary host paths,
 * storage enumeration, user files, script execution or production grants.
 */
public final class P46HostBroker {
  public static final class Lease implements Closeable {
    private final ParcelFileDescriptor[] fds=new ParcelFileDescriptor[P46ResourceBundle.COUNT];
    private final File[] files=new File[P46ResourceBundle.COUNT];
    private boolean closed;
    public final String fingerprint;

    private Lease(Context context,Bundle b) throws IOException {
      byte[] a=P46FixtureData.bytes(0);
      byte[] z=P46FixtureData.bytes(1);
      P46ResourceBundle manifest=P46ResourceBundle.fromFixture(a,z);
      fingerprint=manifest.fingerprint();
      try {
        final byte[][] bytes={a,z};
        for(int i=0;i<bytes.length;i++){
          files[i]=File.createTempFile("p46-private-"+i+"-", ".bin",context.getCacheDir());
          try(FileOutputStream out=new FileOutputStream(files[i])){
            out.write(bytes[i]);out.getFD().sync();
          }
          fds[i]=ParcelFileDescriptor.open(files[i],ParcelFileDescriptor.MODE_READ_ONLY);
          if(!files[i].delete())throw new IOException("P46_UNLINK_FAILED");
          files[i]=null;
          b.putParcelable("p46_fd_"+i,fds[i]);
        }
        b.putString("p46_manifest",manifest.wire());
        b.putInt("p46_fd_count",P46ResourceBundle.COUNT);
      }catch(Exception failure){
        close();throw new IOException("P46_BROKER_SETUP_FAILED",failure);
      }
    }
    @Override public void close() {
      if(closed)return;closed=true;
      for(ParcelFileDescriptor fd:fds)if(fd!=null)try{fd.close();}catch(IOException ignored){}
      for(File f:files)if(f!=null)f.delete();
    }
  }
  private P46HostBroker(){}
  public static Lease attachFixture(Context context,Bundle b) throws IOException {
    if(context==null || b==null)throw new IOException("P46_NO_TRUSTED_HOST");
    return new Lease(context,b);
  }
}
