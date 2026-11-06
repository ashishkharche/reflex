# Debug socket in the sample apps, 6 Nov 2026

Mac: Apple silicon, macOS 26.5.1, Xcode with the iOS 26.5 simulator runtime, Android SDK build tools 36.0.0. One dedicated iPhone 17 simulator and one dedicated API 36 ATD emulator, each created for the run, used one at a time and deleted afterwards. No physical phone.

| File | What it shows |
| --- | --- |
| `ios-ui.log`, `ios/ios-01.png` to `ios-06.png` | `live_ui_check.py ios`: six screen checks pass after OpenProduct, SetQuantity, Save, goBack and the restore |
| `android-ui.log`, `android/android-01.xml` to `android-06.xml` | `live_ui_check.py android`: the same six checks pass on the view tree |
| `ios-runner.log`, `android-runner.log` | `tests/inventory/live.json` with `--repeat 2 --allow-unguarded`: `RESULT PASS-UNGUARDED guard=live-socket` |
| `ios/ios-after-runner.png` | The simulator screen after the runner, back at `Cotton shirt: 3` |
| `exclusion.log` | `check_release_exclusion.sh`: every marker is 0 in Release and above 0 in Debug |
| `ios/ios-release.png` | The Release app launched with `-reflexPort 47814`: the list draws and no port opens |
| `red-unsaved-edit.log`, `ios/red-unsaved-edit-04.png` | Red: the first check skipped Save, so the list showed 3 and the check failed. Copied from the terminal of that run. |
| `red-no-app.log` | Red: the runner with no app listening ends `RESULT FAIL` and exits 2 |

Also seen and not saved as files:

- Android listening sockets after the bind fix: `::ffff:127.0.0.1:47815` only. Before it the Kotlin host bound `::1`.
- A debug build launched without `reflexPort` opened no port on either platform.
- The release APK, signed with the debug key only to install it, launched with `--ei reflexPort 47815`, drew the list, opened no port and had no `INTERNET` permission.
- With port 47815 already taken on the emulator, the debug app logged `socket host failed: java.net.BindException` and kept running.
