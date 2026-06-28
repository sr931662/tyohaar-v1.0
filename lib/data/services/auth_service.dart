import 'package:dio/dio.dart';
import '../api_client.dart';
import '../models.dart';

class AuthCredentials {
  final String accessToken;
  final String refreshToken;
  final User user;

  AuthCredentials({
    required this.accessToken,
    required this.refreshToken,
    required this.user,
  });
}

class AuthService {
  final ApiClient _api = ApiClient();

  Future<AuthCredentials> login(String email, String password) async {
    final response = await _api.dio.post('auth/login', data: {
      'email': email,
      'password': password,
    });
    return _credentialsFromResponse(response.data as Map<String, dynamic>);
  }

  Future<AuthCredentials> register(String email, String password, {String? name}) async {
    final response = await _api.dio.post('auth/register', data: {
      'email': email,
      'password': password,
      if (name != null && name.isNotEmpty) 'full_name': name,
    });
    return _credentialsFromResponse(response.data as Map<String, dynamic>);
  }

  // The auth endpoints return only user_id, not the full user object.
  // Fetch the profile from users/me using the new token before it is stored
  // in AuthManager (so the interceptor won't overwrite the explicit header).
  Future<AuthCredentials> _credentialsFromResponse(Map<String, dynamic> json) async {
    final data = (json['data'] ?? json) as Map<String, dynamic>;
    final accessToken = data['access_token'] as String;
    final refreshToken = data['refresh_token'] as String;
    final userResp = await _api.dio.get(
      'users/me',
      options: Options(headers: {'Authorization': 'Bearer $accessToken'}),
    );
    final userData = (userResp.data['data'] ?? userResp.data) as Map<String, dynamic>;
    return AuthCredentials(
      accessToken: accessToken,
      refreshToken: refreshToken,
      user: User.fromJson(userData),
    );
  }

  Future<void> logout() async {
    try {
      await _api.dio.post('auth/logout');
    } catch (_) {
      // Best-effort: clear local state regardless
    }
  }

  Future<String?> refreshToken(String refreshToken) async {
    final response = await _api.dio.post('auth/token/refresh', data: {
      'refresh_token': refreshToken,
    });
    final data = (response.data?['data'] ?? response.data) as Map<String, dynamic>?;
    return data?['access_token'] as String?;
  }

  Future<void> requestOtp(String phone) async {
    await _api.dio.post('auth/otp/request', data: {
      'identifier': phone,
      'channel': 'sms',
      'purpose': 'login',
      'device_fingerprint': 'mobile_app_default',
    });
  }

  Future<AuthCredentials> verifyOtp(String phone, String code) async {
    final response = await _api.dio.post('auth/otp/verify', data: {
      'identifier': phone,
      'otp_code': code,
      'purpose': 'login',
    });
    return _credentialsFromResponse(response.data as Map<String, dynamic>);
  }
}
