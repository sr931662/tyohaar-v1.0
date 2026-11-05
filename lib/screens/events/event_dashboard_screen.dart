import 'package:cached_network_image/cached_network_image.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../data/services/event_service.dart';
import '../../data/services/invitation_service.dart' show invitationErrorMessage;
import '../../l10n/generated/app_localizations.dart';
import '../../theme/colors.dart';
import '../../theme/typography.dart';
import '../../widgets/event_ui.dart';
import '../../widgets/state_screens.dart';
import '../../widgets/ty_button.dart';
import '../invitation_management_screen.dart';
import '../invitations/gate_scan_screen.dart';
import '../invitations/invitation_form_screen.dart';
import '../invitations/invitation_labels.dart';
import 'functions_editor.dart';
import 'households_screen.dart';
import 'invitation_setup_screen.dart';
import 'reminders_screen.dart';

/// One event's invitations, the same screen for both kinds of customer.
/// Every number is the server's, computed from real guests and responses.
/// The Guests tab is the existing guest, pass and gate screen, embedded.
class EventDashboardScreen extends StatefulWidget {
  final String eventId;
  final EventService? service;
  final bool justPublished;
  final int initialTab;

  const EventDashboardScreen({
    super.key,
    required this.eventId,
    this.service,
    this.justPublished = false,
    this.initialTab = 0,
  });

  @override
  State<EventDashboardScreen> createState() => _EventDashboardScreenState();
}

class _EventDashboardScreenState extends State<EventDashboardScreen> with SingleTickerProviderStateMixin {
  late final EventService _service = widget.service ?? EventService();
  late final TabController _tabs;
  EventDetail? _event;
  EventAnalytics? _analytics;
  bool _loading = true;
  bool _failed = false;
  bool _permissionDenied = false;

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 6, vsync: this, initialIndex: widget.initialTab);
    _load();
    if (widget.justPublished) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(AppLocalizations.of(context)!.evPublishedMessage)));
        }
      });
    }
  }

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = _event == null;
      _failed = false;
    });
    try {
      final results = await Future.wait([_service.get(widget.eventId), _service.analytics(widget.eventId)]);
      if (!mounted) return;
      setState(() {
        _event = results[0] as EventDetail;
        _analytics = results[1] as EventAnalytics;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      final message = e.toString();
      setState(() {
        _loading = false;
        _failed = _event == null;
        _permissionDenied = message.contains('404') || message.contains('403');
      });
    }
  }

  Future<void> _open(Widget screen) async {
    await Navigator.of(context).push(MaterialPageRoute(builder: (_) => screen));
    if (mounted) _load();
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final event = _event;
    if (_loading) {
      return Scaffold(backgroundColor: ty.paper, body: const Center(child: CircularProgressIndicator()));
    }
    if (_failed || event == null) {
      return Scaffold(
        backgroundColor: ty.paper,
        appBar: AppBar(backgroundColor: ty.paper, elevation: 0),
        body: _permissionDenied
            ? EventEmpty(icon: Icons.lock_outline_rounded, title: l10n.evNoAccessTitle, message: l10n.evNoAccessMessage)
            : TyStateScreen.error(context, onAction: _load),
      );
    }
    return Scaffold(
      backgroundColor: ty.paper,
      appBar: AppBar(
        backgroundColor: ty.paper,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        scrolledUnderElevation: 0,
        title: Text(event.title, maxLines: 1, overflow: TextOverflow.ellipsis,
            style: TyType.sans(16, color: ty.ink, weight: FontWeight.w700)),
        bottom: TabBar(
          controller: _tabs,
          isScrollable: true,
          tabAlignment: TabAlignment.start,
          labelColor: ty.saffronDeep,
          unselectedLabelColor: ty.ink3,
          indicatorColor: ty.saffron,
          labelStyle: TyType.sans(13.5, weight: FontWeight.w700),
          tabs: [
            Tab(text: l10n.evDashOverview),
            Tab(text: l10n.evDashGuests),
            Tab(text: l10n.evDashInvitations),
            Tab(text: l10n.evDashRsvps),
            Tab(text: l10n.evDashFood),
            Tab(text: l10n.evDashActivity),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabs,
        children: [
          _OverviewTab(event: event, analytics: _analytics, onRefresh: _load, onOpen: _open, onSelectTab: (i) => _tabs.animateTo(i)),
          InvitationManagementScreen(celebrationId: event.id, embedded: true),
          _InvitationsTab(event: event, service: _service, onChanged: _load, onOpen: _open),
          _RsvpsTab(event: event, service: _service),
          _FoodTab(event: event, service: _service, onChanged: _load),
          _ActivityTab(eventId: event.id, service: _service),
        ],
      ),
    );
  }
}

// ── Overview ─────────────────────────────────────────────────────────────────

class _OverviewTab extends StatelessWidget {
  final EventDetail event;
  final EventAnalytics? analytics;
  final Future<void> Function() onRefresh;
  final Future<void> Function(Widget) onOpen;
  final ValueChanged<int> onSelectTab;

  const _OverviewTab({required this.event, this.analytics, required this.onRefresh, required this.onOpen, required this.onSelectTab});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final a = analytics;
    final e = event;
    return RefreshIndicator(
      onRefresh: onRefresh,
      color: ty.saffron,
      child: ListView(
        padding: EdgeInsets.fromLTRB(18, 14, 18, 28 + MediaQuery.paddingOf(context).bottom),
        children: [
          _Header(event: e),
          if (e.isDraft) ...[
            const SizedBox(height: 12),
            _Banner(
              icon: Icons.drafts_outlined,
              text: l10n.evDraftBanner,
              action: l10n.evFinishSetup,
              onTap: () => onOpen(InvitationSetupScreen(eventId: e.id, initialStep: 4)),
            ),
          ] else if (!e.invitationsConfigured) ...[
            const SizedBox(height: 12),
            _Banner(
              icon: Icons.auto_awesome_outlined,
              text: l10n.evSetUpInvitations,
              action: l10n.evSetUpCta,
              onTap: () => onOpen(InvitationSetupScreen(eventId: e.id)),
            ),
          ],
          const SizedBox(height: 16),
          Row(children: [
            _Tile(value: a?.generated, label: l10n.evStatInvited, color: ty.ink),
            const SizedBox(width: 8),
            _Tile(value: a?.confirmed, label: l10n.evStatConfirmed, color: ty.leaf),
            const SizedBox(width: 8),
            _Tile(value: a?.pending, label: l10n.evStatPending, color: ty.saffronDeep),
            const SizedBox(width: 8),
            _Tile(value: a?.declined, label: l10n.evStatDeclined, color: ty.rose),
          ]),
          const SizedBox(height: 14),
          if (a != null && a.generated > 0) _ResponseRate(a: a),
          const SizedBox(height: 16),
          Text(l10n.evQuickActions, style: TyType.eyebrow(11, color: ty.ink3)),
          const SizedBox(height: 10),
          GridView.count(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            crossAxisCount: 3,
            mainAxisSpacing: 8,
            crossAxisSpacing: 8,
            childAspectRatio: 1.15,
            children: [
              _Action(Icons.style_outlined, l10n.evActionCreate, () => onOpen(InvitationSetupScreen(eventId: e.id))),
              _Action(Icons.person_add_alt_1_rounded, l10n.evActionAddGuest, () => onOpen(InvitationFormScreen(celebrationId: e.id))),
              _Action(Icons.ios_share_rounded, l10n.evActionShare, () => onSelectTab(1)),
              _Action(Icons.notifications_active_outlined, l10n.evActionRemind, () => onOpen(RemindersScreen(event: e))),
              if (e.entitlements.qrCheckIn)
                _Action(Icons.qr_code_scanner_rounded, l10n.evActionCheckIn,
                    () => onOpen(GateScanScreen(celebrationId: e.id, celebrationTitle: e.title))),
            ],
          ),
          if (a != null && a.functions.isNotEmpty) ...[
            const SizedBox(height: 20),
            EventSection(
              title: l10n.evFunctionWise,
              children: [for (final f in a.functions) _FunctionRow(f: f)],
            ),
          ],
          if (a != null && a.generated > 0) ...[
            const SizedBox(height: 18),
            EventSection(
              title: l10n.evFunnelTitle,
              subtitle: l10n.evFunnelNote,
              children: [
                _FunnelRow(l10n.evFunnelGenerated, a.generated, a.generated),
                _FunnelRow(l10n.evFunnelShared, a.shared, a.generated),
                _FunnelRow(l10n.evFunnelAccessed, a.linkAccessed, a.generated),
                _FunnelRow(l10n.evFunnelVisited, a.qualifiedVisits, a.generated),
                _FunnelRow(l10n.evFunnelStarted, a.rsvpStarted, a.generated),
                _FunnelRow(l10n.evFunnelResponded, a.responded, a.generated),
                if (a.arrivedGuests > 0) _FunnelRow(l10n.evFunnelCheckedIn, a.arrivedGuests, a.generated),
                if (a.generalLinkVisits > 0)
                  Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Text(l10n.evGeneralVisits(a.generalLinkVisits), style: TyType.sans(12.5, color: ty.ink3)),
                  ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class _Header extends StatelessWidget {
  final EventDetail event;
  const _Header({required this.event});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final e = event;
    final cover = e.coverImageUrl;
    return Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
      ClipRRect(
        borderRadius: BorderRadius.circular(14),
        child: SizedBox(
          width: 72,
          height: 72,
          child: cover == null
              ? ColoredBox(color: kInvitationBurgundy, child: Icon(Icons.celebration_outlined, color: kInvitationGold))
              : CachedNetworkImage(
                  imageUrl: cover,
                  fit: BoxFit.cover,
                  memCacheWidth: 220,
                  errorWidget: (_, __, ___) =>
                      const ColoredBox(color: kInvitationBurgundy, child: Icon(Icons.celebration_outlined, color: kInvitationGold)),
                ),
        ),
      ),
      const SizedBox(width: 12),
      Expanded(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          EventSourceBadge(booked: e.isBooked),
          const SizedBox(height: 5),
          Text(eventDateRange(context, e.date, e.endDate), style: TyType.sans(14, color: ty.ink, weight: FontWeight.w700)),
          if (e.location.isNotEmpty)
            Text(e.location, maxLines: 2, overflow: TextOverflow.ellipsis, style: TyType.sans(12.5, color: ty.ink3)),
          const SizedBox(height: 2),
          Text(eventStatusLine(l10n, e), style: TyType.sans(12.5, color: ty.saffronDeep, weight: FontWeight.w700)),
        ]),
      ),
    ]);
  }
}

class _Banner extends StatelessWidget {
  final IconData icon;
  final String text;
  final String action;
  final VoidCallback onTap;
  const _Banner({required this.icon, required this.text, required this.action, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 10, 8, 10),
      decoration: BoxDecoration(color: ty.saffronSoft, borderRadius: BorderRadius.circular(14)),
      child: Row(children: [
        Icon(icon, size: 18, color: ty.saffronDeep),
        const SizedBox(width: 10),
        Expanded(child: Text(text, style: TyType.sans(13, color: ty.ink, weight: FontWeight.w600))),
        TextButton(onPressed: onTap, child: Text(action)),
      ]),
    );
  }
}

class _Tile extends StatelessWidget {
  final int? value;
  final String label;
  final Color color;
  const _Tile({this.value, required this.label, required this.color});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 3),
        decoration: eventCardDecoration(ty),
        child: Column(children: [
          Text(value?.toString() ?? '–', maxLines: 1, style: TyType.display(21, color: color)),
          const SizedBox(height: 2),
          Text(label, maxLines: 1, overflow: TextOverflow.ellipsis, style: TyType.sans(11, color: ty.ink3, weight: FontWeight.w600)),
        ]),
      ),
    );
  }
}

class _ResponseRate extends StatelessWidget {
  final EventAnalytics a;
  const _ResponseRate({required this.a});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final percent = (a.responseRate * 100).round();
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: eventCardDecoration(ty),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text(l10n.evResponseRate, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w700))),
          Text('$percent%', style: TyType.display(19, color: ty.saffronDeep)),
        ]),
        const SizedBox(height: 8),
        ClipRRect(
          borderRadius: BorderRadius.circular(9),
          child: LinearProgressIndicator(
            value: a.responseRate.clamp(0, 1),
            minHeight: 7,
            backgroundColor: ty.line,
            valueColor: AlwaysStoppedAnimation(ty.saffron),
            semanticsLabel: l10n.evResponseRate,
            semanticsValue: '$percent%',
          ),
        ),
        const SizedBox(height: 8),
        // Says what it counts: "maybe" and "no" are responses, not attendance.
        Text(l10n.evResponseRateNote(a.responded, a.generated, a.confirmed, a.expectedPeople),
            style: TyType.sans(12, color: ty.ink3, height: 1.35)),
      ]),
    );
  }
}

class _Action extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;
  const _Action(this.icon, this.label, this.onTap);

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return Material(
      color: ty.surface,
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 8),
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(16), border: Border.all(color: ty.line)),
          child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
            Icon(icon, color: ty.saffronDeep),
            const SizedBox(height: 6),
            Text(label, textAlign: TextAlign.center, maxLines: 2, overflow: TextOverflow.ellipsis,
                style: TyType.sans(12, color: ty.ink, weight: FontWeight.w700)),
          ]),
        ),
      ),
    );
  }
}

class _FunctionRow extends StatelessWidget {
  final FunctionNumbers f;
  const _FunctionRow({required this.f});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final progress = f.invited == 0 ? 0.0 : f.confirmed / f.invited;
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: eventCardDecoration(ty),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text(f.name, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w700))),
          if (f.isCancelled)
            Text(l10n.evFunctionCancelled, style: TyType.sans(12, color: ty.rose, weight: FontWeight.w700))
          else if (f.date != null)
            Text(DateFormat('d MMM').format(f.date!), style: TyType.sans(12, color: ty.ink3)),
        ]),
        const SizedBox(height: 4),
        Text(
          f.maybe > 0
              ? l10n.evFunctionNumbersMaybe(f.invited, f.confirmed, f.maybe, f.pending, f.declined)
              : l10n.evFunctionNumbers(f.invited, f.confirmed, f.pending, f.declined),
          style: TyType.sans(12.5, color: ty.ink2),
        ),
        if (f.confirmedPeople != f.confirmed)
          Text(l10n.evFunctionPeople(f.confirmedPeople), style: TyType.sans(12, color: ty.ink3)),
        const SizedBox(height: 7),
        ClipRRect(
          borderRadius: BorderRadius.circular(9),
          child: LinearProgressIndicator(value: progress, minHeight: 5, backgroundColor: ty.line, valueColor: AlwaysStoppedAnimation(ty.leaf)),
        ),
      ]),
    );
  }
}

class _FunnelRow extends StatelessWidget {
  final String label;
  final int value;
  final int total;
  const _FunnelRow(this.label, this.value, this.total);

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(children: [
        Expanded(child: Text(label, style: TyType.sans(13.5, color: ty.ink2))),
        Text('$value', style: TyType.sans(14, color: ty.ink, weight: FontWeight.w700)),
        Text(' / $total', style: TyType.sans(12.5, color: ty.ink3)),
      ]),
    );
  }
}

// ── Invitations ──────────────────────────────────────────────────────────────

class _InvitationsTab extends StatefulWidget {
  final EventDetail event;
  final EventService service;
  final Future<void> Function() onChanged;
  final Future<void> Function(Widget) onOpen;
  const _InvitationsTab({required this.event, required this.service, required this.onChanged, required this.onOpen});

  @override
  State<_InvitationsTab> createState() => _InvitationsTabState();
}

class _InvitationsTabState extends State<_InvitationsTab> {
  bool _busy = false;

  void _snack(String m) {
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));
  }

  Future<void> _run(Future<void> Function() action) async {
    setState(() => _busy = true);
    try {
      await action();
      await widget.onChanged();
    } catch (e) {
      _snack(invitationErrorMessage(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _preview() async {
    final l10n = AppLocalizations.of(context)!;
    try {
      final url = await widget.service.previewLink(widget.event.id);
      await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
    } catch (_) {
      _snack(l10n.evPreviewFailed);
    }
  }

  Future<void> _import() async {
    final l10n = AppLocalizations.of(context)!;
    final picked = await FilePicker.platform.pickFiles(type: FileType.custom, allowedExtensions: const ['csv', 'xlsx']);
    final file = picked?.files.single;
    if (file?.path == null || !mounted) return;
    setState(() => _busy = true);
    try {
      final outcome = await widget.service.importGuests(widget.event.id, file!.path!, file.name);
      await widget.onChanged();
      if (!mounted) return;
      final problems = outcome.rows.where((r) => r.status == 'error' || r.status == 'duplicate').toList();
      await showDialog<void>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: Text(l10n.evImportDone(outcome.created, outcome.skipped)),
          content: SizedBox(
            width: double.maxFinite,
            child: problems.isEmpty
                ? Text(l10n.evImportAllGood)
                : ListView(shrinkWrap: true, children: [
                    for (final r in problems.take(50))
                      Padding(
                        padding: const EdgeInsets.only(bottom: 6),
                        child: Text(l10n.evImportRow(r.row, r.name ?? '—', r.message ?? ''), style: const TextStyle(fontSize: 13)),
                      ),
                  ]),
          ),
          actions: [TextButton(onPressed: () => Navigator.pop(ctx), child: Text(l10n.invDone))],
        ),
      );
    } catch (e) {
      _snack(invitationErrorMessage(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final e = widget.event;
    final generalOn = e.generalLinkUrl != null;
    return ListView(
      padding: EdgeInsets.fromLTRB(18, 14, 18, 28 + MediaQuery.paddingOf(context).bottom),
      children: [
        EventSection(
          title: l10n.evInvitationStatus,
          children: [
            Container(
              padding: const EdgeInsets.all(14),
              decoration: eventCardDecoration(ty),
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                Text(e.isDraft ? l10n.evStatusDraftLine : l10n.evStatusPublishedLine,
                    style: TyType.sans(13.5, color: ty.ink2, height: 1.4)),
                const SizedBox(height: 12),
                Row(children: [
                  Expanded(child: TyButton(l10n.evEditInvitation, kind: TyButtonKind.ghost, full: true,
                      onTap: () => widget.onOpen(InvitationSetupScreen(eventId: e.id)))),
                  const SizedBox(width: 8),
                  Expanded(child: TyButton(l10n.evPreviewShort, kind: TyButtonKind.ghost, full: true, onTap: _preview)),
                ]),
                const SizedBox(height: 8),
                if (e.isDraft)
                  TyButton(l10n.evPublish, full: true, enabled: !_busy, onTap: () => _run(() => widget.service.publish(e.id)))
                else
                  TextButton(
                    onPressed: _busy ? null : () => _run(() => widget.service.unpublish(e.id)),
                    child: Text(l10n.evUnpublish),
                  ),
              ]),
            ),
          ],
        ),
        const SizedBox(height: 18),
        EventSection(
          title: l10n.evGeneralLinkTitle,
          subtitle: l10n.evGeneralLinkNote,
          children: [
            EventTileCard(
              child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                SwitchListTile.adaptive(
                  contentPadding: EdgeInsets.zero,
                  value: generalOn,
                  activeTrackColor: ty.saffron,
                  onChanged: _busy ? null : (v) => _run(() => widget.service.setGeneralLink(e.id, enabled: v)),
                  title: Text(l10n.evGeneralLinkToggle, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w600)),
                ),
                if (generalOn) ...[
                  SelectableText(e.generalLinkUrl!, style: TyType.sans(12.5, color: ty.ink2)),
                  const SizedBox(height: 10),
                  Row(children: [
                    Expanded(
                      child: TyButton(l10n.invCopyLink, kind: TyButtonKind.ghost, full: true, onTap: () async {
                        await Clipboard.setData(ClipboardData(text: e.generalLinkUrl!));
                        _snack(l10n.evLinkCopied);
                      }),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: TyButton(l10n.invShareSheet, kind: TyButtonKind.ghost, full: true,
                          onTap: () => Share.share(l10n.evGeneralShareMessage(e.title, e.generalLinkUrl!))),
                    ),
                  ]),
                  TextButton(
                    onPressed: _busy ? null : () => _run(() => widget.service.setGeneralLink(e.id, enabled: true, rotate: true)),
                    child: Text(l10n.evGeneralLinkReplace),
                  ),
                ],
              ]),
              ),
            ),
          ],
        ),
        const SizedBox(height: 18),
        EventSection(
          title: l10n.evStepFunctions,
          children: [
            FunctionsEditor(eventId: e.id, functions: e.functions, service: widget.service, onChanged: (_) => widget.onChanged()),
          ],
        ),
        const SizedBox(height: 18),
        EventSection(
          title: l10n.evGuestListTools,
          children: [
            _ToolRow(Icons.diversity_3_rounded, l10n.evHouseholdsTitle, l10n.evHouseholdsCount(e.groups.length),
                () => widget.onOpen(HouseholdsScreen(eventId: e.id, service: widget.service))),
            _ToolRow(Icons.upload_file_rounded, l10n.evImportTitle, l10n.evImportNote, _busy ? null : _import),
          ],
        ),
      ],
    );
  }
}

class _ToolRow extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback? onTap;
  const _ToolRow(this.icon, this.title, this.subtitle, this.onTap);

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return EventTileCard(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: Icon(icon, color: ty.ink2),
        title: Text(title, style: TyType.sans(14.5, color: ty.ink, weight: FontWeight.w700)),
        subtitle: Text(subtitle, style: TyType.sans(12, color: ty.ink3)),
        trailing: Icon(Icons.chevron_right_rounded, color: ty.ink3),
        onTap: onTap,
      ),
    );
  }
}

// ── RSVPs ────────────────────────────────────────────────────────────────────

class _RsvpsTab extends StatefulWidget {
  final EventDetail event;
  final EventService service;
  const _RsvpsTab({required this.event, required this.service});

  @override
  State<_RsvpsTab> createState() => _RsvpsTabState();
}

class _RsvpsTabState extends State<_RsvpsTab> with AutomaticKeepAliveClientMixin {
  final List<RsvpRow> _rows = [];
  String? _functionId;
  String? _status;
  int _page = 1;
  bool _hasNext = false;
  bool _loading = true;
  bool _error = false;
  int _token = 0;

  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load({bool more = false}) async {
    final token = ++_token;
    setState(() {
      _loading = true;
      _error = false;
    });
    try {
      final page = await widget.service.rsvps(widget.event.id, functionId: _functionId, status: _status, page: more ? _page + 1 : 1);
      if (!mounted || token != _token) return;
      setState(() {
        if (!more) _rows.clear();
        _rows.addAll(page.items);
        _page = more ? _page + 1 : 1;
        _hasNext = page.hasNext;
        _loading = false;
      });
    } catch (_) {
      if (mounted && token == _token) {
        setState(() {
          _loading = false;
          _error = true;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final labels = InvitationLabels(context);
    return RefreshIndicator(
      onRefresh: _load,
      color: ty.saffron,
      child: ListView(
        padding: EdgeInsets.fromLTRB(18, 12, 18, 28 + MediaQuery.paddingOf(context).bottom),
        children: [
          if (widget.event.functions.isNotEmpty)
            SizedBox(
              height: 42,
              child: ListView(scrollDirection: Axis.horizontal, children: [
                _chip(l10n.evAllFunctions, _functionId == null, () => _setFunction(null)),
                for (final f in widget.event.functions) _chip(f.name, _functionId == f.id, () => _setFunction(f.id)),
              ]),
            ),
          SizedBox(
            height: 42,
            child: ListView(scrollDirection: Axis.horizontal, children: [
              _chip(l10n.invFilterAll, _status == null, () => _setStatus(null)),
              _chip(l10n.invRsvpAttending, _status == 'attending', () => _setStatus('attending')),
              _chip(l10n.invRsvpMaybe, _status == 'maybe', () => _setStatus('maybe')),
              _chip(l10n.invRsvpDeclined, _status == 'declined', () => _setStatus('declined')),
              _chip(l10n.invRsvpPending, _status == 'pending', () => _setStatus('pending')),
            ]),
          ),
          const SizedBox(height: 8),
          if (_error)
            TyStateScreen.error(context, onAction: _load)
          else if (_rows.isEmpty && _loading)
            const Padding(padding: EdgeInsets.only(top: 40), child: Center(child: CircularProgressIndicator()))
          else if (_rows.isEmpty)
            EventEmpty(icon: Icons.how_to_reg_outlined, title: l10n.evRsvpsEmpty, message: l10n.evRsvpsEmptyMessage)
          else
            for (final r in _rows)
              Container(
                margin: const EdgeInsets.only(bottom: 8),
                padding: const EdgeInsets.all(12),
                decoration: eventCardDecoration(ty),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [
                    Expanded(child: Text(r.guestName, maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: TyType.sans(14.5, color: ty.ink, weight: FontWeight.w700))),
                    Text(labels.rsvp(r.status), style: TyType.sans(12, color: labels.rsvpColor(r.status), weight: FontWeight.w700)),
                  ]),
                  const SizedBox(height: 2),
                  Text(
                    [
                      if (r.functionName != null) r.functionName!,
                      if (r.groupName != null) r.groupName!,
                      if ((r.attendeeCount ?? 0) > 1) l10n.evFunctionPeople(r.attendeeCount!),
                      if (r.dietaryType != null) dietaryLabel(l10n, r.dietaryType!),
                      if (r.mealSelection != null) r.mealSelection!,
                    ].join(' · '),
                    style: TyType.sans(12.5, color: ty.ink3),
                  ),
                  if (r.allergies != null) Text(l10n.evAllergiesLine(r.allergies!), style: TyType.sans(12.5, color: ty.rose)),
                  if (r.specialRequirements != null) Text(r.specialRequirements!, style: TyType.sans(12.5, color: ty.ink2)),
                ]),
              ),
          if (_hasNext)
            TextButton(onPressed: _loading ? null : () => _load(more: true), child: Text(l10n.evLoadMore)),
        ],
      ),
    );
  }

  void _setFunction(String? id) {
    setState(() => _functionId = id);
    _load();
  }

  void _setStatus(String? s) {
    setState(() => _status = s);
    _load();
  }

  Widget _chip(String label, bool active, VoidCallback onTap) => Padding(
        padding: const EdgeInsets.only(right: 6),
        child: ChoiceChip(label: Text(label), selected: active, onSelected: (_) => onTap()),
      );
}

String dietaryLabel(AppLocalizations l10n, String d) => switch (d) {
      'vegetarian' => l10n.evDietVegetarian,
      'non_vegetarian' => l10n.evDietNonVeg,
      'jain' => l10n.evDietJain,
      'vegan' => l10n.evDietVegan,
      _ => l10n.evDietOther,
    };

// ── Food & preferences ───────────────────────────────────────────────────────

class _FoodTab extends StatefulWidget {
  final EventDetail event;
  final EventService service;
  final Future<void> Function() onChanged;
  const _FoodTab({required this.event, required this.service, required this.onChanged});

  @override
  State<_FoodTab> createState() => _FoodTabState();
}

class _FoodTabState extends State<_FoodTab> with AutomaticKeepAliveClientMixin {
  FoodReport? _report;
  bool _error = false;
  bool _busy = false;

  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _error = false);
    try {
      final report = await widget.service.food(widget.event.id);
      if (mounted) setState(() => _report = report);
    } catch (_) {
      if (mounted) setState(() => _error = true);
    }
  }

  Future<void> _download() async {
    setState(() => _busy = true);
    try {
      final dir = await getTemporaryDirectory();
      final file = await widget.service.downloadFoodReport(widget.event.id, dir.path);
      await Share.shareXFiles([XFile(file.path, mimeType: 'text/csv')], subject: widget.event.title);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(invitationErrorMessage(e))));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _approve() async {
    final l10n = AppLocalizations.of(context)!;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(l10n.evApproveTitle),
        content: Text(l10n.evApproveMessage),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(l10n.commonCancel)),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: Text(l10n.evApproveConfirm)),
        ],
      ),
    );
    if (ok != true) return;
    setState(() => _busy = true);
    try {
      await widget.service.approveOperationsSummary(widget.event.id);
      await widget.onChanged();
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l10n.evApproved)));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(invitationErrorMessage(e))));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final report = _report;
    if (_error) return TyStateScreen.error(context, onAction: _load);
    if (report == null) return const Center(child: CircularProgressIndicator());
    final e = widget.event;
    return RefreshIndicator(
      onRefresh: _load,
      color: ty.saffron,
      child: ListView(
        padding: EdgeInsets.fromLTRB(18, 14, 18, 28 + MediaQuery.paddingOf(context).bottom),
        children: [
          if (!report.enabled)
            EventEmpty(
              icon: Icons.restaurant_outlined,
              title: l10n.evFoodOffTitle,
              message: l10n.evFoodOffMessage,
              action: e.entitlements.foodPreferences ? l10n.evFoodTurnOn : null,
              onAction: e.entitlements.foodPreferences
                  ? () async {
                      await Navigator.of(context).push(MaterialPageRoute(
                        builder: (_) => InvitationSetupScreen(eventId: e.id, initialStep: 3),
                      ));
                      if (mounted) _load();
                    }
                  : null,
            )
          else if (report.functions.isEmpty)
            EventEmpty(icon: Icons.restaurant_outlined, title: l10n.evFoodEmpty, message: l10n.evFoodEmptyMessage)
          else
            for (final f in report.functions)
              Container(
                margin: const EdgeInsets.only(bottom: 10),
                padding: const EdgeInsets.all(14),
                decoration: eventCardDecoration(ty),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [
                    Expanded(child: Text(f.name == 'Event' ? e.title : f.name, style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700))),
                    Text(l10n.evFunctionPeople(f.people), style: TyType.sans(12.5, color: ty.ink3)),
                  ]),
                  const SizedBox(height: 8),
                  for (final d in f.dietary.entries)
                    _FoodLine(label: dietaryLabel(l10n, d.key), value: d.value, total: f.people),
                  for (final m in f.meals.entries) _FoodLine(label: m.key, value: m.value, total: f.people),
                  if (f.notSpecified > 0) _FoodLine(label: l10n.evFoodNotSpecified, value: f.notSpecified, total: f.people),
                  if (f.withAllergies > 0)
                    Padding(
                      padding: const EdgeInsets.only(top: 4),
                      child: Text(l10n.evFoodAllergies(f.withAllergies), style: TyType.sans(12.5, color: ty.rose, weight: FontWeight.w600)),
                    ),
                ]),
              ),
          if (report.enabled && report.functions.isNotEmpty) ...[
            const SizedBox(height: 6),
            TyButton(l10n.evFoodDownload, kind: TyButtonKind.ghost, full: true, leadingIcon: Icons.download_rounded, enabled: !_busy, onTap: _download),
          ],
          if (e.entitlements.vendorReports && report.functions.isNotEmpty) ...[
            const SizedBox(height: 16),
            Text(e.operationsApproved ? l10n.evVendorApproved : l10n.evVendorNote, style: TyType.sans(12.5, color: ty.ink3, height: 1.4)),
            const SizedBox(height: 8),
            TyButton(e.operationsApproved ? l10n.evVendorUpdate : l10n.evVendorShare, full: true, enabled: !_busy, onTap: _approve),
          ],
        ],
      ),
    );
  }
}

class _FoodLine extends StatelessWidget {
  final String label;
  final int value;
  final int total;
  const _FoodLine({required this.label, required this.value, required this.total});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(children: [
        Expanded(child: Text(label, style: TyType.sans(13.5, color: ty.ink2))),
        Text('$value', style: TyType.sans(14, color: ty.ink, weight: FontWeight.w700)),
      ]),
    );
  }
}

// ── Activity ─────────────────────────────────────────────────────────────────

/// Plain statements of what we observed. "Link accessed" is not "read".
String activityLabel(AppLocalizations l10n, InvitationLabels labels, ActivityEntry a) {
  final fn = a.functionName;
  return switch (a.eventType) {
    'invited' => l10n.evActCreated,
    'shared' => l10n.evActShared(labels.channel(a.channel)),
    'email_sent' => l10n.invHistEmailed,
    'email_failed' => l10n.invHistEmailFailed,
    'link_accessed' => l10n.evActAccessed,
    'invitation_opened' => l10n.evActVisited,
    'rsvp_started' => l10n.evActStarted,
    'rsvp_changed' => a.isUpdate
        ? (fn == null ? l10n.evActUpdated(labels.rsvp(a.newStatus ?? '')) : l10n.evActUpdatedFn(labels.rsvp(a.newStatus ?? ''), fn))
        : (fn == null ? l10n.evActSubmitted(labels.rsvp(a.newStatus ?? '')) : l10n.evActSubmittedFn(labels.rsvp(a.newStatus ?? ''), fn)),
    'checked_in' => l10n.invHistCheckedIn,
    'checked_out' => l10n.invHistCheckedOut,
    'reminder_sent' => l10n.evActReminder,
    'functions_changed' => l10n.evActFunctions,
    'details_updated' => l10n.invHistEdited,
    'link_rotated' => l10n.invHistRotated,
    'revoked' => l10n.invHistRevoked,
    _ => a.eventType,
  };
}

IconData _activityIcon(String type) => switch (type) {
      'invited' => Icons.mail_outline_rounded,
      'shared' || 'email_sent' => Icons.send_rounded,
      'link_accessed' => Icons.link_rounded,
      'invitation_opened' => Icons.visibility_outlined,
      'rsvp_started' => Icons.edit_outlined,
      'rsvp_changed' => Icons.how_to_reg_outlined,
      'checked_in' => Icons.login_rounded,
      'checked_out' => Icons.logout_rounded,
      'reminder_sent' => Icons.notifications_active_outlined,
      'revoked' => Icons.block_rounded,
      _ => Icons.history_rounded,
    };

class _ActivityTab extends StatefulWidget {
  final String eventId;
  final EventService service;
  const _ActivityTab({required this.eventId, required this.service});

  @override
  State<_ActivityTab> createState() => _ActivityTabState();
}

class _ActivityTabState extends State<_ActivityTab> with AutomaticKeepAliveClientMixin {
  final List<ActivityEntry> _items = [];
  int _page = 1;
  bool _hasNext = false;
  bool _loading = true;
  bool _error = false;

  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load({bool more = false}) async {
    setState(() {
      _loading = true;
      _error = false;
    });
    try {
      final page = await widget.service.activity(widget.eventId, page: more ? _page + 1 : 1);
      if (!mounted) return;
      setState(() {
        if (!more) _items.clear();
        _items.addAll(page.items);
        _page = more ? _page + 1 : 1;
        _hasNext = page.hasNext;
        _loading = false;
      });
    } catch (_) {
      if (mounted) {
        setState(() {
          _loading = false;
          _error = true;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final labels = InvitationLabels(context);
    if (_error) return TyStateScreen.error(context, onAction: _load);
    if (_items.isEmpty && _loading) return const Center(child: CircularProgressIndicator());
    return RefreshIndicator(
      onRefresh: _load,
      color: ty.saffron,
      child: ListView(
        padding: EdgeInsets.fromLTRB(18, 12, 18, 28 + MediaQuery.paddingOf(context).bottom),
        children: [
          if (_items.isEmpty) EventEmpty(icon: Icons.history_rounded, title: l10n.evActivityEmpty, message: l10n.evActivityEmptyMessage),
          for (final a in _items)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 7),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                CircleAvatar(radius: 16, backgroundColor: ty.surface2, child: Icon(_activityIcon(a.eventType), size: 16, color: ty.saffronDeep)),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(a.guestName, maxLines: 1, overflow: TextOverflow.ellipsis, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w700)),
                    Text(activityLabel(l10n, labels, a), style: TyType.sans(13, color: ty.ink2)),
                    Text(labels.when(a.occurredAt), style: TyType.sans(11.5, color: ty.ink3)),
                  ]),
                ),
              ]),
            ),
          if (_hasNext) TextButton(onPressed: _loading ? null : () => _load(more: true), child: Text(l10n.evLoadMore)),
        ],
      ),
    );
  }
}
