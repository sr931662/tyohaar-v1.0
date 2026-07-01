import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/auth_manager.dart';
import '../data/models.dart';
import '../data/services/package_service.dart';
import '../data/services/celebration_service.dart';
import '../widgets/avatar.dart';
import '../widgets/photo_placeholder.dart';
import '../widgets/progress_ring.dart';
import '../widgets/common.dart';
import '../widgets/state_screens.dart';
import 'event_hub_screen.dart';
import 'budget_screen.dart';
import 'guests_screen.dart';
import 'plan_flow/plan_flow_screen.dart';
import 'package:tyohaar/screens/package_detail_screen.dart';
import 'package:tyohaar/screens/invitation_management_screen.dart';
import 'package:tyohaar/screens/occasion_detail_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final PackageService _packageService = PackageService();
  final CelebrationService _celebrationService = CelebrationService();

  List<Package> _bestSellers = [];
  List<Occasion> _occasions = [];
  Celebration? _activeCelebration;
  List<Guest> _guests = [];
  List<CelebrationChecklistItem> _checklist = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    try {
      final results = await Future.wait([
        _packageService.listPackages().catchError((e) {
          debugPrint('Error loading packages: $e');
          return <Package>[];
        }),
        _packageService.listOccasions().catchError((e) {
          debugPrint('Error loading occasions: $e');
          return <Occasion>[];
        }),
        _celebrationService.listCelebrations().catchError((e) {
          debugPrint('Error loading celebrations: $e');
          return <Celebration>[];
        }),
      ]);

      setState(() {
        _bestSellers = results[0] as List<Package>;
        _occasions = results[1] as List<Occasion>;
        final celebrations = results[2] as List<Celebration>;
        if (celebrations.isNotEmpty) {
          _activeCelebration = celebrations.first;
          _loadGuests(_activeCelebration!.id);
          _loadChecklist(_activeCelebration!.id);
        }
        _isLoading = false;
        _error = null;
      });
    } catch (e) {
      if (mounted) setState(() { _error = 'Could not load home data.'; _isLoading = false; });
    }
  }

  Future<void> _loadGuests(String celebrationId) async {
    try {
      final guests = await _celebrationService.listGuests(celebrationId);
      setState(() => _guests = guests);
    } catch (e) {
      debugPrint('Error loading guests: $e');
    }
  }

  Future<void> _loadChecklist(String celebrationId) async {
    try {
      final checklist = await _celebrationService.listChecklist(celebrationId);
      setState(() => _checklist = checklist);
    } catch (e) {
      debugPrint('Error loading checklist: $e');
    }
  }

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

    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return TyStateScreen.error(onAction: _loadData);
    }

    final totalGuests = _guests.length;
    final rsvpdGuests = _guests.where((g) => g.rsvpStatus == 'confirmed').length;
    final pct = _activeCelebration?.completionPercentage ?? 0;
    final pendingTasks = _checklist.where((t) => !t.isCompleted).toList();
    final openTasks = pendingTasks.take(2).toList();

    return ListView(
      padding: EdgeInsets.zero,
      children: [
        _buildHeroCard(context, pct, totalGuests, pendingTasks.length),

        Padding(
          padding: const EdgeInsets.fromLTRB(18, 18, 18, 28),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
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

              SectionHeader('Up next',
                  action: 'Timeline',
                  onAction: () => _push(context, const PlanFlowScreen(startStep: 4), authAction: 'view your timeline')),
              if (openTasks.isEmpty)
                _taskRow(context, 'All caught up!', 'No pending tasks right now')
              else
                ...openTasks.map((t) => _taskRow(
                  context,
                  t.title,
                  t.timingLabel ?? '',
                )),
              const SizedBox(height: 12),
              _taskRow(
                context,
                'Manage Invitations',
                totalGuests > 0 ? '$totalGuests invited · $rsvpdGuests RSVP\'d' : 'No invitations yet',
                icon: Icons.mail_outline_rounded,
                onTap: () => _push(context, const InvitationManagementScreen(), authAction: 'manage invitations'),
              ),
              const SizedBox(height: 26),

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

              _membershipBanner(context),
              const SizedBox(height: 26),

              if (_bestSellers.isNotEmpty) ...[
                SectionHeader('Best Selling Packages'),
                _packageRail(context, _bestSellers),
                const SizedBox(height: 26),
              ],

              if (_occasions.any((o) => o.category == 'major_festival')) ...[
                SectionHeader('Popular Festivals'),
                _festivalRail(context, _occasions.where((o) => o.category == 'major_festival').toList()),
                const SizedBox(height: 26),
              ],

              if (_occasions.any((o) => o.category == 'life_event')) ...[
                SectionHeader('Life Moments'),
                _festivalRail(context, _occasions.where((o) => o.category == 'life_event').toList()),
                const SizedBox(height: 26),
              ],

              if (_occasions.any((o) => o.category == 'minor_festival')) ...[
                SectionHeader('Upcoming Celebrations'),
                _festivalRail(context, _occasions.where((o) => o.category == 'minor_festival').toList()),
              ],
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildHeroCard(BuildContext context, int pct, int totalGuests, int pendingTaskCount) {
    final ty = context.ty;
    const double radius = 42.0;
    
    final title = _activeCelebration?.title ?? 'Start Planning';
    final dt = _activeCelebration?.celebrationDate;
    final date = dt != null ? '${dt.day}/${dt.month}/${dt.year}' : '';
    final location = _activeCelebration?.venueAddress ?? 'Select Location';
    
    // Resolve hero image and category from occasions list if needed
    String? heroUrl = _activeCelebration?.heroImageUrl;
    String category = _activeCelebration?.category ?? 'Celebration';
    
    if (heroUrl == null && _activeCelebration?.occasionId != null) {
      final occ = _occasions.cast<Occasion?>().firstWhere(
        (o) => o?.id == _activeCelebration?.occasionId,
        orElse: () => null
      );
      if (occ != null) {
        heroUrl = occ.heroImageUrl;
        category = occ.category;
      }
    }

    return GestureDetector(
      onTap: () => _push(context, const EventHubScreen(), authAction: 'view your event hub'),
      child: SizedBox(
        height: 440,
        child: Stack(
          children: [
            Positioned.fill(
              child: ClipRRect(
                borderRadius: const BorderRadius.vertical(bottom: Radius.circular(radius)),
                child: CachedNetworkImage(
                  imageUrl: heroUrl ?? '',
                  fit: BoxFit.cover,
                  placeholder: (context, url) => PhotoPlaceholder(tint: 'saffron', height: 440, arch: false, radius: BorderRadius.vertical(bottom: Radius.circular(radius))),
                  errorWidget: (context, url, error) => Image.asset(
                    'assets/images/Landing page image.png',
                    fit: BoxFit.cover,
                  ),
                ),
              ),
            ),
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
              bottom: 32,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('YOUR NEXT CELEBRATION',
                      style: TyType.eyebrow(11.5, color: Colors.white.withOpacity(0.7))),
                  const SizedBox(height: 12),
                  Row(children: [
                    TyPill(category),
                    const SizedBox(width: 8),
                    if (date.isNotEmpty)
                      const TyPill('Upcoming', background: Colors.orange, foreground: Colors.white),
                  ]),
                  const SizedBox(height: 14),
                  Text(title, style: TyType.display(34, color: Colors.white)),
                  const SizedBox(height: 6),
                  Row(children: [
                    const Icon(Icons.event, size: 15, color: Colors.white70),
                    const SizedBox(width: 6),
                    Text('$date · $location',
                        style: TyType.sans(14, color: Colors.white70)),
                  ]),
                  const SizedBox(height: 20),
                  Row(
                    children: [
                      _stackedAvatars(_guests, totalGuests),
                      const Spacer(),
                      _progressChip(context, pct, pendingTaskCount),
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
                      ClipRRect(
                        borderRadius: BorderRadius.circular(20),
                        child: CachedNetworkImage(
                          imageUrl: p.coverImageUrl ?? '',
                          height: 130,
                          width: double.infinity,
                          fit: BoxFit.cover,
                          placeholder: (context, url) => PhotoPlaceholder(tint: p.tint, height: 130, arch: false),
                          errorWidget: (context, url, error) => PhotoPlaceholder(tint: p.tint, height: 130, arch: false),
                        ),
                      ),
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
                  Text(p.slug ?? p.name, style: TyType.sans(12, color: ty.ink2)),
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
                  Text(f.name,
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

  Widget _stackedAvatars(List<Guest> guests, int total) {
    if (guests.isEmpty) return const SizedBox();
    return SizedBox(
      width: 112,
      height: 30,
      child: Stack(
        children: [
          for (int i = 0; i < guests.length.clamp(0, 4); i++)
            Positioned(
              left: i * 20.0,
              child: TyAvatar(name: guests[i].name, index: i, size: 30),
            ),
          if (total > 4)
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
                child: Text('+${total - 4}',
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
