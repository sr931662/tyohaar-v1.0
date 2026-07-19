import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'app.dart';

/// Runs in a separate isolate when a push arrives while the app is
/// backgrounded/terminated. Must be a top-level function. FCM's own OS-level
/// SDK already renders the system-tray notification for messages that carry
/// a `notification` payload (which is what our backend always sends) — this
/// handler exists so custom background data-processing has somewhere to go
/// later without needing to change the entry point again.
@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  try {
    await Firebase.initializeApp();
  } catch (_) {
    // Firebase not configured yet — nothing to do.
  }
}

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  try {
    await Firebase.initializeApp();
    FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);
  } catch (e) {
    debugPrint('Firebase not configured yet ($e). Push notifications disabled.');
  }

  runApp(const TyohaarApp());
}
