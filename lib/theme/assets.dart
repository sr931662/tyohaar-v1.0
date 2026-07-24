import 'package:flutter/material.dart';
import '../widgets/photo_placeholder.dart';

/// Occasion/package imagery now comes entirely from the backend
/// (occasion.iconUrl, package.coverImageUrl, etc). This only provides
/// a tinted placeholder for the loading/error states — there are no
/// bundled local fallback images anymore.
class OccasionAssets {
  static String? getBackground(String occasionName) => null;

  static String? getRelatedBackground(String name) => null;

  static Widget getFallback(String name, {String tint = 'saffron', bool arch = false}) {
    return PhotoPlaceholder(tint: tint, arch: arch);
  }
}
