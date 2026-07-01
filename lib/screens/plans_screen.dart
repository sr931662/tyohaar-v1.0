import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shimmer/shimmer.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/models.dart';
import '../widgets/photo_placeholder.dart';
import '../widgets/common.dart';
import '../data/auth_manager.dart';
import '../data/services/celebration_service.dart';
import 'event_hub_screen.dart';
import 'plan_flow/plan_flow_screen.dart';

class PlansScreen extends StatefulWidget {
  const PlansScreen({super.key});

  @override
  State<PlansScreen> createState() => _PlansScreenState();
}

class _PlansScreenState extends State<PlansScreen> {
  List<Celebration> _celebrations = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    if (!AuthManager.instance.isAuthenticated) {
      setState(() => _loading = false);
      return;
    }
    setState(() { _loading = true; _error = null; });
    try {
      final list = await context.read<CelebrationService>().listCelebrations();
      if (mounted) setState(() { _celebrations = list; _loading = false; });
    } catch (e) {
      if (mounted) setState(() { _error = 'Could not load your plans.'; _loading = false; });
    }
  }

  static String _tintFor(String? occasion) {
    final o = (occasion ?? '').toLowerCase();
    if (o.contains('birth') || o.contains('anniv')) return 'rose';
    if (o.contains('house') || o.contains('griha') || o.contains('wed')) return 'leaf';
    return 'saffron';
  }

  static String _dateLabel(DateTime? dt) {
    if (dt == null) return '';
    try {
      const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
      return '${dt.day} ${months[dt.month - 1]}';
    } catch (_) {
      return '';
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final topPadding = MediaQuery.of(context).padding.top + 70;

    return ListView(
      padding: EdgeInsets.fromLTRB(18, topPadding, 18, 28),
      children: [
        Row(
          children: [
            Expanded(child: Text('Your plans', style: TyType.display(26, color: ty.ink))),
            ChromeIconButton(
              icon: Icons.add_rounded,
              onTap: () => Navigator.of(context)
                  .push(MaterialPageRoute(builder: (_) => const PlanFlowScreen()))
                  .then((_) => _load()),
            ),
          ],
        ),
        const SizedBox(height: 22),
        if (_loading) ..._buildSkeletons(ty),
        if (!_loading && _error != null) _buildError(ty),
        if (!_loading && _error == null && _celebrations.isEmpty) _buildEmpty(context, ty),
        if (!_loading && _error == null && _celebrations.isNotEmpty) ...[
          const SectionHeader('In progress'),
          ..._celebrations.map((c) => _celebrationCard(context, c)),
        ],
        const SizedBox(height: 12),
        _addNewCard(context, ty),
      ],
    );
  }

  List<Widget> _buildSkeletons(TyColors ty) {
    return List.generate(
      3,
      (_) => Shimmer.fromColors(
        baseColor: ty.line,
        highlightColor: ty.surface2,
        child: Container(
          margin: const EdgeInsets.only(bottom: 12),
          height: 84,
          decoration: BoxDecoration(
            color: ty.surface,
            borderRadius: BorderRadius.circular(20),
          ),
        ),
      ),
    );
  }

  Widget _buildError(TyColors ty) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 32),
      child: Column(
        children: [
          Icon(Icons.error_outline_rounded, size: 48, color: ty.rose),
          const SizedBox(height: 12),
          Text(_error!, style: TyType.sans(14, color: ty.ink2), textAlign: TextAlign.center),
          const SizedBox(height: 16),
          TextButton(
            onPressed: _load,
            child: Text('Try Again', style: TyType.sans(14, color: ty.saffron, weight: FontWeight.w700)),
          ),
        ],
      ),
    );
  }

  Widget _buildEmpty(BuildContext context, TyColors ty) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 40),
      child: Column(
        children: [
          Icon(Icons.event_note_outlined, size: 56, color: ty.ink3),
          const SizedBox(height: 16),
          Text('No celebrations yet',
              style: TyType.display(20, color: ty.ink), textAlign: TextAlign.center),
          const SizedBox(height: 8),
          Text(
            'Start planning your first unforgettable event.',
            style: TyType.sans(14, color: ty.ink2, height: 1.5),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),
          GestureDetector(
            onTap: () => Navigator.of(context)
                .push(MaterialPageRoute(builder: (_) => const PlanFlowScreen()))
                .then((_) => _load()),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
              decoration: BoxDecoration(
                color: ty.saffron,
                borderRadius: BorderRadius.circular(16),
              ),
              child: Text('Start Planning',
                  style: TyType.sans(15, color: Colors.white, weight: FontWeight.w700)),
            ),
          ),
        ],
      ),
    );
  }

  Widget _celebrationCard(BuildContext context, Celebration c) {
    final ty = context.ty;
    final title = c.title;
    final occasionName = c.occasionName ?? '';
    final tint = _tintFor(occasionName);
    final dateStr = _dateLabel(c.celebrationDate);
    final status = c.status ?? 'planning';

    return GestureDetector(
      onTap: () => Navigator.of(context)
          .push(MaterialPageRoute(builder: (_) => EventHubScreen(celebrationId: c.id)))
          .then((_) => _load()),
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(13),
        decoration: BoxDecoration(
          color: ty.surface,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: ty.line),
        ),
        child: Row(
          children: [
            SizedBox(
              width: 58,
              height: 58,
              child: PhotoPlaceholder(tint: tint, arch: false),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '${occasionName.isNotEmpty ? occasionName : 'Celebration'}${dateStr.isNotEmpty ? ' · $dateStr' : ''}'.toUpperCase(),
                    style: TyType.eyebrow(11, color: ty.tint(tint)),
                  ),
                  const SizedBox(height: 3),
                  Text(title, style: TyType.sans(16, color: ty.ink, weight: FontWeight.w700)),
                  const SizedBox(height: 9),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(3),
                    child: LinearProgressIndicator(
                      value: _statusProgress(status),
                      minHeight: 5,
                      backgroundColor: ty.surface2,
                      color: ty.saffron,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            Column(
              children: [
                Text('${(_statusProgress(status) * 100).round()}%',
                    style: TyType.sans(15, color: ty.ink, weight: FontWeight.w800)),
                Text(_capitalise(status), style: TyType.sans(10.5, color: ty.ink3)),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _addNewCard(BuildContext context, TyColors ty) {
    return GestureDetector(
      onTap: () => Navigator.of(context)
          .push(MaterialPageRoute(builder: (_) => const PlanFlowScreen()))
          .then((_) => _load()),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: ty.line, width: 1.5),
        ),
        child: Row(
          children: [
            Container(
              width: 46,
              height: 46,
              decoration: BoxDecoration(
                color: ty.saffronSoft,
                borderRadius: BorderRadius.circular(14),
              ),
              child: Icon(Icons.add_rounded, color: ty.saffronDeep, size: 22),
            ),
            const SizedBox(width: 13),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Plan a new celebration',
                      style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
                  const SizedBox(height: 2),
                  Text('Start from any occasion', style: TyType.sans(12.5, color: ty.ink2)),
                ],
              ),
            ),
            Icon(Icons.chevron_right_rounded, color: ty.ink3),
          ],
        ),
      ),
    );
  }

  static double _statusProgress(String status) {
    switch (status.toLowerCase()) {
      case 'idea': return 0.1;
      case 'planning': return 0.35;
      case 'confirmed': return 0.6;
      case 'in_progress': return 0.8;
      case 'completed': return 1.0;
      default: return 0.2;
    }
  }

  static String _capitalise(String s) =>
      s.isEmpty ? s : '${s[0].toUpperCase()}${s.substring(1).toLowerCase().replaceAll('_', ' ')}';
}
