import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';

import 'colors.dart';

/// Status bar / navigation bar styling for an ordinary screen, where the system
/// bars sit over the app's own background colour.
///
/// The two status bar fields are inverses of each other and it is easy to get
/// wrong: on Android `statusBarIconBrightness` is the brightness of the *icons*,
/// while on iOS `statusBarBrightness` is the brightness of the *background*
/// behind them. A light page therefore needs dark icons (Android) and a light
/// background (iOS).
SystemUiOverlayStyle tySystemOverlay(Brightness brightness, Color background) {
  final isDark = brightness == Brightness.dark;
  return SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: isDark ? Brightness.light : Brightness.dark,
    statusBarBrightness: isDark ? Brightness.dark : Brightness.light,
    systemNavigationBarColor: background,
    systemNavigationBarIconBrightness:
        isDark ? Brightness.light : Brightness.dark,
  );
}

/// Status bar styling for screens whose content runs full-bleed *under* the
/// status bar over a photograph — the home hero, event hub, vendor detail.
///
/// These always paint a dark scrim behind the status bar in both themes, so the
/// icons must stay white regardless of the app theme. Letting them follow the
/// theme is what makes the clock unreadable in light mode: dark icons land on a
/// dark scrim over a busy image.
const SystemUiOverlayStyle tyOverlayOverImage = SystemUiOverlayStyle(
  statusBarColor: Colors.transparent,
  statusBarIconBrightness: Brightness.light,
  statusBarBrightness: Brightness.dark,
);

/// Builds a [ThemeData] for a given brightness, wiring in the [TyColors]
/// extension and the Plus Jakarta Sans base text theme.
ThemeData buildTyTheme(Brightness brightness) {
  final ty = brightness == Brightness.dark ? TyColors.dark : TyColors.light;
  final base = ThemeData(brightness: brightness, useMaterial3: true);

  final textTheme = GoogleFonts.plusJakartaSansTextTheme(base.textTheme)
      .apply(bodyColor: ty.ink, displayColor: ty.ink);

  return base.copyWith(
    scaffoldBackgroundColor: ty.paper,
    canvasColor: ty.paper,
    extensions: <ThemeExtension<dynamic>>[ty],
    textTheme: textTheme,
    splashColor: ty.saffron.withValues(alpha: 0.10),
    highlightColor: ty.saffron.withValues(alpha: 0.06),
    colorScheme: base.colorScheme.copyWith(
      brightness: brightness,
      primary: ty.saffron,
      onPrimary: ty.onPrimary,
      secondary: ty.rose,
      surface: ty.surface,
      onSurface: ty.ink,
    ),
    iconTheme: IconThemeData(color: ty.ink, size: 22),
    // Without this the system bars fall back to Flutter's platform default,
    // which does not track the app theme — the reason light mode shipped with
    // an unreadable status bar.
    appBarTheme: base.appBarTheme.copyWith(
      systemOverlayStyle: tySystemOverlay(brightness, ty.paper),
    ),
  );
}
