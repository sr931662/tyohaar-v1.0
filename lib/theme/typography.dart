import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Tyohaar's type system.
///  * [display] — Yeseva One: warm ceremonial serif for emotional peaks.
///  * [sans]    — Plus Jakarta Sans: the humanist UI workhorse.
///  * [deva]    — Tiro Devanagari Hindi: the brand's mother-tongue signature.
///
/// Every helper builds on a memoized base style per (family, weight). Going
/// through GoogleFonts on each call re-ran its variant matching and
/// font-load check hundreds of times per frame (TyType is used ~800 times
/// across the app); copyWith on a cached base produces the identical style.
class TyType {
  const TyType._();

  static final Map<FontWeight, TextStyle> _displayBase = {};
  static final Map<FontWeight, TextStyle> _sansBase = {};
  static final Map<FontWeight, TextStyle> _devaBase = {};

  static TextStyle _display(FontWeight w) =>
      _displayBase[w] ??= GoogleFonts.yesevaOne(fontWeight: w);
  static TextStyle _sans(FontWeight w) =>
      _sansBase[w] ??= GoogleFonts.plusJakartaSans(fontWeight: w);
  static TextStyle _deva(FontWeight w) =>
      _devaBase[w] ??= GoogleFonts.getFont('Tiro Devanagari Hindi', fontWeight: w);

  static TextStyle display(
    double size, {
    Color? color,
    FontWeight weight = FontWeight.w400,
    double height = 1.05,
  }) {
    return _display(weight).copyWith(
      fontSize: size,
      color: color,
      height: height,
      letterSpacing: -0.2,
    );
  }

  static TextStyle sans(
    double size, {
    Color? color,
    FontWeight weight = FontWeight.w500,
    double height = 1.4,
    double spacing = 0,
  }) {
    return _sans(weight).copyWith(
      fontSize: size,
      color: color,
      height: height,
      letterSpacing: spacing,
    );
  }

  static TextStyle deva(double size, {Color? color, FontWeight weight = FontWeight.w400}) {
    return _deva(weight).copyWith(fontSize: size, color: color);
  }

  /// An uppercase eyebrow / label style.
  static TextStyle eyebrow(double size, {Color? color}) {
    return _sans(FontWeight.w700).copyWith(
      fontSize: size,
      color: color,
      letterSpacing: 1.4,
    );
  }
}
