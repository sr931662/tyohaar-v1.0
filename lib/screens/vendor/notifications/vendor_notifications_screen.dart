import 'package:flutter/material.dart';

import '../../../theme/colors.dart';
import '../../../theme/typography.dart';
import '../../../data/models.dart';
import '../../../data/services/notification_service.dart';

class VendorNotificationsScreen extends StatefulWidget {
  const VendorNotificationsScreen({super.key});

  @override
  State<VendorNotificationsScreen> createState() => _VendorNotificationsScreenState();
}

class _VendorNotificationsScreenState extends State<VendorNotificationsScreen> {
  final _notificationService = NotificationService();
  List<NotifItem> _items = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _isLoading = true);
    try {
      final items = await _notificationService.listNotifications();
      if (mounted) setState(() { _items = items; _isLoading = false; });
    } catch (_) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _markAllRead() async {
    try {
      await _notificationService.markAllAsRead();
      _load();
    } catch (_) {}
  }

  Future<void> _markRead(NotifItem item) async {
    try {
      await _notificationService.markAsRead(item.id);
      _load();
    } catch (_) {}
  }

  Future<void> _delete(NotifItem item) async {
    try {
      await _notificationService.deleteNotification(item.id);
      _load();
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: AppBar(
        title: const Text('Notifications'),
        actions: [TextButton(onPressed: _markAllRead, child: const Text('Mark all read'))],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _items.isEmpty
              ? Center(child: Text('No notifications', style: TyType.sans(14, color: ty.ink2)))
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView.separated(
                    padding: const EdgeInsets.all(18),
                    itemCount: _items.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 8),
                    itemBuilder: (context, i) {
                      final item = _items[i];
                      return Dismissible(
                        key: ValueKey(item.id),
                        direction: DismissDirection.endToStart,
                        background: Container(
                          alignment: Alignment.centerRight,
                          padding: const EdgeInsets.only(right: 20),
                          decoration: BoxDecoration(color: Colors.red.withOpacity(0.15), borderRadius: BorderRadius.circular(14)),
                          child: const Icon(Icons.delete_outline, color: Colors.red),
                        ),
                        onDismissed: (_) => _delete(item),
                        child: GestureDetector(
                          onTap: () { if (item.unread) _markRead(item); },
                          child: Container(
                            padding: const EdgeInsets.all(14),
                            decoration: BoxDecoration(
                              color: item.unread ? ty.saffron.withOpacity(0.06) : ty.surface,
                              borderRadius: BorderRadius.circular(14),
                              border: Border.all(color: ty.line),
                            ),
                            child: Row(
                              children: [
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(item.title, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w700)),
                                      const SizedBox(height: 2),
                                      Text(item.text, style: TyType.sans(12.5, color: ty.ink2)),
                                    ],
                                  ),
                                ),
                                if (item.unread) Container(width: 8, height: 8, decoration: BoxDecoration(color: ty.saffron, shape: BoxShape.circle)),
                              ],
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                ),
    );
  }
}
