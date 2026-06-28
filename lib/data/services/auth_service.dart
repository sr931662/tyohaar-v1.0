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

  factory AuthCredentials.fromJson(Map<String, dynamic> json) {
    // Backend wraps in SuccessResponse: { "success": true, "data": { ... } }
    final data = (json['data'] ?? json) as Map<String, dynamic>;
    return AuthCredentials(
      accessToken: data['access_token'] as String,
      refreshToken: data['refresh_token'] as String,
      user: User.fromJson(data['user'] as Map<String, dynamic>),
    );
  }
}

class AuthService {
  final ApiClient _api = ApiClient();

  Future<AuthCredentials> login(String email, String password) async {
    final response = await _api.dio.post('auth/login', data: {
      'email': email,
      'password': password,
    });
    return AuthCredentials.fromJson(response.data as Map<String, dynamic>);
  }

  Future<AuthCredentials> register(String email, String password, {String? name}) async {
    final response = await _api.dio.post('auth/register', data: {
      'email': email,
      'password': password,
      if (name != null && name.isNotEmpty) 'full_name': name,
    });
    return AuthCredentials.fromJson(response.data as Map<String, dynamic>);
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
    return AuthCredentials.fromJson(response.data as Map<String, dynamic>);
  }
}
