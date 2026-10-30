# P33: pinned signed-v138 Android native host Node/IPC invocation graph

## Real P31/P32 facts that must not be relabeled
P31 real physical device Android36 ARM64 user-copied result establishes:
- authenticated Binder sender, isolated Worker and original Node child UID 99055;
- identical exact signed v138 Node plus 10 native libs SHA-256;
- Node can read own ELF signature, and native Node child unable to stat or
  read host-owned random canary (ENOENT) while host SHA remains unchanged;
- native Node cannot connect to the two tested local/TEST-NET TCP endpoints,
  EACCES both; not full network security, generic JavaScript safety,
  or the exact cause of file ENOENT.

P32 (https://github.com/u2584604327-a11y/dshe/pull/16) has a
compiled Android Messenger host adapter with UID/session-bound one-shot
synthetic METADATA_COUNT; GitHub JDK/Android compilation CI passed.
But that adapter has not been invoked from original DSH MainActivity.

## P33 exact actual signed APK audit
Source: host_candidate/p33_original_host_entry_graph.py
Workflow: .github/workflows/p33-original-host-entry-graph.yml

Only source allowed: privately held original v138
DSH-vc138-P0-OFFLINE-TEST-fixed-signature.apk
SHA256 3ca56655d79afc57431636e340823e7071bc830615ca615c485b0b9a30b6e3e5.

In temporary, private CI, parse each real classes*.dex directly with pinned
androguard. Record only bounded method/class names, direct invoke
callee signatures and original method offsets, including:
- MainActivity/DshApplication lifecycle methods;
- Node, native runtime, server, bootstrap, plugin/tool registration;
- ProcessBuilder.start, Runtime.exec, System.loadLibrary/load;
- WebView addJavascriptInterface/evaluateJavascript/loadUrl;
- Android Context bindService/startService;
- prior uploader and diagnostic bridge.
Reconstruct one- and two-hop *static direct* application caller paths
into fixed platform sinks. The graph is an audit aid, not a committed
alteration or runtime execution trace.

No user data, raw string pool, file or network payload, APK binary,
signed ZIP, signing key, credential, model chat history or generated
executable is committed, uploaded as an Artifact or published.
Parsed JSON and exact original APK are destroyed in the ephemeral runner.
Only source, fixed status and bounded method/count summaries remain.

## Interpretation and next genuine integration
1. Use the measured actual invoke sites to identify the intended native
   process-start edge, class/declaration and entry lifecycle; compare
   Android Activity to existing original Node bootstrap JS.
2. A DEX static callsite alone does NOT authorize patching that method;
   callback behavior, native-side dynamic dispatch, Node JS plugins,
   WebView JavaScript bridge and ART compatibility need separate checks.
3. The actual full Android Java/Kotlin source remains unavailable in
   this repo. A validated host adapter class added to a new DEX
   without a real call edge is NOT wired.
4. Only a private, separately signed, disposable integration candidate
   can be tested, with real Android ART, zero leaking API keys and no
   unrestricted file/URL/FD broker. Original v138 installed user APK
   and fixed certificate remain unchanged.
5. The previous Android app's chats, API stream, file/photo sends,
   automation, WebView profiles, logs and native tool UI need specific
   functional regression before considering production signing.
6. Any real production v139 data-preserving signing requires separate
   explicit authorization after all hard gates, no original key in GitHub.

P33_ORIGINAL_V138_DEX_METHOD_EDGE_GRAPH=CI_PENDING
P33_RUNNING_ORIGINAL_NODE_APP_HOST_INTEGRATION=NOT_IMPLEMENTED
P33_ONE_SHOT_NATIVE_IPC_REAL_DSH_INVOCATION=NOT_IMPLEMENTED
P33_SIGNED_ORIGINAL_DSH_V139=NO
P33_REAL_PHONE_DATA_AND_PRODUCTION=UNCHANGED
P33_RELEASE=BLOCKED
