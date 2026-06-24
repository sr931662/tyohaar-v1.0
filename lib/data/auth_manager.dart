import 'package:flutter/material.dart';
import '../screens/auth_screen.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../widgets/ty_button.dart';

/// A global manager to track authentication state and guest access.
class AuthManager extends ChangeNotifier {
  static final AuthManager instance = AuthManager._internal();
  AuthManager._internal();

  bool _isAuthenticated = false;
  bool _isGuest = false;

  bool get isAuthenticated => _isAuthenticated;
  bool get isGuest => _isGuest;

  void login() {
    _isAuthenticated = true;
    _isGuest = false;
    notifyListeners();
  }

  void skip() {
    _isAuthenticated = false;
    _isGuest = true;
    notifyListeners();
  }

  void logout() {
    _isAuthenticated = false;
    _isGuest = false;
    notifyListeners();
  }

  /// Checks if the user is authenticated, otherwise shows the login prompt.
  /// Returns true if authenticated, false if the prompt was shown.
  bool checkAuth(BuildContext context, {required String action, VoidCallback? onAuthenticated}) {
    if (_isAuthenticated) return true;

    showAuthGate(context, action: action, onAuthenticated: onAuthenticated);
    return false;
  }
}

/// Helper to show a login prompt when a guest tries to access protected features.
void showAuthGate(BuildContext context, {required String action, VoidCallback? onAuthenticated}) {
  showModalBottomSheet(
    context: context,
    backgroundColor: Colors.transparent,
    isScrollControlled: true,
    builder: (context) => _AuthGateSheet(
      action: action, 
      onAuthenticated: onAuthenticated,
    ),
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
            decoration: BoxDecoration(
              color: ty.line,
              borderRadius: BorderRadius.circular(2),
            ),
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
          Text(
            'Sign in required',
            style: TyType.display(28, color: ty.ink),
          ),
          const SizedBox(height: 12),
          Text(
            'To $action, you\'ll need to create an account or sign in to your existing one.',
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
                  builder: (_) => AuthScreen(
                    onAuthenticated: onAuthenticated,
                  ),
                ),
              );
            },
          ),
          const SizedBox(height: 12),
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text(
              'Maybe Later',
              style: TyType.sans(14, color: ty.ink3, weight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}
