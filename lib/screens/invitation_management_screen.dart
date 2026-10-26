import 'dart:async';

import 'package:flutter/material.dart';
import 'package:share_plus/share_plus.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/models.dart';
import '../data/services/celebration_service.dart';
import '../data/services/invitation_service.dart';
import '../utils/log.dart';
import '../widgets/invitation_card.dart';
import '../widgets/state_screens.dart';
import '../widgets/ty_button.dart';
import '../widgets/ty_chip.dart';
import '../widgets/common.dart';
import '../l10n/generated/app_localizations.dart';
import 'invitations/bulk_invite_screen.dart';
import 'invitations/gate_access_screen.dart';
import 'invitations/gate_scan_screen.dart';
import 'invitations/invitation_detail_screen.dart';
import 'invitations/invitation_form_screen.dart';
import 'invitations/invitation_labels.dart';

/// The Invitations hub: who is invited to the selected celebration, who has
/// replied, who has arrived and who is still expected — plus creating,
/// sharing and gate check-in. Data comes from the server only; the counts
/// are server aggregates, never computed from a partially loaded page.
class InvitationManagementScreen extends StatefulWidget {
  const InvitationManagementScreen({super.key});

  @override
  State<InvitationManagementScreen> createState() => _InvitationManagementScreenState();
}

class _InvitationManagementScreenState extends State<InvitationManagementScreen> {
  static const _pageSize = 20;
  static const _filters = [
    'all', 'expected', 'arrived', 'attending', 'pending_rsvp', 'declined', 'not_opened', 'revoked',
  ];

  final CelebrationService _celebrationService = CelebrationService();
  final InvitationService _service = InvitationService();
  final GlobalKey _cardKey = GlobalKey();
  final ScrollController _scroll = ScrollController();
  final TextEditingController _searchCtrl = TextEditingController();
  Timer? _searchDebounce;

  List<Celebration> _celebrations = [];
  Celebration? _selected;
  InvitationSummary? _summary;
  final List<GuestInvitation> _items = [];
  int _total = 0;
  int _page = 1;
  bool _hasNext = false;
  bool _loadingMore = false;
  String _filter = 'all';
  String _query = '';

  bool _isLoading = true;
  bool _error = false;
  bool _listError = false;
  bool _isSharing = false;
  bool _showCard = false;
  int _loadToken = 0;

  @override
  void initState() {
    super.initState();
    _scroll.addListener(() {
      if (_scroll.position.pixels > _scroll.position.maxScrollExtent - 400) _loadMore();
    });
    _loadData();
  }

  @override
  void dispose() {
    _scroll.dispose();
    _searchCtrl.dispose();
    _searchDebounce?.cancel();
    super.dispose();
  }

  Future<void> _loadData() async {
    setState(() {
      _isLoading = true;
      _error = false;
    });
    try {
      final celebrations = await _celebrationService.listCelebrations();
      if (!mounted) return;
      if (celebrations.isEmpty) {
        setState(() {
          _celebrations = [];
          _isLoading = false;
        });
        return;
      }
      final selected = _selected != null
          ? celebrations.firstWhere((c) => c.id == _selected!.id, orElse: () => _defaultCelebration(celebrations))
          : _defaultCelebration(celebrations);
      setState(() {
        _celebrations = celebrations;
        _selected = selected;
      });
      await _reload();
      if (mounted) setState(() => _isLoading = false);
    } catch (e) {
      logDebug('Error loading invitation data: $e');
      if (mounted) {
        setState(() {
          _isLoading = false;
          _error = true;
        });
      }
    }
  }

  /// The next upcoming celebration is what a host is usually managing.
  Celebration _defaultCelebration(List<Celebration> all) {
    final today = DateTime.now();
    final upcoming = all
        .where((c) => c.celebrationDate != null && !c.celebrationDate!.isBefore(DateTime(today.year, today.month, today.day)))
        .toList()
      ..sort((a, b) => a.celebrationDate!.compareTo(b.celebrationDate!));
    return upcoming.isNotEmpty ? upcoming.first : all.first;
  }

  /// Summary + first page. A token discards responses that arrive after the
  /// user has already switched celebration, filter or search.
  Future<void> _reload() async {
    final celebration = _selected;
    if (celebration == null) return;
    final token = ++_loadToken;
    setState(() => _listError = false);
    try {
      final results = await Future.wait([
        _service.summary(celebration.id),
        _service.list(celebration.id, status: _filter, query: _query, page: 1, pageSize: _pageSize),
      ]);
      if (!mounted || token != _loadToken) return;
      final page = results[1] as InvitationPage;
      setState(() {
        _summary = results[0] as InvitationSummary;
        _items
          ..clear()
          ..addAll(page.items);
        _total = page.total;
        _page = 1;
        _hasNext = page.hasNext;
      });
    } catch (e) {
      if (mounted && token == _loadToken) setState(() => _listError = true);
    }
  }

  Future<void> _loadMore() async {
    final celebration = _selected;
    if (celebration == null || !_hasNext || _loadingMore) return;
    final token = _loadToken;
    setState(() => _loadingMore = true);
    try {
      final page = await _service.list(celebration.id,
          status: _filter, query: _query, page: _page + 1, pageSize: _pageSize);
      if (!mounted || token != _loadToken) return;
      setState(() {
        final known = _items.map((i) => i.id).toSet();
        _items.addAll(page.items.where((i) => !known.contains(i.id)));
        _page += 1;
        _hasNext = page.hasNext;
      });
    } catch (_) {
      // Leave hasNext set; scrolling again retries.
    } finally {
      if (mounted) setState(() => _loadingMore = false);
    }
  }

  void _selectCelebration(Celebration c) {
    setState(() {
      _selected = c;
      _summary = null;
      _items.clear();
    });
    _reload();
  }

  void _onSearch(String v) {
    _searchDebounce?.cancel();
    _searchDebounce = Timer(const Duration(milliseconds: 350), () {
      if (!mounted || v.trim() == _query) return;
      setState(() => _query = v.trim());
      _reload();
    });
  }

  Future<void> _open(Widget screen) async {
    final changed = await Navigator.of(context).push<Object?>(MaterialPageRoute(builder: (_) => screen));
    if (changed != null && changed != false) _reload();
  }

  Future<void> _create() async {
    final c = _selected!;
    final created = await Navigator.of(context).push<GuestInvitation>(
      MaterialPageRoute(builder: (_) => InvitationFormScreen(celebrationId: c.id)),
    );
    if (created == null || !mounted) return;
    await _reload();
    if (!mounted) return;
    // Straight to the pass so the host can share it.
    _open(InvitationDetailScreen(celebrationId: c.id, guestId: created.id, celebrationTitle: c.title));
  }

  Future<void> _shareCard() async {
    final l10n = AppLocalizations.of(context)!;
    setState(() => _isSharing = true);
    try {
      final bytes = await InvitationCard.captureCard(_cardKey);
      if (bytes == null) throw Exception('Could not render invitation card.');
      final title = _selected?.title ?? l10n.invitationManagementCelebrationFallback;
      await Share.shareXFiles(
        [XFile.fromData(bytes, mimeType: 'image/png', name: 'invitation.png')],
        text: l10n.invitationManagementShareTextMessage(title),
        subject: l10n.invitationManagementShareSubject(title),
      );
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(l10n.invitationManagementShareError)),
        );
      }
    } finally {
      if (mounted) setState(() => _isSharing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;

    if (_isLoading && _celebrations.isEmpty) {
      return Scaffold(backgroundColor: ty.paper, body: const Center(child: CircularProgressIndicator()));
    }

    if (_error && _celebrations.isEmpty) {
      return Scaffold(
        backgroundColor: ty.paper,
        appBar: tyAppBar(context, title: l10n.invitationManagementAppBarTitle),
        body: TyStateScreen.error(context, onAction: _loadData),
      );
    }

    if (_celebrations.isEmpty) {
      return Scaffold(
        backgroundColor: ty.paper,
        appBar: tyAppBar(context, title: l10n.invitationManagementAppBarTitle),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(32),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.celebration_outlined, size: 48, color: ty.ink3),
                const SizedBox(height: 16),
                Text(l10n.invitationManagementNoEventsTitle, style: TyType.display(18, color: ty.ink)),
                const SizedBox(height: 8),
                Text(
                  l10n.invitationManagementNoEventsMessage,
                  textAlign: TextAlign.center,
                  style: TyType.sans(13.5, color: ty.ink3),
                ),
              ],
            ),
          ),
        ),
      );
    }

    final selected = _selected!;
    final showFooter = _hasNext || _loadingMore;
    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: l10n.invitationManagementAppBarTitle, actions: [
        IconButton(
          tooltip: l10n.invGateTitle,
          icon: Icon(Icons.qr_code_scanner_rounded, color: ty.ink),
          onPressed: () => _open(GateScanScreen(celebrationId: selected.id, celebrationTitle: selected.title)),
        ),
        const SizedBox(width: 6),
      ]),
      body: RefreshIndicator(
        onRefresh: _reload,
        color: ty.saffron,
        child: ListView.builder(
          controller: _scroll,
          physics: const AlwaysScrollableScrollPhysics(),
          padding: EdgeInsets.fromLTRB(18, 8, 18, 28 + MediaQuery.paddingOf(context).bottom),
          itemCount: 1 + (_items.isEmpty ? 1 : _items.length) + (showFooter ? 1 : 0),
          itemBuilder: (context, index) {
            if (index == 0) return _header(context, selected);
            if (_items.isEmpty) return _emptyList(context);
            final i = index - 1;
            if (i >= _items.length) {
              return const Padding(
                padding: EdgeInsets.symmetric(vertical: 16),
                child: Center(child: CircularProgressIndicator()),
              );
            }
            return _row(context, selected, _items[i]);
          },
        ),
      ),
    );
  }

  Widget _header(BuildContext context, Celebration selected) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final s = _summary;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (_celebrations.length > 1) ...[
          Text(l10n.invitationManagementEventLabel, style: TyType.eyebrow(11, color: ty.ink3)),
          const SizedBox(height: 8),
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
                        child: Text(c.title,
                            overflow: TextOverflow.ellipsis,
                            style: TyType.sans(14, color: ty.ink, weight: FontWeight.w600))))
                    .toList(),
                onChanged: (id) => _selectCelebration(_celebrations.firstWhere((c) => c.id == id)),
              ),
            ),
          ),
          const SizedBox(height: 18),
        ],
        Text(l10n.invitationManagementGuestStatusLabel, style: TyType.eyebrow(11, color: ty.ink3)),
        const SizedBox(height: 10),
        Row(children: [
          _stat(context, s?.active, l10n.invitationManagementInvitedLabel, ty.ink2),
          const SizedBox(width: 8),
          _stat(context, s?.attending, l10n.invStatComing, ty.leaf),
          const SizedBox(width: 8),
          _stat(context, s?.arrivedGuests, l10n.invStatArrived, ty.saffronDeep),
          const SizedBox(width: 8),
          _stat(context, s?.stillExpected, l10n.invStatExpected, ty.ink2),
        ]),
        if (s != null && (s.arrivedPeople > 0 || s.expectedPeople > 0))
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(l10n.invPeopleSummary(s.arrivedPeople, s.expectedPeople, s.insideNow),
                style: TyType.sans(12.5, color: ty.ink3)),
          ),
        const SizedBox(height: 16),
        Row(children: [
          Expanded(child: _action(context, Icons.person_add_alt_1_rounded, l10n.invAddGuest, _create)),
          const SizedBox(width: 8),
          Expanded(
            child: _action(context, Icons.group_add_rounded, l10n.invInviteMany,
                () => _open(BulkInviteScreen(celebrationId: selected.id))),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: _action(context, Icons.qr_code_scanner_rounded, l10n.invScanPasses,
                () => _open(GateScanScreen(celebrationId: selected.id, celebrationTitle: selected.title))),
          ),
        ]),
        const SizedBox(height: 10),
        _tile(context, Icons.badge_outlined, l10n.invGateAccessTitle, l10n.invGateAccessTileSubtitle,
            () => _open(GateAccessScreen(celebrationId: selected.id, celebrationTitle: selected.title))),
        const SizedBox(height: 8),
        _tile(context, Icons.style_outlined, l10n.invCardTileTitle, l10n.invitationManagementShareHintMessage,
            () => setState(() => _showCard = !_showCard), trailing: _showCard ? Icons.expand_less_rounded : Icons.expand_more_rounded),
        if (_showCard) ...[
          const SizedBox(height: 14),
          Center(child: InvitationCard(celebration: selected, boundaryKey: _cardKey)),
          const SizedBox(height: 14),
          TyButton(
            _isSharing ? l10n.invitationManagementPreparingLabel : l10n.invitationManagementShareButtonLabel,
            full: true,
            enabled: !_isSharing,
            leadingIcon: Icons.ios_share_rounded,
            onTap: _shareCard,
          ),
        ],
        const SizedBox(height: 18),
        TextField(
          controller: _searchCtrl,
          onChanged: _onSearch,
          textInputAction: TextInputAction.search,
          decoration: InputDecoration(
            hintText: l10n.invSearchHint,
            prefixIcon: const Icon(Icons.search_rounded),
            filled: true,
            fillColor: ty.surface,
            contentPadding: const EdgeInsets.symmetric(vertical: 12),
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide(color: ty.line)),
            enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide(color: ty.line)),
          ),
        ),
        const SizedBox(height: 10),
        SizedBox(
          height: 40,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: _filters.length,
            separatorBuilder: (_, __) => const SizedBox(width: 8),
            itemBuilder: (context, i) => TyChip(
              label: _filterLabel(l10n, _filters[i]),
              active: _filter == _filters[i],
              onTap: () {
                if (_filter == _filters[i]) return;
                setState(() => _filter = _filters[i]);
                _reload();
              },
            ),
          ),
        ),
        const SizedBox(height: 10),
        if (_summary != null)
          Text(l10n.invShowingCount(_items.length, _total), style: TyType.sans(12, color: ty.ink3)),
        const SizedBox(height: 6),
      ],
    );
  }

  String _filterLabel(AppLocalizations l10n, String f) => switch (f) {
        'expected' => l10n.invFilterExpected,
        'arrived' => l10n.invFilterArrived,
        'attending' => l10n.invFilterComing,
        'pending_rsvp' => l10n.invFilterNoReply,
        'declined' => l10n.invFilterDeclined,
        'not_opened' => l10n.invFilterNotOpened,
        'revoked' => l10n.invFilterCancelled,
        _ => l10n.invFilterAll,
      };

  Widget _emptyList(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    if (_listError) {
      return Padding(
        padding: const EdgeInsets.only(top: 24),
        child: Column(children: [
          Text(l10n.invListError, style: TyType.sans(14, color: ty.ink2)),
          TextButton(onPressed: _reload, child: Text(l10n.commonTryAgain)),
        ]),
      );
    }
    if (_summary == null) {
      return const Padding(padding: EdgeInsets.only(top: 32), child: Center(child: CircularProgressIndicator()));
    }
    final filtered = _filter != 'all' || _query.isNotEmpty;
    return Padding(
      padding: const EdgeInsets.only(top: 28),
      child: Column(children: [
        Icon(filtered ? Icons.search_off_rounded : Icons.mail_outline_rounded, size: 40, color: ty.ink3),
        const SizedBox(height: 10),
        Text(filtered ? l10n.invEmptyFiltered : l10n.invEmptyTitle,
            textAlign: TextAlign.center, style: TyType.sans(14.5, color: ty.ink2, weight: FontWeight.w600)),
        if (!filtered) ...[
          const SizedBox(height: 4),
          Text(l10n.invEmptyMessage, textAlign: TextAlign.center, style: TyType.sans(13, color: ty.ink3)),
        ],
      ]),
    );
  }

  Widget _row(BuildContext context, Celebration celebration, GuestInvitation inv) {
    final ty = context.ty;
    final labels = InvitationLabels(context);
    final stateColor = labels.passColor(inv.passState);
    final sub = [
      labels.allowance(inv.plusOnesAllowed),
      if (!inv.isRevoked) labels.rsvp(inv.rsvpStatus),
      if (inv.checkedInAt != null) labels.when(inv.checkedInAt!),
    ].join(' · ');
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Material(
        color: ty.surface,
        borderRadius: BorderRadius.circular(16),
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: () => _open(InvitationDetailScreen(
            celebrationId: celebration.id,
            guestId: inv.id,
            celebrationTitle: celebration.title,
          )),
          child: Container(
            padding: const EdgeInsets.fromLTRB(14, 12, 12, 12),
            decoration: BoxDecoration(borderRadius: BorderRadius.circular(16), border: Border.all(color: ty.line)),
            child: Row(children: [
              CircleAvatar(
                radius: 19,
                backgroundColor: stateColor.withValues(alpha: 0.15),
                child: Text(inv.name.isEmpty ? '?' : inv.name.characters.first.toUpperCase(),
                    style: TyType.sans(15, color: stateColor, weight: FontWeight.w800)),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(inv.name, maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
                  const SizedBox(height: 2),
                  Text(sub, maxLines: 1, overflow: TextOverflow.ellipsis, style: TyType.sans(12.5, color: ty.ink3)),
                ]),
              ),
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                decoration: BoxDecoration(color: stateColor.withValues(alpha: 0.13), borderRadius: BorderRadius.circular(999)),
                child: Text(labels.passState(inv.passState),
                    style: TyType.sans(11.5, color: stateColor, weight: FontWeight.w700)),
              ),
            ]),
          ),
        ),
      ),
    );
  }

  Widget _action(BuildContext context, IconData icon, String label, VoidCallback onTap) {
    final ty = context.ty;
    return Material(
      color: ty.surface,
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onTap,
        child: Container(
          constraints: const BoxConstraints(minHeight: 76),
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 12),
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(16), border: Border.all(color: ty.line)),
          child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
            Icon(icon, color: ty.saffronDeep),
            const SizedBox(height: 6),
            Text(label, textAlign: TextAlign.center, maxLines: 2, overflow: TextOverflow.ellipsis,
                style: TyType.sans(12.5, color: ty.ink, weight: FontWeight.w700)),
          ]),
        ),
      ),
    );
  }

  Widget _tile(BuildContext context, IconData icon, String title, String subtitle, VoidCallback onTap,
      {IconData trailing = Icons.chevron_right_rounded}) {
    final ty = context.ty;
    return Material(
      color: ty.surface,
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.fromLTRB(14, 12, 10, 12),
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(16), border: Border.all(color: ty.line)),
          child: Row(children: [
            Icon(icon, color: ty.ink2),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(title, style: TyType.sans(14.5, color: ty.ink, weight: FontWeight.w700)),
                Text(subtitle, maxLines: 2, overflow: TextOverflow.ellipsis, style: TyType.sans(12, color: ty.ink3)),
              ]),
            ),
            Icon(trailing, color: ty.ink3),
          ]),
        ),
      ),
    );
  }

  Widget _stat(BuildContext context, int? value, String label, Color color) {
    final ty = context.ty;
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 4),
        decoration: BoxDecoration(
          color: ty.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: ty.line),
        ),
        child: Column(
          children: [
            Text(value?.toString() ?? '–',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TyType.display(21, color: color)),
            const SizedBox(height: 2),
            Text(label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TyType.sans(11.5, color: ty.ink3, weight: FontWeight.w600)),
          ],
        ),
      ),
    );
  }
}
