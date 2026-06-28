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

  Future<void> addAddress(Map<String, dynamic> data) async {
    await _api.dio.post('users/me/addresses', data: data);
  }
}
