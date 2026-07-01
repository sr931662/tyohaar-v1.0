import '../api_client.dart';
import '../models.dart';

class NotificationService {
  final ApiClient _api = ApiClient();

  Future<List<NotifItem>> listNotifications() async {
    final response = await _api.dio.get('notifications');
    final List list = response.data['data'];
    return list.map<NotifItem>((item) => NotifItem.fromJson(item)).toList();
  }

  Future<void> markAllAsRead() async {
    await _api.dio.post('notifications/mark-read');
  }

  Future<int> getUnreadCount() async {
    final list = await listNotifications();
    return list.where((n) => n.unread).length;
  }
}
