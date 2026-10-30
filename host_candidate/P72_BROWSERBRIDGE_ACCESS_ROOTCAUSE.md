# P72 original AiBrowserView.currentWebView access and BrowserBridge failure

Prior user-supplied Android error was IllegalAccessError: android.webkit.WebView com.dsh.android.browser.AiBrowserView.currentWebView() inaccessible to com.dsh.android.browser.BrowserBridge. Current screenshots also show browser no reply and missing model tool results. P70 repaired one actual shared mailbox race, P71 tests result lifetime and synthetic WebView persistence, but neither changes original native BrowserBridge.

This phase inspects exact signed v138 DEX for the target WebView accessor's declared visibility and callsites in BrowserBridge, without copying source, executing scripts or accessing user data. If and only if it proves a unique inaccessible accessor and call, next implementation may change only its access modifier in a disposable derived package, verify all method bytes, preserve original features, then run actual ART invocation. It must NOT broadly make every WebView method public, alter arbitrary bridge behavior, weaken origin/permission checks or claim publication works.

Original model tool_result continuation, Bilibili comments and persistent user profile are still unverified. No fixed signer, no device install, no release. The P47 host-start deny and P68 isolated child must remain intact.
