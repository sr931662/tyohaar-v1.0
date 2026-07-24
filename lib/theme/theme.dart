import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'colors.dart';

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
  );
}
