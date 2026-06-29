import '../api_client.dart';
import '../models.dart';

class MediaService {
  final ApiClient _api = ApiClient();

  Future<List<Memory>> listMemories() async {
    final response = await _api.dio.get('media/memories');
    final List list = response.data['data'];
    return list.map<Memory>((item) {
      return Memory(
        title: item['title'] ?? '',
        date: item['celebration_date'] ?? '',
        tint: item['tint'] ?? 'saffron',
        photos: item['image_count'] ?? 0,
        span: (item['is_featured'] == true) ? 2 : 1,
      );
    }).toList();
  }
}
