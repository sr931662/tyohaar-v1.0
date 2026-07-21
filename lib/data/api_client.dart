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
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      ),
    );

    dio.interceptors.add(_cacheInterceptor);

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
