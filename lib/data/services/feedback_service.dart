import '../api_client.dart';

class FeedbackService {
  final ApiClient _api = ApiClient();

  Future<void> submitFeedback({
    required int rating,
    required String category,
    String? comments,
  }) async {
    await _api.dio.post('feedback', data: {
      'rating': rating,
      'category': category,
      if (comments != null && comments.trim().isNotEmpty) 'comments': comments.trim(),
    });
  }
}
