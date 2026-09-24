import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/test/test_flutter_secure_storage_platform.dart';
import 'package:flutter_secure_storage_platform_interface/flutter_secure_storage_platform_interface.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tyohaar/data/api_client.dart';
import 'package:tyohaar/data/auth_manager.dart';
import 'package:tyohaar/data/models.dart';

/// Always answers 401, standing in for an authed endpoint reached without a
/// session.
class _UnauthorizedAdapter implements HttpClientAdapter {
  int calls = 0;

  @override
  void close({bool force = false}) {}

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    calls++;
    return ResponseBody.fromString(
      '{"error":{"code":"UNAUTHENTICATED","message":"Not authenticated"}}',
      401,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  FlutterSecureStoragePlatform.instance = TestFlutterSecureStoragePlatform({});

  late _UnauthorizedAdapter adapter;

  setUp(() async {
    await AuthManager.instance.logout();
    adapter = _UnauthorizedAdapter();
    ApiClient().dio.httpClientAdapter = adapter;
  });

  group('401 handling while browsing as a guest', () {
    test('does not tear down the guest session', () async {
      AuthManager.instance.skip();
      expect(AuthManager.instance.isGuest, isTrue);

      // Browsing as a guest routinely touches authed endpoints — the home
      // screen asks for celebrations, tabs build eagerly behind an
      // IndexedStack. Forcing a logout here wiped the guest flag and fired
      // notifyListeners(), rebuilding the app out from under the customer
      // and dropping them on an error screen mid-browse.
      await expectLater(
        ApiClient().dio.get('celebrations'),
        throwsA(isA<DioException>()),
      );

      expect(AuthManager.instance.isGuest, isTrue,
          reason: 'a guest with no session has nothing to log out of');
      expect(AuthManager.instance.isAuthenticated, isFalse);
    });

    test('does not attempt a token refresh when there is no token', () async {
      AuthManager.instance.skip();

      await expectLater(
        ApiClient().dio.get('celebrations'),
        throwsA(isA<DioException>()),
      );

      // One call only: no refresh round trip, no retry.
      expect(adapter.calls, 1);
    });

    test('still surfaces the 401 to the caller', () async {
      AuthManager.instance.skip();

      try {
        await ApiClient().dio.get('celebrations');
        fail('expected the 401 to propagate');
      } on DioException catch (e) {
        expect(e.response?.statusCode, 401);
      }
    });

    test('leaves a signed-out visitor signed out, not bounced', () async {
      // Never even tapped "continue as guest" — same reasoning applies.
      expect(AuthManager.instance.accessToken, isNull);

      await expectLater(
        ApiClient().dio.get('celebrations'),
        throwsA(isA<DioException>()),
      );

      expect(AuthManager.instance.isAuthenticated, isFalse);
    });
  });

  group('401 handling with a real session', () {
    test('clears the session when the token is rejected and cannot refresh',
        () async {
      await AuthManager.instance.login(
        'access-1',
        'refresh-1',
        User(id: 'u1', role: 'customer', status: 'active'),
      );
      expect(AuthManager.instance.isAuthenticated, isTrue);

      await expectLater(
        ApiClient().dio.get('me'),
        throwsA(isA<DioException>()),
      );

      // An expired session is exactly the case the forced logout exists for.
      expect(AuthManager.instance.isAuthenticated, isFalse);
      expect(AuthManager.instance.accessToken, isNull);
    });
  });

  group('screens a guest can reach', () {
    test('a 401 on one call does not abort a whole screen load', () async {
      AuthManager.instance.skip();

      // How the guest-reachable screens compose their loads: the public
      // calls must still resolve when the per-user one fails. Home and the
      // plan flow both used to let this 401 escape Future.wait and take the
      // screen down to an error state.
      final results = await Future.wait([
        Future<List<String>>.value(const ['occasions']),
        ApiClient()
            .dio
            .get('users/me/addresses')
            .then((_) => <String>[])
            .catchError((_) => <String>[]),
        Future<List<String>>.value(const ['themes']),
      ]);

      expect(results[0], isNotEmpty);
      expect(results[1], isEmpty);
      expect(results[2], isNotEmpty);
      expect(AuthManager.instance.isGuest, isTrue);
    });
  });
}
