import '../api_client.dart';
import '../models.dart';

class CelebrationService {
  final ApiClient _api = ApiClient();

  Future<List<Celebration>> listCelebrations() async {
    final response = await _api.dio.get('celebrations');
    final List list = (response.data['data'] ?? []) as List;
    return list.map((item) => Celebration.fromJson(item)).toList();
  }

  Future<Celebration> getCelebrationDetails(String id) async {
    final response = await _api.dio.get('celebrations/$id');
    return Celebration.fromJson(response.data['data']);
  }

  Future<List<Guest>> listGuests(String celebrationId) async {
    final response = await _api.dio.get('celebrations/$celebrationId/guests');
    final List list = (response.data['data'] ?? []) as List;
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

  Future<List<GuestHistoryEvent>> listGuestHistory(String celebrationId) async {
    final response = await _api.dio.get('celebrations/$celebrationId/guest-history');
    final List list = response.data['data'] ?? [];
    return list.map((item) => GuestHistoryEvent.fromJson(item)).toList();
  }
}

class GuestHistoryEvent {
  final String id;
  final String celebrationGuestId;
  final String eventType;
  final String? previousStatus;
  final String? newStatus;
  final DateTime occurredAt;

  GuestHistoryEvent({
    required this.id,
    required this.celebrationGuestId,
    required this.eventType,
    this.previousStatus,
    this.newStatus,
    required this.occurredAt,
  });

  factory GuestHistoryEvent.fromJson(Map<String, dynamic> json) {
    return GuestHistoryEvent(
      id: json['id'] as String,
      celebrationGuestId: json['celebration_guest_id'] as String,
      eventType: json['event_type'] as String,
      previousStatus: json['previous_status'] as String?,
      newStatus: json['new_status'] as String?,
      occurredAt: DateTime.tryParse(json['occurred_at'] as String? ?? '') ?? DateTime.now(),
    );
  }
}
