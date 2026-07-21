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
      backgroundColor: Colors.transparent,
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _items.isEmpty
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.notifications_none_rounded, size: 48, color: ty.ink3.withOpacity(0.5)),
                      const SizedBox(height: 16),
                      Text('No notifications', style: TyType.sans(14, color: ty.ink2)),
                    ],
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView.separated(
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
                    itemCount: _items.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 10),
                    itemBuilder: (context, i) {
                      final item = _items[i];
                      return Dismissible(
                        key: ValueKey(item.id),
                        direction: DismissDirection.endToStart,
                        background: Container(
                          alignment: Alignment.centerRight,
                          padding: const EdgeInsets.only(right: 20),
                          decoration: BoxDecoration(color: ty.rose.withOpacity(0.15), borderRadius: BorderRadius.circular(16)),
                          child: Icon(Icons.delete_outline, color: ty.rose),
                        ),
                        onDismissed: (_) => _delete(item),
                        child: GestureDetector(
                          onTap: () { if (item.unread) _markRead(item); },
                          child: Container(
                            padding: const EdgeInsets.all(16),
                            decoration: BoxDecoration(
                              color: item.unread ? ty.saffron.withOpacity(0.06) : ty.surface,
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(color: item.unread ? ty.saffron.withOpacity(0.2) : ty.line),
                              boxShadow: item.unread ? [BoxShadow(color: ty.saffron.withOpacity(0.04), blurRadius: 4, offset: const Offset(0, 2))] : null,
                            ),
                            child: Row(
                              children: [
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(item.title, style: TyType.sans(14.5, color: ty.ink, weight: FontWeight.w700)),
                                      const SizedBox(height: 4),
                                      Text(item.text, style: TyType.sans(13, color: ty.ink2)),
                                    ],
                                  ),
                                ),
                                if (item.unread) ...[
                                  const SizedBox(width: 12),
                                  Container(width: 10, height: 10, decoration: BoxDecoration(color: ty.saffron, shape: BoxShape.circle, border: Border.all(color: ty.surface, width: 2))),
                                ],
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
