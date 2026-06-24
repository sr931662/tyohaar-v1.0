import 'package:flutter/material.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/auth_manager.dart';
import '../data/sample_data.dart';
import '../data/models.dart';
import '../widgets/avatar.dart';
import '../widgets/photo_placeholder.dart';
import '../widgets/progress_ring.dart';
import '../widgets/common.dart';
import 'event_hub_screen.dart';
import 'budget_screen.dart';
import 'guests_screen.dart';
import 'plan_flow/plan_flow_screen.dart';
import 'package:tyohaar/screens/package_detail_screen.dart';
import 'package:tyohaar/screens/invitation_management_screen.dart';
import 'package:tyohaar/screens/occasion_detail_screen.dart';

/// A logical, scannable hub: the active celebration, quick actions,
/// the nearest tasks, a vendor message, and inspiration.
class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  void _push(BuildContext context, Widget page, {String? authAction}) {
    if (authAction != null) {
      AuthManager.instance.checkAuth(
        context, 
        action: authAction,
        onAuthenticated: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => page)),
      );
    } else {
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => page));
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final guests = TyData.seedGuests();
    final totalGuests = guests.fold<int>(0, (s, g) => s + g.count);
    final phases = TyData.planTemplate();
    final allTasks = phases.expand((p) => p.items).toList();
    final done = allTasks.where((t) => t.done).length;
    final total = allTasks.length;
    final pct = (done / total * 100).round();
    final openTasks = phases
        .expand((p) => p.items.where((t) => !t.done).map((t) => [t.title, '${p.phase} · ${t.who}']))
        .take(3)
        .toList();

    return ListView(
      padding: EdgeInsets.zero,
      children: [
        // ── active celebration (Hero) ──
        _buildHeroCard(context, pct, total - done, guests, totalGuests),

        Padding(
          padding: const EdgeInsets.fromLTRB(18, 18, 18, 28),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // ── quick actions ──
              Row(
                children: [
                  _quickAction(context, Icons.group_outlined, 'Guests', ty.saffron,
                      () => _push(context, const GuestsScreen(), authAction: 'manage guests')),
                  _quickAction(context, Icons.account_balance_wallet_outlined, 'Budget',
                      ty.leaf, () => _push(context, const BudgetScreen(), authAction: 'view your budget')),
                  _quickAction(context, Icons.checklist_rounded, 'My Plans', ty.gold,
                      () => _push(context, const PlanFlowScreen(startStep: 4), authAction: 'view your plans')),
                ],
              ),
              const SizedBox(height: 26),

              // ── up next ──
              SectionHeader('Up next',
                  action: 'Timeline',
                  onAction: () => _push(context, const PlanFlowScreen(startStep: 4), authAction: 'view your timeline')),
              ...openTasks.map((t) => _taskRow(context, t[0], t[1])),
              const SizedBox(height: 12),
              _taskRow(context, 'Manage Invitations', '38 opened · 24 RSVP’d', 
                  icon: Icons.mail_outline_rounded, 
                  onTap: () => _push(context, const InvitationManagementScreen(), authAction: 'manage invitations')),
              const SizedBox(height: 26),

              // ── from your team ──
              SectionHeader('From your team'),
              Container(
                padding: const EdgeInsets.all(13),
                decoration: _cardDecoration(ty),
                child: Row(
                  children: [
                    const SizedBox(
                        width: 44,
                        height: 44,
                        child: PhotoPlaceholder(tint: 'rose', arch: false)),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Frame Stories',
                              style: TyType.sans(13.5, color: ty.ink, weight: FontWeight.w700)),
                          const SizedBox(height: 2),
                          Text('Shared 3 sample albums for your review ✨',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: TyType.sans(12.5, color: ty.ink2)),
                        ],
                      ),
                    ),
                    Container(
                      width: 34,
                      height: 34,
                      decoration: BoxDecoration(
                          color: ty.saffron, borderRadius: BorderRadius.circular(11)),
                      child: Icon(Icons.chat_bubble_outline_rounded,
                          color: ty.onPrimary, size: 17),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 26),

              // ── start a celebration ──
              GestureDetector(
                onTap: () => _push(context, const PlanFlowScreen(), authAction: 'start a celebration'),
                child: Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: ty.saffronSoft.withOpacity(ty.isDark ? 0.08 : 0.6),
                    borderRadius: BorderRadius.circular(22),
                    border: Border.all(color: ty.saffron.withOpacity(0.15)),
                  ),
                  child: Row(
                    children: [
                      Container(
                        width: 50,
                        height: 50,
                        decoration: BoxDecoration(
                          color: ty.saffron.withOpacity(0.12),
                          borderRadius: BorderRadius.circular(15),
                        ),
                        child: Icon(Icons.auto_awesome, color: ty.saffron, size: 24),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('Start a celebration',
                                style: TyType.sans(16, color: ty.ink, weight: FontWeight.w700)),
                            const SizedBox(height: 2),
                            Text('We build the plan, you enjoy the moment',
                                style: TyType.sans(12.5, color: ty.ink2)),
                          ],
                        ),
                      ),
                      Icon(Icons.chevron_right_rounded, color: ty.ink3),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 26),

              // ── membership banner ──
              _membershipBanner(context),
              const SizedBox(height: 26),

              // ── best selling packages ──
              SectionHeader('Best Selling Packages'),
              _packageRail(context, TyData.bestSellers),
              const SizedBox(height: 26),

              // ── popular festivals ──
              SectionHeader('Popular Festivals'),
              _festivalRail(context, TyData.occasions.where((o) => o.category == 'major_festival').toList()),
              const SizedBox(height: 26),

              // ── life moments ──
              SectionHeader('Life Moments'),
              _festivalRail(context, TyData.occasions.where((o) => o.category == 'life').toList()),
              const SizedBox(height: 26),

              // ── upcoming celebrations ──
              SectionHeader('Upcoming Celebrations'),
              _festivalRail(context, TyData.occasions.where((o) => o.category == 'minor_festival').toList()),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildHeroCard(BuildContext context, int pct, int tasksLeft, List guests, int totalGuests) {
    final ty = context.ty;
    const double radius = 42.0;
    
    return GestureDetector(
      onTap: () => _push(context, const EventHubScreen(), authAction: 'view your event hub'),
      child: SizedBox(
        height: 440,
        child: Stack(
          children: [
            // Background Image
            Positioned.fill(
              child: ClipRRect(
                borderRadius: const BorderRadius.vertical(bottom: Radius.circular(radius)),
                child: Image.asset(
                  'assets/images/Landing page image.png',
                  fit: BoxFit.cover,
                  errorBuilder: (context, error, stackTrace) => PhotoPlaceholder(
                    tint: 'saffron', 
                    height: 440, 
                    arch: false,
                    radius: BorderRadius.vertical(bottom: Radius.circular(radius)),
                  ),
                ),
              ),
            ),
            // Top overlay for header readability - STRENGTHENED for light imagery
            Positioned(
              top: 0,
              left: 0,
              right: 0,
              height: 200,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      Colors.black.withOpacity(ty.isDark ? 0.6 : 0.4),
                      Colors.black.withOpacity(ty.isDark ? 0.3 : 0.1),
                      Colors.transparent,
                    ],
                    stops: const [0, 0.45, 1.0],
                  ),
                ),
              ),
            ),
            // Bottom overlay for content readability
            Positioned.fill(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  borderRadius: const BorderRadius.vertical(bottom: Radius.circular(radius)),
                  gradient: LinearGradient(
                    begin: Alignment.bottomCenter,
                    end: Alignment.topCenter,
                    colors: [
                      Colors.black.withOpacity(0.85),
                      Colors.black.withOpacity(0.20),
                      Colors.transparent,
                    ],
                    stops: const [0, 0.5, 0.8],
                  ),
                ),
              ),
            ),
            Positioned(
              left: 18,
              right: 18,
              bottom: 32, // Increased bottom padding to clear the curve
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('YOUR NEXT CELEBRATION',
                      style: TyType.eyebrow(11.5, color: Colors.white.withOpacity(0.7))),
                  const SizedBox(height: 12),
                  Row(children: const [
                    TyPill('Birthday'),
                    SizedBox(width: 8),
                    TyPill('in 11 days', background: Colors.orange, foreground: Colors.white),
                  ]),
                  const SizedBox(height: 14),
                  Text('Diya turns One',
                      style: TyType.display(34, color: Colors.white)),
                  const SizedBox(height: 6),
                  Row(children: [
                    const Icon(Icons.event, size: 15, color: Colors.white70),
                    const SizedBox(width: 6),
                    Text('Sat, 14 June · Jaipur',
                        style: TyType.sans(14, color: Colors.white70)),
                  ]),
                  const SizedBox(height: 20),
                  Row(
                    children: [
                      _stackedAvatars(guests, totalGuests),
                      const Spacer(),
                      _progressChip(context, pct, tasksLeft),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  // Placeholder for setstate in stateless widget fix
  void setState(VoidCallback fn) {}

  Widget _membershipBanner(BuildContext context) {
    final ty = context.ty;
    return Container(
      padding: const EdgeInsets.all(20),
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
            blurRadius: 15,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Upgrade to Gold',
                    style: TyType.display(20, color: Colors.white)),
                const SizedBox(height: 4),
                Text('Get exclusive access to premium themes and early bird discounts.',
                    style: TyType.sans(12, color: Colors.white.withOpacity(0.9))),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text('Join Now',
                style: TyType.sans(13, color: ty.saffronDeep, weight: FontWeight.w700)),
          ),
        ],
      ),
    );
  }

  Widget _packageRail(BuildContext context, List<Package> packages) {
    final ty = context.ty;
    return SizedBox(
      height: 210,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: packages.length,
        separatorBuilder: (_, __) => const SizedBox(width: 16),
        itemBuilder: (context, i) {
          final p = packages[i];
          return GestureDetector(
            onTap: () => _push(context, PackageDetailScreen(package: p)),
            child: SizedBox(
              width: 180,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Stack(
                    children: [
                      p.coverImage.startsWith('assets/')
                          ? ClipRRect(
                              borderRadius: BorderRadius.circular(20),
                              child: Image.asset(p.coverImage, height: 130, width: double.infinity, fit: BoxFit.cover),
                            )
                          : PhotoPlaceholder(tint: p.tint, height: 130, arch: false),
                      Positioned(
                        top: 10,
                        right: 10,
                        child: TyPill('₹${(p.price / 1000).toStringAsFixed(0)}K'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Text(p.name,
                      style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
                  Text(p.theme, style: TyType.sans(12, color: ty.ink2)),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _festivalRail(BuildContext context, List<Occasion> festivals) {
    final ty = context.ty;
    return SizedBox(
      height: 140,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: festivals.length,
        separatorBuilder: (_, __) => const SizedBox(width: 12),
        itemBuilder: (context, i) {
          final f = festivals[i];
          return GestureDetector(
            onTap: () => _push(context, OccasionDetailScreen(occasion: f)),
            child: SizedBox(
              width: 110,
              child: Column(
                children: [
                  Container(
                    width: 80,
                    height: 80,
                    decoration: BoxDecoration(
                      color: ty.tint(f.tint).withOpacity(0.12),
                      shape: BoxShape.circle,
                    ),
                    child: Center(
                      child: Icon(
                        f.icon,
                        color: ty.tint(f.tint),
                        size: 32,
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(f.en,
                      textAlign: TextAlign.center,
                      maxLines: 2,
                      style: TyType.sans(12, color: ty.ink, weight: FontWeight.w600)),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _stackedAvatars(List guests, int total) {
    return SizedBox(
      width: 112,
      height: 30,
      child: Stack(
        children: [
          for (int i = 0; i < 4; i++)
            Positioned(
              left: i * 20.0,
              child: TyAvatar(name: guests[i].name, index: i, size: 30),
            ),
          Positioned(
            left: 4 * 20.0 - 10,
            child: Container(
              width: 30,
              height: 30,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.22),
                shape: BoxShape.circle,
                border: Border.all(color: Colors.white.withOpacity(0.5), width: 2),
              ),
              child: Text('+${total - 8}',
                  style: const TextStyle(
                      color: Colors.white, fontSize: 10.5, fontWeight: FontWeight.w700)),
            ),
          ),
        ],
      ),
    );
  }

  Widget _progressChip(BuildContext context, int pct, int left) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.16),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        children: [
          ProgressRing(
            percent: pct.toDouble(),
            size: 36,
            stroke: 4,
            color: Colors.white,
            center: Text('$pct%',
                style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.w700)),
          ),
          const SizedBox(width: 9),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('on track',
                  style: TextStyle(color: Colors.white, fontSize: 11)),
              Text('$left tasks left',
                  style: const TextStyle(
                      color: Colors.white, fontSize: 11, fontWeight: FontWeight.w700)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _quickAction(
      BuildContext context, IconData icon, String label, Color color, VoidCallback onTap) {
    final ty = context.ty;
    return Expanded(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 4.5),
        child: GestureDetector(
          onTap: onTap,
          child: Container(
            padding: const EdgeInsets.fromLTRB(6, 14, 6, 11),
            decoration: _cardDecoration(ty),
            child: Column(
              children: [
                Container(
                  width: 38,
                  height: 38,
                  decoration: BoxDecoration(
                    color: color.withOpacity(0.14),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(icon, color: color, size: 20),
                ),
                const SizedBox(height: 7),
                Text(label,
                    style: TyType.sans(11.5, color: ty.ink, weight: FontWeight.w700)),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _taskRow(BuildContext context, String title, String meta, {IconData? icon, VoidCallback? onTap}) {
    final ty = context.ty;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(bottom: 9),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: _cardDecoration(ty),
        child: Row(
          children: [
            Container(
              width: 34,
              height: 34,
              decoration: BoxDecoration(
                color: ty.saffronSoft,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(icon ?? Icons.schedule_rounded, color: ty.saffronDeep, size: 17),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TyType.sans(14, color: ty.ink, weight: FontWeight.w600)),
                  const SizedBox(height: 1),
                  Text(meta, style: TyType.sans(11.5, color: ty.ink3)),
                ],
              ),
            ),
            Icon(Icons.chevron_right_rounded, color: ty.ink3, size: 18),
          ],
        ),
      ),
    );
  }

  BoxDecoration _cardDecoration(TyColors ty) => BoxDecoration(
        color: ty.surface,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: ty.line),
      );
}
