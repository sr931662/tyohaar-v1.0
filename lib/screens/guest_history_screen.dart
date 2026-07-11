import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/models.dart';
import '../data/services/celebration_service.dart';
import '../widgets/common.dart';
import '../widgets/state_screens.dart';

const _kEventTypeLabels = <String, String>{
  'invited': 'Invited',
  'invitation_opened': 'Opened the invite',
  'rsvp_changed': 'RSVP updated',
  'checked_in': 'Checked in',
};

const _kEventTypeIcons = <String, IconData>{
  'invited': Icons.mail_outline_rounded,
  'invitation_opened': Icons.visibility_outlined,
  'rsvp_changed': Icons.event_available_outlined,
  'checked_in': Icons.how_to_reg_outlined,
};

class GuestHistoryScreen extends StatefulWidget {
  const GuestHistoryScreen({super.key});

  @override
  State<GuestHistoryScreen> createState() => _GuestHistoryScreenState();
}

class _GuestHistoryScreenState extends State<GuestHistoryScreen> {
  final CelebrationService _celebrationService = CelebrationService();

  List<Celebration> _celebrations = [];
  Celebration? _selected;
  List<Guest> _guests = [];
  List<GuestHistoryEvent> _history = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() { _isLoading = true; _error = null; });
    try {
      final celebrations = await _celebrationService.listCelebrations();
      if (celebrations.isEmpty) {
        if (mounted) setState(() { _celebrations = []; _isLoading = false; });
        return;
      }
      final selected = _selected != null
          ? celebrations.firstWhere((c) => c.id == _selected!.id, orElse: () => celebrations.first)
          : celebrations.first;
      await _loadForCelebration(selected, celebrations);
    } catch (e) {
      if (mounted) setState(() { _error = 'Could not load guest history.'; _isLoading = false; });
    }
  }

  Future<void> _loadForCelebration(Celebration c, [List<Celebration>? all]) async {
    setState(() { _selected = c; _isLoading = true; });
    try {
      final results = await Future.wait([
        _celebrationService.listGuests(c.id),
        _celebrationService.listGuestHistory(c.id),
      ]);
      if (mounted) {
        setState(() {
          if (all != null) _celebrations = all;
          _guests = results[0] as List<Guest>;
          _history = results[1] as List<GuestHistoryEvent>;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) setState(() { _error = 'Could not load guest history.'; _isLoading = false; });
    }
  }

  String _guestName(String guestId) {
    final match = _guests.where((g) => g.id == guestId);
    return match.isNotEmpty ? match.first.name : 'A guest';
  }

  String _describeEvent(GuestHistoryEvent e) {
    final label = _kEventTypeLabels[e.eventType] ?? e.eventType;
    if (e.eventType == 'rsvp_changed' && e.newStatus != null) {
      return '$label to ${e.newStatus}';
    }
    return label;
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;

    if (_isLoading && _celebrations.isEmpty) {
      return Scaffold(backgroundColor: ty.paper, body: const Center(child: CircularProgressIndicator()));
    }

    if (_celebrations.isEmpty) {
      return Scaffold(
        backgroundColor: ty.paper,
        appBar: tyAppBar(context, title: 'Guest History'),
        body: TyStateScreen.empty(
          title: 'No celebrations yet',
          message: 'Once you start planning, guest activity will show up here.',
          icon: Icons.history_rounded,
        ),
      );
    }

    final selected = _selected!;

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: 'Guest History'),
      body: RefreshIndicator(
        onRefresh: _loadData,
        color: ty.saffron,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(18, 12, 18, 28),
          children: [
            if (_celebrations.length > 1) ...[
              Text('EVENT', style: TyType.eyebrow(11, color: ty.ink3)),
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14),
                decoration: BoxDecoration(
                  color: ty.surface2,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: ty.line),
                ),
                child: DropdownButtonHideUnderline(
                  child: DropdownButton<String>(
                    value: selected.id,
                    isExpanded: true,
                    items: _celebrations
                        .map((c) => DropdownMenuItem(
                            value: c.id,
                            child: Text(c.title, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w600))))
                        .toList(),
                    onChanged: (id) {
                      final c = _celebrations.firstWhere((c) => c.id == id);
                      _loadForCelebration(c);
                    },
                  ),
                ),
              ),
              const SizedBox(height: 20),
            ],
            if (_error != null)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 24),
                child: Center(child: Text(_error!, style: TyType.sans(14, color: ty.ink2))),
              )
            else if (_history.isEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 40),
                child: Center(
                  child: Text('No guest activity yet for this celebration.',
                      style: TyType.sans(14, color: ty.ink2)),
                ),
              )
            else
              ..._history.map((e) => _historyRow(context, e)),
          ],
        ),
      ),
    );
  }

  Widget _historyRow(BuildContext context, GuestHistoryEvent e) {
    final ty = context.ty;
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: ty.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: ty.line),
      ),
      child: Row(
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(color: ty.saffronSoft, borderRadius: BorderRadius.circular(10)),
            child: Icon(_kEventTypeIcons[e.eventType] ?? Icons.circle_outlined,
                color: ty.saffronDeep, size: 18),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(_guestName(e.celebrationGuestId),
                    style: TyType.sans(14, color: ty.ink, weight: FontWeight.w700)),
                const SizedBox(height: 2),
                Text(_describeEvent(e), style: TyType.sans(12.5, color: ty.ink2)),
              ],
            ),
          ),
          Text(DateFormat('d MMM, h:mm a').format(e.occurredAt),
              style: TyType.sans(11, color: ty.ink3)),
        ],
      ),
    );
  }
}
