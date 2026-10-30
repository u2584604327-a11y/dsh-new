#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DIR="$ROOT/host_candidate/p37_remote_process"
OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT
javac --release 8 -d "$OUT" \
 "$DIR/src/com/dsh/p37/P37RemoteProcess.java" \
 "$DIR/test/com/dsh/p37/P37RemoteProcessTest.java"
java -cp "$OUT" com.dsh.p37.P37RemoteProcessTest
