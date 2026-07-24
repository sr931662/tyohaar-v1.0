import 'dart:io';
import 'package:dio/dio.dart';

import '../api_client.dart';
import '../vendor_models.dart';

/// Options for the customer-facing vendor profile/package-list reads below —
/// opts them into ApiClient's in-memory cache so revisiting a vendor's page
/// within the same app session doesn't re-fetch data that rarely changes
/// (mirrors the same pattern in package_service.dart/common_service.dart).
Options _cacheable({Duration ttl = const Duration(minutes: 10)}) =>
    Options(extra: {'cache': true, 'cacheTtl': ttl});

/// All vendor-portal operations, mapped 1:1 to the same endpoints the web
/// vendor portal calls (client/src/vendor/api/index.js is the contract).
class VendorService {
  final ApiClient _api = ApiClient();

  // ── Profile / business ──────────────────────────────────────────────────

  Future<VendorBusinessProfile?> getMe() async {
    try {
      final response = await _api.dio.get('vendors/me');
      return VendorBusinessProfile.fromJson(response.data['data'] as Map<String, dynamic>);
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) return null;
      rethrow;
    }
  }

  Future<VendorBusinessProfile> create(Map<String, dynamic> body) async {
    final response = await _api.dio.post('vendors', data: body);
    return VendorBusinessProfile.fromJson(response.data['data'] as Map<String, dynamic>);
  }

  Future<VendorBusinessProfile> update(String vendorId, Map<String, dynamic> body) async {
    final response = await _api.dio.put('vendors/$vendorId', data: body);
    return VendorBusinessProfile.fromJson(response.data['data'] as Map<String, dynamic>);
  }

  Future<void> updateProfile(String vendorId, Map<String, dynamic> body) async {
    await _api.dio.put('vendors/$vendorId/profile', data: body);
  }

  // ── Gallery ──────────────────────────────────────────────────────────────

  Future<List<VendorGalleryItem>> listGallery(String vendorId) async {
    final response = await _api.dio.get('vendors/$vendorId/gallery');
    final List list = (response.data['data'] ?? []) as List;
    return list.map((e) => VendorGalleryItem.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<void> addGalleryItem(String vendorId, Map<String, dynamic> body) async {
    await _api.dio.post('vendors/$vendorId/gallery', data: body);
  }

  Future<void> deleteGalleryItem(String vendorId, String itemId) async {
    await _api.dio.delete('vendors/$vendorId/gallery/$itemId');
  }

  // ── Documents ────────────────────────────────────────────────────────────

  Future<List<VendorDocument>> listDocuments(String vendorId) async {
    final response = await _api.dio.get('vendors/$vendorId/documents');
    final List list = (response.data['data'] ?? []) as List;
    return list.map((e) => VendorDocument.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<void> addDocument(String vendorId, {required String documentType, required String documentUrl}) async {
    await _api.dio.post('vendors/$vendorId/documents', data: {
      'vendor_id': vendorId,
      'document_type': documentType,
      'document_url': documentUrl,
    });
  }

  Future<void> deleteDocument(String vendorId, String documentId) async {
    await _api.dio.delete('vendors/$vendorId/documents/$documentId');
  }

  // ── Bank accounts ────────────────────────────────────────────────────────

  Future<List<VendorBankAccount>> listBankAccounts(String vendorId) async {
    final response = await _api.dio.get('vendors/$vendorId/bank-accounts');
    final List list = (response.data['data'] ?? []) as List;
    return list.map((e) => VendorBankAccount.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<void> addBankAccount(String vendorId, Map<String, dynamic> body) async {
    await _api.dio.post('vendors/$vendorId/bank-accounts', data: body);
  }

  Future<void> deleteBankAccount(String vendorId, String bankId) async {
    await _api.dio.delete('vendors/$vendorId/bank-accounts/$bankId');
  }

  // ── Availability ─────────────────────────────────────────────────────────

  Future<List<VendorAvailabilityDay>> listAvailability(String vendorId) async {
    final response = await _api.dio.get('vendors/$vendorId/availability');
    final List list = (response.data['data'] ?? []) as List;
    return list.map((e) => VendorAvailabilityDay.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<void> createAvailability(String vendorId, VendorAvailabilityDay day) async {
    await _api.dio.post('vendors/$vendorId/availability', data: day.toJson());
  }

  Future<void> updateAvailability(String vendorId, String slotId, VendorAvailabilityDay day) async {
    await _api.dio.put('vendors/$vendorId/availability/$slotId', data: day.toJson());
  }

  // ── Reviews ──────────────────────────────────────────────────────────────

  Future<List<VendorReview>> listReviews(String vendorId) async {
    final response = await _api.dio.get('vendors/$vendorId/reviews');
    final data = response.data['data'];
    final List list = (data is Map ? data['items'] : data) ?? [];
    return list.map((e) => VendorReview.fromJson(e as Map<String, dynamic>)).toList();
  }

  // ── Public vendor listing (customer-facing vendor_detail_screen.dart) ───

  Future<VendorPublicDetail> getVendorById(String vendorId) async {
    final response = await _api.dio.get('vendors/$vendorId', options: _cacheable());
    return VendorPublicDetail.fromJson(response.data['data'] as Map<String, dynamic>);
  }

  Future<List<Map<String, dynamic>>> getVendorPackages(String vendorId) async {
    final response = await _api.dio.get('vendors/$vendorId/packages', options: _cacheable());
    final List list = (response.data['data'] ?? []) as List;
    return List<Map<String, dynamic>>.from(list);
  }

  Future<List<PublicVendorReview>> getVendorReviews(String vendorId, {int limit = 5}) async {
    final response = await _api.dio.get('vendors/$vendorId/reviews', queryParameters: {'limit': limit});
    final data = response.data['data'];
    final List list = (data is Map ? data['items'] : data) ?? [];
    return list.map((r) => PublicVendorReview.fromJson(r as Map<String, dynamic>)).toList();
  }

  // ── Packages (vendor-owned) ──────────────────────────────────────────────

  Future<List<VendorPackage>> listMyPackages() async {
    final response = await _api.dio.get('packages/vendor/mine', queryParameters: {'per_page': 100});
    final data = response.data['data'];
    final List list = (data is Map ? data['items'] : data) ?? [];
    return list.map((e) => VendorPackage.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<VendorPackage> getPackage(String packageId) async {
    final response = await _api.dio.get('packages/$packageId');
    return VendorPackage.fromJson(response.data['data'] as Map<String, dynamic>);
  }

  Future<VendorPackage> createPackage(Map<String, dynamic> body) async {
    final response = await _api.dio.post('packages', data: body);
    return VendorPackage.fromJson(response.data['data'] as Map<String, dynamic>);
  }

  Future<VendorPackage> updatePackage(String packageId, Map<String, dynamic> body) async {
    final response = await _api.dio.put('packages/$packageId', data: body);
    return VendorPackage.fromJson(response.data['data'] as Map<String, dynamic>);
  }

  Future<void> deletePackage(String packageId) async {
    await _api.dio.delete('packages/$packageId');
  }

  Future<void> submitPackageForReview(String packageId) async {
    await _api.dio.post('packages/$packageId/publish');
  }

  Future<void> unpublishPackage(String packageId) async {
    await _api.dio.post('packages/$packageId/unpublish');
  }

  Future<List<VendorPackageItem>> listPackageItems(String packageId) async {
    final response = await _api.dio.get('packages/$packageId/items');
    final List list = (response.data['data'] ?? []) as List;
    return list.map((e) => VendorPackageItem.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<void> addPackageItem(String packageId, Map<String, dynamic> body) async {
    await _api.dio.post('packages/$packageId/items', data: body);
  }

  Future<void> updatePackageItem(String packageId, String itemId, Map<String, dynamic> body) async {
    await _api.dio.put('packages/$packageId/items/$itemId', data: body);
  }

  Future<void> deletePackageItem(String packageId, String itemId) async {
    await _api.dio.delete('packages/$packageId/items/$itemId');
  }

  Future<void> addItemImage(String packageId, String itemId, String imageUrl) async {
    await _api.dio.post('packages/$packageId/items/$itemId/images', data: {'image_url': imageUrl});
  }

  Future<void> deleteItemImage(String packageId, String itemId, String imageId) async {
    await _api.dio.delete('packages/$packageId/items/$itemId/images/$imageId');
  }

  Future<List<VendorGalleryItem>> listPackageGallery(String packageId) async {
    final response = await _api.dio.get('packages/$packageId/gallery');
    final List list = (response.data['data'] ?? []) as List;
    return list.map((e) => VendorGalleryItem.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<void> addPackageGalleryItem(String packageId, String fileUrl) async {
    await _api.dio.post('packages/$packageId/gallery', data: {'file_url': fileUrl});
  }

  Future<void> deletePackageGalleryItem(String packageId, String galleryId) async {
    await _api.dio.delete('packages/$packageId/gallery/$galleryId');
  }

  // ── Common items (reusable templates) ───────────────────────────────────

  Future<List<VendorCommonItem>> listCommonItems() async {
    final response = await _api.dio.get('packages/vendor/common-items');
    final List list = (response.data['data'] ?? []) as List;
    return list.map((e) => VendorCommonItem.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<void> createCommonItem(Map<String, dynamic> body) async {
    await _api.dio.post('packages/vendor/common-items', data: body);
  }

  Future<void> deleteCommonItem(String itemId) async {
    await _api.dio.delete('packages/vendor/common-items/$itemId');
  }

  Future<void> attachCommonItem(String packageId, String itemId) async {
    await _api.dio.post('packages/$packageId/common-items/$itemId');
  }

  Future<void> detachCommonItem(String packageId, String itemId) async {
    await _api.dio.delete('packages/$packageId/common-items/$itemId');
  }

  // ── Earnings ─────────────────────────────────────────────────────────────

  Future<VendorEarnings> getEarnings() async {
    final response = await _api.dio.get('payments/vendor/earnings');
    return VendorEarnings.fromJson(response.data['data'] as Map<String, dynamic>);
  }

  // ── Media upload (shared by profile photo, package cover, gallery, docs) ──

  Future<String> uploadImage(File file, String usage) async {
    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(file.path, filename: file.path.split('/').last),
      'usage': usage,
    });
    final response = await _api.dio.post('media/upload', data: formData);
    return (response.data['data'] as Map?)?['url'] as String? ?? '';
  }
}
