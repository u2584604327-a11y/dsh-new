/* Disposable JNI bridge for Bionic documented dlopen("base.apk!/lib/...").
 * No shell, device data, credentials or arbitrary file/network broker.
 */
#include <jni.h>
#include <dlfcn.h>
#include <string.h>
#include <stdint.h>

JNIEXPORT jint JNICALL
Java_com_dsh_p22_ziplink_P22ZipLinkWorker_probeNativeZipDlopen(
        JNIEnv *env, jclass klass, jstring zip_native_path) {
    (void)klass;
    if (zip_native_path == NULL) return -10;
    const char *path = (*env)->GetStringUTFChars(env, zip_native_path, NULL);
    if (path == NULL) return -11;
    const char *fixed = "!/lib/x86_64/libp22version.so.3";
    const size_t length = strlen(path), suffix_len = strlen(fixed);
    int valid = length > suffix_len && length < 1024
        && strcmp(path + length - suffix_len, fixed) == 0;
    if (!valid) {
        (*env)->ReleaseStringUTFChars(env, zip_native_path, path);
        return -12;
    }
    // Only the test APK's ZIP library is allowed; no generic native proxy.
    void *handle = dlopen(path, RTLD_NOW | RTLD_LOCAL);
    (*env)->ReleaseStringUTFChars(env, zip_native_path, path);
    if (handle == NULL) {
        const char *error = dlerror();
        if (error == NULL) return -20;
        if (strstr(error, "not found") != NULL) return -21;
        if (strstr(error, "not accessible") != NULL) return -22;
        if (strstr(error, "Permission denied") != NULL) return -23;
        if (strstr(error, "bad ELF") != NULL) return -24;
        return -25;
    }
    int (*answer)(void) = (int (*)(void))dlsym(handle, "p22_versioned_answer");
    int result = answer == NULL ? -31 : answer();
    dlclose(handle);
    return result;
}
