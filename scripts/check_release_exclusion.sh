#!/bin/bash
# Proves that release builds of the sample apps leave the debug socket host out and that
# debug builds keep it (the positive control). Usage: scripts/check_release_exclusion.sh [ios|android|both]
# iOS needs Xcode and XcodeGen. Android needs the Android SDK (ANDROID_HOME or ~/Library/Android/sdk).
set -euo pipefail
cd "$(dirname "$0")/.."
which=${1:-both}
failures=0
report() { # name, count in release, count in debug
    if [ "$2" -eq 0 ] && [ "$3" -gt 0 ]; then
        echo "EXCLUSION PASS $1 release=0 debug=$3"
    else
        echo "EXCLUSION FAIL $1 release=$2 debug=$3"; failures=$((failures + 1))
    fi
}

if [ "$which" = ios ] || [ "$which" = both ]; then
    data=.build/ios-dd
    (cd mobile/ios && xcodegen generate --quiet)
    for config in Release Debug; do
        xcodebuild -project mobile/ios/InventoryMobile.xcodeproj -scheme InventoryMobile -configuration $config \
            -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' -derivedDataPath $data -jobs 2 \
            CODE_SIGNING_ALLOWED=NO build -quiet > .build/ios-$config.log 2>&1 || { echo "ios $config build failed: .build/ios-$config.log"; exit 2; }
    done
    release=$data/Build/Products/Release-iphonesimulator/InventoryMobile.app
    debug=$data/Build/Products/Debug-iphonesimulator/InventoryMobile.app
    echo "IOS release binary $(lipo -archs $release/InventoryMobile) files=$(ls $release | tr '\n' ' ')"
    for marker in SocketHost ReflexSocketHost ReflexKit InventoryIntrospection AppNode "REFLEX LISTENING"; do
        r=$(cat $release/InventoryMobile | strings -a | grep -c "$marker" || true)
        d=$(cat $debug/InventoryMobile $debug/*.dylib 2>/dev/null | strings -a | grep -c "$marker" || true)
        report "ios string=\"$marker\"" "$r" "$d"
    done
fi

if [ "$which" = android ] || [ "$which" = both ]; then
    sdk=${ANDROID_HOME:-$HOME/Library/Android/sdk}
    tools=$(ls -d "$sdk"/build-tools/* | sort -V | tail -1)
    # lintVital is skipped: it is unrelated to exclusion and runs out of metaspace on small machines.
    kotlin/gradlew -p kotlin -Pmobile=true --no-daemon --max-workers=1 :mobile:assembleDebug :mobile:assembleRelease \
        -x lintVitalAnalyzeRelease --console=plain -q > .build/android-build.log 2>&1 || { echo "android build failed: .build/android-build.log"; exit 2; }
    release=kotlin/mobile/build/outputs/apk/release/mobile-release-unsigned.apk
    debug=kotlin/mobile/build/outputs/apk/debug/mobile-debug.apk
    classes() { "$tools/dexdump" "$1" 2>/dev/null | grep "Class descriptor" | grep -cE "$2" || true; }
    report "android classes=reflex.kit.*" "$(classes $release 'Lreflex/kit/')" "$(classes $debug 'Lreflex/kit/')"
    report "android class=SocketHost" "$(classes $release 'SocketHost')" "$(classes $debug 'SocketHost')"
    report "android class=reflex.AppNode" "$(classes $release 'Lreflex/AppNode;')" "$(classes $debug 'Lreflex/AppNode;')"
    # The dependency graph itself, so the proof does not rest on shrinking or a runtime flag.
    graph() { kotlin/gradlew -p kotlin -Pmobile=true --no-daemon --max-workers=1 -q :mobile:dependencies \
        --configuration "$1" --console=plain 2>>.build/android-build.log | grep -cE "project ':(reflex-socket|introspection)'" || true; }
    report "android dependency=:reflex-socket,:introspection" "$(graph releaseRuntimeClasspath)" "$(graph debugRuntimeClasspath)"
    perm() { "$tools/aapt2" dump permissions "$1" | grep -c "android.permission.INTERNET" || true; }
    report "android permission=INTERNET" "$(perm $release)" "$(perm $debug)"
fi

if [ "$failures" -eq 0 ]; then echo "RESULT EXCLUSION PASS"; else echo "RESULT EXCLUSION FAIL failures=$failures"; exit 1; fi
