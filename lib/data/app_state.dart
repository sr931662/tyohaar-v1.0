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
}
