import '../api_client.dart';

/// UI-facing category labels mapped to the backend's TicketCategory enum
/// values (lowercase, must match exactly — these are Python str enums).
const Map<String, String> ticketCategoryOptions = {
  'Planning': 'general',
  'Packages': 'booking',
  'Payments': 'payment',
  'Technical Issue': 'technical',
  'Others': 'general',
};

class SupportTicket {
  final String id;
  final String ticketNumber;
  final String subject;
  final String description;
  final String category;
  final String priority;
  final String status;
  final String? resolutionSummary;
  final DateTime createdAt;
  final DateTime? lastActivityAt;

  SupportTicket({
    required this.id,
    required this.ticketNumber,
    required this.subject,
    required this.description,
    required this.category,
    required this.priority,
    required this.status,
    this.resolutionSummary,
    required this.createdAt,
    this.lastActivityAt,
  });

  factory SupportTicket.fromJson(Map<String, dynamic> json) {
    return SupportTicket(
      id: json['id'] as String,
      ticketNumber: json['ticket_number'] as String? ?? '',
      subject: json['subject'] as String? ?? '',
      description: json['description'] as String? ?? '',
      category: json['category'] as String? ?? 'general',
      priority: json['priority'] as String? ?? 'medium',
      status: json['ticket_status'] as String? ?? 'open',
      resolutionSummary: json['resolution_summary'] as String?,
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
      lastActivityAt: json['last_activity_at'] != null ? DateTime.tryParse(json['last_activity_at'] as String) : null,
    );
  }
}

class SupportMessage {
  final String id;
  final String? senderId;
  final String senderRole;
  final String body;
  final DateTime createdAt;

  SupportMessage({
    required this.id,
    this.senderId,
    required this.senderRole,
    required this.body,
    required this.createdAt,
  });

  bool get isMine => senderRole == 'customer';

  factory SupportMessage.fromJson(Map<String, dynamic> json) {
    return SupportMessage(
      id: json['id'] as String,
      senderId: json['sender_id'] as String?,
      senderRole: json['sender_role'] as String? ?? 'customer',
      body: json['body'] as String? ?? '',
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
    );
  }
}

class SupportService {
  final ApiClient _api = ApiClient();

  /// [category] must be one of ticketCategoryOptions' backend values, not
  /// the UI display label. [description] must be at least 20 characters
  /// (enforced by the backend).
  Future<SupportTicket> createTicket({
    required String category,
    required String subject,
    required String description,
  }) async {
    final response = await _api.dio.post('support/tickets', data: {
      'category': category,
      'subject': subject,
      'description': description,
    });
    return SupportTicket.fromJson(response.data['data'] as Map<String, dynamic>);
  }

  Future<List<SupportTicket>> listMyTickets() async {
    final response = await _api.dio.get('support/tickets');
    final List list = (response.data['data'] ?? []) as List;
    return list.map((item) => SupportTicket.fromJson(item as Map<String, dynamic>)).toList();
  }

  Future<SupportTicket> getTicket(String ticketId) async {
    final response = await _api.dio.get('support/tickets/$ticketId');
    return SupportTicket.fromJson(response.data['data'] as Map<String, dynamic>);
  }

  // The backend returns the full thread as a plain list (not paginated) —
  // a ticket's message count is naturally bounded.
  Future<List<SupportMessage>> listMessages(String ticketId) async {
    final response = await _api.dio.get('support/tickets/$ticketId/messages');
    final List list = (response.data['data'] ?? []) as List;
    return list.map((item) => SupportMessage.fromJson(item as Map<String, dynamic>)).toList();
  }

  Future<SupportMessage> addMessage(String ticketId, String body) async {
    final response = await _api.dio.post('support/tickets/$ticketId/messages', data: {
      'body': body,
    });
    return SupportMessage.fromJson(response.data['data'] as Map<String, dynamic>);
  }
}
