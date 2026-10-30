package com.dsh.android.p90;

/** Presentation-only evidence projections. These values are not auth or privilege grants. */
public final class P90EvidenceProjection {
    private P90EvidenceProjection() {}
    public static String balance(boolean authenticated, Long wallet, Long bonus) {
        if (!authenticated) return "未登录";
        if (wallet == null || bonus == null || wallet < 0 || bonus < 0) return "未提供";
        if (Long.MAX_VALUE - wallet < bonus) return "未提供";
        return "合计 " + (wallet + bonus) + "（钱包 " + wallet + "，赠送 " + bonus + "）";
    }
    public static String tokens(Long providerUsage, Long localEstimate) {
        if (providerUsage != null && providerUsage >= 0) return providerUsage + "（官方）";
        if (localEstimate != null && localEstimate > 0) return "≈" + localEstimate + "（本地估算）";
        return "未提供";
    }
    public static String privilege(boolean managerPresent, boolean binderAlive,
                                   boolean explicitlyAuthorized, boolean liveChannel) {
        if (!managerPresent) return "管理器未安装";
        if (!binderAlive) return "Binder 未连接";
        if (!explicitlyAuthorized) return "尚未授权";
        if (!liveChannel) return "通道未就绪";
        return "已授权且通道就绪";
    }
}
