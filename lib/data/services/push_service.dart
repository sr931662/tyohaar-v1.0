import 'dart:io';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:device_info_plus/device_info_plus.dart';

import '../api_client.dart';

/// Handles Firebase Cloud Messaging setup: permission request, token
/// registration with the backend, foreground display via a local
/// notification, and tap-to-open handling.
///
/// Safe to call even before a Firebase project is configured — every step
/// is wrapped so a missing/invalid `google-services.json` /
/// `GoogleService-Info.plist` degrades to a no-op instead of crashing the app.
class PushService {
  PushService._();
  static final PushService instance = PushService._();

  final ApiClient _api = ApiClient();
  final FlutterLocalNotificationsPlugin _localNotifications =
      FlutterLocalNotificationsPlugin();

  static const _androidChannel = AndroidNotificationChannel(
    'tyohaar_default',
    'Tyohaar Notifications',
    description: 'Booking updates, reminders, and offers from Tyohaar.',
    importance: Importance.high,
  );

  bool _initialized = false;
  String? _deviceId;

  /// Call once, after the user is authenticated (e.g. from RootNav.initState).
  Future<void> initialize() async {
    if (_initialized) return;
    _initialized = true;

    try {
      await Firebase.initializeApp();
    } catch (e) {
      debugPrint('PushService: Firebase not configured yet ($e). Push notifications disabled.');
      return;
    }

    try {
      await _setupLocalNotifications();
      await _requestPermission();
      await _registerToken();

      FirebaseMessaging.instance.onTokenRefresh.listen((newToken) {
        _registerToken(tokenOverride: newToken);
      });

      FirebaseMessaging.onMessage.listen(_handleForegroundMessage);
      FirebaseMessaging.onMessageOpenedApp.listen(_handleNotificationTap);
    } catch (e) {
      debugPrint('PushService: initialization failed ($e).');
    }
  }

  Future<void> _setupLocalNotifications() async {
    const androidInit = AndroidInitializationSettings('@mipmap/ic_launcher');
    const iosInit = DarwinInitializationSettings();
    await _localNotifications.initialize(
      const InitializationSettings(android: androidInit, iOS: iosInit),
    );
    await _localNotifications
        .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(_androidChannel);
  }

  Future<void> _requestPermission() async {
    await FirebaseMessaging.instance.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );
  }

  void _handleForegroundMessage(RemoteMessage message) {
    final notification = message.notification;
    if (notification == null) return;
    _localNotifications.show(
      notification.hashCode,
      notification.title,
      notification.body,
      NotificationDetails(
        android: AndroidNotificationDetails(
          _androidChannel.id,
          _androidChannel.name,
          channelDescription: _androidChannel.description,
          importance: Importance.high,
          priority: Priority.high,
        ),
        iOS: const DarwinNotificationDetails(),
      ),
    );
  }

  void _handleNotificationTap(RemoteMessage message) {
    // Deep-link routing can be added here using message.data['action_url']
    // once a global navigator key is wired in — left as a no-op for now.
    debugPrint('PushService: notification tapped, data=${message.data}');
  }

  Future<String> _getStableDeviceId() async {
    if (_deviceId != null) return _deviceId!;
    final deviceInfo = DeviceInfoPlugin();
    try {
      if (Platform.isAndroid) {
        final info = await deviceInfo.androidInfo;
        _deviceId = info.id;
      } else if (Platform.isIOS) {
        final info = await deviceInfo.iosInfo;
        _deviceId = info.identifierForVendor ?? info.name;
      } else {
        _deviceId = 'unknown-device';
      }
    } catch (_) {
      _deviceId = 'unknown-device';
    }
    return _deviceId!;
  }

  Future<void> _registerToken({String? tokenOverride}) async {
    try {
      final token = tokenOverride ?? await FirebaseMessaging.instance.getToken();
      if (token == null) return;

      final deviceId = await _getStableDeviceId();
      final platform = Platform.isIOS ? 'ios' : (Platform.isAndroid ? 'android' : 'web');

      String? manufacturer;
      String? model;
      String? osVersion;
      final deviceInfo = DeviceInfoPlugin();
      try {
        if (Platform.isAndroid) {
          final info = await deviceInfo.androidInfo;
          manufacturer = info.manufacturer;
          model = info.model;
          osVersion = info.version.release;
        } else if (Platform.isIOS) {
          final info = await deviceInfo.iosInfo;
          manufacturer = 'Apple';
          model = info.utsname.machine;
          osVersion = info.systemVersion;
        }
      } catch (_) {}

      await _api.dio.post('users/me/devices', data: {
        'device_id': deviceId,
        'device_type': 'mobile',
        'platform': platform,
        'push_notification_token': token,
        'manufacturer': manufacturer,
        'model': model,
        'os': platform,
        'os_version': osVersion,
      });
    } catch (e) {
      debugPrint('PushService: device registration failed ($e).');
    }
  }
}
