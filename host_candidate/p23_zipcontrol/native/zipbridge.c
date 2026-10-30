/* P23: bounded synthetic JNI Bionic linker probe; only three fixed own-APK paths. */
#include <jni.h>
#include <dlfcn.h>
#include <stdint.h>
#include <string.h>

JNIEXPORT jint JNICALL
Java_com_dsh_p23_zipcontrol_P23ControlWorker_probeNativeZipDlopen(
        JNIEnv *env, jclass unused, jstring apk_path, jint which) {
    (void)unused;
    const char *suffix = NULL;
    if(which==1) suffix="!/assets/p23control.so";
    if(which==2) suffix="!/assets/p23control.so.3";
    if(which==3) suffix="!/lib/x86_64/libp22version.so.3";
    if(suffix==NULL || apk_path==NULL) return -10;
    const char *base=(*env)->GetStringUTFChars(env,apk_path,NULL);
    if(base==NULL)return -11;
    size_t length=strlen(base);
    /* App sourceDir is platform-provided, not supplied by user/model. */
    if(length<8 || length>1000 ||
       !(length>4 && strcmp(base+length-4,".apk")==0)) {
       (*env)->ReleaseStringUTFChars(env,apk_path,base);
       return -12;
    }
    char path[1200];
    if(length+strlen(suffix)+1>sizeof(path)) {
        (*env)->ReleaseStringUTFChars(env,apk_path,base);return -13;
    }
    memcpy(path,base,length);
    strcpy(path+length,suffix);
    (*env)->ReleaseStringUTFChars(env,apk_path,base);
    void *handle=dlopen(path,RTLD_NOW|RTLD_LOCAL);
    if(handle==NULL){
        const char *error=dlerror();
        if(error==NULL)return -20;
        if(strstr(error,"not found")!=NULL)return -21;
        if(strstr(error,"not accessible")!=NULL)return -22;
        if(strstr(error,"Permission denied")!=NULL)return -23;
        if(strstr(error,"bad ELF")!=NULL)return -24;
        return -25;
    }
    int (*answer)(void)=(int (*)(void))dlsym(handle,"p22_versioned_answer");
    int result=answer==NULL?-31:answer();
    dlclose(handle);
    return result;
}
