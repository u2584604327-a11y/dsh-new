package com.dsh.android.p92;

import android.os.Looper;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

/**
 * Read-only mobile preflight for a DSH-owned request. GET /health only.
 * The frozen OmniGate POST layer remains the authoritative owner guard.
 */
public final class P92OmniGateHealthReader {
    private P92OmniGateHealthReader() {}
    public static P92DshRouteGate.Health read() throws Exception {
        if(Looper.myLooper()==Looper.getMainLooper())
            throw new IllegalStateException("P92_HEALTH_CANNOT_RUN_ON_MAIN_THREAD");
        HttpURLConnection con=(HttpURLConnection)
            new URL(P92DshRouteGate.HEALTH).openConnection();
        con.setRequestMethod("GET");
        con.setConnectTimeout(1800);
        con.setReadTimeout(2200);
        con.setUseCaches(false);
        con.setInstanceFollowRedirects(false);
        try {
            if(con.getResponseCode()!=200)
                throw new IllegalStateException("P92_HEALTH_UNAVAILABLE");
            ByteArrayOutputStream b=new ByteArrayOutputStream();
            try(InputStream in=con.getInputStream()){
                byte[] chunk=new byte[2048];int n;
                while((n=in.read(chunk))!=-1){
                    if(n==0)continue;
                    if(b.size()+n>32768)throw new IllegalStateException("P92_HEALTH_TOO_LARGE");
                    b.write(chunk,0,n);
                }
            }
            JSONObject obj=new JSONObject(new String(b.toByteArray(),
                StandardCharsets.UTF_8));
            if(!obj.has("verifiedNativeOwner")||!obj.has("observedRuntimeRoute"))
                throw new IllegalStateException("P92_MISSING_OWNER_FIELDS");
            JSONObject continuity=obj.optJSONObject("ownerContinuity");
            // Owner continuity is diagnostic only; live authoritative validation
            // happens inside SidecarProxyServer before each native API POST.
            boolean ambiguous=continuity!=null &&
                continuity.optBoolean("ambiguousOwners",false);
            String owner=obj.optString("verifiedNativeOwner","");
            String route=obj.optString("observedRuntimeRoute","");
            if("ambiguous_native_owners".equals(route))ambiguous=true;
            boolean verified=("main".equals(owner) &&
                "main_socket_and_driver_match".equals(route)) ||
                ("overlay".equals(owner) &&
                "overlay_socket_and_driver_match".equals(route));
            return new P92DshRouteGate.Health(obj.optBoolean("ok",false),
                obj.optBoolean("upstreamReachable",false),verified,ambiguous,
                obj.optString("listen",""),owner,route);
        } finally { con.disconnect(); }
    }
}
