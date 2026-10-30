package androidx.startup;
import android.content.Context;
import java.util.List;
/** Compile-time ONLY copy of the AndroidX Startup Initializer interface.
 * Never include this .class in the APK: the original v138 already has it.
 */
public interface Initializer<T> {
    T create(Context context);
    List<Class<? extends Initializer<?>>> dependencies();
}
