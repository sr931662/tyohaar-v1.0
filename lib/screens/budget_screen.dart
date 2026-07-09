import 'package:flutter/material.dart';

import 'package:provider/provider.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../theme/responsive.dart';
import '../data/models.dart';
import '../data/services/celebration_service.dart';
import '../data/services/budget_service.dart' as bs;
import '../widgets/common.dart';
import '../widgets/state_screens.dart';

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
      final celebSvc = context.read<CelebrationService>();
      final budgetSvc = context.read<bs.BudgetService>();

      final celebrations = await celebSvc.listCelebrations();
      if (celebrations.isNotEmpty) {
        final activeCeleb = celebrations.first;
        final budget = await budgetSvc.getBudgetForCelebration(activeCeleb.id);
        
        if (budget != null) {
          final expenses = await budgetSvc.listExpenses(budget.id);
          if (mounted) {
            setState(() {
              _totalBudget = budget.totalPlanned;
              _expenses = expenses;
              _isLoading = false;
            });
          }
        } else {
          if (mounted) {
            setState(() {
              _totalBudget = activeCeleb.estimatedBudget ?? 0;
              _expenses = [];
              _isLoading = false;
            });
          }
        }
      } else {
        if (mounted) setState(() => _isLoading = false);
      }
    } catch (e) {
      debugPrint('Error loading budget: $e');
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
    final resp = context.resp;
    
    if (_isLoading) {
      return Scaffold(backgroundColor: ty.paper, body: const Center(child: CircularProgressIndicator()));
    }

    if (_error != null) {
      return Scaffold(
        backgroundColor: ty.paper,
        appBar: tyAppBar(context, title: 'Budget'),
        body: TyStateScreen.error(onAction: _loadBudgetData),
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
        padding: EdgeInsets.fromLTRB(resp.w(18), resp.h(4), resp.w(18), resp.h(28)),
        children: [
          Container(
            padding: EdgeInsets.all(resp.w(20)),
            decoration: _card(ty, resp),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Total budget',
                    style: TyType.sans(resp.sp(12.5), color: ty.ink2, weight: FontWeight.w600)),
                SizedBox(height: resp.h(2)),
                Text(_inr(total), style: TyType.display(resp.sp(40), color: ty.ink)),
                SizedBox(height: resp.h(16)),
                ClipRRect(
                  borderRadius: BorderRadius.circular(resp.w(6)),
                  child: Row(
                    children: [
                      if (paid > 0) Expanded(flex: paid.toInt(), child: Container(height: resp.h(10), color: ty.leaf)),
                      if (allocated - paid > 0)
                        Expanded(
                            flex: (allocated - paid).toInt(),
                            child: Container(height: resp.h(10), color: ty.saffron)),
                      if (total - allocated > 0)
                        Expanded(
                            flex: (total - allocated).toInt(),
                            child: Container(height: resp.h(10), color: ty.surface2)),
                      if (total == 0) Expanded(child: Container(height: resp.h(10), color: ty.surface2)),
                    ],
                  ),
                ),
                SizedBox(height: resp.h(12)),
                Wrap(
                  spacing: resp.w(16),
                  runSpacing: resp.h(6),
                  children: [
                    _legend(context, ty.leaf, 'Paid ${_short(paid)}'),
                    _legend(context, ty.saffron, 'Booked ${_short(allocated - paid)}'),
                    _legend(context, ty.surface2, 'Free ${_short(total - allocated)}'),
                  ],
                ),
              ],
            ),
          ),
          SizedBox(height: resp.h(18)),
          Row(
            children: [
              _stat(context, 'Allocated', _short(allocated), '$pct% of budget'),
              SizedBox(width: resp.w(10)),
              _stat(context, 'Remaining', _short(total - paid), 'after payments'),
            ],
          ),
          SizedBox(height: resp.h(24)),
          const SectionHeader('By category'),
          if (_expenses.isEmpty)
             Center(child: Padding(
               padding: EdgeInsets.only(top: resp.h(24)),
               child: Text('No expenses added yet', style: TyType.sans(resp.sp(14), color: ty.ink3)),
             ))
          else
            ..._expenses.map((l) {
              final p = (l.isPaid && l.amount > 0) ? 100 : 0;
              final c = ty.tint(l.tint);
              return Container(
                margin: EdgeInsets.only(bottom: resp.h(11)),
                padding: EdgeInsets.all(resp.w(14)),
                decoration: _card(ty, resp),
                child: Column(
                  children: [
                    Row(
                      children: [
                        Container(
                          width: resp.w(36),
                          height: resp.w(36),
                          decoration: BoxDecoration(
                            color: Color.alphaBlend(c.withOpacity(0.16), ty.surface2),
                            borderRadius: BorderRadius.circular(resp.w(11)),
                          ),
                          child: Icon(Icons.sell_outlined, color: c, size: resp.sp(18)),
                        ),
                        SizedBox(width: resp.w(11)),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(l.category,
                                  style: TyType.sans(resp.sp(14.5), color: ty.ink, weight: FontWeight.w700)),
                              Text(l.isPaid ? '${_short(l.amount)} paid' : 'Not paid yet',
                                  style: TyType.sans(resp.sp(11.5), color: ty.ink3)),
                            ],
                          ),
                        ),
                        Text(_short(l.amount),
                            style: TyType.sans(resp.sp(14.5), color: ty.ink, weight: FontWeight.w800)),
                      ],
                    ),
                    SizedBox(height: resp.h(11)),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(resp.w(4)),
                      child: LinearProgressIndicator(
                        value: p / 100,
                        minHeight: resp.h(6),
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

  BoxDecoration _card(TyColors ty, TyResponsive resp) => BoxDecoration(
        color: ty.surface,
        borderRadius: BorderRadius.circular(resp.w(20)),
        border: Border.all(color: ty.line),
      );

  Widget _legend(BuildContext context, Color c, String t) {
    final ty = context.ty;
    final resp = context.resp;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(width: resp.w(9), height: resp.w(9), decoration: BoxDecoration(color: c, shape: BoxShape.circle)),
        SizedBox(width: resp.w(6)),
        Text(t, style: TyType.sans(resp.sp(12), color: ty.ink2)),
      ],
    );
  }

  Widget _stat(BuildContext context, String l, String v, String s) {
    final ty = context.ty;
    final resp = context.resp;
    return Expanded(
      child: Container(
        padding: EdgeInsets.all(resp.w(14)),
        decoration: _card(ty, resp),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(l, style: TyType.sans(resp.sp(11.5), color: ty.ink3, weight: FontWeight.w600)),
            SizedBox(height: resp.h(3)),
            Text(v, style: TyType.display(resp.sp(24), color: ty.ink)),
            SizedBox(height: resp.h(2)),
            Text(s, style: TyType.sans(resp.sp(11), color: ty.ink2)),
          ],
        ),
      ),
    );
  }
}
