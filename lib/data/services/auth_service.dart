import 'package:dio/dio.dart';
import '../api_client.dart';
import '../models.dart';

class AuthCredentials {
  final String accessToken;
  final String refreshToken;
  final User user;
  // Only meaningful right after registration — true for every other flow
  // (login, vendor register, OTP login) since those responses simply don't
  // include the field and it defaults to true.
  final bool emailVerificationSent;

  AuthCredentials({
    required this.accessToken,
    required this.refreshToken,
    required this.user,
    this.emailVerificationSent = true,
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
    final emailVerificationSent = data['email_verification_sent'] as bool? ?? true;
    final userResp = await _api.dio.get(
      'users/me',
      options: Options(headers: {'Authorization': 'Bearer $accessToken'}),
    );
    final userData = (userResp.data['data'] ?? userResp.data) as Map<String, dynamic>;
    return AuthCredentials(
      accessToken: accessToken,
      refreshToken: refreshToken,
      user: User.fromJson(userData),
      emailVerificationSent: emailVerificationSent,
    );
  }

  /// Vendor self-registration — distinct schema from customer `register`
  /// (business name, vendor type, phone, etc.). Mirrors the web vendor
  /// portal's `vendorAuthApi.register` (`POST /auth/vendor/register`).
  Future<AuthCredentials> vendorRegister({
    required String fullName,
    required String email,
    required String phone,
    required String businessName,
    required String vendorType,
    required String password,
  }) async {
    final response = await _api.dio.post('auth/vendor/register', data: {
      'full_name': fullName,
      'email': email,
      'phone': phone,
      'business_name': businessName,
      'vendor_type': vendorType,
      'password': password,
    });
    return _credentialsFromResponse(response.data as Map<String, dynamic>);
  }

  /// Requests a password-reset OTP by email (used by both customer and
  /// vendor forgot-password flows).
  Future<void> requestPasswordResetOtp(String email) async {
    await _api.dio.post('auth/otp/request', data: {
      'identifier': email,
      'channel': 'email',
      'purpose': 'password_reset',
    });
  }

  /// Requests an email-verification OTP (used for the initial send failing
  /// or for the "Resend code" action on the verification screen).
  Future<void> requestEmailVerificationOtp(String email) async {
    await _api.dio.post('auth/otp/request', data: {
      'identifier': email,
      'channel': 'email',
      'purpose': 'email_verification',
    });
  }

  Future<void> verifyEmailOtp(String email, String otpCode) async {
    await _api.dio.post('auth/email/verify', data: {
      'email': email,
      'otp_code': otpCode,
    });
  }

  Future<void> resetPasswordWithOtp(String email, String otpCode, String newPassword) async {
    await _api.dio.post('auth/password/reset', data: {
      'email': email,
      'otp_code': otpCode,
      'new_password': newPassword,
    });
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
