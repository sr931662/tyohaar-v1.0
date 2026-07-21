import '../api_client.dart';
import '../models.dart';
import 'booking_service.dart';
import 'celebration_service.dart';

class NotificationService {
  final ApiClient _api = ApiClient();
  final BookingService _bookingService = BookingService();
  final CelebrationService _celebrationService = CelebrationService();

  Future<List<NotifItem>> listNotifications() async {
    final response = await _api.dio.get('notifications');
    final List list = response.data['data'];
    final items = list.map<NotifItem>((item) => NotifItem.fromJson(item)).toList();
    return _enrichNotifications(items);
  }

  Future<void> markAllAsRead() async {
    await _api.dio.post('notifications/mark-read');
  }

  Future<void> markAsRead(String notificationId) async {
    await _api.dio.patch('notifications/$notificationId/read');
  }

  Future<void> deleteNotification(String notificationId) async {
    await _api.dio.delete('notifications/$notificationId');
  }

  Future<int> getUnreadCount() async {
    final response = await _api.dio.get('notifications/unread-count');
    return (response.data['data'] as num).toInt();
  }

  Future<List<NotifItem>> _enrichNotifications(List<NotifItem> items) async {
    final bookingIds = items
        .where((item) => item.referenceType == 'booking' && item.referenceId != null)
        .map((item) => item.referenceId!)
        .toSet()
        .toList();

    if (bookingIds.isEmpty) return items;

    final bookingPairs = await Future.wait(
      bookingIds.map((id) async {
        try {
          final booking = await _bookingService.getBookingDetails(id);
          return MapEntry(id, booking);
        } catch (_) {
          return null;
        }
      }),
    );

    final bookings = <String, Booking>{
      for (final pair in bookingPairs)
        if (pair != null) pair.key: pair.value,
    };

    final celebrationIds = bookings.values
        .map((booking) => booking.celebrationId)
        .where((id) => id.isNotEmpty)
        .toSet()
        .toList();

    final celebrationPairs = await Future.wait(
      celebrationIds.map((id) async {
        try {
          final celebration = await _celebrationService.getCelebrationDetails(id);
          return MapEntry(id, celebration);
        } catch (_) {
          return null;
        }
      }),
    );

    final celebrations = <String, Celebration>{
      for (final pair in celebrationPairs)
        if (pair != null) pair.key: pair.value,
    };

    return items.map((item) {
      final bookingId = item.referenceId;
      if (item.referenceType != 'booking' || bookingId == null) return item;

      final booking = bookings[bookingId];
      if (booking == null) return item;

      final celebration = celebrations[booking.celebrationId];
      final eventTitle = celebration?.title.trim();
      final hasEventTitle = eventTitle != null && eventTitle.isNotEmpty;
      final body = _replaceBookingNumber(
        item.text,
        booking.bookingNumber,
        hasEventTitle ? eventTitle : null,
      );

      return item.copyWith(
        title: hasEventTitle ? eventTitle! : item.title,
        subtitle: hasEventTitle ? item.title : item.subtitle,
        text: body,
      );
    }).toList();
  }

  String _replaceBookingNumber(
    String body,
    String bookingNumber,
    String? replacement,
  ) {
    final cleanBody = body.replaceAll(RegExp(r'\s+'), ' ').trim();
    if (replacement == null || replacement.isEmpty || bookingNumber.isEmpty) {
      return cleanBody;
    }

    return cleanBody
        .replaceAll('booking $bookingNumber', replacement)
        .replaceAll('Booking $bookingNumber', replacement)
        .replaceAll('#$bookingNumber', replacement);
  }
}
