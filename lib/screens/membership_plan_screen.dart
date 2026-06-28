import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shimmer/shimmer.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../widgets/ty_button.dart';
import '../widgets/common.dart';
import '../data/services/membership_service.dart';

class MembershipPlanScreen extends StatefulWidget {
  const MembershipPlanScreen({super.key});

  @override
  State<MembershipPlanScreen> createState() => _MembershipPlanScreenState();
}

class _MembershipPlanScreenState extends State<MembershipPlanScreen> {
  List<MembershipPlan> _plans = [];
  ActiveMembership? _active;
  bool _loading = true;
  String? _error;
  String? _subscribing;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final svc = context.read<MembershipService>();
      final results = await Future.wait([
        svc.listPlans(),
        svc.getActiveMembership(),
      ]);
      if (mounted) {
        setState(() {
          _plans = results[0] as List<MembershipPlan>;
          _active = results[1] as ActiveMembership?;
          _loading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() { _error = 'Could not load membership plans.'; _loading = false; });
    }
  }

  Future<void> _subscribe(String planId) async {
    setState(() => _subscribing = planId);
    try {
      await context.read<MembershipService>().subscribe(planId);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Membership subscribed successfully!')),
        );
        await _load();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not subscribe. Please try again.')),
        );
      }
    } finally {
      if (mounted) setState(() => _subscribing = null);
    }
  }

  Future<void> _cancel() async {
    final id = _active?.id;
    if (id == null) return;
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Cancel membership?'),
        content: const Text('Your membership benefits will end at the current billing period.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Keep')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Cancel', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
    if (confirm != true || !mounted) return;
    try {
      await context.read<MembershipService>().cancelMembership(id);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Membership cancelled.')),
        );
        await _load();
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not cancel. Please try again.')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: 'Membership Plans'),
      body: _loading
          ? _buildSkeleton(ty)
          : _error != null
              ? _buildError(ty)
              : ListView(
                  padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
                  children: [
                    if (_active != null) _buildActiveCard(ty),
                    if (_plans.isNotEmpty) ...[
                      const SizedBox(height: 24),
                      Text('ALL PLANS', style: TyType.eyebrow(11, color: ty.ink3)),
                      const SizedBox(height: 16),
                      ..._plans.map((p) => _buildPlanCard(p, ty)),
                    ],
                  ],
                ),
    );
  }

  Widget _buildSkeleton(TyColors ty) {
    return Shimmer.fromColors(
      baseColor: ty.line,
      highlightColor: ty.surface2,
      child: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Container(height: 160, decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(24))),
          const SizedBox(height: 20),
          Container(height: 120, decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(20))),
          const SizedBox(height: 12),
          Container(height: 120, decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(20))),
        ],
      ),
    );
  }

  Widget _buildError(TyColors ty) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.error_outline_rounded, size: 48, color: ty.rose),
          const SizedBox(height: 12),
          Text(_error!, style: TyType.sans(14, color: ty.ink2)),
          const SizedBox(height: 16),
          TextButton(onPressed: _load, child: Text('Try Again', style: TyType.sans(14, color: ty.saffron, weight: FontWeight.w700))),
        ],
      ),
    );
  }

  Widget _buildActiveCard(TyColors ty) {
    final a = _active!;
    final expiry = a.expiresAt;
    final expiryStr = expiry != null
        ? '${expiry.day} ${_month(expiry.month)} ${expiry.year}'
        : 'Active';
    final isActive = a.status == 'active';

    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [ty.saffron, ty.saffronDeep],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(color: ty.saffron.withOpacity(0.3), blurRadius: 15, offset: const Offset(0, 8)),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(a.planName.toUpperCase(), style: TyType.display(24, color: Colors.white)),
              const Icon(Icons.stars_rounded, color: Colors.white, size: 32),
            ],
          ),
          const SizedBox(height: 8),
          Text(expiry != null ? 'Valid till $expiryStr' : 'No expiry',
              style: TyType.sans(14, color: Colors.white.withOpacity(0.9))),
          const SizedBox(height: 24),
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  isActive ? 'ACTIVE' : a.status.toUpperCase(),
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12),
                ),
              ),
              const Spacer(),
              if (isActive)
                TextButton(
                  onPressed: _cancel,
                  child: Text('Cancel', style: TyType.sans(13, color: Colors.white.withOpacity(0.8))),
                ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildPlanCard(MembershipPlan plan, TyColors ty) {
    final isCurrentPlan = _active?.planId == plan.id;
    final isSubscribing = _subscribing == plan.id;

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: ty.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: isCurrentPlan ? ty.saffron : ty.line,
          width: isCurrentPlan ? 2 : 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(plan.name, style: TyType.display(18, color: ty.ink)),
              Text(
                '₹${plan.price.toStringAsFixed(0)}/${plan.billingCycle == 'monthly' ? 'mo' : 'yr'}',
                style: TyType.sans(16, color: ty.saffron, weight: FontWeight.w700),
              ),
            ],
          ),
          if (plan.description.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(plan.description, style: TyType.sans(13, color: ty.ink2)),
          ],
          if (plan.features.isNotEmpty) ...[
            const SizedBox(height: 12),
            ...plan.features.map((f) => Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                children: [
                  Icon(Icons.check_rounded, size: 14, color: ty.saffronDeep),
                  const SizedBox(width: 8),
                  Expanded(child: Text(f, style: TyType.sans(13, color: ty.ink2))),
                ],
              ),
            )),
          ],
          const SizedBox(height: 16),
          if (isCurrentPlan)
            Container(
              alignment: Alignment.center,
              padding: const EdgeInsets.symmetric(vertical: 10),
              decoration: BoxDecoration(
                color: ty.saffronSoft,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text('Current Plan', style: TyType.sans(13, color: ty.saffronDeep, weight: FontWeight.w700)),
            )
          else
            TyButton(
              isSubscribing ? 'Subscribing...' : 'Subscribe',
              full: true,
              enabled: !isSubscribing,
              onTap: () => _subscribe(plan.id),
            ),
        ],
      ),
    );
  }

  static String _month(int m) {
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return months[m - 1];
  }
}
