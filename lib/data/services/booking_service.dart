import '../api_client.dart';
import '../models.dart';

class BookingService {
  final ApiClient _api = ApiClient();

  Future<List<Booking>> listMyBookings() async {
    final response = await _api.dio.get('bookings');
    final List list = response.data['data'];
    return list.map((item) => Booking.fromJson(item)).toList();
  }

  Future<List<Booking>> listByCelebration(String celebrationId) async {
    final response = await _api.dio
        .get('bookings', queryParameters: {'celebration_id': celebrationId});
    final List list = response.data['data'];
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
