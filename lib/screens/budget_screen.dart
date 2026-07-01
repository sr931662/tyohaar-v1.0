import 'package:flutter/material.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/models.dart';
import '../data/services/celebration_service.dart';
import '../widgets/common.dart';

class BudgetScreen extends StatefulWidget {
  const BudgetScreen({super.key});

  @override
  State<BudgetScreen> createState() => _BudgetScreenState();
}

class _BudgetScreenState extends State<BudgetScreen> {
  final CelebrationService _celebrationService = CelebrationService();
  double _totalBudget = 0;
  List<BudgetExpense> _expenses = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadBudgetData();
  }

  Future<void> _loadBudgetData() async {
    setState(() { _isLoading = true; _error = null; });
    try {
      final celebrations = await _celebrationService.listCelebrations();
      if (celebrations.isNotEmpty) {
        final details = await _celebrationService.getCelebrationDetails(celebrations.first['id']);
        final budget = details['budget'];
        if (mounted) {
          setState(() {
            _totalBudget = (budget?['total_amount'] ?? 0).toDouble();
            _expenses = (budget?['expenses'] as List?)?.map((e) => BudgetExpense.fromJson(e)).toList() ?? [];
            _isLoading = false;
          });
        }
      } else {
        if (mounted) setState(() => _isLoading = false);
      }
    } catch (e) {
      if (mounted) setState(() { _error = 'Could not load budget data.'; _isLoading = false; });
    }
  }

  String _inr(double n) {
    final s = n.toInt().toString();
    final buf = StringBuffer();
    int count = 0;
    for (int i = s.length - 1; i >= 0; i--) {
      buf.write(s[i]);
      count++;
      if (count == 3 && s.length > 3) buf.write(',');
      else if (count > 3 && (count - 3) % 2 == 0 && i > 0) buf.write(',');
    }
    return '₹${buf.toString().split('').reversed.join()}';
  }

  String _short(double n) => n >= 100000
      ? '₹${(n / 100000).toStringAsFixed(1)}L'
      : _inr(n);

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    
    if (_isLoading) {
      return Scaffold(backgroundColor: ty.paper, body: const Center(child: CircularProgressIndicator()));
    }

    if (_error != null) {
      return Scaffold(
        backgroundColor: ty.paper,
        appBar: tyAppBar(context, title: 'Budget'),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.error_outline_rounded, size: 48, color: ty.rose),
              const SizedBox(height: 12),
              Text(_error!, style: TyType.sans(14, color: ty.ink2)),
              const SizedBox(height: 16),
              TextButton(
                onPressed: _loadBudgetData,
                child: Text('Try Again', style: TyType.sans(14, color: ty.saffron, weight: FontWeight.w700)),
              ),
            ],
          ),
        ),
      );
    }

    final allocated = _expenses.fold<double>(0, (s, l) => s + l.amount);
    final paid = _expenses.fold<double>(0, (s, l) => s + (l.isPaid ? l.amount : 0.0));
    final total = _totalBudget;
    final pct = total > 0 ? (allocated / total * 100).round() : 0;

    return Scaffold(
      appBar: tyAppBar(context, title: 'Budget', actions: const [
        Padding(padding: EdgeInsets.only(right: 16), child: ChromeIconButton(icon: Icons.add_rounded)),
      ]),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(18, 4, 18, 28),
        children: [
          Container(
            padding: const EdgeInsets.all(20),
            decoration: _card(ty),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Total budget',
                    style: TyType.sans(12.5, color: ty.ink2, weight: FontWeight.w600)),
                const SizedBox(height: 2),
                Text(_inr(total), style: TyType.display(40, color: ty.ink)),
                const SizedBox(height: 16),
                ClipRRect(
                  borderRadius: BorderRadius.circular(6),
                  child: Row(
                    children: [
                      if (paid > 0) Expanded(flex: paid.toInt(), child: Container(height: 10, color: ty.leaf)),
                      if (allocated - paid > 0)
                        Expanded(
                            flex: (allocated - paid).toInt(),
                            child: Container(height: 10, color: ty.saffron)),
                      if (total - allocated > 0)
                        Expanded(
                            flex: (total - allocated).toInt(),
                            child: Container(height: 10, color: ty.surface2)),
                      if (total == 0) Expanded(child: Container(height: 10, color: ty.surface2)),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 16,
                  runSpacing: 6,
                  children: [
                    _legend(context, ty.leaf, 'Paid ${_short(paid)}'),
                    _legend(context, ty.saffron, 'Booked ${_short(allocated - paid)}'),
                    _legend(context, ty.surface2, 'Free ${_short(total - allocated)}'),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),
          Row(
            children: [
              _stat(context, 'Allocated', _short(allocated), '$pct% of budget'),
              const SizedBox(width: 10),
              _stat(context, 'Remaining', _short(total - paid), 'after payments'),
            ],
          ),
          const SizedBox(height: 24),
          const SectionHeader('By category'),
          if (_expenses.isEmpty)
             Center(child: Padding(
               padding: const EdgeInsets.only(top: 24),
               child: Text('No expenses added yet', style: TyType.sans(14, color: ty.ink3)),
             ))
          else
            ..._expenses.map((l) {
              final p = (l.isPaid && l.amount > 0) ? 100 : 0;
              final c = ty.tint(l.tint);
              return Container(
                margin: const EdgeInsets.only(bottom: 11),
                padding: const EdgeInsets.all(14),
                decoration: _card(ty),
                child: Column(
                  children: [
                    Row(
                      children: [
                        Container(
                          width: 36,
                          height: 36,
                          decoration: BoxDecoration(
                            color: Color.alphaBlend(c.withOpacity(0.16), ty.surface2),
                            borderRadius: BorderRadius.circular(11),
                          ),
                          child: Icon(Icons.sell_outlined, color: c, size: 18),
                        ),
                        const SizedBox(width: 11),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(l.category,
                                  style: TyType.sans(14.5, color: ty.ink, weight: FontWeight.w700)),
                              Text(l.isPaid ? '${_short(l.amount)} paid' : 'Not paid yet',
                                  style: TyType.sans(11.5, color: ty.ink3)),
                            ],
                          ),
                        ),
                        Text(_short(l.amount),
                            style: TyType.sans(14.5, color: ty.ink, weight: FontWeight.w800)),
                      ],
                    ),
                    const SizedBox(height: 11),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(4),
                      child: LinearProgressIndicator(
                        value: p / 100,
                        minHeight: 6,
                        backgroundColor: ty.surface2,
                        color: c,
                      ),
                    ),
                  ],
                ),
              );
            }),
        ],
      ),
    );
  }

  BoxDecoration _card(TyColors ty) => BoxDecoration(
        color: ty.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: ty.line),
      );

  Widget _legend(BuildContext context, Color c, String t) {
    final ty = context.ty;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(width: 9, height: 9, decoration: BoxDecoration(color: c, shape: BoxShape.circle)),
        const SizedBox(width: 6),
        Text(t, style: TyType.sans(12, color: ty.ink2)),
      ],
    );
  }

  Widget _stat(BuildContext context, String l, String v, String s) {
    final ty = context.ty;
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: _card(ty),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(l, style: TyType.sans(11.5, color: ty.ink3, weight: FontWeight.w600)),
            const SizedBox(height: 3),
            Text(v, style: TyType.display(24, color: ty.ink)),
            const SizedBox(height: 2),
            Text(s, style: TyType.sans(11, color: ty.ink2)),
          ],
        ),
      ),
    );
  }
}
