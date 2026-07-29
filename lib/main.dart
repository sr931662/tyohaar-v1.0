import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_crashlytics/firebase_crashlytics.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:firebase_performance/firebase_performance.dart';
import 'package:flutter_native_splash/flutter_native_splash.dart';
import 'app.dart';
import 'firebase_options.dart';
import 'utils/log.dart';
import 'widgets/production_error_screen.dart';

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
    final widgetsBinding = WidgetsFlutterBinding.ensureInitialized();
    // Keeps the native splash on screen (instead of a blank/white frame)
    // until app.dart's _AppStartup finishes resolving auth state and calls
    // FlutterNativeSplash.remove() — replaces the old in-app splash widget
    // with a direct native-splash-to-real-content handoff.
    FlutterNativeSplash.preserve(widgetsBinding: widgetsBinding);

    // Replaces Flutter's default error UI for any widget that throws during
    // build. In debug, keep the full diagnostic red screen — developers need
    // it. In release/profile, `assert()` failures like the one that prompted
    // this can't even reach here (asserts are compiled out entirely), but
    // other exceptions (null checks, index errors, etc.) still can, and
    // users should see a graceful fallback instead of the framework's bare
    // default. Reporting (Crashlytics) is handled separately below via
    // FlutterError.onError / PlatformDispatcher.onError — this only governs
    // what's drawn on screen.
    ErrorWidget.builder = (FlutterErrorDetails details) {
      if (kDebugMode) return ErrorWidget(details.exception);
      return const ProductionErrorScreen();
    };

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
