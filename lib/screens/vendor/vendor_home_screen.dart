import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import 'package:shimmer/shimmer.dart';

import '../../theme/colors.dart';
import '../../theme/typography.dart';
import '../../data/auth_manager.dart';
import '../../data/services/vendor_service.dart';
import '../../widgets/common.dart';
import '../../widgets/ty_button.dart';

class VendorHomeScreen extends StatefulWidget {
  final VoidCallback? onOpenDrawer;
  const VendorHomeScreen({super.key, this.onOpenDrawer});

  @override
  State<VendorHomeScreen> createState() => VendorHomeScreenState();
}

class VendorHomeScreenState extends State<VendorHomeScreen> {
  VendorProfile? _profile;
  VendorStats? _stats;
  List<VendorBooking> _pendingBookings = [];
  List<VendorBooking> _upcomingBookings = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final svc = context.read<VendorService>();
      final results = await Future.wait([
        svc.getMyVendorProfile(),
        svc.getMyStats().catchError((_) => VendorStats(
          activeBookings: 0, completedBookings: 0,
          monthlyEarnings: 0, earningsChangePercent: 0, pendingRequests: 0,
        )),
        svc.listMyBookings(limit: 5, status: 'pending').catchError((_) => <VendorBooking>[]),
        svc.listMyBookings(limit: 5, status: 'confirmed').catchError((_) => <VendorBooking>[]),
      ]);
      if (mounted) {
        setState(() {
          _profile = results[0] as VendorProfile;
          _stats = results[1] as VendorStats;
          _pendingBookings = results[2] as List<VendorBooking>;
          _upcomingBookings = results[3] as List<VendorBooking>;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) setState(() { _error = 'Could not load dashboard data.'; _loading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;

    return Scaffold(
      backgroundColor: ty.paper,
      body: CustomScrollView(
        slivers: [
          _buildAppBar(context),
          if (_loading)
            SliverToBoxAdapter(child: _buildSkeleton(context))
          else if (_error != null)
            SliverFillRemaining(child: _buildError(context))
          else
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 24, 20, 100),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildBusinessStats(context),
                    const SizedBox(height: 32),
                    SectionHeader(
                      'New Requests${_stats != null && _stats!.pendingRequests > 0 ? ' (${_stats!.pendingRequests})' : ''}',
                      action: 'View All', onAction: () {},
                    ),
                    const SizedBox(height: 16),
                    _buildRequestsRail(context),
                    const SizedBox(height: 32),
                    SectionHeader('Upcoming Schedule', action: 'Calendar', onAction: () {}),
                    const SizedBox(height: 16),
                    _buildScheduleList(context),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildAppBar(BuildContext context) {
    final ty = context.ty;
    final user = AuthManager.instance.currentUser;
    final businessName = _profile?.businessName ?? user?.displayName ?? 'Partner';
    return SliverAppBar(
      pinned: true,
      expandedHeight: 140,
      backgroundColor: ty.paper,
      elevation: 0,
      leading: Padding(
        padding: const EdgeInsets.only(left: 12, top: 8),
        child: ChromeIconButton(icon: Icons.menu_rounded, onTap: widget.onOpenDrawer),
      ),
      surfaceTintColor: Colors.transparent,
      flexibleSpace: FlexibleSpaceBar(
        centerTitle: false,
        titlePadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        title: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Namaste, $businessName', style: TyType.display(24, color: ty.ink)),
            Text("Ready for today's celebrations?", style: TyType.sans(12, color: ty.ink3, weight: FontWeight.w600)),
          ],
        ),
      ),
      actions: [
        Padding(
          padding: const EdgeInsets.only(right: 12),
          child: ChromeIconButton(icon: Icons.notifications_none_rounded, onTap: () {}),
        ),
      ],
    );
  }

  Widget _buildBusinessStats(BuildContext context) {
    final ty = context.ty;
    final Color cardBg = ty.isDark ? const Color(0xFF2D1F35) : ty.ink;
    const Color textColor = Colors.white;

    final stats = _stats;
    final profile = _profile;
    final earnings = stats?.monthlyEarnings ?? 0.0;
    final changePercent = stats?.earningsChangePercent ?? 0.0;
    final isPositive = changePercent >= 0;
    final rating = profile?.rating;
    final activeJobs = stats?.activeBookings ?? 0;
    final completed = stats?.completedBookings ?? 0;

    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(28),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.25),
            blurRadius: 20,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('MONTHLY EARNINGS',
                      style: TyType.eyebrow(10, color: textColor.withValues(alpha: 0.6))),
                  const SizedBox(height: 6),
                  Text(
                    '₹${_formatEarnings(earnings)}',
                    style: TyType.display(34, color: textColor),
                  ),
                ],
              ),
              if (changePercent != 0)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: (isPositive ? ty.leaf : ty.rose).withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: (isPositive ? ty.leaf : ty.rose).withValues(alpha: 0.3)),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        isPositive ? Icons.trending_up_rounded : Icons.trending_down_rounded,
                        color: isPositive ? ty.leaf : ty.rose,
                        size: 14,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        '${isPositive ? '+' : ''}${changePercent.toStringAsFixed(0)}%',
                        style: TyType.sans(11, color: isPositive ? ty.leaf : ty.rose, weight: FontWeight.w700),
                      ),
                    ],
                  ),
                ),
            ],
          ),
          const SizedBox(height: 24),
          Container(height: 1, color: textColor.withValues(alpha: 0.1)),
          const SizedBox(height: 24),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _miniStat('Active Jobs', activeJobs.toString().padLeft(2, '0'), ty.saffron, textColor),
              _miniStat(
                'Rating',
                rating != null ? '${rating.toStringAsFixed(1)} ★' : '—',
                ty.gold, textColor,
              ),
              _miniStat('Completed', completed.toString(), ty.leaf, textColor),
            ],
          ),
        ],
      ),
    );
  }

  String _formatEarnings(double amount) {
    if (amount >= 100000) return '${(amount / 100000).toStringAsFixed(1)}L';
    if (amount >= 1000) return '${(amount / 1000).toStringAsFixed(0)}K';
    return amount.toInt().toString();
  }

  Widget _miniStat(String label, String value, Color accent, Color textColor) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label.toUpperCase(),
            style: TyType.eyebrow(9, color: textColor.withValues(alpha: 0.5))),
        const SizedBox(height: 6),
        Row(
          children: [
            Container(
              width: 3, height: 12,
              decoration: BoxDecoration(color: accent, borderRadius: BorderRadius.circular(2)),
            ),
            const SizedBox(width: 8),
            Text(value, style: TyType.sans(18, color: textColor, weight: FontWeight.w700)),
          ],
        ),
      ],
    );
  }

  Widget _buildRequestsRail(BuildContext context) {
    final ty = context.ty;

    if (_pendingBookings.isEmpty) {
      return Container(
        height: 100,
        alignment: Alignment.center,
        child: Text('No pending requests', style: TyType.sans(14, color: ty.ink3)),
      );
    }

    return SizedBox(
      height: 180,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: _pendingBookings.length,
        separatorBuilder: (_, __) => const SizedBox(width: 16),
        itemBuilder: (context, i) {
          final b = _pendingBookings[i];
          final expiresIn = b.quoteExpiresAt != null
              ? b.quoteExpiresAt!.difference(DateTime.now())
              : null;
          return Container(
            width: 300,
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: ty.surface,
              borderRadius: BorderRadius.circular(24),
              border: Border.all(color: ty.line),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    TyPill(b.occasionName, background: ty.saffron.withOpacity(0.15), foreground: ty.saffron),
                    const Spacer(),
                    if (expiresIn != null && expiresIn.inHours < 24)
                      Text(
                        'Ends in ${expiresIn.inHours}h',
                        style: TyType.sans(11, color: ty.rose, weight: FontWeight.w700),
                      ),
                  ],
                ),
                const SizedBox(height: 16),
                Text(
                  b.clientName ?? 'Customer',
                  style: TyType.sans(18, color: ty.ink, weight: FontWeight.w700),
                ),
                const SizedBox(height: 4),
                Text(
                  '${DateFormat('EEE, d MMM').format(b.scheduledDate)}${b.location != null ? ' · ${b.location}' : ''}',
                  style: TyType.sans(13, color: ty.ink2),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const Spacer(),
                Row(
                  children: [
                    Text('₹${b.totalAmount.toInt()}', style: TyType.display(20, color: ty.ink)),
                    const Spacer(),
                    TyButton(
                      'Review',
                      kind: TyButtonKind.soft,
                      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
                      onTap: () {},
                    ),
                  ],
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildScheduleList(BuildContext context) {
    final ty = context.ty;

    if (_upcomingBookings.isEmpty) {
      return Container(
        padding: const EdgeInsets.symmetric(vertical: 24),
        alignment: Alignment.center,
        child: Text('No upcoming bookings', style: TyType.sans(14, color: ty.ink3)),
      );
    }

    return Column(
      children: _upcomingBookings
          .map((b) => _scheduleRow(context, b))
          .toList(),
    );
  }

  Widget _scheduleRow(BuildContext context, VendorBooking b) {
    final ty = context.ty;
    const color = Colors.teal;
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
            width: 50, height: 50,
            decoration: BoxDecoration(
              color: color.withOpacity(0.1),
              borderRadius: BorderRadius.circular(15),
            ),
            child: const Icon(Icons.event_available_rounded, color: color, size: 24),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  DateFormat('EEE, d MMM · h:mm a').format(b.scheduledDate),
                  style: TyType.sans(11, color: ty.saffron, weight: FontWeight.w700),
                ),
                const SizedBox(height: 2),
                Text(b.occasionName, style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
                Text(
                  '${b.clientName ?? 'Customer'}${b.location != null ? ' · ${b.location}' : ''}',
                  style: TyType.sans(13, color: ty.ink2),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
          Icon(Icons.chevron_right_rounded, color: ty.ink3),
        ],
      ),
    );
  }

  Widget _buildSkeleton(BuildContext context) {
    final ty = context.ty;
    return Shimmer.fromColors(
      baseColor: ty.line,
      highlightColor: ty.surface2,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 24, 20, 40),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              height: 200,
              decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(28)),
            ),
            const SizedBox(height: 32),
            Container(height: 16, width: 120, color: ty.surface),
            const SizedBox(height: 16),
            SizedBox(
              height: 180,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: 2,
                separatorBuilder: (_, __) => const SizedBox(width: 16),
                itemBuilder: (_, __) => Container(
                  width: 300,
                  decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(24)),
                ),
              ),
            ),
            const SizedBox(height: 32),
            Container(height: 16, width: 150, color: ty.surface),
            const SizedBox(height: 16),
            ...List.generate(2, (_) => Container(
              margin: const EdgeInsets.only(bottom: 12),
              height: 80,
              decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(20)),
            )),
          ],
        ),
      ),
    );
  }

  Widget _buildError(BuildContext context) {
    final ty = context.ty;
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.error_outline_rounded, size: 48, color: ty.rose),
          const SizedBox(height: 12),
          Text(_error!, style: TyType.sans(14, color: ty.ink2)),
          const SizedBox(height: 16),
          TextButton(
            onPressed: _load,
            child: Text('Try Again', style: TyType.sans(14, color: ty.saffron, weight: FontWeight.w700)),
          ),
        ],
      ),
    );
  }
}
