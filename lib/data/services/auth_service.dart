import 'package:dio/dio.dart';
import '../api_client.dart';
import '../models.dart';
import '../sign_in_identifier.dart';

/// The message to show for a failed auth call. The server answers errors as
/// {"error": {"message": ...}}; older code read `detail`/`message` at the top
/// level, found nothing, and always showed a generic "failed" line.
String authErrorMessage(Object error, String fallback) {
  if (error is DioException) {
    final data = error.response?.data;
    if (data is Map) {
      final nested = data['error'];
      if (nested is Map && nested['message'] is String) return nested['message'] as String;
      if (data['detail'] is String) return data['detail'] as String;
      if (data['message'] is String) return data['message'] as String;
    }
    if (error.type == DioExceptionType.connectionError ||
        error.type == DioExceptionType.connectionTimeout ||
        error.type == DioExceptionType.receiveTimeout) {
      return fallback;
    }
  }
  return fallback;
}

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

/// Public, non-secret auth config from `GET auth/config` — currently just the
/// Google web client ID, fetched at runtime so it lives only in the server's
/// .env rather than in a build-time --dart-define.
class AuthProviderConfig {
  final String googleClientId;
  final bool googleEnabled;
  // Whether the server can deliver one-time codes by email / SMS right now.
  // Missing from an older server -> assume email works, phone doesn't.
  final bool emailOtpEnabled;
  final bool phoneOtpEnabled;

  AuthProviderConfig({
    required this.googleClientId,
    required this.googleEnabled,
    this.emailOtpEnabled = true,
    this.phoneOtpEnabled = false,
  });

  factory AuthProviderConfig.fromJson(Map<String, dynamic> json) {
    return AuthProviderConfig(
      googleClientId: json['google_client_id'] as String? ?? '',
      googleEnabled: json['google_enabled'] as bool? ?? false,
      emailOtpEnabled: json['email_otp_enabled'] as bool? ?? true,
      phoneOtpEnabled: json['phone_otp_enabled'] as bool? ?? false,
    );
  }
}

/// Result of signing in with a one-time code.
class CodeSignInResult {
  final AuthCredentials credentials;
  /// True when this sign-in created the account (so the app can ask a name).
  final bool isNewUser;
  const CodeSignInResult(this.credentials, this.isNewUser);
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

  /// Fetches the public provider config. Cached for the process — the values
  /// come from server config and don't change between sign-in attempts.
  AuthProviderConfig? _providerConfig;

  Future<AuthProviderConfig> getProviderConfig() async {
    final cached = _providerConfig;
    if (cached != null) return cached;
    final response = await _api.dio.get('auth/config');
    final data = (response.data['data'] ?? response.data) as Map<String, dynamic>;
    return _providerConfig = AuthProviderConfig.fromJson(data);
  }

  /// Exchanges a Google ID token for a Tyohaar session. Sign-in and sign-up
  /// are the same call: the backend creates the customer account on first use.
  Future<AuthCredentials> signInWithGoogle(String idToken) async {
    final response = await _api.dio.post('auth/google', data: {
      'id_token': idToken,
    });
    return _credentialsFromResponse(response.data as Map<String, dynamic>);
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

  /// Sends a one-time sign-in code to an email address or mobile number.
  /// Works the same for new and existing accounts: the code both signs in
  /// and, on first use, creates the account. The server also shows the code
  /// as a push notification on devices already signed in to that account.
  Future<void> requestSignInCode(SignInIdentifier id) async {
    await _api.dio.post('auth/otp/request', data: {
      'identifier': id.value,
      'channel': id.channel,
      'purpose': 'login',
    });
  }

  Future<CodeSignInResult> verifySignInCode(SignInIdentifier id, String code) async {
    final response = await _api.dio.post('auth/otp/verify', data: {
      'identifier': id.value,
      'otp_code': code,
      'purpose': 'login',
    });
    final json = response.data as Map<String, dynamic>;
    final data = (json['data'] ?? json) as Map<String, dynamic>;
    final creds = await _credentialsFromResponse(json);
    return CodeSignInResult(creds, data['is_new_user'] as bool? ?? false);
  }

  /// Saves the name a brand-new account was asked for. Called before the
  /// tokens are handed to AuthManager, so the token is passed explicitly.
  Future<void> saveName(String accessToken, String name) async {
    await _api.dio.put(
      'users/me',
      data: {'full_name': name},
      options: Options(headers: {'Authorization': 'Bearer $accessToken'}),
    );
  }
}
