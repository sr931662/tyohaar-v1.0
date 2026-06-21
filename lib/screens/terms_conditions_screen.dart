import 'package:flutter/material.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../widgets/common.dart';

class TermsConditionsScreen extends StatelessWidget {
  const TermsConditionsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: 'Terms & Conditions'),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
        children: [
          Text('Last updated: June 2026', style: TyType.sans(12, color: ty.ink3)),
          const SizedBox(height: 24),
          _section('1. Acceptance of Terms', 
            'By accessing or using the Tyohaar application, you agree to be bound by these Terms & Conditions and all applicable laws and regulations.'),
          _section('2. Booking and Payments', 
            'All bookings are subject to availability. Full payment or a specified advance is required to confirm a celebration package.'),
          _section('3. Cancellation and Refunds', 
            'Cancellations made 15 days prior to the event date are eligible for a 50% refund. Cancellations within 7 days are non-refundable.'),
          _section('4. User Responsibilities', 
            'Users are responsible for providing accurate guest counts and event locations. Any damages caused during the event may incur additional charges.'),
          _section('5. Limitation of Liability', 
            'Tyohaar is not liable for any indirect, incidental, or consequential damages arising from the use of our services or third-party vendor performance.'),
        ],
      ),
    );
  }

  Widget _section(String title, String content) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: TyType.sans(16, weight: FontWeight.w700)),
          const SizedBox(height: 8),
          Text(content, style: TyType.sans(14, color: Colors.grey[700], height: 1.6)),
        ],
      ),
    );
  }
}
