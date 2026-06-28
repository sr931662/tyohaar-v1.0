import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'theme/theme.dart';
import 'theme/theme_controller.dart';
import 'data/app_state.dart';
import 'data/auth_manager.dart';
import 'data/services/user_service.dart';
import 'data/services/package_service.dart';
import 'data/services/booking_service.dart';
import 'data/services/wallet_service.dart';
import 'data/services/celebration_service.dart';
import 'data/services/media_service.dart';
import 'data/services/auth_service.dart';
import 'data/services/notification_service.dart';
import 'data/services/support_service.dart';
import 'screens/vendor/vendor_root_nav.dart';
import 'screens/onboarding_screen.dart';

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
        Provider(create: (_) => WalletService()),
        Provider(create: (_) => CelebrationService()),
        Provider(create: (_) => MediaService()),
        Provider(create: (_) => NotificationService()),
        Provider(create: (_) => SupportService()),
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
              return Stack(
                children: [
                  if (child != null) child,
                  Positioned(
                    right: 16,
                    bottom: 100,
                    child: Material(
                      color: Colors.transparent,
                      child: GestureDetector(
                        onTap: () => AppState.instance.togglePOV(),
                        child: Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: Colors.black.withOpacity(0.8),
                            borderRadius: BorderRadius.circular(16),
                            boxShadow: [
                              BoxShadow(color: Colors.black.withOpacity(0.3), blurRadius: 10)
                            ],
                          ),
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(Icons.swap_horiz_rounded, color: Colors.white, size: 20),
                              const SizedBox(height: 4),
                              Text(
                                pov == UserPOV.customer ? 'TO VENDOR' : 'TO CUSTOMER',
                                style: const TextStyle(color: Colors.white, fontSize: 8, fontWeight: FontWeight.bold),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              );
            },
            home: pov == UserPOV.vendor 
                ? const VendorRootNav() 
                : const OnboardingScreen(),
          );
        },
      ),
    );
  }
}
