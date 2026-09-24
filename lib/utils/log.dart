import 'package:firebase_crashlytics/firebase_crashlytics.dart';
import 'package:flutter/foundation.dart';

/// Debug-only logging — compiled out of release behavior via [kDebugMode]
/// so error/diagnostic traces never reach release-build device logs.
void logDebug(String message) {
  if (kDebugMode) debugPrint(message);
}

/// Reports a caught error that the UI handled but a developer still needs to
/// see — a screen that fell back to "Something went wrong", say.
///
/// [logDebug] alone is a no-op in release, so these failures were invisible
/// on real devices: a tester could only report the fallback message, with no
/// endpoint, status code or stack to act on. This keeps the debug print and
/// additionally records a Crashlytics non-fatal in release, where [context]
/// names the operation that failed.
///
/// Never throws: reporting a problem must not create a second one.
void logError(String context, Object error, [StackTrace? stack]) {
  if (kDebugMode) {
    debugPrint('$context: $error');
    return;
  }
  try {
    FirebaseCrashlytics.instance.recordError(
      error,
      stack,
      reason: context,
      fatal: false,
    );
  } catch (_) {
    // Crashlytics not initialised (or disabled) — nothing further to do.
  }
}
