import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:intl/intl.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/models.dart';
import '../data/services/booking_service.dart';
import '../widgets/photo_placeholder.dart';
import '../widgets/common.dart';
import 'event_hub_screen.dart';

class MyBookingsScreen extends StatefulWidget {
  const MyBookingsScreen({super.key});

  @override
  State<MyBookingsScreen> createState() => _MyBookingsScreenState();
}

class _MyBookingsScreenState extends State<MyBookingsScreen> {
  final BookingService _bookingService = BookingService();
  List<Booking> _bookings = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadBookings();
  }

  Future<void> _loadBookings() async {
    try {
      final bookings = await _bookingService.listMyBookings();
      setState(() {
        _bookings = bookings;
        _isLoading = false;
      });
    } catch (e) {
      debugPrint('Error loading bookings: $e');
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    
    final upcoming = _bookings.where((b) => b.scheduledDate.isAfter(DateTime.now())).toList();
    final past = _bookings.where((b) => b.scheduledDate.isBefore(DateTime.now())).toList();

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: 'My Bookings'),
      body: _isLoading 
        ? const Center(child: CircularProgressIndicator())
        : _bookings.isEmpty 
          ? _buildEmptyState(context)
          : ListView(
              padding: const EdgeInsets.fromLTRB(18, 12, 18, 28),
              children: [
                if (upcoming.isNotEmpty) ...[
                  Text('UPCOMING', style: TyType.eyebrow(11, color: ty.ink3)),
                  const SizedBox(height: 12),
                  ...upcoming.map((b) => _bookingCard(context, b)),
                  const SizedBox(height: 32),
                ],
                if (past.isNotEmpty) ...[
                  Text('PAST', style: TyType.eyebrow(11, color: ty.ink3)),
                  const SizedBox(height: 12),
                  ...past.map((b) => _bookingCard(context, b)),
                ],
              ],
            ),
    );
  }

  Widget _buildEmptyState(BuildContext context) {
    final ty = context.ty;
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.calendar_today_outlined, size: 64, color: ty.ink3),
          const SizedBox(height: 16),
          Text('No bookings yet', style: TyType.display(20, color: ty.ink)),
          const SizedBox(height: 8),
          Text('Your upcoming celebrations will appear here.', 
            style: TyType.sans(14, color: ty.ink2)),
        ],
      ),
    );
  }

  Widget _bookingCard(BuildContext context, Booking b) {
    final ty = context.ty;
    final isDone = b.status == 'completed';
    final dateStr = DateFormat('dd MMM').format(b.scheduledDate);
    
    return GestureDetector(
      onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const EventHubScreen())),
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: ty.surface,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: ty.line),
        ),
        child: Row(
          children: [
            SizedBox(
              width: 64,
              height: 64,
              child: ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: CachedNetworkImage(
                  imageUrl: b.packageCoverUrl ?? '',
                  fit: BoxFit.cover,
                  placeholder: (context, url) => PhotoPlaceholder(tint: 'saffron', arch: false),
                  errorWidget: (context, url, error) => PhotoPlaceholder(tint: 'saffron', arch: false),
                ),
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(b.packageName ?? 'Custom Booking', style: TyType.sans(16, color: ty.ink, weight: FontWeight.w700)),
                  const SizedBox(height: 2),
                  Text(dateStr, style: TyType.sans(12, color: ty.ink2)),
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: BoxDecoration(
                color: isDone ? ty.leaf.withOpacity(0.1) : ty.saffron.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                b.status.toUpperCase(),
                style: TyType.sans(10, color: isDone ? ty.leaf : ty.saffronDeep, weight: FontWeight.w700),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
