import '../api_client.dart';
import '../models.dart';



class PackageService {
  final ApiClient _api = ApiClient();

  Future<List<Package>> listPackages({
    String? categoryId,
    String? occasionId,
    String? query,
    String? city,
  }) async {
    final response = await _api.dio.get(
      'packages',
      queryParameters: {
        if (categoryId != null) 'category_id': categoryId,
        if (occasionId != null) 'occasion_id': occasionId,
        if (query != null) 'search': query,
        if (city != null) 'city': city,
        'page_size': 100, // Ensure we fetch enough packages for the initial view
      },
    );
    final List list = response.data['data'];
    return list.map((item) => Package.fromJson(item as Map<String, dynamic>)).toList();
  }

  Future<Package> getPackageDetails(String id) async {
    final response = await _api.dio.get('packages/$id');
    return Package.fromJson(response.data['data']);
  }

  Future<List<PackageItem>> listPackageItems(String packageId) async {
    final response = await _api.dio.get('packages/$packageId/items');
    final List list = (response.data['data'] ?? []) as List;
    return list.map((item) => PackageItem.fromJson(item as Map<String, dynamic>)).toList();
  }

  Future<List<PackageCategory>> listCategories() async {
    final response = await _api.dio.get('packages/categories');
    final List list = response.data['data'];
    return list
        .map((item) => PackageCategory.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<List<Occasion>> listOccasions() async {
    final response = await _api.dio.get('occasions');
    final List list = response.data['data'];
    return list.map((item) => Occasion.fromJson(item)).toList();
  }
}
