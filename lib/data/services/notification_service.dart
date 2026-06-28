import '../api_client.dart';
import '../models.dart';

class NotificationService {
  final ApiClient _api = ApiClient();

  Future<List<NotifItem>> listNotifications() async {
    final response = await _api.dio.get('notifications');
    final List list = response.data['data']['items'];
    return list.map<NotifItem>((item) {
      return NotifItem(
        icon: _getIconForType(item['notification_type'] ?? ''),
        tint: _getTintForType(item['notification_type'] ?? ''),
        who: item['sender_name'] ?? 'System',
        text: item['body'] ?? '',
        time: _formatRelativeTime(DateTime.parse(item['created_at'])),
        unread: item['status'] == 'pending' || item['status'] == 'delivered',
      );
    }).toList();
  }

  String _getIconForType(String type) {
    if (type.contains('booking')) return 'check';
    if (type.contains('payment')) return 'wallet';
    if (type.contains('chat')) return 'chat';
    return 'spark';
  }

  String _getTintForType(String type) {
    if (type.contains('booking')) return 'leaf';
    if (type.contains('payment')) return 'gold';
    return 'saffron';
  }

  String _formatRelativeTime(DateTime dt) {
    final diff = DateTime.now().difference(dt);
    if (diff.inMinutes < 60) return '${diff.inMinutes}m';
    if (diff.inHours < 24) return '${diff.inHours}h';
    return '${diff.inDays}d';
  }
}
