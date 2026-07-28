import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

import 'auth_manager.dart';

class _CacheEntry {
  final dynamic data;
  final DateTime expiresAt;
  _CacheEntry(this.data, this.expiresAt);
  bool get isExpired => DateTime.now().isAfter(expiresAt);
}

/// Opt-in, in-memory GET response cache — screens/services mark a request
/// cacheable via `options.extra['cache'] = true` (optionally with a
/// `cacheTtl` Duration override). Nothing is cached by default, so
/// pull-to-refresh and user/booking-specific data are unaffected; this only
/// speeds up repeat navigations to largely-static catalog data (occasions,
/// packages, themes, etc.) within the same app session.
class _MemoryCacheInterceptor extends Interceptor {
  final Map<String, _CacheEntry> _cache = {};

  String _keyFor(RequestOptions options) => '${options.method}:${options.uri}';

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    final shouldCache = options.extra['cache'] == true;
    if (!shouldCache || options.method.toUpperCase() != 'GET') {
      return handler.next(options);
    }
    final entry = _cache[_keyFor(options)];
    if (entry != null && !entry.isExpired) {
      handler.resolve(Response(
        requestOptions: options,
        data: entry.data,
        statusCode: 200,
      ));
      return;
    }
    return handler.next(options);
  }

  @override
  void onResponse(Response response, ResponseInterceptorHandler handler) {
    final options = response.requestOptions;
    if (options.extra['cache'] == true &&
        options.method.toUpperCase() == 'GET' &&
        response.statusCode == 200) {
      final ttl = options.extra['cacheTtl'] as Duration? ?? const Duration(minutes: 10);
      _cache[_keyFor(options)] = _CacheEntry(response.data, DateTime.now().add(ttl));
    }
    return handler.next(response);
  }

  void clear() => _cache.clear();
}

/// Retries idempotent GET requests on transient network failures
/// (connection/receive/send timeouts, connection errors, and 502/503/504)
/// with exponential backoff. Never retries non-GET requests — retrying a
/// POST/PUT/DELETE blindly risks duplicating a booking/payment/etc. Never
/// retries 4xx responses, since those won't succeed on a second attempt.
class _RetryInterceptor extends Interceptor {
  final Dio _dio;
  static const _maxRetries = 2;
  static const _baseDelay = Duration(milliseconds: 500);

  _RetryInterceptor(this._dio);

  bool _isRetryable(DioException e) {
    if (e.requestOptions.method.toUpperCase() != 'GET') return false;
    final status = e.response?.statusCode;
    if (status != null) return status == 502 || status == 503 || status == 504;
    return e.type == DioExceptionType.connectionTimeout ||
        e.type == DioExceptionType.receiveTimeout ||
        e.type == DioExceptionType.sendTimeout ||
        e.type == DioExceptionType.connectionError;
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) async {
    final attempt = (err.requestOptions.extra['retryAttempt'] as int?) ?? 0;
    if (!_isRetryable(err) || attempt >= _maxRetries) {
      return handler.next(err);
    }
    await Future.delayed(_baseDelay * (attempt + 1));
    final opts = err.requestOptions;
    opts.extra['retryAttempt'] = attempt + 1;
    try {
      final response = await _dio.fetch(opts);
      return handler.resolve(response);
    } on DioException catch (e) {
      return handler.next(e);
    }
  }
}

/// Maps a caught network/API error to a short, user-facing message instead
/// of Dio's technical `DioException [type]: ...` text. Screens that
/// currently render `error.toString()` directly to the user should use
/// this instead.
String describeApiError(Object error) {
  if (error is DioException) {
    switch (error.type) {
      case DioExceptionType.connectionError:
        return 'No internet connection. Please check your network and try again.';
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return 'The request timed out. Please try again.';
      case DioExceptionType.badResponse:
        final status = error.response?.statusCode;
        if (status != null && status >= 500) {
          return 'Something went wrong on our end. Please try again shortly.';
        }
        if (status == 404) return 'The requested information could not be found.';
        return 'That request could not be completed. Please try again.';
      case DioExceptionType.cancel:
        return 'Request cancelled.';
      default:
        return 'Something went wrong. Please try again.';
    }
  }
  return 'Something went wrong. Please try again.';
}

class ApiClient {
  static final ApiClient _instance = ApiClient._internal();
  factory ApiClient() => _instance;

  late final Dio dio;
  final _MemoryCacheInterceptor _cacheInterceptor = _MemoryCacheInterceptor();

  /// Clears every cached GET response. Only public catalog endpoints
  /// (occasions, packages, themes, categories) opt into this cache, so it's
  /// not user-specific — exposed mainly for pull-to-refresh flows that want
  /// to force a genuinely fresh fetch.
  void clearCache() => _cacheInterceptor.clear();

  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://tyohaar-v1-0-527701068133.asia-south1.run.app/api/v1/',
  );

  ApiClient._internal() {
    dio = Dio(
      BaseOptions(
        baseUrl: baseUrl,
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 30),
        sendTimeout: const Duration(seconds: 15),
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      ),
    );

    dio.interceptors.add(_cacheInterceptor);
    dio.interceptors.add(_RetryInterceptor(dio));

    if (kDebugMode) {
      dio.interceptors.add(LogInterceptor(
        requestHeader: false,
        requestBody: true,
        responseHeader: false,
        responseBody: true,
        error: true,
        logPrint: (obj) => debugPrint('API: $obj'),
      ));
    }

    // Auth interceptor: attach Bearer token and handle 401 refresh/logout
    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final token = AuthManager.instance.accessToken;
          if (token != null && token.isNotEmpty) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          return handler.next(options);
        },
        onError: (DioException e, handler) async {
          if (e.response?.statusCode == 401) {
            // Avoid infinite loops: check if this is already a retry
            if (e.requestOptions.extra['retry'] == true) {
              await AuthManager.instance.logout();
              return handler.next(e);
            }

            // Attempt token refresh
            final refreshed = await _tryRefreshToken();
            if (refreshed) {
              final opts = e.requestOptions;
              opts.headers['Authorization'] = 'Bearer ${AuthManager.instance.accessToken}';
              opts.extra['retry'] = true; // Mark as retry
              
              try {
                // Use the main dio instance to retry the request
                final retryResp = await dio.fetch(opts);
                return handler.resolve(retryResp);
              } catch (_) {
                // Retry failed even with new token
                await AuthManager.instance.logout();
                return handler.next(e);
              }
            } else {
              // Refresh failed: session is truly dead
              await AuthManager.instance.logout();
            }
          }
          return handler.next(e);
        },
      ),
    );
  }

  /// Calls the refresh-token endpoint and stores the new access token.
  /// Returns true on success, false on failure.
  Future<bool> _tryRefreshToken() async {
    final refreshToken = AuthManager.instance.refreshToken;
    if (refreshToken == null) return false;
    try {
      // Use a separate Dio instance to avoid triggering the auth interceptor again
      final plainDio = Dio(BaseOptions(baseUrl: baseUrl));
      final resp = await plainDio.post(
        'auth/token/refresh',
        data: {'refresh_token': refreshToken},
      );
      final newToken = resp.data?['data']?['access_token'] as String?;
      if (newToken != null) {
        await AuthManager.instance.updateAccessToken(newToken);
        return true;
      }
    } catch (_) {}
    return false;
  }
}
