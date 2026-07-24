import 'package:flutter/material.dart';

/// Tyohaar's full token palette, exposed as a [ThemeExtension] so every
/// widget can read brand colours via `context.ty`.
///
/// Two instances mirror the web build's `:root[data-theme]` skins:
///  * [TyColors.light] — Warm Light (cream + marigold daylight)
///  * [TyColors.dark]  — Festival of Lights (aubergine dusk + glowing gold)
@immutable
class TyColors extends ThemeExtension<TyColors> {
  final Color paper, paper2, surface, surface2;
  final Color ink, ink2, ink3, line, line2;
  final Color saffron, saffronDeep, saffronSoft;
  final Color rose, leaf, gold, onPrimary;
  final bool isDark;

  const TyColors({
    required this.paper,
    required this.paper2,
    required this.surface,
    required this.surface2,
    required this.ink,
    required this.ink2,
    required this.ink3,
    required this.line,
    required this.line2,
    required this.saffron,
    required this.saffronDeep,
    required this.saffronSoft,
    required this.rose,
    required this.leaf,
    required this.gold,
    required this.onPrimary,
    required this.isDark,
  });

  /// Maps a tint keyword ("saffron" | "rose" | "leaf" | "gold") to a colour.
  Color tint(String name) {
    switch (name) {
      case 'rose':
        return rose;
      case 'leaf':
        return leaf;
      case 'gold':
        return gold;
      default:
        return saffron;
    }
  }

  /// A soft, surface-blended version of a tint — for chips, emblems, fills.
  Color tintSoft(String name) =>
      Color.alphaBlend(tint(name).withValues(alpha: 0.14), surface2);

  static const TyColors light = TyColors(
    paper: Color(0xFFF6F1E8),
    paper2: Color(0xFFFBF8F2),
    surface: Color(0xFFFFFFFF),
    surface2: Color(0xFFFCF8F1),
    ink: Color(0xFF2A2018),
    ink2: Color(0xFF6B5D50),
    ink3: Color(0xFFA99C8C),
    line: Color(0x1A2A2018),
    line2: Color(0x0F2A2018),
    saffron: Color(0xFFE68A2E),
    saffronDeep: Color(0xFFC96E1A),
    saffronSoft: Color(0xFFFBE7CC),
    rose: Color(0xFFC8456B),
    leaf: Color(0xFF5E8C5A),
    gold: Color(0xFFC99A3B),
    onPrimary: Color(0xFFFFFFFF),
    isDark: false,
  );

  static const TyColors dark = TyColors(
    paper: Color(0xFF1B1320),
    paper2: Color(0xFF211627),
    surface: Color(0xFF271A2E),
    surface2: Color(0xFF2E1F36),
    ink: Color(0xFFF4EBDC),
    ink2: Color(0xFFC6B2C0),
    ink3: Color(0xFF8A7588),
    line: Color(0x1FF4EBDC),
    line2: Color(0x12F4EBDC),
    saffron: Color(0xFFF0A93C),
    saffronDeep: Color(0xFFE0922A),
    saffronSoft: Color(0x29F0A93C),
    rose: Color(0xFFEC6E92),
    leaf: Color(0xFF7FC9A7),
    gold: Color(0xFFE8C46A),
    onPrimary: Color(0xFF2A1A0A),
    isDark: true,
  );

  @override
  TyColors copyWith({
    Color? paper,
    Color? paper2,
    Color? surface,
    Color? surface2,
    Color? ink,
    Color? ink2,
    Color? ink3,
    Color? line,
    Color? line2,
    Color? saffron,
    Color? saffronDeep,
    Color? saffronSoft,
    Color? rose,
    Color? leaf,
    Color? gold,
    Color? onPrimary,
    bool? isDark,
  }) {
    return TyColors(
      paper: paper ?? this.paper,
      paper2: paper2 ?? this.paper2,
      surface: surface ?? this.surface,
      surface2: surface2 ?? this.surface2,
      ink: ink ?? this.ink,
      ink2: ink2 ?? this.ink2,
      ink3: ink3 ?? this.ink3,
      line: line ?? this.line,
      line2: line2 ?? this.line2,
      saffron: saffron ?? this.saffron,
      saffronDeep: saffronDeep ?? this.saffronDeep,
      saffronSoft: saffronSoft ?? this.saffronSoft,
      rose: rose ?? this.rose,
      leaf: leaf ?? this.leaf,
      gold: gold ?? this.gold,
      onPrimary: onPrimary ?? this.onPrimary,
      isDark: isDark ?? this.isDark,
    );
  }

  @override
  TyColors lerp(ThemeExtension<TyColors>? other, double t) {
    if (other is! TyColors) return this;
    return t < 0.5 ? this : other;
  }
}

/// Sugar: `context.ty.saffron` instead of the long `Theme.of(...)` lookup.
extension TyColorsX on BuildContext {
  TyColors get ty => Theme.of(this).extension<TyColors>()!;
}
