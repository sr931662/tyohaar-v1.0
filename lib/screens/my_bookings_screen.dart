import 'package:flutter/material.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/sample_data.dart';
import '../widgets/photo_placeholder.dart';
import '../widgets/common.dart';
import 'event_hub_screen.dart';

class MyBookingsScreen extends StatelessWidget {
  const MyBookingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: 'My Bookings'),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(18, 12, 18, 28),
        children: [
          Text('UPCOMING', style: TyType.eyebrow(11, color: ty.ink3)),
          const SizedBox(height: 12),
          _bookingCard(context, 'Birthday Bliss', '14 Jun', 'Confirmed', 'saffron'),
          _bookingCard(context, 'Griha Pravesh', '02 Aug', 'Pending Payment', 'leaf'),
          const SizedBox(height: 32),
          Text('PAST', style: TyType.eyebrow(11, color: ty.ink3)),
          const SizedBox(height: 12),
          _bookingCard(context, 'Diwali Celebration', '12 Nov 2025', 'Completed', 'gold'),
          _bookingCard(context, 'Dadi’s 70th', '20 Sep 2025', 'Completed', 'rose'),
        ],
      ),
    );
  }

  Widget _bookingCard(BuildContext context, String title, String date, String status, String tint) {
    final ty = context.ty;
    final isDone = status == 'Completed';
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
              child: PhotoPlaceholder(tint: tint, arch: false),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: TyType.sans(16, color: ty.ink, weight: FontWeight.w700)),
                  const SizedBox(height: 2),
                  Text(date, style: TyType.sans(12, color: ty.ink2)),
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
                status,
                style: TyType.sans(10, color: isDone ? ty.leaf : ty.saffronDeep, weight: FontWeight.w700),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
