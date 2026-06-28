import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

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
        receiveTimeout: const Duration(seconds: 15),
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      ),
    );

    // Force logging in debug mode to see exact error responses
    dio.interceptors.add(LogInterceptor(
      requestHeader: true,
      requestBody: true,
      responseHeader: true,
      responseBody: true,
      error: true,
      logPrint: (obj) => debugPrint('API_LOG: $obj'),
    ));

    // Add Auth Interceptor
    dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        // TODO: Get token from AuthManager or Secure Storage
        return handler.next(options);
      },
      onError: (DioException e, handler) {
        debugPrint('API_ERROR: [${e.response?.statusCode}] ${e.response?.data}');
        if (e.response?.statusCode == 401) {
          // Handle unauthorized
        }
        return handler.next(e);
      },
    ));
  }
}
