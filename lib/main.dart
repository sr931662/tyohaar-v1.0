import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_crashlytics/firebase_crashlytics.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:firebase_performance/firebase_performance.dart';
import 'app.dart';
import 'firebase_options.dart';
import 'utils/log.dart';

/// Runs in a separate isolate when a push arrives while the app is
/// backgrounded/terminated. Must be a top-level function. FCM's own OS-level
/// SDK already renders the system-tray notification for messages that carry
/// a `notification` payload (which is what our backend always sends) — this
/// handler exists so custom background data-processing has somewhere to go
/// later without needing to change the entry point again.
@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  try {
    await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
  } catch (_) {
    // Firebase not configured yet — nothing to do.
  }
}

void main() {
  runZonedGuarded(() async {
    WidgetsFlutterBinding.ensureInitialized();

    try {
      await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
      FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);

      // Crashlytics/Performance collection is disabled in debug builds to
      // avoid noise from local development crashes and profiling runs.
      await FirebaseCrashlytics.instance
          .setCrashlyticsCollectionEnabled(!kDebugMode);
      await FirebasePerformance.instance
          .setPerformanceCollectionEnabled(!kDebugMode);
      FlutterError.onError = FirebaseCrashlytics.instance.recordFlutterFatalError;
      PlatformDispatcher.instance.onError = (error, stack) {
        FirebaseCrashlytics.instance.recordError(error, stack, fatal: true);
        return true;
      };
    } catch (e) {
      logDebug('Firebase not configured yet ($e). Push notifications, crash reporting, analytics, and performance monitoring disabled.');
    }

    runApp(const TyohaarApp());
  }, (error, stack) {
    logDebug('Uncaught zone error: $error');
    FirebaseCrashlytics.instance.recordError(error, stack, fatal: true);
  });
}
