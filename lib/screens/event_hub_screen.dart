import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/models.dart';
import '../data/services/celebration_service.dart';
import '../widgets/avatar.dart';
import '../widgets/photo_placeholder.dart';
import '../widgets/progress_ring.dart';
import '../widgets/common.dart';
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
  Map<String, dynamic>? _celebration;
  List<Guest> _guests = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadCelebration();
  }

  Future<void> _loadCelebration() async {
    try {
      String? id = widget.celebrationId;
      if (id == null) {
        final celebrations = await _celebrationService.listCelebrations();
        if (celebrations.isEmpty) {
          setState(() => _isLoading = false);
          return;
        }
        id = celebrations.first['id'] as String;
      }
      final details = await _celebrationService.getCelebrationDetails(id);
      final guests = await _celebrationService.listGuests(id);
      if (mounted) {
        setState(() {
          _celebration = details;
          _guests = guests;
          _isLoading = false;
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

    if (_isLoading) {
      return Scaffold(backgroundColor: ty.paper, body: const Center(child: CircularProgressIndicator()));
    }

    if (_celebration == null) {
      return Scaffold(
        backgroundColor: ty.paper,
        appBar: tyAppBar(context, title: 'Event Hub'),
        body: Center(child: Text('No active celebration', style: TyType.sans(16, color: ty.ink2))),
      );
    }

    final totalGuests = _guests.fold<int>(0, (s, g) => s + g.count);
    final pct = _celebration?['progress_percentage'] ?? 0;
    
    // Placeholder for next task
    const nextTask = 'Confirm the venue';

    return Scaffold(
      backgroundColor: ty.paper,
      body: ListView(
        padding: EdgeInsets.zero,
        children: [
          Stack(
            children: [
              CachedNetworkImage(
                imageUrl: _celebration?['hero_image_url'] ?? '',
                height: 360,
                width: double.infinity,
                fit: BoxFit.cover,
                placeholder: (context, url) => PhotoPlaceholder(tint: 'saffron', height: 360, arch: false, radius: BorderRadius.zero),
                errorWidget: (context, url, error) => PhotoPlaceholder(tint: 'saffron', height: 360, arch: false, radius: BorderRadius.zero),
              ),
              Positioned.fill(
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.bottomCenter,
                      end: Alignment.topCenter,
                      colors: [ty.paper, Colors.black.withOpacity(0.3), Colors.black.withOpacity(0.35)],
                      stops: const [0.02, 0.55, 1],
                    ),
                  ),
                ),
              ),
              Positioned(
                top: MediaQuery.of(context).padding.top + 8,
                left: 18,
                right: 18,
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    _glass(Icons.chevron_left_rounded, () => Navigator.of(context).maybePop()),
                    _glass(Icons.favorite_border_rounded, () {}),
                  ],
                ),
              ),
              Positioned(
                left: 20,
                right: 20,
                bottom: 18,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    TyPill('${_celebration?['category']} · ${_celebration?['occasion']?['name_localized'] ?? ""}',
                        background: ty.saffron, foreground: ty.onPrimary),
                    const SizedBox(height: 12),
                    Text(_celebration?['title'] ?? '', style: TyType.display(38, color: Colors.white)),
                    const SizedBox(height: 8),
                    Row(children: [
                      const Icon(Icons.event, size: 16, color: Colors.white70),
                      const SizedBox(width: 8),
                      Text('${_celebration?['scheduled_date']} · ${_celebration?['scheduled_time'] ?? ""}',
                          style: TyType.sans(14, color: Colors.white70)),
                    ]),
                  ],
                ),
              ),
            ],
          ),
          Transform.translate(
            offset: const Offset(0, -14),
            child: Padding(
              padding: const EdgeInsets.fromLTRB(18, 0, 18, 28),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      _stat(context, '11', 'days'), // Still placeholder for days until
                      const SizedBox(width: 10),
                      _stat(context, '06', 'hrs'),
                      const SizedBox(width: 10),
                      _stat(context, '$totalGuests', 'guests'),
                    ],
                  ),
                  const SizedBox(height: 22),
                  const SectionHeader('The plan'),
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: _card(ty),
                    child: Row(
                      children: [
                        ProgressRing(
                          percent: pct.toDouble(),
                          size: 56,
                          center: Text('$pct%',
                              style: TyType.sans(14, color: ty.ink, weight: FontWeight.w800)),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('On track',
                                  style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
                              const SizedBox(height: 2),
                              Text('Next: $nextTask',
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: TyType.sans(12.5, color: ty.ink2)),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 24),
                  SectionHeader('Package details'),
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: _card(ty),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Text(_celebration?['package']?['name'] ?? 'Custom Package',
                                style: TyType.sans(16, color: ty.ink, weight: FontWeight.w700)),
                            const Spacer(),
                            Text('₹${_celebration?['package']?['base_price'] ?? 0}',
                                style: TyType.sans(16, color: ty.saffronDeep, weight: FontWeight.w800)),
                          ],
                        ),
                        const SizedBox(height: 12),
                        Wrap(
                          spacing: 8, runSpacing: 8,
                          children: (_celebration?['package']?['items'] as List?)?.take(3).map((item) => Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                            decoration: BoxDecoration(color: ty.surface2, borderRadius: BorderRadius.circular(6)),
                            child: Text(item['name'], style: TyType.sans(11, color: ty.ink)),
                          )).toList() ?? [],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 14),
                  Row(
                    children: [
                      Expanded(
                        child: _navCard(context, Icons.account_balance_wallet_outlined,
                            'Budget', '₹${_celebration?['budget']?['total_amount'] ?? 0}', const BudgetScreen()),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: _navCard(context, Icons.group_outlined, 'Guests',
                            '$totalGuests invited', const GuestsScreen()),
                      ),
                    ],
                  ),
                  const SizedBox(height: 18),
                  SectionHeader('The gathering', action: 'Manage', onAction: () {
                    Navigator.of(context).push(
                        MaterialPageRoute(builder: (_) => const GuestsScreen()));
                  }),
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: _card(ty),
                    child: Row(
                      children: [
                        if (_guests.isNotEmpty)
                          SizedBox(
                            width: 110,
                            height: 36,
                            child: Stack(
                              children: [
                                for (int i = 0; i < _guests.length.clamp(0, 4); i++)
                                  Positioned(
                                    left: i * 20.0,
                                    child: TyAvatar(name: _guests[i].name, index: i, size: 36),
                                  ),
                              ],
                            ),
                          ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('$totalGuests loved ones',
                                  style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
                              Text('${_guests.length} households invited',
                                  style: TyType.sans(12.5, color: ty.ink2)),
                            ],
                          ),
                        ),
                        Icon(Icons.chevron_right_rounded, color: ty.ink3),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _glass(IconData icon, VoidCallback onTap) => GestureDetector(
        onTap: onTap,
        child: Container(
          width: 42,
          height: 42,
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.18),
            borderRadius: BorderRadius.circular(14),
          ),
          child: Icon(icon, color: Colors.white, size: 20),
        ),
      );

  Widget _stat(BuildContext context, String n, String l) {
    final ty = context.ty;
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 8),
        decoration: _card(ty),
        child: Column(
          children: [
            Text(n, style: TyType.display(26, color: ty.ink)),
            const SizedBox(height: 4),
            Text(l.toUpperCase(), style: TyType.eyebrow(11, color: ty.ink2)),
          ],
        ),
      ),
    );
  }

  Widget _navCard(BuildContext context, IconData icon, String label, String meta, Widget page) {
    final ty = context.ty;
    return GestureDetector(
      onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => page)),
      child: Container(
        padding: const EdgeInsets.all(15),
        decoration: _card(ty),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: ty.saffron, size: 22),
            const SizedBox(height: 10),
            Text(label, style: TyType.sans(14.5, color: ty.ink, weight: FontWeight.w700)),
            Text(meta, style: TyType.sans(12, color: ty.ink2)),
          ],
        ),
      ),
    );
  }

  BoxDecoration _card(TyColors ty) => BoxDecoration(
        color: ty.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: ty.line),
      );
}
