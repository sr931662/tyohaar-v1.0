import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// The city that drives package filtering app-wide, once the user has
/// explicitly confirmed one — either by accepting a GPS-based suggestion or
/// picking one manually in Explore. Persisted so a confirmed choice survives
/// restarts; until it's set, screens fall back to their existing per-screen
/// city logic (saved address, "All Cities", etc).
class CityPreference extends ChangeNotifier {
  static final CityPreference instance = CityPreference._internal();
  CityPreference._internal();

  static const _storage = FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );
  static const _key = 'ty_active_city';

  String? _activeCity;
  bool _hasDecided = false;

  /// The confirmed city filter, or null if none is active (either nothing
  /// has been decided yet, or the user explicitly chose "All Cities").
  String? get activeCity => _activeCity;

  /// Whether the user has ever made an explicit choice (a city, or
  /// explicitly "All Cities"). Used to stop the GPS-suggestion prompt from
  /// firing again once the user has decided either way.
  bool get hasDecided => _hasDecided;

  Future<void> loadStored() async {
    try {
      final stored = await _storage.read(key: _key);
      if (stored != null) {
        _hasDecided = true;
        _activeCity = stored.isEmpty ? null : stored;
      }
    } catch (_) {
      // Non-fatal — screens just fall back to their default city logic.
    }
  }

  Future<void> setActiveCity(String cityName) async {
    _activeCity = cityName;
    _hasDecided = true;
    notifyListeners();
    try {
      await _storage.write(key: _key, value: cityName);
    } catch (_) {}
  }

  /// Explicit "no city filter" choice (e.g. picking "All Cities" in
  /// Explore) — distinct from never having decided.
  Future<void> clearActiveCity() async {
    _activeCity = null;
    _hasDecided = true;
    notifyListeners();
    try {
      await _storage.write(key: _key, value: '');
    } catch (_) {}
  }
}
