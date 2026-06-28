import '../api_client.dart';

class SupportService {
  final ApiClient _api = ApiClient();

  Future<void> createTicket(String category, String description) async {
    await _api.dio.post('support/tickets', data: {
      'category': category.toLowerCase(),
      'title': 'Ticket: $category',
      'description': description,
    });
  }

  Future<List<Map<String, dynamic>>> listMyTickets() async {
    final response = await _api.dio.get('support/tickets');
    return List<Map<String, dynamic>>.from(response.data['data']['items']);
  }
}
