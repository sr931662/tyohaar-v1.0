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
  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    await AuthManager.instance.loadStoredAuth();
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
        if (AuthManager.instance.isAuthenticated) {
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
