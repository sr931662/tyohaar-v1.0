import '../api_client.dart';

class AuthService {
  final ApiClient _api = ApiClient();

  Future<Map<String, dynamic>> login(String email, String password) async {
    final response = await _api.dio.post('auth/login', data: {
      'email': email,
      'password': password,
    });
    return response.data;
  }

  Future<Map<String, dynamic>> register(String email, String password, {String? name}) async {
    final response = await _api.dio.post('auth/register', data: {
      'email': email,
      'password': password,
      if (name != null && name.isNotEmpty) 'full_name': name,
    });
    return response.data;
  }

  Future<void> logout() async {
    await _api.dio.post('auth/logout');
  }

  // Keeping OTP for future use if needed, but not used in the current flow
  Future<void> requestOtp(String phone) async {
    await _api.dio.post('auth/otp/request', data: {
      'identifier': phone,
      'channel': 'sms',
      'purpose': 'login',
      'device_fingerprint': 'mobile_app_default',
    });
  }

  Future<Map<String, dynamic>> verifyOtp(String phone, String code) async {
    final response = await _api.dio.post('auth/otp/verify', data: {
      'identifier': phone,
      'otp_code': code,
      'purpose': 'login',
    });
    return response.data['data'];
  }
}
