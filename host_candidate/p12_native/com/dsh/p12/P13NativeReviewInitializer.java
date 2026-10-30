package com.dsh.p12;

import android.app.Activity;
import android.app.Application;
import android.content.Context;
import android.os.Bundle;
import android.view.View;
import androidx.startup.Initializer;
import com.dsh.p1.ConsentLedger;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.WeakHashMap;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * P13 source candidate: AndroidX Startup -> original Activity lifecycle hook.
 *
 * Instantiated ONLY by the pre-existing non-exported androidx.startup
 * InitializationProvider after a separately verified binary AXML metadata
 * addition. No JS, Node, Intent, shell, server or reflection bridge.
 *
 * This has NO network send implementation and no user-provided destination:
 * .invalid is reserved for local-only P5 consent preview compatibility.
 * P10 old full ZIP creation and P11 raw AI log commands remain denied.
 *
 * Source compiles against an SDK stub for AndroidX Initializer but the stub
 * must NEVER be packaged into the resulting DEX: original DSH ships Startup.
 */
public final class P13NativeReviewInitializer implements Initializer<Void> {
    private static final String VIEWER="com.dsh.android.LogViewerActivity";
    private static final String DISABLED_DESTINATION =
        "https://diagnostic-test.invalid/v1/review";
    private static final AtomicInteger LOCAL_DENIALS = new AtomicInteger();
    private final Map<Activity, P12LogViewerReviewEntry> installed =
        Collections.synchronizedMap(new WeakHashMap<Activity, P12LogViewerReviewEntry>());

    @Override public Void create(Context context) {
        // AndroidX InitializationProvider executes before Application.onCreate.
        // Do not throw/crash the host if the context is unexpectedly non-native.
        if (context == null || !(context.getApplicationContext() instanceof Application))
            return null;
        Application app = (Application)context.getApplicationContext();
        app.registerActivityLifecycleCallbacks(new Application.ActivityLifecycleCallbacks() {
            @Override public void onActivityCreated(Activity a, Bundle b) { }
            @Override public void onActivityStarted(Activity a) { }
            @Override public void onActivityResumed(Activity a) {
                if (a == null || !VIEWER.equals(a.getClass().getName())) return;
                // Activity has finished its onResume and views are expected
                // to be bound; post to the actual Android main view queue.
                final View decor = a.getWindow() == null ? null : a.getWindow().getDecorView();
                if (decor == null) return;
                decor.post(() -> {
                    if (a.isFinishing() || a.isDestroyed() || installed.containsKey(a))
                        return;
                    try {
                        ConsentLedger.Audit audit=(stage,entry,reason,time,count)->{
                            // No raw file names, paths, network destinations,
                            // tokens, stack traces or diagnostic contents logged.
                            LOCAL_DENIALS.incrementAndGet();
                        };
                        P12LogViewerReviewEntry entry =
                            P12LogViewerReviewEntry.attach(
                                a, DISABLED_DESTINATION,
                                Collections.singleton(DISABLED_DESTINATION),
                                audit);
                        installed.put(a,entry);
                    } catch (RuntimeException denied) {
                        // No startup crash and no fallback to old raw export.
                        // Original P10 still blocks known raw ZIP construction.
                        LOCAL_DENIALS.incrementAndGet();
                    }
                });
            }
            @Override public void onActivityPaused(Activity a) { }
            @Override public void onActivitySaveInstanceState(Activity a, Bundle out) { }
            @Override public void onActivityStopped(Activity a) { }
            @Override public void onActivityDestroyed(Activity a) {
                if (a != null) installed.remove(a);
            }
        });
        return null;
    }

    @Override public List<Class<? extends Initializer<?>>> dependencies() {
        return Collections.emptyList();
    }
}
