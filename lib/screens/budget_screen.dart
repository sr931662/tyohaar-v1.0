import 'package:flutter/material.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/sample_data.dart';
import '../data/models.dart';
import '../widgets/common.dart';

/// Budget — paid / booked / free at a glance, then category by category.
class BudgetScreen extends StatelessWidget {
  const BudgetScreen({super.key});

  String _inr(int n) {
    final s = n.toString();
    final buf = StringBuffer();
    int count = 0;
    for (int i = s.length - 1; i >= 0; i--) {
      buf.write(s[i]);
      count++;
      // Indian grouping: first 3, then 2s
      final remaining = i;
      if (remaining > 0) {
        if (count == 3 && s.length > 3) buf.write(',');
        else if (count > 3 && (count - 3) % 2 == 0) buf.write(',');
      }
    }
    return '₹${buf.toString().split('').reversed.join()}';
  }

  String _short(int n) => n >= 100000
      ? '₹${(n / 100000).toStringAsFixed(n % 100000 == 0 ? 1 : 2)}L'
      : _inr(n);

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final allocated = TyData.budget.fold<int>(0, (s, l) => s + l.est);
    final paid = TyData.budget.fold<int>(0, (s, l) => s + l.paid);
    const total = TyData.budgetTotal;
    final pct = (allocated / total * 100).round();

    return Scaffold(
      appBar: tyAppBar(context, title: 'Budget', actions: const [
        Padding(padding: EdgeInsets.only(right: 16), child: ChromeIconButton(icon: Icons.add_rounded)),
      ]),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(18, 4, 18, 28),
        children: [
          // headline
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
                      Expanded(flex: paid, child: Container(height: 10, color: ty.leaf)),
                      Expanded(
                          flex: allocated - paid,
                          child: Container(height: 10, color: ty.saffron)),
                      Expanded(
                          flex: total - allocated,
                          child: Container(height: 10, color: ty.surface2)),
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
          ...TyData.budget.map((l) {
            final p = (l.paid / l.est * 100).round();
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
                            Text(l.cat,
                                style: TyType.sans(14.5, color: ty.ink, weight: FontWeight.w700)),
                            Text(l.paid > 0 ? '${_short(l.paid)} paid' : 'Not paid yet',
                                style: TyType.sans(11.5, color: ty.ink3)),
                          ],
                        ),
                      ),
                      Text(_short(l.est),
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
