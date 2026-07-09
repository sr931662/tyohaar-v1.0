import 'package:flutter/material.dart';
import '../widgets/photo_placeholder.dart';

class OccasionAssets {
  static const Map<String, String> _mapping = {
    'Baby Shower': 'assets/images/baby-shower.png',
    'Birthday Party': 'assets/images/birthday party card.png',
    'Diwali Celebration': 'assets/images/Diwali Celebration card.png',
    'House Warming Pooja': 'assets/images/House warminng pooja card.png',
    'Mehndi Ceremony': 'assets/images/Mehndi Ceremony Card.png',
    'Graduation Party': 'assets/images/Graduation party card.png',
  };

  static String? getBackground(String occasionName) {
    return _mapping[occasionName];
  }

  /// Returns a related asset path for a given name if a direct match isn't found.
  /// Useful for "Haldi Ceremony" or "Sangeet Night" if we want to reuse "Mehndi Ceremony" image.
  static String? getRelatedBackground(String name) {
    if (_mapping.containsKey(name)) return _mapping[name];
    
    final lower = name.toLowerCase();
    if (lower.contains('birthday')) return _mapping['Birthday Party'];
    if (lower.contains('haldi') || lower.contains('sangeet') || lower.contains('wedding') || lower.contains('marriage')) {
      return _mapping['Mehndi Ceremony'];
    }
    if (lower.contains('pooja') || lower.contains('griha') || lower.contains('house')) {
      return _mapping['House Warming Pooja'];
    }
    if (lower.contains('diwali') || lower.contains('festival')) {
      return _mapping['Diwali Celebration'];
    }
    if (lower.contains('baby') || lower.contains('shower')) {
      return _mapping['Baby Shower'];
    }
    if (lower.contains('grad') || lower.contains('party') || lower.contains('convocation')) {
      return _mapping['Graduation Party'];
    }
    
    return null;
  }

  /// Helper to get a fallback widget for an occasion or package.
  static Widget getFallback(String name, {String tint = 'saffron', bool arch = false}) {
    final local = getRelatedBackground(name);
    if (local != null) {
      return Image.asset(local, fit: BoxFit.cover);
    }
    return PhotoPlaceholder(tint: tint, arch: arch);
  }
}
