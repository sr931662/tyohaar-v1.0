import 'package:flutter/material.dart';

import 'theme/theme.dart';
import 'theme/theme_controller.dart';
import 'screens/root_nav.dart';

import 'screens/onboarding_screen.dart';

/// Root of the Tyohaar customer app.
///
/// Two skins share one system — *Warm Light* (daylight) and
/// *Festival of Lights* (dusk) — driven by [themeController].
class TyohaarApp extends StatelessWidget {
  const TyohaarApp({super.key});

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: themeController,
      builder: (context, _) {
        return MaterialApp(
          title: 'Tyohaar',
          debugShowCheckedModeBanner: false,
          theme: buildTyTheme(Brightness.light),
          darkTheme: buildTyTheme(Brightness.dark),
          themeMode: themeController.mode,
          home: const OnboardingScreen(),
        );
      },
    );
  }
}
