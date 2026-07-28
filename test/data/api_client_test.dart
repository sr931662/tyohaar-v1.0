import 'dart:async';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tyohaar/data/api_client.dart';

/// Records every request handed to it and replies from a scripted queue of
/// responses (or throws a scripted [DioException]) so retry/error-mapping
/// behavior can be exercised without a real network call.
class _ScriptedAdapter implements HttpClientAdapter {
  final List<Object> _script;
  int calls = 0;

  _ScriptedAdapter(this._script);

  @override
  void close({bool force = false}) {}

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    final index = calls;
    calls++;
    final entry = index < _script.length ? _script[index] : _script.last;
    if (entry is DioException) {
      throw entry;
    }
    final response = entry as ResponseBody Function(RequestOptions);
    return response(options);
  }
}

ResponseBody _jsonResponse(int statusCode, Object data) {
  return ResponseBody.fromString(
    data.toString(),
    statusCode,
    headers: {
      Headers.contentTypeHeader: [Headers.jsonContentType],
    },
  );
}

void main() {
  group('describeApiError', () {
    test('maps connection errors to an offline-friendly message', () {
      final err = DioException(
        requestOptions: RequestOptions(path: '/x'),
        type: DioExceptionType.connectionError,
      );
      expect(describeApiError(err), contains('internet connection'));
    });

    test('maps timeouts to a retry message', () {
      for (final type in [
        DioExceptionType.connectionTimeout,
        DioExceptionType.sendTimeout,
        DioExceptionType.receiveTimeout,
      ]) {
        final err = DioException(requestOptions: RequestOptions(path: '/x'), type: type);
        expect(describeApiError(err), contains('timed out'));
      }
    });

    test('maps 5xx responses to a server-error message', () {
      final err = DioException(
        requestOptions: RequestOptions(path: '/x'),
        type: DioExceptionType.badResponse,
        response: Response(requestOptions: RequestOptions(path: '/x'), statusCode: 502),
      );
      expect(describeApiError(err), contains('our end'));
    });

    test('maps 404 to a not-found message', () {
      final err = DioException(
        requestOptions: RequestOptions(path: '/x'),
        type: DioExceptionType.badResponse,
        response: Response(requestOptions: RequestOptions(path: '/x'), statusCode: 404),
      );
      expect(describeApiError(err), contains('could not be found'));
    });

    test('maps other 4xx responses to a generic retry message', () {
      final err = DioException(
        requestOptions: RequestOptions(path: '/x'),
        type: DioExceptionType.badResponse,
        response: Response(requestOptions: RequestOptions(path: '/x'), statusCode: 422),
      );
      expect(describeApiError(err), contains('could not be completed'));
    });

    test('falls back to a generic message for non-Dio errors', () {
      expect(describeApiError(StateError('boom')), 'Something went wrong. Please try again.');
    });
  });

  group('ApiClient configuration', () {
    test('is a singleton with production-ready timeouts', () {
      final client = ApiClient();
      expect(identical(client, ApiClient()), isTrue);
      expect(client.dio.options.connectTimeout, const Duration(seconds: 15));
      expect(client.dio.options.receiveTimeout, const Duration(seconds: 30));
      expect(client.dio.options.sendTimeout, const Duration(seconds: 15));
      expect(client.dio.options.baseUrl, isNotEmpty);
      expect(client.dio.options.baseUrl, startsWith('https://'));
    });
  });

  group('GET retry interceptor', () {
    late ApiClient client;
    late _ScriptedAdapter adapter;

    setUp(() {
      client = ApiClient();
      client.clearCache();
    });

    test('retries a GET on 503 and eventually succeeds', () async {
      adapter = _ScriptedAdapter([
        (opts) => _jsonResponse(503, '{"detail":"unavailable"}'),
        (opts) => _jsonResponse(200, '{"ok":true}'),
      ]);
      client.dio.httpClientAdapter = adapter;

      final response = await client.dio.get('/health-check');
      expect(response.statusCode, 200);
      expect(adapter.calls, 2);
    });

    test('gives up after the max retry count on persistent 503s', () async {
      adapter = _ScriptedAdapter([
        (opts) => _jsonResponse(503, '{}'),
        (opts) => _jsonResponse(503, '{}'),
        (opts) => _jsonResponse(503, '{}'),
        (opts) => _jsonResponse(503, '{}'),
      ]);
      client.dio.httpClientAdapter = adapter;

      await expectLater(
        client.dio.get('/health-check'),
        throwsA(isA<DioException>()),
      );
      // Initial attempt + 2 retries = 3 calls, never a 4th.
      expect(adapter.calls, 3);
    });

    test('never retries a POST, even on 503', () async {
      adapter = _ScriptedAdapter([
        (opts) => _jsonResponse(503, '{}'),
      ]);
      client.dio.httpClientAdapter = adapter;

      await expectLater(
        client.dio.post('/bookings', data: {}),
        throwsA(isA<DioException>()),
      );
      expect(adapter.calls, 1);
    });

    test('never retries a 4xx GET response', () async {
      adapter = _ScriptedAdapter([
        (opts) => _jsonResponse(404, '{}'),
      ]);
      client.dio.httpClientAdapter = adapter;

      await expectLater(
        client.dio.get('/missing'),
        throwsA(isA<DioException>()),
      );
      expect(adapter.calls, 1);
    });
  });
}
