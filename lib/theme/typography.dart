import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Tyohaar's type system.
///  * [display] — Yeseva One: warm ceremonial serif for emotional peaks.
///  * [sans]    — Plus Jakarta Sans: the humanist UI workhorse.
///  * [deva]    — Tiro Devanagari Hindi: the brand's mother-tongue signature.
class TyType {
  const TyType._();

  static TextStyle display(
    double size, {
    Color? color,
    FontWeight weight = FontWeight.w400,
    double height = 1.05,
  }) {
    return GoogleFonts.yesevaOne(
      fontSize: size,
      color: color,
      fontWeight: weight,
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
    return GoogleFonts.plusJakartaSans(
      fontSize: size,
      color: color,
      fontWeight: weight,
      height: height,
      letterSpacing: spacing,
    );
  }

  static TextStyle deva(double size, {Color? color, FontWeight weight = FontWeight.w400}) {
    return GoogleFonts.getFont(
      'Tiro Devanagari Hindi',
      fontSize: size,
      color: color,
      fontWeight: weight,
    );
  }

  /// An uppercase eyebrow / label style.
  static TextStyle eyebrow(double size, {Color? color}) {
    return GoogleFonts.plusJakartaSans(
      fontSize: size,
      color: color,
      fontWeight: FontWeight.w700,
      letterSpacing: 1.4,
    );
  }
}
