import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/models.dart';
import '../data/services/celebration_service.dart';
import '../widgets/common.dart';
import '../widgets/state_screens.dart';
import '../l10n/generated/app_localizations.dart';

Map<String, String> _kEventTypeLabels(BuildContext context) {
  final l10n = AppLocalizations.of(context)!;
  return <String, String>{
    'invited': l10n.guestHistoryEventInvited,
    'invitation_opened': l10n.guestHistoryEventInvitationOpened,
    'rsvp_changed': l10n.guestHistoryEventRsvpChanged,
    'checked_in': l10n.guestHistoryEventCheckedIn,
  };
}

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
      if (mounted) {
        setState(() { _error = AppLocalizations.of(context)!.guestHistoryLoadError; _isLoading = false; });
      }
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
      if (mounted) {
        setState(() { _error = AppLocalizations.of(context)!.guestHistoryLoadError; _isLoading = false; });
      }
    }
  }

  String _guestName(BuildContext context, String guestId) {
    final match = _guests.where((g) => g.id == guestId);
    return match.isNotEmpty ? match.first.name : AppLocalizations.of(context)!.guestHistoryUnknownGuestFallback;
  }

  String _describeEvent(BuildContext context, GuestHistoryEvent e) {
    final label = _kEventTypeLabels(context)[e.eventType] ?? e.eventType;
    if (e.eventType == 'rsvp_changed' && e.newStatus != null) {
      return AppLocalizations.of(context)!.guestHistoryEventWithStatus(label, e.newStatus!);
    }
    return label;
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;

    if (_isLoading && _celebrations.isEmpty) {
      return Scaffold(backgroundColor: ty.paper, body: const Center(child: CircularProgressIndicator()));
    }

    if (_celebrations.isEmpty) {
      return Scaffold(
        backgroundColor: ty.paper,
        appBar: tyAppBar(context, title: l10n.guestHistoryTitle),
        body: TyStateScreen.empty(
          title: l10n.guestHistoryNoCelebrationsTitle,
          message: l10n.guestHistoryNoCelebrationsMessage,
          icon: Icons.history_rounded,
        ),
      );
    }

    final selected = _selected!;

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: l10n.guestHistoryTitle),
      body: RefreshIndicator(
        onRefresh: _loadData,
        color: ty.saffron,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(18, 12, 18, 28),
          children: [
            if (_celebrations.length > 1) ...[
              Text(l10n.guestHistorySelectorLabel, style: TyType.eyebrow(11, color: ty.ink3)),
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
                  child: Text(l10n.guestHistoryNoActivityMessage,
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
                Text(_guestName(context, e.celebrationGuestId),
                    style: TyType.sans(14, color: ty.ink, weight: FontWeight.w700)),
                const SizedBox(height: 2),
                Text(_describeEvent(context, e), style: TyType.sans(12.5, color: ty.ink2)),
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
