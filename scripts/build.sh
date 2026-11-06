#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .build
clang -dynamiclib -O2 -Wall -Werror scripts/network_guard.c -o .build/network_guard.dylib
swift build --package-path swift -j 2
kotlin/gradlew -p kotlin --no-daemon --max-workers=1 :cli:installDist --console=plain
swift build --package-path samples/outbox/swift -j 2
kotlin/gradlew -p samples/outbox/kotlin --no-daemon --max-workers=1 :cli:installDist --console=plain
