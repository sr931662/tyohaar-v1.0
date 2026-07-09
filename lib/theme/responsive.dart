import 'package:flutter/material.dart';

/// A utility to scale dimensions and text based on the screen size.
/// Uses a base design width of 390px (iPhone 13/14 size).
class TyResponsive {
  final BuildContext context;
  TyResponsive(this.context);

  static double screenWidth(BuildContext context) => MediaQuery.of(context).size.width;
  static double screenHeight(BuildContext context) => MediaQuery.of(context).size.height;

  // Base dimensions from the design (iPhone 13/14)
  static const double baseWidth = 390;
  static const double baseHeight = 844;

  double get scaleW => screenWidth(context) / baseWidth;
  double get scaleH => screenHeight(context) / baseHeight;
  
  // Smart scaling: use a smaller scaling factor for heights to avoid extreme squishing
  // and clamp the values to reasonable ranges.
  double get hScale => (scaleH * 0.8 + 0.2).clamp(0.7, 1.3);
  double get wScale => scaleW.clamp(0.8, 1.4);
  double get spScale => (scaleW * 0.5 + 0.5).clamp(0.85, 1.15);

  /// Scales a width value.
  double w(double px) => px * wScale;

  /// Scales a height value.
  double h(double px) => px * hScale;

  /// Scales a font size value.
  double sp(double px) => px * spScale;

  /// Returns a responsive padding.
  EdgeInsets p(double left, [double? top, double? right, double? bottom]) {
    if (top == null) return EdgeInsets.all(w(left));
    if (right == null) return EdgeInsets.symmetric(horizontal: w(left), vertical: h(top));
    return EdgeInsets.only(
      left: w(left),
      top: h(top),
      right: w(right),
      bottom: h(bottom ?? 0),
    );
  }
}

extension TyResponsiveX on BuildContext {
  TyResponsive get resp => TyResponsive(this);
}
