# Private DSH release workspace security

This repository is currently **private**. A private repository reduces public exposure, but it does not make workflow secrets or binary assets immune to access by maintainers or compromised workflows.

## Credentials
Do **not** upload:
- Original Android signing JKS/P12 and the key password.
- Cloudflare/Vercel/API/GitHub account tokens.
- Real diagnostic bundles, user cookies, chat exports, or device data.

The existing Actions authenticate to this same private repository via the ephemeral built-in `GITHUB_TOKEN` with only `contents: read`. They do not require or request signing secrets.

## APK source
The old signed APK can contain application code and embedded credentials. Upload it only to this private repository's **Release assets**, not a public repository and not regular Git history. If you do not want the APK hosted by GitHub, keep it local; the remote audit then remains blocked.

## No release claims
The v135/v138 audit only checks the existing APK identity, not P1-P6 integration. The P6 audit only runs offline synthetic tests and D8 conversion of JVM-compatible classes. Neither produces a modified APK or proves ART or real-phone safety.

## Future signed Android APKs
If, after code and native-host integration, you choose remote signing, it requires a separate manual authorization and reviewed workflow (prefer a tightly restricted protected Environment). An unexpected change of signing certificate makes a normal update to installed `com.dsh.android` impossible without an unsafe data-affecting operation. Keep the original signing material local by default.
