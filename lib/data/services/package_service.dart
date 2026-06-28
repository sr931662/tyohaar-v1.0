import '../api_client.dart';
import '../models.dart';

class PackageService {
  final ApiClient _api = ApiClient();

  Future<List<Package>> listPackages({String? categoryId, String? query}) async {
    final response = await _api.dio.get(
      'packages',
      queryParameters: {
        if (categoryId != null) 'category_id': categoryId,
        if (query != null) 'search': query,
      },
    );
    final List list = response.data['data']['items'];
    return list.map((item) => Package.fromJson(item)).toList();
  }

  Future<Package> getPackageDetails(String id) async {
    final response = await _api.dio.get('packages/$id');
    return Package.fromJson(response.data['data']);
  }

  Future<List<Occasion>> listOccasions() async {
    final response = await _api.dio.get('occasions');
    final List list = response.data['data'];
    return list.map((item) => Occasion.fromJson(item)).toList();
  }
}
