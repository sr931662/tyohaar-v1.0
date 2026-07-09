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
