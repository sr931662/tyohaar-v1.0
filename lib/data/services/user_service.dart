import '../api_client.dart';
import '../models.dart';

class UserService {
  final ApiClient _api = ApiClient();

  Future<User> getMe() async {
    final response = await _api.dio.get('users/me');
    return User.fromJson(response.data['data']);
  }

  Future<List<Address>> getAddresses() async {
    final response = await _api.dio.get('users/me/addresses');
    final List list = response.data['data'];
    return list.map((item) => Address.fromJson(item)).toList();
  }

  Future<void> updateProfile(Map<String, dynamic> data) async {
    await _api.dio.put('users/me', data: data);
  }

  /// Updates extended profile fields (photo, bio, address, etc.) that live
  /// on UserProfile, not on the User account itself — PUT users/me only
  /// accepts account fields (name/email/phone) and silently drops anything
  /// else, so profile_photo_url must go through this endpoint instead.
  Future<void> updateExtendedProfile(String userId, Map<String, dynamic> data) async {
    await _api.dio.put('users/$userId/profile', data: data);
  }

  Future<Address> addAddress(Map<String, dynamic> data) async {
    final response = await _api.dio.post('users/me/addresses', data: data);
    return Address.fromJson(response.data['data'] as Map<String, dynamic>);
  }

  Future<Address> updateAddress(String addressId, Map<String, dynamic> data) async {
    final response = await _api.dio.put('users/me/addresses/$addressId', data: data);
    return Address.fromJson(response.data['data'] as Map<String, dynamic>);
  }

  Future<void> deleteAddress(String addressId) async {
    await _api.dio.delete('users/me/addresses/$addressId');
  }
}
