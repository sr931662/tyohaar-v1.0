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

  Future<Guest> addGuest(
    String celebrationId, {
    required String name,
    String? phone,
    String? email,
    String? groupTag,
    String? notes,
  }) async {
    final response = await _api.dio.post('celebrations/$celebrationId/guests', data: {
      'name': name,
      if (phone != null && phone.isNotEmpty) 'phone': phone,
      if (email != null && email.isNotEmpty) 'email': email,
      if (groupTag != null && groupTag.isNotEmpty) 'group_tag': groupTag,
      if (notes != null && notes.isNotEmpty) 'notes': notes,
    });
    return Guest.fromJson(response.data['data']);
  }

  Future<Guest> updateGuest(
    String celebrationId,
    String guestId, {
    String? rsvpStatus,
    String? notes,
  }) async {
    final response = await _api.dio.put('celebrations/$celebrationId/guests/$guestId', data: {
      if (rsvpStatus != null) 'rsvp_status': rsvpStatus,
      if (notes != null) 'notes': notes,
    });
    return Guest.fromJson(response.data['data']);
  }

  Future<void> removeGuest(String celebrationId, String guestId) async {
    await _api.dio.delete('celebrations/$celebrationId/guests/$guestId');
  }

  Future<List<CelebrationChecklistItem>> listChecklist(String celebrationId) async {
    final response = await _api.dio.get('celebrations/$celebrationId/checklist');
    final List list = response.data['data'] ?? [];
    return list.map((item) => CelebrationChecklistItem.fromJson(item)).toList();
  }
}
