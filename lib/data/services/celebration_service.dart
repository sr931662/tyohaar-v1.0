import '../api_client.dart';
import '../models.dart';

class CelebrationService {
  final ApiClient _api = ApiClient();

  Future<List<Map<String, dynamic>>> listCelebrations() async {
    final response = await _api.dio.get('celebrations');
    return List<Map<String, dynamic>>.from(response.data['data']);
  }

  Future<Map<String, dynamic>> getCelebrationDetails(String id) async {
    final response = await _api.dio.get('celebrations/$id');
    return Map<String, dynamic>.from(response.data['data']);
  }

  Future<List<Guest>> listGuests(String celebrationId) async {
    final response = await _api.dio.get('celebrations/$celebrationId/guests');
    final List list = response.data['data'];
    return list.map((item) => Guest.fromJson(item)).toList();
  }
}
