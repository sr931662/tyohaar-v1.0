import 'package:flutter/material.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../widgets/ty_button.dart';
import '../widgets/common.dart';
import 'raise_ticket_screen.dart';

class HelpScreen extends StatelessWidget {
  const HelpScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: 'Help & Support'),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
        children: [
          // Search Bar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            decoration: BoxDecoration(
              color: ty.surface2,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: ty.line),
            ),
            child: Row(
              children: [
                Icon(Icons.search_rounded, color: ty.ink3, size: 20),
                const SizedBox(width: 12),
                Expanded(
                  child: TextField(
                    decoration: InputDecoration(
                      hintText: 'Search help topics...',
                      hintStyle: TyType.sans(14, color: ty.ink3),
                      border: InputBorder.none,
                      isDense: true,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 32),

          Text('POPULAR TOPICS', style: TyType.eyebrow(11, color: ty.ink3)),
          const SizedBox(height: 16),
          _topicCard(context, Icons.celebration_outlined, 'Planning your first event'),
          _topicCard(context, Icons.card_membership_rounded, 'Membership benefits'),
          _topicCard(context, Icons.account_balance_wallet_outlined, 'Payments & Refunds'),
          _topicCard(context, Icons.security_rounded, 'Privacy & Safety'),

          const SizedBox(height: 32),
          Text('FAQs', style: TyType.eyebrow(11, color: ty.ink3)),
          const SizedBox(height: 12),
          _faqItem(context, 'How do I change my event date?'),
          _faqItem(context, 'What is included in the Premium package?'),
          _faqItem(context, 'Can I add more guests after booking?'),
          _faqItem(context, 'How do I refer a friend?'),

          const SizedBox(height: 40),
          Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: ty.saffronSoft.withOpacity(0.4),
              borderRadius: BorderRadius.circular(24),
              border: Border.all(color: ty.saffron.withOpacity(0.1)),
            ),
            child: Column(
              children: [
                Text('Still need help?', style: TyType.display(20, color: ty.ink)),
                const SizedBox(height: 8),
                Text('Our support team is available 24/7 to assist you.', 
                    textAlign: TextAlign.center,
                    style: TyType.sans(14, color: ty.ink2)),
                const SizedBox(height: 24),
                TyButton('Raise a Ticket', full: true, onTap: () {
                  Navigator.of(context).push(MaterialPageRoute(builder: (_) => const RaiseTicketScreen()));
                }),
                const SizedBox(height: 12),
                TyButton('Chat with us', kind: TyButtonKind.ghost, full: true, leadingIcon: Icons.chat_bubble_outline_rounded, onTap: () {}),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _topicCard(BuildContext context, IconData icon, String label) {
    final ty = context.ty;
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: ty.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: ty.line),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(color: ty.saffron.withOpacity(0.1), borderRadius: BorderRadius.circular(12)),
            child: Icon(icon, color: ty.saffron, size: 20),
          ),
          const SizedBox(width: 16),
          Expanded(child: Text(label, style: TyType.sans(15, color: ty.ink, weight: FontWeight.w600))),
          Icon(Icons.chevron_right_rounded, color: ty.ink3, size: 20),
        ],
      ),
    );
  }

  Widget _faqItem(BuildContext context, String question) {
    final ty = context.ty;
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 16),
      decoration: BoxDecoration(border: Border(bottom: BorderSide(color: ty.line2))),
      child: Row(
        children: [
          Expanded(child: Text(question, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w500))),
          Icon(Icons.add_rounded, color: ty.ink3, size: 20),
        ],
      ),
    );
  }
}
