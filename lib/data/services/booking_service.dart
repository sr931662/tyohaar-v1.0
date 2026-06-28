import '../api_client.dart';
import '../models.dart';

class BookingService {
  final ApiClient _api = ApiClient();

  Future<List<Booking>> listMyBookings() async {
    final response = await _api.dio.get('bookings');
    final List list = response.data['data']['items'];
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
}
