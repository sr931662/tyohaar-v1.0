import 'package:flutter/material.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../widgets/common.dart';
import '../widgets/ty_button.dart';

class WalletScreen extends StatelessWidget {
  const WalletScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return Scaffold(
      appBar: tyAppBar(context, title: 'Tyohaar Wallet'),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [ty.saffron, ty.saffronDeep],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(24),
              boxShadow: [
                BoxShadow(
                  color: ty.saffron.withOpacity(0.3),
                  blurRadius: 20,
                  offset: const Offset(0, 10),
                ),
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Available Balance',
                    style: TyType.sans(14, color: Colors.white.withOpacity(0.8))),
                const SizedBox(height: 8),
                Text('₹24,500',
                    style: TyType.display(36, color: Colors.white)),
                const SizedBox(height: 24),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('Tyohaar Credits: 500',
                        style: TyType.sans(13, color: Colors.white, weight: FontWeight.w600)),
                    const Icon(Icons.info_outline, color: Colors.white70, size: 18),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 32),
          SectionHeader('Quick Actions'),
          Row(
            children: [
              _actionButton(context, Icons.add_circle_outline, 'Add Money'),
              const SizedBox(width: 12),
              _actionButton(context, Icons.history, 'History'),
              const SizedBox(width: 12),
              _actionButton(context, Icons.local_offer_outlined, 'Offers'),
            ],
          ),
          const SizedBox(height: 32),
          SectionHeader('Recent Transactions'),
          _transactionItem(context, 'Package Booking', '12 June 2024', '-₹12,000', ty.rose),
          _transactionItem(context, 'Refund Processed', '10 June 2024', '+₹2,500', ty.leaf),
          _transactionItem(context, 'Added to Wallet', '05 June 2024', '+₹5,000', ty.leaf),
          const SizedBox(height: 20),
          TyButton('View All Transactions', kind: TyButtonKind.ghost, full: true, onTap: () {}),
        ],
      ),
    );
  }

  Widget _actionButton(BuildContext context, IconData icon, String label) {
    final ty = context.ty;
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 16),
        decoration: BoxDecoration(
          color: ty.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: ty.line),
        ),
        child: Column(
          children: [
            Icon(icon, color: ty.saffron, size: 24),
            const SizedBox(height: 8),
            Text(label, style: TyType.sans(12, color: ty.ink, weight: FontWeight.w600)),
          ],
        ),
      ),
    );
  }

  Widget _transactionItem(BuildContext context, String title, String date, String amount, Color amountColor) {
    final ty = context.ty;
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: ty.surface,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: ty.line),
      ),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: ty.saffronSoft,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(Icons.payment, color: ty.saffronDeep, size: 20),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
                Text(date, style: TyType.sans(12, color: ty.ink3)),
              ],
            ),
          ),
          Text(amount, style: TyType.sans(15, color: amountColor, weight: FontWeight.w800)),
        ],
      ),
    );
  }
}
