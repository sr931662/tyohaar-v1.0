import 'package:flutter_test/flutter_test.dart';
import 'package:tyohaar/data/models.dart';

User _user({String? phone}) => User.fromJson({
      'id': 'u1',
      'phone': phone,
      'email': 'someone@example.com',
      'full_name': 'Test User',
      'role': 'customer',
      'account_status': 'active',
    });

void main() {
  group('User.displayPhone', () {
    test('hides the synthetic phone a social sign-up gets', () {
      // server/app/services/auth/service.py writes TMP-<hex> when the
      // provider gives no phone number.
      expect(_user(phone: 'TMP-a1b2c3d4e5').displayPhone, isNull);
      expect(_user(phone: 'TMP-a1b2c3d4e5').hasRealPhone, isFalse);
    });

    test('is case-insensitive about the placeholder prefix', () {
      expect(_user(phone: 'tmp-a1b2c3d4e5').displayPhone, isNull);
    });

    test('keeps a real number', () {
      expect(_user(phone: '9876543210').displayPhone, '9876543210');
      expect(_user(phone: '9876543210').hasRealPhone, isTrue);
    });

    test('treats missing and empty as absent', () {
      expect(_user(phone: null).displayPhone, isNull);
      expect(_user(phone: '').displayPhone, isNull);
    });
  });

  group('User.displayName', () {
    test('never falls back to a placeholder phone', () {
      final u = User.fromJson({
        'id': 'u1',
        'phone': 'TMP-a1b2c3d4e5',
        'role': 'customer',
        'account_status': 'active',
      });
      expect(u.displayName, 'u1');
    });
  });
}
