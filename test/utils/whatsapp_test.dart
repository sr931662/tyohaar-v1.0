import 'package:flutter_test/flutter_test.dart';
import 'package:tyohaar/utils/whatsapp.dart';

void main() {
  group('whatsAppNumber', () {
    test('international numbers lose the plus and formatting', () {
      expect(whatsAppNumber('+91 98765-43210'), '919876543210');
      expect(whatsAppNumber('+44 (0) 7700 900123'), '4407700900123');
    });

    test('a bare local number gets the default country code', () {
      expect(whatsAppNumber('98765 43210'), '919876543210');
      expect(whatsAppNumber('09876543210'), '919876543210'); // 0 trunk prefix
    });

    test('00 is an international prefix, not part of the number', () {
      expect(whatsAppNumber('00919876543210'), '919876543210');
    });

    test('an already-complete number is left alone', () {
      expect(whatsAppNumber('919876543210'), '919876543210');
    });

    test('junk and too-short/long input is rejected', () {
      expect(whatsAppNumber(null), isNull);
      expect(whatsAppNumber(''), isNull);
      expect(whatsAppNumber('call me'), isNull);
      expect(whatsAppNumber('12345'), isNull);
      expect(whatsAppNumber('+1234567890123456'), isNull);
    });

    test('the country code is configurable', () {
      expect(whatsAppNumber('7700900123', defaultCountryCode: '44'), '447700900123');
    });
  });

  group('whatsAppLink', () {
    test('pre-fills the message for a usable number', () {
      final uri = whatsAppLink('+91 98765 43210', 'Hi Asha & friends!');
      expect(uri.host, 'wa.me');
      expect(uri.path, '/919876543210');
      expect(uri.queryParameters['text'], 'Hi Asha & friends!');
    });

    test('falls back to the contact picker when there is no number', () {
      final uri = whatsAppLink(null, 'Hello');
      expect(uri.path, '/');
      expect(uri.queryParameters['text'], 'Hello');
    });
  });
}
