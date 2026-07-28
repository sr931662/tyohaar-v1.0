import 'package:flutter_secure_storage/test/test_flutter_secure_storage_platform.dart';
import 'package:flutter_secure_storage_platform_interface/flutter_secure_storage_platform_interface.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tyohaar/data/auth_manager.dart';
import 'package:tyohaar/data/models.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  FlutterSecureStoragePlatform.instance = TestFlutterSecureStoragePlatform({});

  final testUser = User(id: 'u1', role: 'customer', status: 'active');

  setUp(() async {
    // Reset shared singleton state between tests.
    await AuthManager.instance.logout();
  });

  group('AuthManager', () {
    test('starts unauthenticated', () {
      expect(AuthManager.instance.isAuthenticated, isFalse);
      expect(AuthManager.instance.accessToken, isNull);
    });

    test('login stores tokens and marks authenticated', () async {
      await AuthManager.instance.login('access-1', 'refresh-1', testUser);
      expect(AuthManager.instance.isAuthenticated, isTrue);
      expect(AuthManager.instance.isGuest, isFalse);
      expect(AuthManager.instance.accessToken, 'access-1');
      expect(AuthManager.instance.refreshToken, 'refresh-1');
      expect(AuthManager.instance.currentUser?.id, 'u1');
    });

    test('updateAccessToken replaces only the access token', () async {
      await AuthManager.instance.login('access-1', 'refresh-1', testUser);
      await AuthManager.instance.updateAccessToken('access-2');
      expect(AuthManager.instance.accessToken, 'access-2');
      expect(AuthManager.instance.refreshToken, 'refresh-1');
      expect(AuthManager.instance.isAuthenticated, isTrue);
    });

    test('logout clears all session state', () async {
      await AuthManager.instance.login('access-1', 'refresh-1', testUser);
      await AuthManager.instance.logout();
      expect(AuthManager.instance.isAuthenticated, isFalse);
      expect(AuthManager.instance.accessToken, isNull);
      expect(AuthManager.instance.refreshToken, isNull);
      expect(AuthManager.instance.currentUser, isNull);
    });

    test('skip enters guest mode without authenticating', () {
      AuthManager.instance.skip();
      expect(AuthManager.instance.isGuest, isTrue);
      expect(AuthManager.instance.isAuthenticated, isFalse);
    });

    test('loadStoredAuth restores a persisted session', () async {
      await AuthManager.instance.login('access-1', 'refresh-1', testUser);
      // Simulate a fresh app start reloading from (still-populated) storage.
      await AuthManager.instance.loadStoredAuth();
      expect(AuthManager.instance.isAuthenticated, isTrue);
      expect(AuthManager.instance.accessToken, 'access-1');
      expect(AuthManager.instance.isInitializing, isFalse);
    });

    test('completeOnboarding persists the seen-onboarding flag', () async {
      expect(AuthManager.instance.seenOnboarding, isFalse);
      await AuthManager.instance.completeOnboarding();
      expect(AuthManager.instance.seenOnboarding, isTrue);
    });
  });
}
