import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../screens/auth_screen.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../widgets/ty_button.dart';
import 'models.dart';

const _kAccessToken = 'ty_access_token';
const _kRefreshToken = 'ty_refresh_token';

/// Manages authentication state and persists tokens securely across app restarts.
class AuthManager extends ChangeNotifier {
  static final AuthManager instance = AuthManager._internal();
  AuthManager._internal();

  static const _storage = FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );

  bool _isAuthenticated = false;
  bool _isGuest = false;
  bool _isInitializing = true;

  String? _accessToken;
  String? _refreshToken;
  User? _currentUser;

  bool get isAuthenticated => _isAuthenticated;
  bool get isGuest => _isGuest;
  bool get isInitializing => _isInitializing;
  String? get accessToken => _accessToken;
  String? get refreshToken => _refreshToken;
  User? get currentUser => _currentUser;

  /// Called once at app startup to restore a persisted session.
  Future<void> loadStoredAuth() async {
    try {
      final access = await _storage.read(key: _kAccessToken);
      final refresh = await _storage.read(key: _kRefreshToken);
      if (access != null && access.isNotEmpty) {
        _accessToken = access;
        _refreshToken = refresh;
        _isAuthenticated = true;
      }
    } catch (_) {
      // Storage read failure — treat as logged-out
    } finally {
      _isInitializing = false;
      notifyListeners();
    }
  }

  /// Called after a successful login or register response from the API.
  Future<void> login(String accessToken, String refreshToken, User user) async {
    _accessToken = accessToken;
    _refreshToken = refreshToken;
    _currentUser = user;
    _isAuthenticated = true;
    _isGuest = false;
    await _storage.write(key: _kAccessToken, value: accessToken);
    await _storage.write(key: _kRefreshToken, value: refreshToken);
    notifyListeners();
  }

  /// Updates the current user object (e.g. after fetching /users/me).
  void setUser(User user) {
    _currentUser = user;
    notifyListeners();
  }

  /// Replaces the stored access token after a successful token refresh.
  Future<void> updateAccessToken(String newAccessToken) async {
    _accessToken = newAccessToken;
    await _storage.write(key: _kAccessToken, value: newAccessToken);
    notifyListeners();
  }

  void skip() {
    _isAuthenticated = false;
    _isGuest = true;
    notifyListeners();
  }

  /// Clears all tokens and user state — call this after the logout API succeeds.
  Future<void> logout() async {
    _isAuthenticated = false;
    _isGuest = false;
    _accessToken = null;
    _refreshToken = null;
    _currentUser = null;
    await _storage.deleteAll();
    notifyListeners();
  }

  /// Checks if the user is authenticated; shows the login gate if not.
  bool checkAuth(BuildContext context, {required String action, VoidCallback? onAuthenticated}) {
    if (_isAuthenticated) return true;
    showAuthGate(context, action: action, onAuthenticated: onAuthenticated);
    return false;
  }
}

void showAuthGate(BuildContext context, {required String action, VoidCallback? onAuthenticated}) {
  showModalBottomSheet(
    context: context,
    backgroundColor: Colors.transparent,
    isScrollControlled: true,
    builder: (context) => _AuthGateSheet(action: action, onAuthenticated: onAuthenticated),
  );
}

class _AuthGateSheet extends StatelessWidget {
  final String action;
  final VoidCallback? onAuthenticated;

  const _AuthGateSheet({required this.action, this.onAuthenticated});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;

    return Container(
      padding: EdgeInsets.fromLTRB(24, 24, 24, MediaQuery.of(context).padding.bottom + 32),
      decoration: BoxDecoration(
        color: ty.paper,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(32)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 40,
            height: 4,
            decoration: BoxDecoration(color: ty.line, borderRadius: BorderRadius.circular(2)),
          ),
          const SizedBox(height: 32),
          Container(
            width: 80,
            height: 80,
            decoration: BoxDecoration(
              color: ty.saffron.withOpacity(0.1),
              shape: BoxShape.circle,
            ),
            child: Icon(Icons.lock_outline_rounded, size: 40, color: ty.saffron),
          ),
          const SizedBox(height: 24),
          Text('Sign in required', style: TyType.display(28, color: ty.ink)),
          const SizedBox(height: 12),
          Text(
            'To $action, you\'ll need to create an account or sign in.',
            textAlign: TextAlign.center,
            style: TyType.sans(15, color: ty.ink2, height: 1.5),
          ),
          const SizedBox(height: 32),
          TyButton(
            'Sign In / Sign Up',
            full: true,
            onTap: () {
              Navigator.pop(context);
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => AuthScreen(onAuthenticated: onAuthenticated),
                ),
              );
            },
          ),
          const SizedBox(height: 12),
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('Maybe Later',
                style: TyType.sans(14, color: ty.ink3, weight: FontWeight.w600)),
          ),
        ],
      ),
    );
  }
}
