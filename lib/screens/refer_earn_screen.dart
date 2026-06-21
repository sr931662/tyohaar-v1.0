import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../widgets/ty_button.dart';
import '../widgets/common.dart';

class ReferEarnScreen extends StatelessWidget {
  const ReferEarnScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    const referralCode = 'TYO-AARAV-2026';

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: 'Refer & Earn'),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
        children: [
          // Hero Illustration Placeholder
          Container(
            height: 200,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [ty.saffron.withOpacity(0.1), ty.saffron.withOpacity(0.02)],
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
              ),
              borderRadius: BorderRadius.circular(24),
            ),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: ty.saffron.withOpacity(0.1),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(Icons.card_giftcard_rounded, size: 64, color: ty.saffron),
                ),
                const SizedBox(height: 16),
                Text('Share the joy, earn rewards!', 
                    style: TyType.display(20, color: ty.ink)),
              ],
            ),
          ),
          const SizedBox(height: 32),
          
          Text('HOW IT WORKS', style: TyType.eyebrow(11, color: ty.ink3)),
          const SizedBox(height: 16),
          _step(context, 1, 'Share your code', 'Invite your friends to Tyohaar using your unique referral code.'),
          _step(context, 2, 'They book a package', 'They get ₹500 off on their first celebration package booking.'),
          _step(context, 3, 'You earn rewards', 'You earn ₹1,000 in your wallet for every successful booking.'),
          
          const SizedBox(height: 32),
          
          Text('YOUR REFERRAL CODE', style: TyType.eyebrow(11, color: ty.ink3)),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: ty.surface,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: ty.line, width: 1.5),
            ),
            child: Row(
              children: [
                Text(referralCode, style: TyType.display(20, color: ty.ink)),
                const Spacer(),
                TyButton('Copy', kind: TyButtonKind.ghost, padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8), onTap: () {
                  Clipboard.setData(const ClipboardData(text: referralCode));
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Code copied to clipboard!')),
                  );
                }),
              ],
            ),
          ),
          
          const SizedBox(height: 24),
          
          Row(
            children: [
              _stat(context, '₹2,000', 'Total Earned', ty.leaf),
              const SizedBox(width: 12),
              _stat(context, '2', 'Referrals', ty.saffron),
            ],
          ),
          
          const SizedBox(height: 40),
          
          TyButton('Share with Friends', full: true, leadingIcon: Icons.share_rounded, onTap: () {}),
        ],
      ),
    );
  }

  Widget _step(BuildContext context, int n, String title, String sub) {
    final ty = context.ty;
    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 28,
            height: 28,
            alignment: Alignment.center,
            decoration: BoxDecoration(color: ty.saffronDeep, shape: BoxShape.circle),
            child: Text('$n', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13)),
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

  Widget _stat(BuildContext context, String value, String label, Color color) {
    final ty = context.ty;
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 20),
        decoration: BoxDecoration(
          color: ty.surface,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: ty.line),
        ),
        child: Column(
          children: [
            Text(value, style: TyType.display(24, color: color)),
            const SizedBox(height: 4),
            Text(label, style: TyType.sans(12, color: ty.ink3, weight: FontWeight.w600)),
          ],
        ),
      ),
    );
  }
}
