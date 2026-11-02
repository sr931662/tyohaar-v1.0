import 'package:flutter_test/flutter_test.dart';
import 'package:tyohaar/data/models.dart';

void main() {
  Map<String, dynamic> json({Object? style}) => {
        'id': 'x',
        'name': 'Marquee letters',
        'base_price': '399.00',
        'is_customizable': true,
        'character_set': 'alphanumeric',
        if (style != null) 'marquee_style': style,
      };

  group('marquee_style parsing', () {
    test('items and services read balloon', () {
      expect(PackageItem.fromJson(json(style: 'balloon')).marqueeStyle, 'balloon');
      expect(PackageServiceLine.fromJson(json(style: 'balloon')).marqueeStyle, 'balloon');
    });

    test('an older server without the field keeps the LED look', () {
      expect(PackageItem.fromJson(json()).marqueeStyle, 'led');
      expect(PackageServiceLine.fromJson(json()).marqueeStyle, 'led');
    });

    test('anything unrecognised is LED', () {
      expect(PackageItem.fromJson(json(style: 'neon')).marqueeStyle, 'led');
    });

    test('the style survives copyWith (like count / liking an item)', () {
      final item = PackageItem.fromJson(json(style: 'balloon'));
      expect(item.copyWith(isLiked: true).marqueeStyle, 'balloon');
    });

    test('the style does not change what is billed', () {
      final led = PackageItem.fromJson(json(style: 'led'));
      final balloon = PackageItem.fromJson(json(style: 'balloon'));
      expect(balloon.unitPrice, led.unitPrice);
      expect(balloon.characterSet, led.characterSet);
      expect(balloon.needsNumericCustomization, led.needsNumericCustomization);
    });
  });
}
