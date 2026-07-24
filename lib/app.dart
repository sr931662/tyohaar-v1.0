import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'theme/theme.dart';
import 'theme/theme_controller.dart';
import 'theme/colors.dart';
import 'data/app_state.dart';
import 'data/auth_manager.dart';
import 'data/services/user_service.dart';
import 'data/services/package_service.dart';
import 'data/services/booking_service.dart';
import 'data/services/celebration_service.dart';
import 'data/services/media_service.dart';
import 'data/services/auth_service.dart';
import 'data/services/notification_service.dart';
import 'data/services/support_service.dart';
import 'data/services/membership_service.dart';
import 'data/services/referral_service.dart';
import 'data/services/common_service.dart';
import 'data/services/vendor_service.dart';
import 'screens/vendor/vendor_root_nav.dart';
import 'screens/onboarding_screen.dart';
import 'screens/root_nav.dart';
import 'screens/auth_screen.dart';
import 'screens/email_verification_screen.dart';

class TyohaarApp extends StatelessWidget {
  const TyohaarApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider.value(value: AuthManager.instance),
        ChangeNotifierProvider.value(value: AppState.instance),
        Provider(create: (_) => UserService()),
        Provider(create: (_) => AuthService()),
        Provider(create: (_) => PackageService()),
        Provider(create: (_) => BookingService()),
        Provider(create: (_) => CelebrationService()),
        Provider(create: (_) => MediaService()),
        Provider(create: (_) => NotificationService()),
        Provider(create: (_) => SupportService()),
        Provider(create: (_) => MembershipService()),
        Provider(create: (_) => ReferralService()),
        Provider(create: (_) => CommonService()),
        Provider(create: (_) => VendorService()),
      ],
      child: ListenableBuilder(
        listenable: Listenable.merge([themeController, AppState.instance]),
        builder: (context, _) {
          final pov = AppState.instance.pov;

          return MaterialApp(
            title: 'Tyohaar',
            debugShowCheckedModeBanner: false,
            theme: buildTyTheme(Brightness.light),
            darkTheme: buildTyTheme(Brightness.dark),
            themeMode: themeController.mode,
            builder: (context, child) {
              return child ?? const SizedBox.shrink();
            },
            home: pov == UserPOV.vendor
                ? const VendorRootNav()
                : const _AppStartup(),
          );
        },
      ),
    );
  }
}

/// Handles auth restoration on app startup, then routes to OnboardingScreen
/// or RootNav depending on stored session.
class _AppStartup extends StatefulWidget {
  const _AppStartup();

  @override
  State<_AppStartup> createState() => _AppStartupState();
}

class _AppStartupState extends State<_AppStartup> {
  // True once we've resolved (or given up resolving) the signed-in user's
  // role. Restoring stored tokens flips isAuthenticated to true well before
  // the role fetch below completes — without this gate, build() would show
  // RootNav (customer) for that whole window even for a persisted vendor
  // session, then swap to VendorRootNav once the role arrives. Keeping the
  // splash up until this resolves closes that flash entirely.
  bool _roleResolved = false;

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    await AuthManager.instance.loadStoredAuth();
    // loadStoredAuth only restores tokens, not the User (and thus not the
    // role) — fetch it now so a vendor with a persisted session lands
    // straight in the Vendor POV instead of flashing the customer shell.
    if (AuthManager.instance.isAuthenticated) {
      try {
        final user = await UserService().getMe();
        AuthManager.instance.setUser(user);
        AppState.instance.applyRole(user.role);
      } catch (_) {
        // Best-effort — if this fails, the customer shell's own
        // _ensureUserLoaded() retry will pick it up, and role stays default.
      }
    }
    if (mounted) setState(() => _roleResolved = true);
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: AuthManager.instance,
      builder: (context, _) {
        if (AuthManager.instance.isInitializing) {
          // Splash screen while restoring session
          return const _SplashScreen();
        }
        if (AuthManager.instance.isAuthenticated && !_roleResolved) {
          // Tokens are restored but we don't know the role yet — stay on
          // the splash rather than guessing which shell to show.
          return const _SplashScreen();
        }
        if (AuthManager.instance.isAuthenticated) {
          // A persisted session for a customer who never finished email
          // verification (e.g. closed the app before entering the code)
          // must not reach the normal app shell — send them back to the
          // verification screen every time until it succeeds.
          final user = AuthManager.instance.currentUser;
          if (user != null && user.role == 'customer' && !user.emailVerified) {
            return EmailVerificationScreen(email: user.email ?? '');
          }
          return const RootNav();
        }
        if (AuthManager.instance.seenOnboarding) {
          return const AuthScreen();
        }
        return const OnboardingScreen();
      },
    );
  }
}

class _SplashScreen extends StatelessWidget {
  const _SplashScreen();

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return Scaffold(
      backgroundColor: ty.paper,
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Image.asset('assets/images/tyohaar-mark.png', width: 64, height: 64),
            const SizedBox(height: 24),
            SizedBox(
              width: 24,
              height: 24,
              child: CircularProgressIndicator(
                strokeWidth: 2.5,
                color: ty.saffron,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
