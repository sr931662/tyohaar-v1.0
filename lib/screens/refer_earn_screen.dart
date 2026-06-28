import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:shimmer/shimmer.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../widgets/ty_button.dart';
import '../widgets/common.dart';
import '../data/services/referral_service.dart';

class ReferEarnScreen extends StatefulWidget {
  const ReferEarnScreen({super.key});

  @override
  State<ReferEarnScreen> createState() => _ReferEarnScreenState();
}

class _ReferEarnScreenState extends State<ReferEarnScreen> {
  ReferralCode? _code;
  ReferralStats? _stats;
  bool _loading = true;
  String? _error;

  final _applyCtrl = TextEditingController();
  bool _applying = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _applyCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final svc = context.read<ReferralService>();
      final results = await Future.wait([svc.getReferralCode(), svc.getReferralStats()]);
      if (mounted) {
        setState(() {
          _code = results[0] as ReferralCode;
          _stats = results[1] as ReferralStats;
          _loading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() { _error = 'Could not load referral data.'; _loading = false; });
    }
  }

  Future<void> _applyCode() async {
    final code = _applyCtrl.text.trim();
    if (code.isEmpty) return;
    setState(() => _applying = true);
    try {
      await context.read<ReferralService>().applyReferralCode(code);
      if (mounted) {
        _applyCtrl.clear();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Referral code applied successfully!')),
        );
        _load();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Invalid or already used referral code.')),
        );
      }
    } finally {
      if (mounted) setState(() => _applying = false);
    }
  }

  void _copyCode() {
    final code = _code?.code ?? '';
    Clipboard.setData(ClipboardData(text: code));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Referral code copied!')),
    );
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: 'Refer & Earn'),
      body: _loading
          ? _buildSkeleton(ty)
          : _error != null
              ? _buildError(ty)
              : ListView(
                  padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
                  children: [
                    _buildHero(ty),
                    const SizedBox(height: 32),
                    Text('HOW IT WORKS', style: TyType.eyebrow(11, color: ty.ink3)),
                    const SizedBox(height: 16),
                    _step(context, 1, 'Share your code', 'Invite friends to Tyohaar using your unique referral code.'),
                    _step(context, 2, 'They book a package', 'They get a discount on their first celebration booking.'),
                    _step(context, 3, 'You earn rewards', 'Earn wallet credits for every successful referral.'),
                    const SizedBox(height: 32),
                    Text('YOUR REFERRAL CODE', style: TyType.eyebrow(11, color: ty.ink3)),
                    const SizedBox(height: 12),
                    _buildCodeCard(ty),
                    const SizedBox(height: 24),
                    _buildStats(ty),
                    const SizedBox(height: 32),
                    Text('APPLY A CODE', style: TyType.eyebrow(11, color: ty.ink3)),
                    const SizedBox(height: 12),
                    _buildApplyField(ty),
                    const SizedBox(height: 40),
                    TyButton(
                      'Share with Friends',
                      full: true,
                      leadingIcon: Icons.share_rounded,
                      onTap: () {
                        final code = _code?.code ?? '';
                        if (code.isNotEmpty) {
                          Clipboard.setData(ClipboardData(text: 'Join Tyohaar using my code $code'));
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('Share text copied to clipboard!')),
                          );
                        }
                      },
                    ),
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
          Container(height: 200, decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(24))),
          const SizedBox(height: 20),
          Container(height: 64, decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(20))),
          const SizedBox(height: 12),
          Container(height: 80, decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(20))),
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

  Widget _buildHero(TyColors ty) {
    return Container(
      height: 180,
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
            decoration: BoxDecoration(color: ty.saffron.withOpacity(0.1), shape: BoxShape.circle),
            child: Icon(Icons.card_giftcard_rounded, size: 56, color: ty.saffron),
          ),
          const SizedBox(height: 16),
          Text('Share the joy, earn rewards!', style: TyType.display(20, color: ty.ink)),
        ],
      ),
    );
  }

  Widget _buildCodeCard(TyColors ty) {
    final code = _code?.code ?? '—';
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: ty.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: ty.line, width: 1.5),
      ),
      child: Row(
        children: [
          Text(code, style: TyType.display(20, color: ty.ink)),
          const Spacer(),
          TyButton(
            'Copy',
            kind: TyButtonKind.ghost,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            onTap: _copyCode,
          ),
        ],
      ),
    );
  }

  Widget _buildStats(TyColors ty) {
    final stats = _stats;
    final earned = stats != null ? '₹${stats.totalEarned.toStringAsFixed(0)}' : '—';
    final total = stats?.totalReferrals.toString() ?? '—';
    final success = stats?.successfulReferrals.toString() ?? '—';

    return Row(
      children: [
        _stat(context, earned, 'Total Earned', ty.leaf),
        const SizedBox(width: 12),
        _stat(context, total, 'Total Referrals', ty.saffron),
        const SizedBox(width: 12),
        _stat(context, success, 'Successful', ty.rose),
      ],
    );
  }

  Widget _buildApplyField(TyColors ty) {
    return Row(
      children: [
        Expanded(
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            decoration: BoxDecoration(
              color: ty.surface,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: ty.line),
            ),
            child: TextField(
              controller: _applyCtrl,
              style: TyType.sans(15, color: ty.ink),
              decoration: InputDecoration(
                hintText: 'Enter a friend\'s code',
                hintStyle: TyType.sans(14, color: ty.ink3),
                border: InputBorder.none,
              ),
            ),
          ),
        ),
        const SizedBox(width: 12),
        TyButton(
          _applying ? '...' : 'Apply',
          enabled: !_applying,
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          onTap: _applyCode,
        ),
      ],
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
            width: 28, height: 28,
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
        padding: const EdgeInsets.symmetric(vertical: 16),
        decoration: BoxDecoration(
          color: ty.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: ty.line),
        ),
        child: Column(
          children: [
            Text(value, style: TyType.display(20, color: color)),
            const SizedBox(height: 4),
            Text(label, style: TyType.sans(11, color: ty.ink3, weight: FontWeight.w600), textAlign: TextAlign.center),
          ],
        ),
      ),
    );
  }
}
