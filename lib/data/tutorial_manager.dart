import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'auth_manager.dart';

/// Tracks which per-screen tutorial overlays a given account has already
/// seen, so each one shows exactly once per account (not once per device,
/// and not once per app session).
class TutorialManager {
  static final TutorialManager instance = TutorialManager._internal();
  TutorialManager._internal();

  static const _storage = FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );

  String? _keyFor(String screenKey) {
    final userId = AuthManager.instance.currentUser?.id;
    if (userId == null || userId.isEmpty) return null;
    return 'ty_tutorial_seen_${userId}_$screenKey';
  }

  /// True when this screen's tutorial has not yet been shown to the
  /// currently signed-in account. Always false when there is no signed-in
  /// user — tutorials are a per-account feature, not shown to guests.
  Future<bool> shouldShow(String screenKey) async {
    final key = _keyFor(screenKey);
    if (key == null) return false;
    try {
      final seen = await _storage.read(key: key);
      return seen != 'true';
    } catch (_) {
      return false;
    }
  }

  Future<void> markSeen(String screenKey) async {
    final key = _keyFor(screenKey);
    if (key == null) return;
    try {
      await _storage.write(key: key, value: 'true');
    } catch (_) {
      // Non-fatal — worst case the tutorial shows again next visit.
    }
  }
}
