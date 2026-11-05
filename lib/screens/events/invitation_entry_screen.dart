import 'package:flutter/material.dart';

import '../../data/services/event_service.dart';
import '../../data/services/invitation_service.dart' show invitationErrorMessage;
import '../../l10n/generated/app_localizations.dart';
import '../../theme/colors.dart';
import '../../theme/typography.dart';
import '../../utils/log.dart';
import '../../widgets/common.dart';
import '../../widgets/event_ui.dart';
import '../../widgets/ty_button.dart';
import 'create_event_wizard.dart';
import 'event_dashboard_screen.dart';
import 'invitation_setup_screen.dart';

/// The one starting point for both kinds of customer. Someone who booked with
/// Tyohaar sees those events; anyone can always start their own, and neither
/// path is presented as the lesser one.
class InvitationEntryScreen extends StatefulWidget {
  final EventService? service;
  const InvitationEntryScreen({super.key, this.service});

  @override
  State<InvitationEntryScreen> createState() => _InvitationEntryScreenState();
}

class _InvitationEntryScreenState extends State<InvitationEntryScreen> {
  late final EventService _service = widget.service ?? EventService();
  EventLists? _lists;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = _lists == null;
      _error = null;
    });
    try {
      final lists = await _service.list();
      if (mounted) {
        setState(() {
          _lists = lists;
          _loading = false;
        });
      }
    } catch (e) {
      logDebug('Error loading invitation events: $e');
      if (mounted) {
        setState(() {
          _error = invitationErrorMessage(e);
          _loading = false;
        });
      }
    }
  }

  Future<void> _open(Widget screen) async {
    await Navigator.of(context).push(MaterialPageRoute(builder: (_) => screen));
    if (mounted) _load();
  }

  Iterable<EventSummaryCard> _active(bool Function(EventSummaryCard) test) =>
      (_lists?.all ?? const <EventSummaryCard>[]).where((e) => e.segment != 'completed' && e.status != 'cancelled' && test(e));

  void _manage(EventSummaryCard e) {
    if (!e.invitationsConfigured) {
      _open(InvitationSetupScreen(eventId: e.id));
    } else {
      _open(EventDashboardScreen(eventId: e.id));
    }
  }

  /// Home is where occasions and packages are browsed.
  void _explorePackages() => Navigator.of(context).popUntil((r) => r.isFirst);

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final booked = _active((e) => e.isBooked).toList();
    final own = _active((e) => !e.isBooked).toList();

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: l10n.evEntryTitle),
      body: RefreshIndicator(
        onRefresh: _load,
        color: ty.saffron,
        child: ListView(
          padding: EdgeInsets.fromLTRB(18, 6, 18, 28 + MediaQuery.paddingOf(context).bottom),
          children: [
            Text(l10n.evEntrySubtitle, style: TyType.display(21, color: ty.ink)),
            const SizedBox(height: 18),
            _JourneyCard(
              icon: Icons.verified_outlined,
              badge: EventSourceBadge(booked: true),
              title: l10n.evEntryBookedTitle,
              message: l10n.evEntryBookedMessage,
              child: _bookedSection(context, booked),
            ),
            const SizedBox(height: 14),
            _JourneyCard(
              icon: Icons.edit_calendar_outlined,
              badge: EventSourceBadge(booked: false),
              title: l10n.evEntryOwnTitle,
              message: l10n.evEntryOwnMessage,
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                for (final e in own) ...[
                  _EventRow(event: e, action: _rowAction(l10n, e), onTap: () => _manage(e)),
                  const SizedBox(height: 8),
                ],
                TyButton(l10n.evEntryCreateCta, full: true, onTap: () => _open(const CreateEventWizard())),
                const SizedBox(height: 8),
                Text(l10n.evEntryOwnNote, textAlign: TextAlign.center, style: TyType.sans(12, color: ty.ink3, height: 1.4)),
              ]),
            ),
          ],
        ),
      ),
    );
  }

  String _rowAction(AppLocalizations l10n, EventSummaryCard e) =>
      e.invitationsConfigured ? l10n.evManageInvitations : l10n.evSetUpInvitations;

  Widget _bookedSection(BuildContext context, List<EventSummaryCard> booked) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    if (_loading) {
      return const Padding(padding: EdgeInsets.all(18), child: Center(child: CircularProgressIndicator()));
    }
    if (_error != null) {
      return Column(children: [
        Text(_error!, textAlign: TextAlign.center, style: TyType.sans(13, color: ty.ink2)),
        TextButton(onPressed: _load, child: Text(l10n.commonTryAgain)),
      ]);
    }
    if (booked.isEmpty) {
      return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Text(l10n.evEntryNoBookings, textAlign: TextAlign.center, style: TyType.sans(14, color: ty.ink2, weight: FontWeight.w600)),
        const SizedBox(height: 10),
        TyButton(l10n.evEntryExplorePackages, kind: TyButtonKind.ghost, full: true, onTap: _explorePackages),
      ]);
    }
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      for (final e in booked) ...[
        _EventRow(event: e, action: _rowAction(l10n, e), onTap: () => _manage(e)),
        if (e != booked.last) const SizedBox(height: 8),
      ],
    ]);
  }
}

class _JourneyCard extends StatelessWidget {
  final IconData icon;
  final Widget badge;
  final String title;
  final String message;
  final Widget child;
  const _JourneyCard({required this.icon, required this.badge, required this.title, required this.message, required this.child});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(20), border: Border.all(color: ty.line)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Align(alignment: Alignment.centerLeft, child: badge),
        const SizedBox(height: 10),
        Text(title, style: TyType.display(20, color: ty.ink)),
        const SizedBox(height: 3),
        Text(message, style: TyType.sans(13.5, color: ty.ink2, height: 1.4)),
        const SizedBox(height: 14),
        child,
      ]),
    );
  }
}

class _EventRow extends StatelessWidget {
  final EventSummaryCard event;
  final String action;
  final VoidCallback onTap;
  const _EventRow({required this.event, required this.action, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final e = event;
    return Material(
      color: ty.surface2,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.fromLTRB(14, 12, 10, 12),
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(14), border: Border.all(color: ty.line)),
          child: Row(children: [
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(e.title, maxLines: 1, overflow: TextOverflow.ellipsis, style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
                const SizedBox(height: 2),
                Text([eventDateRange(context, e.date, e.endDate), if (e.location.isNotEmpty) e.location].join(' · '),
                    maxLines: 2, overflow: TextOverflow.ellipsis, style: TyType.sans(12.5, color: ty.ink3)),
                if (e.isBooked && e.bookingStatus != null)
                  Text(l10n.evBookingStatusLine(_bookingStatus(l10n, e.bookingStatus!)),
                      style: TyType.sans(12, color: ty.ink2, weight: FontWeight.w600)),
                const SizedBox(height: 5),
                Text(action, style: TyType.sans(13, color: ty.saffronDeep, weight: FontWeight.w700)),
              ]),
            ),
            Icon(Icons.chevron_right_rounded, color: ty.ink3),
          ]),
        ),
      ),
    );
  }

  String _bookingStatus(AppLocalizations l10n, String s) => switch (s) {
        'pending' => l10n.evBookingPending,
        'confirmed' => l10n.evBookingConfirmed,
        'in_progress' => l10n.evBookingInProgress,
        'completed' => l10n.evBookingCompleted,
        'rescheduled' => l10n.evBookingRescheduled,
        _ => s,
      };
}
