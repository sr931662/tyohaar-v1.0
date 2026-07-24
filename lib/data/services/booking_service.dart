import 'dart:io';
import 'package:dio/dio.dart';

import '../api_client.dart';
import '../models.dart';

class BookingService {
  final ApiClient _api = ApiClient();

  // ── Vendor-scoped bookings (mirrors vendorBookingsApi on the web) ───────

  Future<Map<String, dynamic>> listVendorBookings({
    int page = 1,
    int perPage = 20,
    String? search,
    String? status,
  }) async {
    final response = await _api.dio.get('bookings/vendor', queryParameters: {
      'page_size': perPage,
      if (search != null && search.isNotEmpty) 'search': search,
      // BookingFilters' field is `booking_status`, not `status` — FastAPI
      // binds query params to the dependency's field names directly.
      if (status != null && status.isNotEmpty) 'booking_status': status,
    });
    final raw = response.data;
    final items = (raw['data'] as List? ?? []).map((e) => Booking.fromJson(e)).toList();
    final meta = raw['meta'] as Map<String, dynamic>? ?? {};
    return {
      'items': items,
      'hasNext': meta['has_next'] as bool? ?? false,
      'cursor': meta['cursor'] as String?,
    };
  }

  Future<Booking> startBooking(String bookingId) async {
    final response = await _api.dio.post('bookings/$bookingId/start');
    return Booking.fromJson(response.data['data']);
  }

  Future<Booking> completeBooking(String bookingId) async {
    final response = await _api.dio.post('bookings/$bookingId/complete');
    return Booking.fromJson(response.data['data']);
  }

  Future<Booking> setPreparationStartTime(String bookingId, DateTime preparationStartAt) async {
    final response = await _api.dio.patch('bookings/$bookingId/pst', data: {
      'preparation_start_at': preparationStartAt.toIso8601String(),
    });
    return Booking.fromJson(response.data['data']);
  }

  Future<List<Map<String, dynamic>>> getBookingHistory(String bookingId) async {
    final response = await _api.dio.get('bookings/$bookingId/history');
    return List<Map<String, dynamic>>.from(response.data['data'] ?? []);
  }

  Future<List<Map<String, dynamic>>> getBookingStatusHistory(String bookingId) async {
    final response = await _api.dio.get('bookings/$bookingId/status-history');
    return List<Map<String, dynamic>>.from(response.data['data'] ?? []);
  }

  // ── Multimedia (vendor uploads for their own bookings) ──────────────────

  Future<List<Map<String, dynamic>>> listVendorBookingMedia() async {
    final response = await _api.dio.get('bookings/vendor/media');
    return List<Map<String, dynamic>>.from(response.data['data'] ?? []);
  }

  Future<void> uploadEventPhoto(String bookingId, File file) async {
    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(file.path, filename: file.path.split('/').last),
    });
    await _api.dio.post('bookings/$bookingId/media/images', data: formData);
  }

  Future<void> uploadEventVideo(String bookingId, File file) async {
    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(file.path, filename: file.path.split('/').last),
    });
    await _api.dio.post('bookings/$bookingId/media/videos', data: formData);
  }

  Future<List<Booking>> listMyBookings() async {
    final response = await _api.dio.get('bookings');
    final List list = (response.data['data'] ?? []) as List;
    return list.map((item) => Booking.fromJson(item)).toList();
  }

  Future<List<Booking>> listByCelebration(String celebrationId) async {
    final response = await _api.dio
        .get('bookings', queryParameters: {'celebration_id': celebrationId});
    final List list = (response.data['data'] ?? []) as List;
    return list.map((item) => Booking.fromJson(item)).toList();
  }

  Future<Booking> createBooking(Map<String, dynamic> data) async {
    final response = await _api.dio.post('bookings', data: data);
    return Booking.fromJson(response.data['data']);
  }

  Future<Booking> getBookingDetails(String id) async {
    final response = await _api.dio.get('bookings/$id');
    return Booking.fromJson(response.data['data']);
  }

  Future<BookingCancellation> requestCancellation({
    required String bookingId,
    required String customerId,
    required String reason,
    String? reasonDetail,
  }) async {
    final response = await _api.dio.post('bookings/$bookingId/cancellation', data: {
      'booking_id': bookingId,
      'reason': reason,
      'reason_detail': reasonDetail,
      'cancelled_by_id': customerId,
    });
    return BookingCancellation.fromJson(response.data['data']);
  }
}

class BookingCancellation {
  final String id;
  final String bookingId;
  final String reason;
  final double? cancellationFee;
  final double? refundAmount;

  BookingCancellation({
    required this.id,
    required this.bookingId,
    required this.reason,
    this.cancellationFee,
    this.refundAmount,
  });

  factory BookingCancellation.fromJson(Map<String, dynamic> json) {
    return BookingCancellation(
      id: json['id'] as String,
      bookingId: json['booking_id'] as String,
      reason: json['reason'] as String,
      cancellationFee: json['cancellation_fee'] != null
          ? asDouble(json['cancellation_fee'])
          : null,
      refundAmount: json['refund_amount'] != null
          ? asDouble(json['refund_amount'])
          : null,
    );
  }
}
