# DSH source migration provenance

## Source and scope

- Read-only source: `u2584604327-a11y/dshe`, PR #80 HEAD `e61eb7f321fe8b9f41f398af202f9d4ed089c3b2`.
- Destination: `u2584604327-a11y/dsh-new`, migration branch `migration/dshe-p98-20261031`.
- Migration type: **tracked working-tree snapshot**, not a complete Git history mirror.
- Source tracked blobs: **495**. Target contains all **495 source paths** plus this provenance document.
- Verification: **495/495 matching Git blob SHA and mode**, zero missing or modified source files, recursive Git tree results not truncated.
- Only text files tracked by the source snapshot were migrated. GitHub Secrets, signing keys, external credentials, original APK/engine binaries, and GitHub Release assets were **not** copied.
- Automated content scan rejected common credential formats before writing each batch. This is a narrow pattern scan, **not** a complete secrets or third-party licensing audit.

## Key verified source blob SHAs

- `.github/workflows/p96-original-stream-owner.yml`: `b883c4fb77bb59413fdcdfce1deac5bbda993135`
- `host_candidate/P98_ORIGINAL_AGENT_SESSION_ANDROID_GATE.md`: `6d036d262c5ad67fe387caeefdb87d2dc8337220`
- `host_candidate/p96_stream_owner/p98_original_agent_session_once.mjs`: `26f4cc51ff046fa6e2cf1241a2a25f6faacfe39e`
- `host_candidate/p96_stream_owner/p98_original_agent_inbox_once.mjs`: `fc74d7c64c2534ccfbb17aec9bf523c964eba33d`

## Next gate (not passed)

1. Adapt workflows that hard-code `u2584604327-a11y/dshe` and `private=true`, including P96.
2. Re-establish required Release asset references in the new repo or replace them with approved, verifiable build inputs; do not distribute original APK, engine, or signing material.
3. Re-run isolated source-only tests on the new repo before opening a PR or merging into `main`.
4. P98 SessionController.prompt / projection / ReactLoopInbox initialization and synthetic user turn are **not yet proven**. No Android production integration or final signed APK is claimed.

Issue: https://github.com/u2584604327-a11y/dsh-new/issues/1
