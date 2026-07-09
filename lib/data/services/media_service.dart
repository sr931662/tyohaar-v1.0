import 'dart:io';
import 'package:dio/dio.dart';
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

  Future<String> uploadProfilePicture(File file) async {
    final fileName = file.path.split('/').last;
    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(file.path, filename: fileName),
      'usage': 'profile_photo',
    });

    final response = await _api.dio.post(
      'media/upload',
      data: formData,
    );
    
    // The backend returns ImageResponse in SuccessResponse.data
    // ImageResponse has a 'url' field (or similar, let's check response.py)
    return response.data['data']['url'] as String;
  }
}
