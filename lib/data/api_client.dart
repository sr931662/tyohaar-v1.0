import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

import 'auth_manager.dart';

class ApiClient {
  static final ApiClient _instance = ApiClient._internal();
  factory ApiClient() => _instance;

  late final Dio dio;

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
            // Attempt token refresh once
            final refreshed = await _tryRefreshToken();
            if (refreshed) {
              // Retry the original request with the new token
              final opts = e.requestOptions;
              opts.headers['Authorization'] = 'Bearer ${AuthManager.instance.accessToken}';
              try {
                final retryResp = await dio.fetch(opts);
                return handler.resolve(retryResp);
              } catch (_) {
                // Retry also failed — fall through to logout
              }
            }
            // Token refresh failed or not possible: force logout
            await AuthManager.instance.logout();
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
