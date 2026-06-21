import 'package:flutter/material.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../widgets/common.dart';

class PrivacyPolicyScreen extends StatelessWidget {
  const PrivacyPolicyScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: 'Privacy Policy'),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
        children: [
          Text('Last updated: June 2026', style: TyType.sans(12, color: ty.ink3)),
          const SizedBox(height: 24),
          _section('1. Information Collection', 
            'We collect information you provide directly to us, such as when you create an account, book a celebration package, or communicate with our support team.'),
          _section('2. Use of Information', 
            'We use the information we collect to provide, maintain, and improve our services, including to process transactions and send related information.'),
          _section('3. Sharing of Information', 
            'We may share your information with third-party vendors (caterers, decorators, etc.) solely for the purpose of fulfilling your booked packages.'),
          _section('4. Data Security', 
            'We take reasonable measures to help protect information about you from loss, theft, misuse, and unauthorized access.'),
          _section('5. Contact Us', 
            'If you have any questions about this Privacy Policy, please contact us at privacy@tyohaar.app.'),
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
