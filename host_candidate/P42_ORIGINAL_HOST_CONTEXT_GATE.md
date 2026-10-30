# P42 real original DSH host and isolated Node launch envelope

P41 rebuilt **the original DSH app** with P40's pass-through bytecode trampoline; original and modified apps both launched 6 seconds in Android 35 emulator. This is **not** the actual isolated Node host.

This gate inspects exact pinned signed v138 (read-only in private CI):
- AndroidManifest application registration, whether it already supplies a custom Application, service/provider counts, exported/isolated Service boundaries, native extraction and permission INTERNET.
- Original EngineManager main coroutine and related direct ProcessBuilder APIs (command, environment, directory, redirects, start), including other two original starts.
- Reports **only categorical API names and booleans**, no command argument contents, file paths, environment values, secrets or original binaries.
- Destroys original byte input and transient report; never publishes/downloads derivative app.

## Hard blockers for production v139
A working Process proxy must faithfully handle original command, environment, working directory, Node script/data, stdin and local HTTP/WebSocket or native sockets. P38's original Node **fixed synthetic eval** is not the actual DSH engine. P31's real isolated Node had TCP denied EACCES, so full original engine communication cannot be assumed to work in restricted UID. Do not grant INTERNET, arbitrary shared private directories, shell or opaque Node actions to the worker by accident.

Only after a concrete least-privilege host broker and authenticated Binder worker is implemented in actual DSH can this bridge return P37's Process. Rejected/failed isolation cannot silently fall back to original ProcessBuilder.start. The original fixed signing environment cannot be used until real functionality, isolation, and owner-device validation pass.

P42_EXACT_HOST_METADATA=READ_ONLY
P42_ORIGINAL_APP_ISOLATED_SERVICE=NOT_IMPLEMENTED
P42_REAL_ENGINE_IPC_AND_FILESYSTEM=NOT_IMPLEMENTED
P42_FINAL_V139_APK=BLOCKED
