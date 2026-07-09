import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
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
  bool _isYearly = false;
  bool _isBusy = false;

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
          _plans = (results[0] as List<MembershipPlan>)
            ..sort((a, b) => a.displayOrder.compareTo(b.displayOrder));
          _active = results[1] as ActiveMembership?;
          _loading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() { _error = 'Could not load membership plans.'; _loading = false; });
    }
  }

  MembershipPlan? get _activePlan {
    if (_active == null) return null;
    for (final p in _plans) {
      if (p.id == _active!.planId) return p;
    }
    return null;
  }

  double _priceFor(MembershipPlan plan) => _isYearly ? plan.yearlyPrice : plan.monthlyPrice;

  Future<void> _subscribe(MembershipPlan plan) async {
    if (_priceFor(plan) > 0) {
      _showPaymentRequiredNotice();
      return;
    }
    setState(() => _isBusy = true);
    try {
      await context.read<MembershipService>().subscribe(
        planId: plan.id,
        billingCycle: _isYearly ? 'annual' : 'monthly',
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Membership activated!')),
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
      if (mounted) setState(() => _isBusy = false);
    }
  }

  void _showPaymentRequiredNotice() {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Paid plan checkout is coming soon — contact support to subscribe for now.')),
    );
  }

  Future<void> _renew() async {
    final active = _active;
    final plan = _activePlan;
    if (active == null) return;
    if (plan != null && _priceFor(plan) > 0) {
      _showPaymentRequiredNotice();
      return;
    }
    setState(() => _isBusy = true);
    try {
      await context.read<MembershipService>().renewMembership(active.id);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Membership renewed.')));
        await _load();
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Could not renew. Please try again.')));
      }
    } finally {
      if (mounted) setState(() => _isBusy = false);
    }
  }

  Future<void> _changeTier({required bool isUpgrade}) async {
    final active = _active;
    final currentPlan = _activePlan;
    if (active == null || currentPlan == null) return;
    final targetTier = isUpgrade ? currentPlan.canUpgradeToTier : currentPlan.canDowngradeToTier;
    if (targetTier == null) return;
    MembershipPlan? targetPlan;
    for (final p in _plans) {
      if (p.tier == targetTier) { targetPlan = p; break; }
    }
    if (targetPlan == null) return;

    if (isUpgrade && _priceFor(targetPlan) > 0) {
      _showPaymentRequiredNotice();
      return;
    }

    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(isUpgrade ? 'Upgrade to ${targetPlan!.name}?' : 'Downgrade to ${targetPlan!.name}?'),
        content: const Text('This takes effect immediately and starts a fresh billing period on the new plan.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Confirm')),
        ],
      ),
    );
    if (confirm != true || !mounted) return;

    setState(() => _isBusy = true);
    try {
      final svc = context.read<MembershipService>();
      if (isUpgrade) {
        await svc.upgrade(active.id, targetPlan.id);
      } else {
        await svc.downgrade(active.id, targetPlan.id);
      }
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(isUpgrade ? 'Upgraded to ${targetPlan.name}.' : 'Downgraded to ${targetPlan.name}.')),
        );
        await _load();
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Could not change plan. Please try again.')));
      }
    } finally {
      if (mounted) setState(() => _isBusy = false);
    }
  }

  Future<void> _cancel() async {
    final id = _active?.id;
    if (id == null) return;
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Cancel membership?'),
        content: const Text('Your membership benefits will end immediately.'),
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
    setState(() => _isBusy = true);
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
    } finally {
      if (mounted) setState(() => _isBusy = false);
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
                    const SizedBox(height: 20),
                    _buildBillingToggle(ty),
                    if (_plans.isNotEmpty) ...[
                      const SizedBox(height: 20),
                      Text('ALL PLANS', style: TyType.eyebrow(11, color: ty.ink3)),
                      const SizedBox(height: 16),
                      ..._plans.map((p) => _buildPlanCard(p, ty)),
                    ],
                  ],
                ),
    );
  }

  Widget _buildBillingToggle(TyColors ty) {
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(color: ty.surface2, borderRadius: BorderRadius.circular(14)),
      child: Row(
        children: [
          Expanded(child: _toggleTab(ty, 'Monthly', !_isYearly, () => setState(() => _isYearly = false))),
          Expanded(child: _toggleTab(ty, 'Yearly', _isYearly, () => setState(() => _isYearly = true))),
        ],
      ),
    );
  }

  Widget _toggleTab(TyColors ty, String label, bool selected, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: BoxDecoration(
          color: selected ? ty.saffron : Colors.transparent,
          borderRadius: BorderRadius.circular(11),
        ),
        alignment: Alignment.center,
        child: Text(label, style: TyType.sans(13.5, color: selected ? ty.onPrimary : ty.ink2, weight: FontWeight.w700)),
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
    final plan = _activePlan;
    final planLabel = plan?.name ?? (a.tier?.toUpperCase() ?? 'Member');
    final inGrace = a.isInGracePeriod;

    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: inGrace ? [ty.rose, ty.rose.withOpacity(0.75)] : [ty.saffron, ty.saffronDeep],
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
              Text(planLabel.toUpperCase(), style: TyType.display(22, color: Colors.white)),
              const Icon(Icons.stars_rounded, color: Colors.white, size: 32),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            a.expiresAt != null ? 'Valid till ${_formatDate(a.expiresAt!)}' : 'No expiry',
            style: TyType.sans(14, color: Colors.white.withOpacity(0.9)),
          ),
          if (inGrace && a.gracePeriodUntil != null) ...[
            const SizedBox(height: 6),
            Text(
              'Your membership has lapsed. Renew by ${_formatDate(a.gracePeriodUntil!)} to keep your benefits.',
              style: TyType.sans(12.5, color: Colors.white.withOpacity(0.95), height: 1.4),
            ),
          ],
          const SizedBox(height: 20),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  a.status.replaceAll('_', ' ').toUpperCase(),
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12),
                ),
              ),
              if (inGrace)
                TextButton(
                  onPressed: _isBusy ? null : _renew,
                  style: TextButton.styleFrom(backgroundColor: Colors.white.withOpacity(0.15)),
                  child: Text('Renew Now', style: TyType.sans(13, color: Colors.white, weight: FontWeight.w700)),
                ),
              if (plan?.canUpgradeToTier != null)
                TextButton(
                  onPressed: _isBusy ? null : () => _changeTier(isUpgrade: true),
                  child: Text('Upgrade', style: TyType.sans(13, color: Colors.white.withOpacity(0.9))),
                ),
              if (plan?.canDowngradeToTier != null)
                TextButton(
                  onPressed: _isBusy ? null : () => _changeTier(isUpgrade: false),
                  child: Text('Downgrade', style: TyType.sans(13, color: Colors.white.withOpacity(0.9))),
                ),
              TextButton(
                onPressed: _isBusy ? null : _cancel,
                child: Text('Cancel', style: TyType.sans(13, color: Colors.white.withOpacity(0.8))),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildPlanCard(MembershipPlan plan, TyColors ty) {
    final isCurrentPlan = _active != null && _active!.isActive && _active!.planId == plan.id;
    final price = _priceFor(plan);
    final badges = <String>[
      if (plan.discountPercentage > 0) '${plan.discountPercentage.toStringAsFixed(0)}% off packages',
      if (plan.cashbackPercentage > 0) '${plan.cashbackPercentage.toStringAsFixed(0)}% cashback',
      if (plan.walletBonus > 0) '₹${plan.walletBonus.toStringAsFixed(0)} welcome bonus',
      if (plan.freeInvitationsCount > 0) '${plan.freeInvitationsCount} free invitations',
      if (plan.priorityBooking) 'Priority booking',
      if (plan.hasExclusivePackages) 'Exclusive packages',
      if (plan.cancellationProtection) 'Free cancellation',
    ];

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
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(plan.name, style: TyType.display(18, color: ty.ink)),
                    if (plan.tagline != null && plan.tagline!.isNotEmpty)
                      Text(plan.tagline!, style: TyType.sans(12, color: ty.ink3)),
                  ],
                ),
              ),
              Text(
                price == 0 ? 'Free' : '₹${price.toStringAsFixed(0)}/${_isYearly ? 'yr' : 'mo'}',
                style: TyType.sans(16, color: ty.saffron, weight: FontWeight.w700),
              ),
            ],
          ),
          if (plan.description.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(plan.description, style: TyType.sans(13, color: ty.ink2)),
          ],
          if (badges.isNotEmpty) ...[
            const SizedBox(height: 12),
            ...badges.map((b) => Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                children: [
                  Icon(Icons.check_rounded, size: 14, color: ty.saffronDeep),
                  const SizedBox(width: 8),
                  Expanded(child: Text(b, style: TyType.sans(13, color: ty.ink2))),
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
              _isBusy ? 'Please wait...' : (price == 0 ? 'Subscribe' : 'Contact Support'),
              full: true,
              enabled: !_isBusy,
              onTap: () => _subscribe(plan),
            ),
        ],
      ),
    );
  }

  static String _formatDate(DateTime d) => DateFormat('d MMM yyyy').format(d);
}
