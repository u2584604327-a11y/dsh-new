# P36: real ORIGINAL ARM64 Node stdout -> Android isolated Worker -> trusted Binder/UI

## Real prior gates and why this phase
P31 owner Android API36: exact original Node and 10 ELF hashes PASS,
framework sendingUid == Worker UID == original Node getuid;
own ELF fs read PASS, host private canary not visible while byte stable;
fixed loopback and TEST-NET TCP connects DENIED_EACCES. Narrow scope only.
P34 Android35 x86_64 emulator: real trusted Activity + Binder isolated worker,
real native button tap, P32 one-shot grant and replay denial PASS
https://github.com/u2584604327-a11y/dshe/actions/runs/40882377690 .
But the P34 Worker had a synthetic hardcoded Java string, not original Node
stdout. P36 connects an actual original ARM64 Node stdout to P32.

## Delivered candidate source
Separate package com.dsh.p36.nodebridge, Android API34+ ARM64 only, zero
requested permissions, nonexported isolatedProcess Service. Original
signed v138 APK SHA256
3ca56655d79afc57431636e340823e7071bc830615ca615c485b0b9a30b6e3e5.
Exact original Node binary SHA256
a0d21a1589312919114b24a5cc520c30ab7f26f9985b3f0c643c153172ebd1e6.
All ten original ELF aliases and preload lock verified against P28/P31
hash record before launching the immutable package native executable.
Node runs one fixed in-package --eval program, only prints
UID=<actual process.getuid> and a single canonical bounded JSON
{"op":"METADATA_COUNT","limit":3}, with no user arguments. The
Worker confirms Node exit zero, child process UID equals actual isolated
Service, exactly two stdout lines, exact canonical JSON, no extra output.
Worker sends that exact verified string through Messenger, with
platform-authenticated Android sendingUid, to actual P32AndroidBinderPort
and P17CapabilityGate in trusted host process.

Host MUST observe unauthenticated denial before allowing the native
approval button. Only a real trusted native UI click can approve a
single 10-second UID/session-bound synthetic count; replay must fail.
Host verifies isolated Worker sender UID and a monotonic sequence of
the fixed status-only events, and only reports PASS once all stages
are received. Background onStop revokes all pending permissions.

No Node network, arbitrary JS/files, real personal file/photo upload,
real AI tool invocation, browser, credential, diagnostic or shell.
No original DSH signing key or Android package replacement. Private
throwaway certificate; APK withheld from any public release. Test
reports contain only fixed stage/state/UID counters, not raw stdout
or private paths.

## IMPORTANT unproven and release blockers
Although Node-origin payload is real, the Worker is test-app code;
node stdout provenance is enforced by this test Worker's code, NOT
by independently attested Node/TEE or the actual original DSH.
Untrusted Node code could still choose to print the same allowed frame;
the host must authorize per capability regardless of claimed origin.
There is NO original DSH MainActivity/EngineManager integration.
P35 exact real original DEX proves EngineManager stores a Java Process
handle and depends on daemon reader thread + startup CountDownLatch +
StateFlow Ready; those actual startup/shutdown semantics are not moved
to isolated Service. Native browser, chat, media, network proxy and
the real diagnostic send pathways remain unintegrated.
VM identity/device impersonation not achieved or implied.
No production v139 versionCode, original fixed signature, merge or deploy.

P36_ORIGINAL_11_ARM64_LIBS_PACKAGING=PASS_CI_40891336044_40891336046
P36_REAL_NODE_STDOUT_TO_P32_BROKER_ON_PHONE=NOT_TESTED
P36_REAL_NODE_CHILD_ISOLATED_UID=NOT_TESTED_THIS_INTEGRATION
P36_REAL_NATIVE_UI_ONETIME_CONSENT=NOT_TESTED_THIS_INTEGRATION
P36_REAL_DSH_ENGINEMANAGER_PROCESS_HANDLE_WIRING=NO
P36_REAL_DSH_V139_RELEASE=BLOCKED

## Verified GitHub private delivery

- Build-only exact original ELF + APK QA: https://github.com/u2584604327-a11y/dshe/actions/runs/40891336044 (SUCCESS)
- Independent private Draft delivery: https://github.com/u2584604327-a11y/dshe/actions/runs/40891336046 (SUCCESS)
- Private unpublished P36 Draft id 427968015: https://github.com/u2584604327-a11y/dshe/releases/tag/untagged-d5956a5a3d74e84f668f
- Exact assets verified via authenticated GitHub Release collection: P36-Private-ARM64-Original-Node-Binder-Bridge.apk (97,392,158 bytes), README-P36-PRIVATE.txt and SHA256SUMS.txt. draft=true; published_at=null.
- P36_ANDROID36_PHYSICAL_PHONE_ACTUAL_NODE_TO_BINDER=AWAITING_OWNER_RESULT. GitHub CI can neither simulate original ARM64 physical Node nor prove original DSH EngineManager migration.
- DO_NOT_PUBLISH_OR_SIGN_V139=YES.
