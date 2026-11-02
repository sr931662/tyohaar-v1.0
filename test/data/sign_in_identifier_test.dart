import 'package:flutter_test/flutter_test.dart';
import 'package:tyohaar/data/sign_in_identifier.dart';

void main() {
  group('one box takes a mobile number or an email', () {
    for (final raw in ['9876543210', '98765 43210', '+91 98765-43210', '+919876543210', '919876543210', '09876543210', '0091 9876543210']) {
      test('"$raw" is the mobile +919876543210', () {
        final id = SignInIdentifier.parse(raw);
        expect(id.isPhone, isTrue);
        expect(id.value, '+919876543210');
        expect(id.channel, 'sms');
        expect(id.display, '+91 98765 43210');
      });
    }

    test('emails are trimmed and lower-cased', () {
      final id = SignInIdentifier.parse('  Asha.Rao@Example.COM ');
      expect(id.isEmail, isTrue);
      expect(id.value, 'asha.rao@example.com');
      expect(id.channel, 'email');
    });

    for (final raw in ['', '12345', '5876543210', '98765432101', 'asha@', 'asha@example', '@example.com', 'hello world']) {
      test('"$raw" is rejected', () => expect(SignInIdentifier.parse(raw).isValid, isFalse));
    }
  });
}
