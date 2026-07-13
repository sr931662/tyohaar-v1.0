import 'package:flutter/material.dart';

import 'colors.dart';

/// Visual treatment for a celebration mood (OccasionMood.slug) — a gradient
/// pair (derived from the existing tint tokens in [TyColors], the same
/// saffron/rose/leaf/gold vocabulary used elsewhere) plus an accent icon.
@immutable
class MoodStyle {
  final String tint;
  final IconData icon;

  const MoodStyle({required this.tint, required this.icon});

  Color primary(TyColors ty) => ty.tint(tint);

  /// A darker variant of [primary], mirroring how saffronDeep relates to
  /// saffron, so any tint gets a matching gradient endpoint.
  Color secondary(TyColors ty) =>
      Color.lerp(primary(ty), Colors.black, 0.22) ?? primary(ty);
}

/// Mood slug → [MoodStyle], matching the OccasionMood seed vocabulary
/// (elegant, grand, fun, romantic). Unrecognized or null moods fall back
/// to 'default', which reproduces the previous hardcoded saffron look.
const Map<String, MoodStyle> moodStyles = {
  'elegant': MoodStyle(tint: 'gold', icon: Icons.diamond_outlined),
  'grand': MoodStyle(tint: 'saffron', icon: Icons.celebration_outlined),
  'fun': MoodStyle(tint: 'leaf', icon: Icons.emoji_emotions_outlined),
  'romantic': MoodStyle(tint: 'rose', icon: Icons.favorite_outline),
  'default': MoodStyle(tint: 'saffron', icon: Icons.auto_awesome),
};

MoodStyle moodStyleFor(String? slug) => moodStyles[slug] ?? moodStyles['default']!;
