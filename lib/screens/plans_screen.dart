import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shimmer/shimmer.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../theme/responsive.dart';
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
    final resp = context.resp;
    final topPadding = MediaQuery.of(context).padding.top + resp.h(85);

    return RefreshIndicator(
      onRefresh: _load,
      displacement: topPadding,
      color: ty.saffron,
      child: ListView(
        padding: EdgeInsets.fromLTRB(resp.w(18), topPadding, resp.w(18),
            resp.h(28) + MediaQuery.of(context).padding.bottom),
        children: [
          Row(
            children: [
              Expanded(child: Text('Your plans', style: TyType.display(resp.sp(26), color: ty.ink))),
              ChromeIconButton(
                icon: Icons.add_rounded,
                onTap: () => Navigator.of(context)
                    .push(MaterialPageRoute(builder: (_) => const PlanFlowScreen()))
                    .then((_) => _load()),
              ),
            ],
          ),
          SizedBox(height: resp.h(22)),
          if (_loading && _celebrations.isEmpty) ..._buildSkeletons(ty, resp),
          if (!_loading && _error != null) _buildError(ty, resp),
          if (!_loading && _error == null && _celebrations.isEmpty) _buildEmpty(context, ty, resp),
          if (_celebrations.isNotEmpty) ...[
            SectionHeader('In progress'),
            ..._celebrations.map((c) => _celebrationCard(context, c)),
          ],
          SizedBox(height: resp.h(12)),
          _addNewCard(context, ty, resp),
        ],
      ),
    );
  }

  List<Widget> _buildSkeletons(TyColors ty, TyResponsive resp) {
    return List.generate(
      3,
      (_) => Shimmer.fromColors(
        baseColor: ty.line,
        highlightColor: ty.surface2,
        child: Container(
          margin: EdgeInsets.only(bottom: resp.h(12)),
          height: resp.h(84),
          decoration: BoxDecoration(
            color: ty.surface,
            borderRadius: BorderRadius.circular(resp.w(20)),
          ),
        ),
      ),
    );
  }

  Widget _buildError(TyColors ty, TyResponsive resp) {
    return Padding(
      padding: EdgeInsets.symmetric(vertical: resp.h(32)),
      child: Column(
        children: [
          Icon(Icons.error_outline_rounded, size: resp.sp(48), color: ty.rose),
          SizedBox(height: resp.h(12)),
          Text(_error!, style: TyType.sans(resp.sp(14), color: ty.ink2), textAlign: TextAlign.center),
          SizedBox(height: resp.h(16)),
          TextButton(
            onPressed: _load,
            child: Text('Try Again', style: TyType.sans(resp.sp(14), color: ty.saffron, weight: FontWeight.w700)),
          ),
        ],
      ),
    );
  }

  Widget _buildEmpty(BuildContext context, TyColors ty, TyResponsive resp) {
    return Padding(
      padding: EdgeInsets.symmetric(vertical: resp.h(40)),
      child: Column(
        children: [
          Icon(Icons.event_note_outlined, size: resp.sp(56), color: ty.ink3),
          SizedBox(height: resp.h(16)),
          Text('No celebrations yet',
              style: TyType.display(resp.sp(20), color: ty.ink), textAlign: TextAlign.center),
          SizedBox(height: resp.h(8)),
          Text(
            'Start planning your first unforgettable event.',
            style: TyType.sans(resp.sp(14), color: ty.ink2, height: 1.5),
            textAlign: TextAlign.center,
          ),
          SizedBox(height: resp.h(24)),
          GestureDetector(
            onTap: () => Navigator.of(context)
                .push(MaterialPageRoute(builder: (_) => const PlanFlowScreen()))
                .then((_) => _load()),
            child: Container(
              padding: EdgeInsets.symmetric(horizontal: resp.w(24), vertical: resp.h(14)),
              decoration: BoxDecoration(
                color: ty.saffron,
                borderRadius: BorderRadius.circular(resp.w(16)),
              ),
              child: Text('Start Planning',
                  style: TyType.sans(resp.sp(15), color: Colors.white, weight: FontWeight.w700)),
            ),
          ),
        ],
      ),
    );
  }

  Widget _celebrationCard(BuildContext context, Celebration c) {
    final ty = context.ty;
    final resp = context.resp;
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
        margin: EdgeInsets.only(bottom: resp.h(12)),
        padding: EdgeInsets.all(resp.w(13)),
        decoration: BoxDecoration(
          color: ty.surface,
          borderRadius: BorderRadius.circular(resp.w(20)),
          border: Border.all(color: ty.line),
        ),
        child: Row(
          children: [
            SizedBox(
              width: resp.w(58),
              height: resp.w(58),
              child: PhotoPlaceholder(tint: tint, arch: false),
            ),
            SizedBox(width: resp.w(14)),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '${occasionName.isNotEmpty ? occasionName : 'Celebration'}${dateStr.isNotEmpty ? ' · $dateStr' : ''}'.toUpperCase(),
                    style: TyType.eyebrow(resp.sp(11), color: ty.tint(tint)),
                  ),
                  SizedBox(height: resp.h(3)),
                  Text(title, style: TyType.sans(resp.sp(16), color: ty.ink, weight: FontWeight.w700)),
                  SizedBox(height: resp.h(9)),
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
            SizedBox(width: resp.w(12)),
            Column(
              children: [
                Text('${(_statusProgress(status) * 100).round()}%',
                    style: TyType.sans(resp.sp(15), color: ty.ink, weight: FontWeight.w800)),
                Text(_capitalise(status), style: TyType.sans(resp.sp(10.5), color: ty.ink3)),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _addNewCard(BuildContext context, TyColors ty, TyResponsive resp) {
    return GestureDetector(
      onTap: () => Navigator.of(context)
          .push(MaterialPageRoute(builder: (_) => const PlanFlowScreen()))
          .then((_) => _load()),
      child: Container(
        padding: EdgeInsets.all(resp.w(16)),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(resp.w(20)),
          border: Border.all(color: ty.line, width: 1.5),
        ),
        child: Row(
          children: [
            Container(
              width: resp.w(46),
              height: resp.w(46),
              decoration: BoxDecoration(
                color: ty.saffronSoft,
                borderRadius: BorderRadius.circular(resp.w(14)),
              ),
              child: Icon(Icons.add_rounded, color: ty.saffronDeep, size: resp.sp(22)),
            ),
            SizedBox(width: resp.w(13)),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Plan a new celebration',
                      style: TyType.sans(resp.sp(15), color: ty.ink, weight: FontWeight.w700)),
                  SizedBox(height: resp.h(2)),
                  Text('Start from any occasion', style: TyType.sans(resp.sp(12.5), color: ty.ink2)),
                ],
              ),
            ),
            Icon(Icons.chevron_right_rounded, color: ty.ink3, size: resp.sp(20)),
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
