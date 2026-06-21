import 'package:flutter/material.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../widgets/ty_button.dart';
import '../widgets/common.dart';

class MembershipPlanScreen extends StatelessWidget {
  const MembershipPlanScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: 'My Membership Plan'),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
        children: [
          Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              gradient: LinearGradient(colors: [ty.saffron, ty.saffronDeep], begin: Alignment.topLeft, end: Alignment.bottomRight),
              borderRadius: BorderRadius.circular(24),
              boxShadow: [BoxShadow(color: ty.saffron.withOpacity(0.3), blurRadius: 15, offset: const Offset(0, 8))],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('GOLD MEMBER', style: TyType.display(24, color: Colors.white)),
                    const Icon(Icons.stars_rounded, color: Colors.white, size: 32),
                  ],
                ),
                const SizedBox(height: 8),
                Text('Valid till 12 Dec 2026', style: TyType.sans(14, color: Colors.white.withOpacity(0.9))),
                const SizedBox(height: 24),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  decoration: BoxDecoration(color: Colors.white.withOpacity(0.2), borderRadius: BorderRadius.circular(12)),
                  child: const Text('ACTIVE', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12)),
                ),
              ],
            ),
          ),
          const SizedBox(height: 32),
          Text('YOUR BENEFITS', style: TyType.eyebrow(11, color: ty.ink3)),
          const SizedBox(height: 16),
          _benefit(context, 'Priority Booking', 'Book popular festival dates 48 hours before anyone else.'),
          _benefit(context, '15% Discount', 'Flat discount on all premium and luxury celebration packages.'),
          _benefit(context, 'Dedicated Manager', 'A personal celebration manager for all your events.'),
          _benefit(context, 'Exclusive Themes', 'Access to member-only traditional and modern decor themes.'),
          const SizedBox(height: 40),
          TyButton('Renew Membership', full: true, onTap: () {}),
          const SizedBox(height: 12),
          TyButton('Compare Plans', kind: TyButtonKind.ghost, full: true, onTap: () {}),
        ],
      ),
    );
  }

  Widget _benefit(BuildContext context, String title, String sub) {
    final ty = context.ty;
    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(color: ty.saffron.withOpacity(0.1), shape: BoxShape.circle),
            child: Icon(Icons.check_rounded, color: ty.saffronDeep, size: 16),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
                const SizedBox(height: 2),
                Text(sub, style: TyType.sans(13, color: ty.ink2)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
