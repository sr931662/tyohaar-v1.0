import 'package:flutter/material.dart';

enum UserPOV { customer, vendor }

class AppState extends ChangeNotifier {
  static final AppState instance = AppState._internal();
  AppState._internal();

  UserPOV _pov = UserPOV.customer;
  UserPOV get pov => _pov;

  void setPOV(UserPOV newPOV) {
    if (_pov == newPOV) return;
    _pov = newPOV;
    notifyListeners();
  }

  void togglePOV() {
    _pov = _pov == UserPOV.customer ? UserPOV.vendor : UserPOV.customer;
    notifyListeners();
  }

  /// Routes the app into the correct shell based on the logged-in user's
  /// backend role — vendors land in the Vendor POV, everyone else (customer,
  /// or unset/unknown) stays in the customer shell.
  void applyRole(String? role) {
    setPOV(role == 'vendor' ? UserPOV.vendor : UserPOV.customer);
  }
}
