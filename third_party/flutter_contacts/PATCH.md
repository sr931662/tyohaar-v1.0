# Local patch of flutter_contacts 1.1.9+2

Vendored from pub.dev (the last release of the 1.x API; 2.x is a rewrite with a
different Dart API). Only `ios/Classes/SwiftFlutterContactsPlugin.swift` differs
from upstream. Android and Dart code are untouched.

## Why
Upstream registers with
`UIApplication.shared.delegate!.window!!.rootViewController!`. With the
scene-based lifecycle (`UIApplicationSceneManifest`, `FlutterSceneDelegate`) and
an implicit Flutter engine, plugins register before any window exists and
`AppDelegate.window` is nil, so the app crashed at launch with
"unexpectedly found nil while unwrapping an Optional value".

## What changed
- The root view controller is no longer captured at registration. It is resolved
  when the picker/editor is opened, from the connected window scene (falling
  back to the app delegate's window for non-scene apps), and presented from the
  topmost presented controller.
- If no controller is available the Flutter call fails with a
  `NO_VIEW_CONTROLLER` error instead of crashing.
- Method/event channel names and behaviour are unchanged.

Drop this directory and go back to `flutter_contacts: ^x` once upstream ships a
scene-safe release.
