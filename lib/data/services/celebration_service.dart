import '../api_client.dart';
import '../models.dart';

class CelebrationService {
  final ApiClient _api = ApiClient();

  Future<List<Celebration>> listCelebrations() async {
    final response = await _api.dio.get('celebrations');
    final List list = response.data['data'];
    return list.map((item) => Celebration.fromJson(item)).toList();
  }

  Future<Celebration> getCelebrationDetails(String id) async {
    final response = await _api.dio.get('celebrations/$id');
    return Celebration.fromJson(response.data['data']);
  }

  Future<List<Guest>> listGuests(String celebrationId) async {
    final response = await _api.dio.get('celebrations/$celebrationId/guests');
    final List list = response.data['data'];
    return list.map((item) => Guest.fromJson(item)).toList();
  }

  Future<List<CelebrationChecklistItem>> listChecklist(String celebrationId) async {
    final response = await _api.dio.get('celebrations/$celebrationId/checklist');
    final List list = response.data['data'] ?? [];
    return list.map((item) => CelebrationChecklistItem.fromJson(item)).toList();
  }
}
