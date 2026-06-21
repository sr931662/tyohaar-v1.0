import 'package:flutter/material.dart';

/// A global, lightweight theme switcher.
///
/// Defaults to *Festival of Lights* (dusk) — the hero, shareable mood.
class ThemeController extends ChangeNotifier {
  bool _dark = true;

  bool get isDark => _dark;
  ThemeMode get mode => _dark ? ThemeMode.dark : ThemeMode.light;

  void toggle() {
    _dark = !_dark;
    notifyListeners();
  }

  void setDark(bool value) {
    if (_dark == value) return;
    _dark = value;
    notifyListeners();
  }
}

/// Simple global instance — fine for a UI layer; swap for your DI of choice.
final themeController = ThemeController();
