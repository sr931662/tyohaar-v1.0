import 'package:flutter/foundation.dart';

/// Debug-only logging — compiled out of release behavior via [kDebugMode]
/// so error/diagnostic traces never reach release-build device logs.
void logDebug(String message) {
  if (kDebugMode) debugPrint(message);
}
