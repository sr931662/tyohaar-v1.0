import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/services/common_service.dart';
import '../widgets/ty_button.dart';
import '../widgets/common.dart';
import 'feedback_screen.dart';
import 'raise_ticket_screen.dart';

class HelpScreen extends StatefulWidget {
  const HelpScreen({super.key});

  @override
  State<HelpScreen> createState() => _HelpScreenState();
}

class _HelpScreenState extends State<HelpScreen> {
  List<FaqItem> _faqs = [];
  List<FaqItem> _filtered = [];
  bool _isLoading = true;
  bool _error = false;
  final TextEditingController _searchCtrl = TextEditingController();
  int? _expandedIndex;

  @override
  void initState() {
    super.initState();
    _loadFaqs();
    _searchCtrl.addListener(_onSearch);
  }

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadFaqs() async {
    setState(() { _isLoading = true; _error = false; });
    try {
      final faqs = await context.read<CommonService>().listFaqs();
      if (mounted) {
        setState(() {
          _faqs = faqs;
          _filtered = faqs;
          _isLoading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() { _isLoading = false; _error = true; });
    }
  }

  void _onSearch() {
    final q = _searchCtrl.text.toLowerCase();
    setState(() {
      _filtered = q.isEmpty
          ? _faqs
          : _faqs.where((f) => f.question.toLowerCase().contains(q) || f.answer.toLowerCase().contains(q)).toList();
      _expandedIndex = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: 'Help & Support'),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
        children: [
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
                    controller: _searchCtrl,
                    decoration: InputDecoration(
                      hintText: 'Search help topics...',
                      hintStyle: TyType.sans(14, color: ty.ink3),
                      border: InputBorder.none,
                      isDense: true,
                    ),
                  ),
                ),
                if (_searchCtrl.text.isNotEmpty)
                  GestureDetector(
                    onTap: () { _searchCtrl.clear(); },
                    child: Icon(Icons.close_rounded, color: ty.ink3, size: 18),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 32),

          if (_isLoading) ...[
            const Center(child: CircularProgressIndicator()),
          ] else ...[
            if (_error) ...[
              Container(
                padding: const EdgeInsets.all(16),
                margin: const EdgeInsets.only(bottom: 20),
                decoration: BoxDecoration(
                  color: Colors.red.withOpacity(0.06),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: Colors.red.withOpacity(0.2)),
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: Text('Could not load FAQs. Please try again.',
                          style: TyType.sans(13.5, color: ty.ink2)),
                    ),
                    TextButton(onPressed: _loadFaqs, child: const Text('Retry')),
                  ],
                ),
              ),
            ],
            if (_filtered.isEmpty && _searchCtrl.text.isEmpty) ...[
              Text('POPULAR TOPICS', style: TyType.eyebrow(11, color: ty.ink3)),
              const SizedBox(height: 16),
              _topicCard(context, Icons.celebration_outlined, 'Planning your first event'),
              _topicCard(context, Icons.card_membership_rounded, 'Membership benefits'),
              _topicCard(context, Icons.account_balance_wallet_outlined, 'Payments & Refunds'),
              _topicCard(context, Icons.security_rounded, 'Privacy & Safety'),
              const SizedBox(height: 32),
            ],

            if (_filtered.isNotEmpty) ...[
              Text('FAQs', style: TyType.eyebrow(11, color: ty.ink3)),
              const SizedBox(height: 12),
              ..._filtered.asMap().entries.map((entry) {
                final i = entry.key;
                final faq = entry.value;
                final expanded = _expandedIndex == i;
                return GestureDetector(
                  onTap: () => setState(() => _expandedIndex = expanded ? null : i),
                  child: Container(
                    decoration: BoxDecoration(
                      border: Border(bottom: BorderSide(color: ty.line2)),
                    ),
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(child: Text(faq.question, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w500))),
                            Icon(expanded ? Icons.remove_rounded : Icons.add_rounded, color: ty.ink3, size: 20),
                          ],
                        ),
                        if (expanded) ...[
                          const SizedBox(height: 10),
                          Text(faq.answer, style: TyType.sans(13.5, color: ty.ink2, height: 1.6)),
                        ],
                      ],
                    ),
                  ),
                );
              }),
            ] else if (_searchCtrl.text.isNotEmpty) ...[
              Center(
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 32),
                  child: Text('No results for "${_searchCtrl.text}"', style: TyType.sans(14, color: ty.ink3)),
                ),
              ),
            ],
          ],

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
                TyButton('Share Feedback', kind: TyButtonKind.ghost, full: true, leadingIcon: Icons.rate_review_outlined, onTap: () {
                  Navigator.of(context).push(MaterialPageRoute(builder: (_) => const FeedbackScreen()));
                }),
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
}
