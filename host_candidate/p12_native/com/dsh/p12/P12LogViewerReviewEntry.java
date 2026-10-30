package com.dsh.p12;

import android.app.Activity;
import android.app.AlertDialog;
import android.app.Application;
import android.os.Bundle;
import android.os.Looper;
import android.system.Os;
import android.system.OsConstants;
import android.system.StructStat;
import android.view.View;
import android.widget.TextView;
import com.dsh.p1.AndroidFdQueue;
import com.dsh.p1.ConsentLedger;
import com.dsh.p1.NativeDiagnosticReview;
import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashSet;
import java.util.Set;

/**
 * P12 native-only LogViewerActivity user-gesture adapter, SOURCE CANDIDATE.
 *
 * A trusted original Activity.onResume hook must explicitly invoke attach().
 * Merely packaging this class does NOT install a hook. Never expose attach()
 * from Node, JavaScriptInterface, web pages, or arbitrary Intent extras.
 *
 * Raw DSH ZIPs are not accepted; P10 legacy export remains disabled and
 * no ApprovedDiagnosticSendGate transport is connected. Existing logged data
 * and ordinary Android attachments are not read or modified by this adapter.
 */
public final class P12LogViewerReviewEntry {
    private static final String OWNER = "com.dsh.android.LogViewerActivity";
    private static final String ROOT = "dsh-native-diagnostic-root";
    private static final String QUEUE = "safe-review-queue";
    private static final int MAX_CHOICES = 24;
    private final Activity activity;
    private final String trustedDestination;
    private final Set<String> allowedDestinations;
    private final ConsentLedger.Audit audit;
    private final Application.ActivityLifecycleCallbacks lifecycle;
    private NativeDiagnosticReview currentReview;
    private AndroidFdQueue currentReader;
    private boolean closed;

    private P12LogViewerReviewEntry(Activity owner, String destination,
            Set<String> allowlist, ConsentLedger.Audit nativeAudit) {
        this.activity = owner;
        this.trustedDestination = destination;
        this.allowedDestinations = Collections.unmodifiableSet(new HashSet<String>(allowlist));
        this.audit = nativeAudit;
        this.lifecycle = new Application.ActivityLifecycleCallbacks() {
            public void onActivityCreated(Activity activity, Bundle state) { }
            public void onActivityStarted(Activity activity) { }
            public void onActivityResumed(Activity activity) { }
            public void onActivityPaused(Activity activity) { }
            public void onActivitySaveInstanceState(Activity activity, Bundle state) { }
            public void onActivityStopped(Activity activity) {
                if (activity == P12LogViewerReviewEntry.this.activity) closeCurrent();
            }
            public void onActivityDestroyed(Activity activity) {
                if (activity == P12LogViewerReviewEntry.this.activity) release();
            }
        };
    }

    public static P12LogViewerReviewEntry attach(Activity viewer,
            String nativeDestination, Set<String> nativeAllowlist,
            ConsentLedger.Audit nativeAudit) {
        if (Looper.myLooper() != Looper.getMainLooper()) throw new IllegalStateException("UI thread only");
        if (viewer == null || !OWNER.equals(viewer.getClass().getName()))
            throw new IllegalArgumentException("Trusted LogViewerActivity only");
        if (viewer.isFinishing() || viewer.isDestroyed())
            throw new IllegalStateException("Viewer already closing");
        if (nativeAudit == null || nativeAllowlist == null || nativeDestination == null ||
            !nativeDestination.startsWith("https://") ||
            !nativeAllowlist.contains(nativeDestination))
            throw new IllegalArgumentException("Trusted native HTTPS destination required");
        int exportId = viewer.getResources().getIdentifier("logExport", "id", viewer.getPackageName());
        int uploadId = viewer.getResources().getIdentifier("logUpload", "id", viewer.getPackageName());
        View export = exportId == 0 ? null : viewer.findViewById(exportId);
        View upload = uploadId == 0 ? null : viewer.findViewById(uploadId);
        if (export == null || upload == null || export == upload)
            throw new IllegalStateException("Legacy log buttons not independently available");

        P12LogViewerReviewEntry entry =
            new P12LogViewerReviewEntry(viewer, nativeDestination, nativeAllowlist, nativeAudit);
        viewer.getApplication().registerActivityLifecycleCallbacks(entry.lifecycle);
        // Avoid invoking legacy raw export/upload callbacks. P10 still blocks
        // their direct bundle creators independently if old paths are reached.
        export.setOnClickListener(v -> entry.showSafeReview());
        upload.setOnClickListener(v -> entry.showSafeReview());
        if (export instanceof TextView)
            ((TextView)export).setContentDescription("预览脱敏诊断包（仅本地，发送未接入）");
        if (upload instanceof TextView)
            ((TextView)upload).setContentDescription("预览脱敏诊断包（仅本地，发送未接入）");
        return entry;
    }

    private static File existingSafeDir(File parent, String leaf) throws IOException {
        if (!leaf.matches("[A-Za-z0-9][A-Za-z0-9._-]{0,63}")) throw new IOException("Invalid native leaf");
        File path = new File(parent, leaf);
        boolean newlyCreated = path.mkdir();
        if (!newlyCreated && !path.exists()) throw new IOException("Private directory cannot be created");
        try {
            if (newlyCreated) Os.chmod(path.getAbsolutePath(), 0700);
            StructStat s = Os.lstat(path.getAbsolutePath());
            if (!OsConstants.S_ISDIR(s.st_mode) ||
                s.st_uid != android.os.Process.myUid() ||
                (s.st_mode & 0077) != 0)
                throw new IOException("Native private directory ownership/mode rejected");
        } catch (android.system.ErrnoException ex) {
            throw new IOException("Native directory verification failed");
        }
        return path;
    }

    private void showSafeReview() {
        if (closed || activity.isFinishing() || activity.isDestroyed()) return;
        closeCurrent();
        try {
            File root = existingSafeDir(activity.getFilesDir(), ROOT);
            File queue = existingSafeDir(root, QUEUE);
            // File.listFiles() is advisory only: AndroidFdQueue independently
            // reopens each selected leaf by descriptor and verifies inode,
            // nlink, owner, mode and content at preview time.
            File[] children = queue.listFiles();
            if (children == null) throw new IOException("Native queue unavailable");
            ArrayList<File> eligible = new ArrayList<File>();
            for (File file : children) {
                String name = file.getName();
                if (name.matches("[A-Za-z0-9][A-Za-z0-9._-]{0,127}\\.json"))
                    eligible.add(file);
                if (eligible.size() > MAX_CHOICES) throw new IOException("Too many diagnostic files");
            }
            Collections.sort(eligible, Comparator.comparing(File::getName));
            if (eligible.isEmpty()) {
                new AlertDialog.Builder(activity).setTitle("安全诊断预览")
                    .setMessage("暂无经原生端生成和验证的脱敏诊断文件。旧 ZIP 导出与发送已关闭；不会访问或发送现存原始日志。")
                    .setPositiveButton("关闭", null).show();
                return;
            }
            currentReader = new AndroidFdQueue(root, QUEUE);
            currentReview = new NativeDiagnosticReview(
                activity, currentReader, allowedDestinations, trustedDestination, audit);
            String[] choices = new String[eligible.size()];
            for (int i = 0; i < choices.length; i++) choices[i] = eligible.get(i).getName();
            new AlertDialog.Builder(activity)
                .setTitle("选择要预览的脱敏诊断包（仅本地）")
                .setItems(choices, (dialog, index) -> {
                    if (!closed && currentReview != null && index >= 0 && index < eligible.size())
                        currentReview.preview(eligible.get(index));
                })
                .setNegativeButton("取消", (dialog, which) -> closeCurrent()).show();
        } catch (IOException | RuntimeException error) {
            closeCurrent();
            new AlertDialog.Builder(activity).setTitle("安全预览不可用")
                .setMessage("可信目录、文件格式或原生组件校验失败。未读取原始日志，也没有执行上传。")
                .setPositiveButton("关闭", null).show();
        }
    }

    private void closeCurrent() {
        if (currentReview != null) { currentReview.close(); currentReview = null; }
        if (currentReader != null) {
            try { currentReader.close(); } catch (IOException ignored) { }
            currentReader = null;
        }
    }

    private void release() {
        if (closed) return;
        closed = true;
        closeCurrent();
        activity.getApplication().unregisterActivityLifecycleCallbacks(lifecycle);
    }
}
