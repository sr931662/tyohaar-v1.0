import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';

import 'package:tyohaar/theme/assets.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../theme/responsive.dart';
import '../data/models.dart';
import '../data/services/celebration_service.dart';
import '../data/services/budget_service.dart' as bs;
import '../widgets/avatar.dart';
import '../widgets/photo_placeholder.dart';
import '../widgets/progress_ring.dart';
import '../widgets/common.dart';
import '../widgets/tutorial/tutorial_overlay.dart';
import 'budget_screen.dart';
import 'guests_screen.dart';

class EventHubScreen extends StatefulWidget {
  final String? celebrationId;
  const EventHubScreen({super.key, this.celebrationId});

  @override
  State<EventHubScreen> createState() => _EventHubScreenState();
}

class _EventHubScreenState extends State<EventHubScreen> {
  final CelebrationService _celebrationService = CelebrationService();
  final bs.BudgetService _budgetService = bs.BudgetService();
  Celebration? _celebration;
  List<Guest> _guests = [];
  List<CelebrationChecklistItem> _checklist = [];
  String _daysLeft = '--';
  String _hoursLeft = '--';
  bool _isLoading = true;
  final GlobalKey _heroKey = GlobalKey();

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      String? id = widget.celebrationId;
      if (id == null) {
        final celebrations = await _celebrationService.listCelebrations();
        if (celebrations.isEmpty) {
          setState(() => _isLoading = false);
          return;
        }
        id = celebrations.first.id;
      }
      final detailsFuture = _celebrationService.getCelebrationDetails(id);
      final guestsFuture = _celebrationService.listGuests(id);
      final checklistFuture = _celebrationService.listChecklist(id);
      final budgetFuture = _budgetService.getBudgetForCelebration(id);
      
      final details = await detailsFuture;
      final guests = await guestsFuture;
      final checklist = await checklistFuture;
      final budget = await budgetFuture;

      String daysLeft = '--';
      String hoursLeft = '--';
      final eventDate = details.celebrationDate;
      if (eventDate != null) {
        if (eventDate.isAfter(DateTime.now())) {
          final diff = eventDate.difference(DateTime.now());
          daysLeft = diff.inDays.toString().padLeft(2, '0');
          hoursLeft = (diff.inHours % 24).toString().padLeft(2, '0');
        } else {
          daysLeft = '00';
          hoursLeft = '00';
        }
      }

      if (mounted) {
        setState(() {
          _celebration = details;
          _guests = guests;
          _checklist = checklist;
          _daysLeft = daysLeft;
          _hoursLeft = hoursLeft;
          _isLoading = false;
        });
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (!mounted) return;
          TutorialOverlay.show(context, screenKey: 'event_hub', steps: [
            TutorialStep(
              targetKey: _heroKey,
              title: 'Your celebration, at a glance',
              description: 'Track the countdown, guest RSVPs, and checklist progress for this event right here.',
            ),
          ]);
        });
      }
    } catch (e) {
      debugPrint('Error loading event hub: $e');
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final resp = context.resp;

    if (_isLoading) {
      return Scaffold(backgroundColor: ty.paper, body: const Center(child: CircularProgressIndicator()));
    }

    if (_celebration == null) {
      return Scaffold(
        backgroundColor: ty.paper,
        appBar: tyAppBar(context, title: 'Event Hub'),
        body: Center(child: Text('No active celebration', style: TyType.sans(resp.sp(16), color: ty.ink2))),
      );
    }

    final totalGuests = _guests.length;
    final pct = _celebration?.completionPercentage ?? 0;
    final nextTask = _checklist.where((t) => !t.isCompleted).map((t) => t.title).firstOrNull ?? 'All tasks complete!';

    final dt = _celebration?.celebrationDate;
    final date = dt != null ? '${dt.day}/${dt.month}/${dt.year}' : '';

    return Scaffold(
      backgroundColor: ty.paper,
      body: RefreshIndicator(
        onRefresh: _load,
        color: ty.saffron,
        child: ListView(
          padding: EdgeInsets.zero,
          children: [
            Stack(
              key: _heroKey,
              children: [
                CachedNetworkImage(
                  imageUrl: _celebration?.heroImageUrl ?? '',
                  height: resp.h(360),
                  width: double.infinity,
                  fit: BoxFit.cover,
                  placeholder: (context, url) => PhotoPlaceholder(
                      tint: 'saffron', height: resp.h(360), arch: false, radius: BorderRadius.zero),
                  errorWidget: (context, url, error) => OccasionAssets.getFallback(
                      _celebration?.occasionName ?? _celebration?.title ?? '',
                      arch: false),
                ),
                Positioned.fill(
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.bottomCenter,
                        end: Alignment.topCenter,
                        colors: [
                          ty.paper,
                          Colors.black.withOpacity(0.3),
                          Colors.black.withOpacity(0.35)
                        ],
                        stops: const [0.02, 0.55, 1],
                      ),
                    ),
                  ),
                ),
                Positioned(
                  top: MediaQuery.of(context).padding.top + resp.h(8),
                  left: resp.w(18),
                  right: resp.w(18),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      _glass(context, Icons.chevron_left_rounded,
                          () => Navigator.of(context).maybePop()),
                      _glass(context, Icons.favorite_border_rounded, () {}),
                    ],
                  ),
                ),
                Positioned(
                  left: resp.w(20),
                  right: resp.w(20),
                  bottom: resp.h(18),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      TyPill(
                          '${_celebration?.category ?? 'Celebration'} · ${_celebration?.occasionName ?? ""}',
                          background: ty.saffron,
                          foreground: ty.onPrimary),
                      SizedBox(height: resp.h(12)),
                      Text(_celebration?.title ?? '',
                          style: TyType.display(resp.sp(38), color: Colors.white)),
                      SizedBox(height: resp.h(8)),
                      Row(children: [
                        Icon(Icons.event, size: resp.sp(16), color: Colors.white70),
                        SizedBox(width: resp.w(8)),
                        Text('$date', style: TyType.sans(resp.sp(14), color: Colors.white70)),
                      ]),
                    ],
                  ),
                ),
              ],
            ),
            Transform.translate(
              offset: Offset(0, resp.h(-14)),
              child: Padding(
                padding: EdgeInsets.fromLTRB(resp.w(18), 0, resp.w(18), resp.h(28)),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        _stat(context, _daysLeft, 'days'),
                        SizedBox(width: resp.w(10)),
                        _stat(context, _hoursLeft, 'hrs'),
                        SizedBox(width: resp.w(10)),
                        _stat(context, '$totalGuests', 'guests'),
                      ],
                    ),
                    SizedBox(height: resp.h(22)),
                    const SectionHeader('The plan'),
                    Container(
                      padding: EdgeInsets.all(resp.w(16)),
                      decoration: _card(ty, resp),
                      child: Row(
                        children: [
                          ProgressRing(
                            percent: pct.toDouble(),
                            size: resp.w(56),
                            center: Text('$pct%',
                                style: TyType.sans(resp.sp(14),
                                    color: ty.ink, weight: FontWeight.w800)),
                          ),
                          SizedBox(width: resp.w(16)),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('On track',
                                    style: TyType.sans(resp.sp(15),
                                        color: ty.ink, weight: FontWeight.w700)),
                                SizedBox(height: resp.h(2)),
                                Text('Next: $nextTask',
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: TyType.sans(resp.sp(12.5), color: ty.ink2)),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                    SizedBox(height: resp.h(24)),
                    SectionHeader('Package details'),
                    Container(
                      padding: EdgeInsets.all(resp.w(16)),
                      decoration: _card(ty, resp),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Text('Custom Package',
                                  style: TyType.sans(resp.sp(16),
                                      color: ty.ink, weight: FontWeight.w700)),
                              const Spacer(),
                            ],
                          ),
                          SizedBox(height: resp.h(12)),
                          const Text('View details in your plans'),
                        ],
                      ),
                    ),
                    SizedBox(height: resp.h(14)),
                    Row(
                      children: [
                        Expanded(
                          child: _navCard(
                              context,
                              Icons.account_balance_wallet_outlined,
                              'Budget',
                              '₹${_celebration?.estimatedBudget ?? 0}',
                              const BudgetScreen()),
                        ),
                        SizedBox(width: resp.w(12)),
                        Expanded(
                          child: _navCard(context, Icons.group_outlined, 'Guests',
                              '$totalGuests invited', const GuestsScreen()),
                        ),
                      ],
                    ),
                    SizedBox(height: resp.h(18)),
                    SectionHeader('The gathering', action: 'Manage', onAction: () {
                      Navigator.of(context)
                          .push(MaterialPageRoute(builder: (_) => const GuestsScreen()));
                    }),
                    Container(
                      padding: EdgeInsets.all(resp.w(16)),
                      decoration: _card(ty, resp),
                      child: Row(
                        children: [
                          if (_guests.isNotEmpty)
                            SizedBox(
                              width: resp.w(110),
                              height: resp.h(36),
                              child: Stack(
                                children: [
                                  for (int i = 0; i < _guests.length.clamp(0, 4); i++)
                                    Positioned(
                                      left: i * resp.w(20.0),
                                      child: TyAvatar(
                                          name: _guests[i].name, index: i, size: resp.w(36)),
                                    ),
                                ],
                              ),
                            ),
                          SizedBox(width: resp.w(8)),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('$totalGuests loved ones',
                                    style: TyType.sans(resp.sp(15),
                                        color: ty.ink, weight: FontWeight.w700)),
                                Text('${_guests.length} households invited',
                                    style: TyType.sans(resp.sp(12.5), color: ty.ink2)),
                              ],
                            ),
                          ),
                          Icon(Icons.chevron_right_rounded, color: ty.ink3, size: resp.sp(24)),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _glass(BuildContext context, IconData icon, VoidCallback onTap) {
    final resp = context.resp;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: resp.w(42),
        height: resp.w(42),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.18),
          borderRadius: BorderRadius.circular(resp.w(14)),
        ),
        child: Icon(icon, color: Colors.white, size: resp.sp(20)),
      ),
    );
  }

  Widget _stat(BuildContext context, String n, String l) {
    final ty = context.ty;
    final resp = context.resp;
    return Expanded(
      child: Container(
        padding: EdgeInsets.symmetric(vertical: resp.h(14), horizontal: resp.w(8)),
        decoration: _card(ty, resp),
        child: Column(
          children: [
            Text(n, style: TyType.display(resp.sp(26), color: ty.ink)),
            SizedBox(height: resp.h(4)),
            Text(l.toUpperCase(), style: TyType.eyebrow(resp.sp(11), color: ty.ink2)),
          ],
        ),
      ),
    );
  }

  Widget _navCard(BuildContext context, IconData icon, String label, String meta, Widget page) {
    final ty = context.ty;
    final resp = context.resp;
    return GestureDetector(
      onTap: () => Navigator.of(context)
          .push(MaterialPageRoute(builder: (_) => page))
          .then((_) => _load()),
      child: Container(
        padding: EdgeInsets.all(resp.w(15)),
        decoration: _card(ty, resp),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: ty.saffron, size: resp.sp(22)),
            SizedBox(height: resp.h(10)),
            Text(label, style: TyType.sans(resp.sp(14.5), color: ty.ink, weight: FontWeight.w700)),
            Text(meta, style: TyType.sans(resp.sp(12), color: ty.ink2)),
          ],
        ),
      ),
    );
  }

  BoxDecoration _card(TyColors ty, TyResponsive resp) => BoxDecoration(
        color: ty.surface,
        borderRadius: BorderRadius.circular(resp.w(20)),
        border: Border.all(color: ty.line),
      );
}
