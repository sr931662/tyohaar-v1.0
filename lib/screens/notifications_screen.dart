import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/models.dart';
import '../data/services/notification_service.dart';
import '../widgets/common.dart';
import '../widgets/state_screens.dart';

class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({super.key});

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  final NotificationService _notificationService = NotificationService();
  List<NotifItem> _notifications = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadNotifications();
  }

  Future<void> _loadNotifications() async {
    setState(() { _isLoading = true; _error = null; });
    try {
      final notifs = await _notificationService.listNotifications();
      if (mounted) setState(() { _notifications = notifs; _isLoading = false; });
    } catch (e) {
      if (mounted) setState(() { _error = 'Could not load notifications.'; _isLoading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;

    return Scaffold(
      appBar: tyAppBar(context, title: 'Activity', actions: [
        Padding(
          padding: const EdgeInsets.only(right: 18),
          child: Center(
            child: GestureDetector(
              onTap: () async {
                await _notificationService.markAllAsRead();
                _loadNotifications();
              },
              child: Text('Mark read',
                  style: TyType.sans(12.5, color: ty.saffron, weight: FontWeight.w700)),
            ),
          ),
        ),
      ]),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? TyStateScreen.error(onAction: _loadNotifications)
              : _notifications.isEmpty
                  ? _buildEmptyState(context)
                  : ListView.builder(
              padding: const EdgeInsets.fromLTRB(18, 4, 18, 28),
              // Section label is item 0; notification rows are built lazily after it.
              itemCount: 1 + _notifications.length,
              itemBuilder: (context, index) {
                if (index == 0) {
                  final ty = context.ty;
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Text('RECENT', style: TyType.eyebrow(11.5, color: ty.ink3)),
                  );
                }
                return _row(context, _notifications[index - 1]);
              },
            ),
    );
  }

  Widget _buildEmptyState(BuildContext context) {
    return TyStateScreen.empty(
      title: 'No activity yet',
      message: "We'll notify you here about your bookings, payments, and upcoming celebrations.",
      icon: Icons.notifications_none_rounded,
    );
  }

  Widget _row(BuildContext context, NotifItem n) {
    final ty = context.ty;
    final c = ty.tint(n.tint);
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
      decoration: BoxDecoration(
        color: ty.surface,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: n.unread ? ty.line : ty.line.withOpacity(0.45)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: Color.alphaBlend(c.withOpacity(0.15), ty.surface2),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(tyIcon(n.icon), color: c, size: 20),
          ),
          const SizedBox(width: 13),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Text(
                        n.title,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: TyType.sans(14.5, color: ty.ink, weight: FontWeight.w700),
                      ),
                    ),
                    if (n.unread)
                      Container(
                        margin: const EdgeInsets.only(top: 4, left: 8),
                        width: 8,
                        height: 8,
                        decoration: BoxDecoration(color: ty.saffron, shape: BoxShape.circle),
                      ),
                  ],
                ),
                if (n.subtitle != null && n.subtitle!.trim().isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Text(
                    n.subtitle!,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TyType.sans(11.5, color: c, weight: FontWeight.w700),
                  ),
                ],
                const SizedBox(height: 6),
                Text(
                  n.text,
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                  style: TyType.sans(13, color: ty.ink2, height: 1.35),
                ),
                const SizedBox(height: 8),
                Text(
                  _formatNotificationTime(n.time),
                  style: TyType.sans(11.5, color: ty.ink3),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  static final _timeFmt = DateFormat('h:mm a');
  static final _dayMonthFmt = DateFormat('d MMM · h:mm a');
  static final _dayMonthYearFmt = DateFormat('d MMM y · h:mm a');

  String _formatNotificationTime(String raw) {
    final parsed = DateTime.tryParse(raw);
    if (parsed == null) return raw;

    final local = parsed.toLocal();
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final date = DateTime(local.year, local.month, local.day);
    final dayDiff = today.difference(date).inDays;

    if (dayDiff == 0) {
      return 'Today · ${_timeFmt.format(local)}';
    }
    if (dayDiff == 1) {
      return 'Yesterday · ${_timeFmt.format(local)}';
    }
    if (local.year == now.year) {
      return _dayMonthFmt.format(local);
    }
    return _dayMonthYearFmt.format(local);
  }
}
