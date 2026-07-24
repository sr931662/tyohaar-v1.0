import 'package:dio/dio.dart';

import '../api_client.dart';
import '../models.dart';

/// Options for the largely-static catalog GET endpoints below — opts them
/// into ApiClient's in-memory cache so repeat navigations (home → explore →
/// plan flow, etc.) don't all re-fetch the same occasions/packages/themes
/// over the network within the same app session.
Options _cacheable({Duration ttl = const Duration(minutes: 10)}) =>
    Options(extra: {'cache': true, 'cacheTtl': ttl});

class PackageService {
  final ApiClient _api = ApiClient();

  Future<List<Package>> listPackages({
    String? categoryId,
    String? occasionId,
    String? query,
    String? city,
    bool? featured,
  }) async {
    final response = await _api.dio.get(
      'packages',
      queryParameters: {
        if (categoryId != null) 'category_id': categoryId,
        if (occasionId != null) 'occasion_id': occasionId,
        if (query != null) 'search': query,
        if (city != null) 'city': city,
        if (featured != null) 'is_featured': featured,
        'page_size': 100, // Ensure we fetch enough packages for the initial view
      },
      // Free-text search results are never cached — only the common,
      // filter-free/city-scoped browse queries repeat often enough to help.
      options: query == null ? _cacheable() : null,
    );
    final List list = (response.data['data'] ?? []) as List;
    return list.map((item) => Package.fromJson(item as Map<String, dynamic>)).toList();
  }

  Future<Package> getPackageDetails(String id) async {
    final response = await _api.dio.get('packages/$id', options: _cacheable());
    return Package.fromJson(response.data['data']);
  }

  Future<List<PackageItem>> listPackageItems(String packageId) async {
    final response = await _api.dio.get('packages/$packageId/items', options: _cacheable());
    final List list = (response.data['data'] ?? []) as List;
    return list.map((item) => PackageItem.fromJson(item as Map<String, dynamic>)).toList();
  }

  Future<List<PackageCategory>> listCategories() async {
    final response = await _api.dio.get('packages/categories', options: _cacheable());
    final List list = (response.data['data'] ?? []) as List;
    return list
        .map((item) => PackageCategory.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<List<Occasion>> listOccasions() async {
    final response = await _api.dio.get('occasions', options: _cacheable());
    final List list = (response.data['data'] ?? []) as List;
    return list.map((item) => Occasion.fromJson(item)).toList();
  }

  Future<List<CelebrationTheme>> listThemes() async {
    final response = await _api.dio.get('occasions/themes', options: _cacheable());
    final List list = (response.data['data'] ?? []) as List;
    return list.map((item) => CelebrationTheme.fromJson(item)).toList();
  }

  // ── Package Reviews ────────────────────────────────────────────────────────

  Future<List<PackageReviewModel>> listPackageReviews(String packageId, {String? cursor}) async {
    final response = await _api.dio.get(
      'packages/$packageId/reviews',
      queryParameters: {if (cursor != null) 'cursor': cursor},
    );
    final List list = (response.data['data'] ?? []) as List;
    return list.map((item) => PackageReviewModel.fromJson(item as Map<String, dynamic>)).toList();
  }

  Future<PackageReviewModel> addPackageReview(
    String packageId, {
    String? bookingId,
    required int rating,
    String? title,
    String? body,
  }) async {
    final response = await _api.dio.post('packages/$packageId/reviews', data: {
      if (bookingId != null) 'booking_id': bookingId,
      'rating': rating,
      if (title != null) 'title': title,
      if (body != null) 'body': body,
    });
    return PackageReviewModel.fromJson(response.data['data']);
  }

  Future<void> deletePackageReview(String packageId, String reviewId) =>
      _api.dio.delete('packages/$packageId/reviews/$reviewId');

  // ── Package Item Reviews ───────────────────────────────────────────────────

  Future<List<PackageItemReviewModel>> listPackageItemReviews(
    String packageId,
    String itemId, {
    String? cursor,
  }) async {
    final response = await _api.dio.get(
      'packages/$packageId/items/$itemId/reviews',
      queryParameters: {if (cursor != null) 'cursor': cursor},
    );
    final List list = (response.data['data'] ?? []) as List;
    return list
        .map((item) => PackageItemReviewModel.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<PackageItemReviewModel> addPackageItemReview(
    String packageId,
    String itemId, {
    String? bookingId,
    required int rating,
    String? title,
    String? body,
  }) async {
    final response = await _api.dio.post('packages/$packageId/items/$itemId/reviews', data: {
      if (bookingId != null) 'booking_id': bookingId,
      'rating': rating,
      if (title != null) 'title': title,
      if (body != null) 'body': body,
    });
    return PackageItemReviewModel.fromJson(response.data['data']);
  }

  Future<void> deletePackageItemReview(String packageId, String itemId, String reviewId) =>
      _api.dio.delete('packages/$packageId/items/$itemId/reviews/$reviewId');

  // ── Likes ──────────────────────────────────────────────────────────────────

  Future<Map<String, dynamic>> likePackage(String packageId) async {
    final response = await _api.dio.post('packages/$packageId/like');
    return response.data['data'] as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> unlikePackage(String packageId) async {
    final response = await _api.dio.delete('packages/$packageId/like');
    return response.data['data'] as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> likePackageItem(String packageId, String itemId) async {
    final response = await _api.dio.post('packages/$packageId/items/$itemId/like');
    return response.data['data'] as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> unlikePackageItem(String packageId, String itemId) async {
    final response = await _api.dio.delete('packages/$packageId/items/$itemId/like');
    return response.data['data'] as Map<String, dynamic>;
  }
}
