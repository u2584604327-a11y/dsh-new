package com.dsh.android.p47;
import java.io.File;
import java.io.IOException;
import java.lang.ProcessBuilder;
import java.util.List;
import java.util.Map;

/**
 * P47 fail-closed original EngineManager spawn seam.
 *
 * A real authenticated Android isolated Binder supervisor is NOT installed
 * yet. This method must NOT execute ProcessBuilder.start(), fork, shell,
 * reflectively invoke start, enable an env override, or silently fallback.
 *
 * Production DSH shipping remains prohibited until a real isolated
 * supervisor, lease/identity checks and runtime parity are implemented.
 */
public final class P47LaunchGate {
  private P47LaunchGate(){}

  /** Sensitive command args, cwd and environment values NEVER leave memory. */
  public static final class Shape {
    public final int argvCount;
    public final boolean hasDirectory;
    public final int environmentEntries;
    public final boolean stderrMerged;
    private Shape(int argvCount, boolean hasDirectory,
                  int environmentEntries, boolean stderrMerged) {
      this.argvCount=argvCount;
      this.hasDirectory=hasDirectory;
      this.environmentEntries=environmentEntries;
      this.stderrMerged=stderrMerged;
    }
  }

  public static Shape categorize(ProcessBuilder builder) {
    if(builder==null)throw new IllegalArgumentException("P47_NULL_BUILDER");
    List<String> argv=builder.command();
    Map<String,String> environment=builder.environment();
    File directory=builder.directory();
    return new Shape(argv==null ? 0 : argv.size(),
        directory!=null,environment==null ? 0 : environment.size(),
        builder.redirectErrorStream());
  }

  /**
   * Bridge target in original classes.dex: fail-closed is the ONLY path in
   * P47. An IOException is intentional and must be surfaced to original
   * EngineManager, NEVER replaced by a host Process.
   */
  public static Process startOrDeny(ProcessBuilder builder) throws IOException {
    Shape shape=categorize(builder);
    if(shape.argvCount<1 || shape.argvCount>128)
      throw new IOException("P47_INVALID_ORIGINAL_LAUNCH_SHAPE");
    throw new IOException("P47_ISOLATED_SUPERVISOR_UNAVAILABLE_NO_HOST_FALLBACK");
  }
}
