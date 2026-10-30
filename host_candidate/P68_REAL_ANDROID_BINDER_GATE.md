P68 REAL Android Binder bridge for P67 and P37

Baseline P67 Draft PR #51, SHA 038b84d92917fa89eb36e1b76ca6fd1681b52e25, JVM CI 41021256412 SUCCESS.

P68 adds Android Messenger adapter using framework Message.sendingUid, isolated UID, host-minted session, per-frame strict Bundle keys and P53 frame order. HELLO cannot allocate Process; CHILD_STARTED creates P37 Process via P67. Invalid frames, spoofing and disconnect fail closed. No READY promotion.

Existing P48 legacy path remains but disposable P43 side-by-side test Activity opts into P68; private APK build includes P67/P68 in classes3.dex. P47 fail-closed original host process launch remains unchanged. Android35 x86 fixture runs only fixed /system/bin/id -u, not Node production.

Source APK hash pinned, ephemeral signature, distinct com.dsh.p51.isolatedprobe no-permission test package. No owner phone update or signing key upload. Original EngineManager, runtime Node argv/env/cwd, READY parser and end-to-end inference remain NOT TESTED; formal v139 BLOCKED. PR Draft.
