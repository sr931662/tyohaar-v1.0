import 'dart:async';

import 'package:flutter/material.dart';
import 'package:share_plus/share_plus.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../theme/responsive.dart';
import '../data/api_client.dart';
import '../data/models.dart';
import '../data/services/celebration_service.dart';
import '../widgets/avatar.dart';
import '../widgets/ty_button.dart';
import '../widgets/ty_chip.dart';
import '../widgets/common.dart';

class GuestsScreen extends StatefulWidget {
  final String? celebrationId;
  const GuestsScreen({super.key, this.celebrationId});

  @override
  State<GuestsScreen> createState() => _GuestsScreenState();
}

class _GuestsScreenState extends State<GuestsScreen> {
  final CelebrationService _celebrationService = CelebrationService();
  List<Guest> _guests = [];
  String _filter = 'All';
  String _search = '';
  bool _isLoading = true;
  String? _activeCelebrationId;
  String? _error;
  bool _isMutating = false;
  Timer? _searchDebounce;

  @override
  void initState() {
    super.initState();
    _loadGuests();
  }

  @override
  void dispose() {
    _searchDebounce?.cancel();
    super.dispose();
  }

  void _onSearchChanged(String v) {
    _searchDebounce?.cancel();
    _searchDebounce = Timer(const Duration(milliseconds: 300), () {
      if (mounted) setState(() => _search = v);
    });
  }

  Future<void> _loadGuests() async {
    setState(() { _isLoading = true; _error = null; });
    try {
      String? celebrationId = widget.celebrationId;
      if (celebrationId == null) {
        final celebrations = await _celebrationService.listCelebrations();
        celebrationId = celebrations.isNotEmpty ? celebrations.first.id : null;
      }
      if (celebrationId != null) {
        _activeCelebrationId = celebrationId;
        final guests = await _celebrationService.listGuests(celebrationId);
        if (mounted) setState(() { _guests = guests; _isLoading = false; });
      } else {
        if (mounted) setState(() => _isLoading = false);
      }
    } catch (e) {
      if (mounted) setState(() { _error = 'Could not load guests.'; _isLoading = false; });
    }
  }

  int _sum(String rsvp) =>
      _guests.where((g) => g.displayStatus == rsvp).length;

  String _rsvpPageUrl(Guest g) {
    if (g.rsvpToken == null) return '';
    return '${ApiClient.baseUrl}public/rsvp/${g.rsvpToken}/page';
  }

  Future<void> _shareInvite(Guest g) async {
    final link = _rsvpPageUrl(g);
    if (link.isEmpty) return;
    final message = 'Hi ${g.name}! You\'re invited 🎉\n\n'
        'Please RSVP here: $link';
    await Share.share(message, subject: 'You\'re invited!');
  }

  Future<void> _openAddGuestDialog() async {
    final celebrationId = _activeCelebrationId;
    if (celebrationId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Create a celebration first to add guests.')),
      );
      return;
    }
    final nameCtrl = TextEditingController();
    final phoneCtrl = TextEditingController();
    final result = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Add Guest'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(controller: nameCtrl, decoration: const InputDecoration(labelText: 'Name')),
            const SizedBox(height: 12),
            TextField(controller: phoneCtrl, decoration: const InputDecoration(labelText: 'Phone (optional)'), keyboardType: TextInputType.phone),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Add')),
        ],
      ),
    );
    if (result != true || nameCtrl.text.trim().isEmpty) return;

    setState(() => _isMutating = true);
    try {
      final guest = await _celebrationService.addGuest(
        celebrationId,
        name: nameCtrl.text.trim(),
        phone: phoneCtrl.text.trim(),
      );
      if (mounted) setState(() => _guests = [..._guests, guest]);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not add guest. Please try again.')),
        );
      }
    } finally {
      if (mounted) setState(() => _isMutating = false);
    }
  }

  Future<void> _removeGuest(Guest g) async {
    final celebrationId = _activeCelebrationId;
    if (celebrationId == null) return;
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Remove guest?'),
        content: Text('Remove ${g.name} from your guest list?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Remove', style: TextStyle(color: Colors.red))),
        ],
      ),
    );
    if (confirm != true) return;
    try {
      await _celebrationService.removeGuest(celebrationId, g.id);
      if (mounted) setState(() => _guests.removeWhere((x) => x.id == g.id));
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not remove guest.')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final resp = context.resp;

    if (_isLoading) {
      return Scaffold(backgroundColor: ty.paper, body: const Center(child: CircularProgressIndicator()));
    }

    if (_error != null) {
      return Scaffold(
        backgroundColor: ty.paper,
        appBar: tyAppBar(context, title: 'Guest list'),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.error_outline_rounded, size: resp.sp(48), color: ty.rose),
              SizedBox(height: resp.h(12)),
              Text(_error!, style: TyType.sans(resp.sp(14), color: ty.ink2)),
              SizedBox(height: resp.h(16)),
              TextButton(
                onPressed: _loadGuests,
                child: Text('Try Again', style: TyType.sans(resp.sp(14), color: ty.saffron, weight: FontWeight.w700)),
              ),
            ],
          ),
        ),
      );
    }

    final total = _guests.length;
    final yes = _sum('attending'), maybe = _sum('maybe'), pending = _sum('pending') + _sum('ignored');

    final shown = _guests.where((g) {
      final matchesFilter = _filter == 'All'
          || (_filter == 'Coming' && g.displayStatus == 'attending')
          || (_filter == 'Pending' && (g.displayStatus == 'pending' || g.displayStatus == 'ignored'));
      final matchesSearch = _search.isEmpty || g.name.toLowerCase().contains(_search.toLowerCase());
      return matchesFilter && matchesSearch;
    }).toList();

    return Scaffold(
      appBar: tyAppBar(context, title: 'Guest list', actions: [
        Padding(
          padding: EdgeInsets.only(right: resp.w(16)),
          child: ChromeIconButton(
            icon: Icons.qr_code_rounded,
            onTap: () => _showQRCheckin(context),
          ),
        ),
      ]),
      body: Column(
        children: [
          Expanded(
            child: RefreshIndicator(
              onRefresh: _loadGuests,
              color: ty.saffron,
              child: ListView.builder(
                padding: EdgeInsets.fromLTRB(resp.w(18), resp.h(4), resp.w(18), resp.h(20)),
                // Header (stats/search/filters) is item 0 so the whole page still
                // scrolls as one list, while guest rows are only built lazily.
                itemCount: 1 + (_guests.isEmpty ? 1 : shown.length),
                itemBuilder: (context, index) {
                  if (index == 0) {
                    return _guestsHeader(context, ty, resp, total: total, yes: yes, maybe: maybe, pending: pending);
                  }
                  if (_guests.isEmpty) {
                    return Center(child: Padding(
                      padding: EdgeInsets.only(top: resp.h(40)),
                      child: Text('No guests in your list yet — tap + to add one', style: TyType.sans(resp.sp(14), color: ty.ink3)),
                    ));
                  }
                  final i = index - 1;
                  return _guestRow(context, shown[i], i, resp);
                },
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _guestsHeader(BuildContext context, TyColors ty, TyResponsive resp,
      {required int total, required int yes, required int maybe, required int pending}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: EdgeInsets.all(resp.w(18)),
          decoration: _card(ty, resp),
          child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text('$total', style: TyType.display(resp.sp(42), color: ty.ink)),
                SizedBox(width: resp.w(6)),
                Padding(
                  padding: EdgeInsets.only(bottom: resp.h(6)),
                  child: Text('guests invited',
                      style: TyType.sans(resp.sp(13), color: ty.ink2)),
                ),
              ],
            ),
            SizedBox(height: resp.h(14)),
            ClipRRect(
              borderRadius: BorderRadius.circular(resp.w(6)),
              child: Row(children: [
                if (yes > 0) Expanded(flex: yes, child: Container(height: resp.h(9), color: ty.leaf)),
                if (maybe > 0) ...[
                  SizedBox(width: resp.w(2)),
                  Expanded(flex: maybe, child: Container(height: resp.h(9), color: ty.saffron)),
                ],
                if (pending > 0) ...[
                  SizedBox(width: resp.w(2)),
                  Expanded(flex: pending, child: Container(height: resp.h(9), color: ty.surface2)),
                ],
                if (total == 0) Expanded(child: Container(height: resp.h(9), color: ty.surface2)),
              ]),
            ),
            SizedBox(height: resp.h(11)),
            Wrap(spacing: resp.w(16), runSpacing: resp.h(6), children: [
              _legend(context, ty.leaf, '$yes coming'),
              _legend(context, ty.saffron, '$maybe maybe'),
              _legend(context, ty.ink3, '$pending pending'),
            ]),
          ],
        ),
      ),
      SizedBox(height: resp.h(16)),
      Row(
        children: [
          Expanded(
            child: Container(
              padding: EdgeInsets.symmetric(horizontal: resp.w(14)),
              decoration: BoxDecoration(
                color: ty.surface2,
                borderRadius: BorderRadius.circular(resp.w(14)),
                border: Border.all(color: ty.line),
              ),
              child: Row(children: [
                Icon(Icons.search_rounded, size: resp.sp(17), color: ty.ink3),
                SizedBox(width: resp.w(8)),
                Expanded(
                  child: TextField(
                    onChanged: _onSearchChanged,
                    decoration: InputDecoration(
                      isDense: true,
                      border: InputBorder.none,
                      hintText: 'Search a guest…',
                      hintStyle: TyType.sans(resp.sp(14), color: ty.ink3),
                    ),
                    style: TyType.sans(resp.sp(14), color: ty.ink),
                  ),
                ),
              ]),
            ),
          ),
          SizedBox(width: resp.w(10)),
          TyButton('', icon: Icons.add_rounded, enabled: !_isMutating, onTap: _openAddGuestDialog),
        ],
      ),
      SizedBox(height: resp.h(16)),
      Row(children: [
        for (final f in const ['All', 'Coming', 'Pending'])
          Padding(
            padding: EdgeInsets.only(right: resp.w(8)),
            child: TyChip(
                label: f,
                active: _filter == f,
                onTap: () => setState(() => _filter = f)),
          ),
      ]),
      SizedBox(height: resp.h(14)),
      ],
    );
  }

  Widget _guestRow(BuildContext context, Guest g, int i, TyResponsive resp) {
    final ty = context.ty;
    final map = {
      'attending': [ty.leaf, 'Coming'],
      'maybe': [ty.saffron, 'Maybe'],
      'pending': [ty.ink3, 'Pending'],
      'ignored': [ty.rose, 'Ignored'],
      'declined': [ty.rose, "Can't come"],
    };
    final c = (map[g.displayStatus]?[0] ?? ty.ink3) as Color;
    final lbl = (map[g.displayStatus]?[1] ?? 'Unknown') as String;

    return Dismissible(
      key: ValueKey(g.id),
      direction: DismissDirection.endToStart,
      confirmDismiss: (_) async {
        await _removeGuest(g);
        return false; // removal already updates state; avoid double-remove from the widget tree
      },
      background: Container(
        alignment: Alignment.centerRight,
        padding: EdgeInsets.only(right: resp.w(20)),
        margin: EdgeInsets.only(bottom: resp.h(9)),
        decoration: BoxDecoration(color: ty.rose, borderRadius: BorderRadius.circular(resp.w(18))),
        child: const Icon(Icons.delete_outline_rounded, color: Colors.white),
      ),
      child: Container(
        margin: EdgeInsets.only(bottom: resp.h(9)),
        padding: EdgeInsets.symmetric(horizontal: resp.w(14), vertical: resp.h(12)),
        decoration: _card(ty, resp),
        child: Row(
          children: [
            TyAvatar(name: g.name, index: i, size: resp.w(40)),
            SizedBox(width: resp.w(12)),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(g.name,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TyType.sans(resp.sp(14.5), color: ty.ink, weight: FontWeight.w600)),
                  SizedBox(height: resp.h(4)),
                  Container(
                    padding: EdgeInsets.symmetric(horizontal: resp.w(10), vertical: resp.h(3)),
                    decoration: BoxDecoration(
                      color: c.withOpacity(0.16),
                      borderRadius: BorderRadius.circular(999),
                    ),
                    child: Text(lbl,
                        style: TextStyle(
                            color: c, fontSize: resp.sp(11.5), fontWeight: FontWeight.w700)),
                  ),
                ],
              ),
            ),
            IconButton(
              icon: Icon(Icons.ios_share_rounded, size: resp.sp(20), color: ty.saffron),
              tooltip: 'Share invite',
              onPressed: () => _shareInvite(g),
            ),
          ],
        ),
      ),
    );
  }

  void _showQRCheckin(BuildContext context) {
    final ty = context.ty;
    final resp = context.resp;
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: ty.surface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(resp.w(28))),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: EdgeInsets.all(resp.w(20)),
              decoration: BoxDecoration(
                color: ty.saffron.withOpacity(0.1),
                borderRadius: BorderRadius.circular(resp.w(24)),
              ),
              child: Icon(Icons.qr_code_2_rounded, size: resp.w(200), color: ty.ink),
            ),
            SizedBox(height: resp.h(24)),
            Text('Digital Check-in', style: TyType.display(resp.sp(24), color: ty.ink)),
            SizedBox(height: resp.h(12)),
            Text(
              'Share this QR with your guests for quick entry and live RSVP tracking at the venue.',
              textAlign: TextAlign.center,
              style: TyType.sans(resp.sp(14), color: ty.ink2, height: 1.5),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('Close', style: TyType.sans(resp.sp(14), color: ty.saffron, weight: FontWeight.w700)),
          ),
        ],
      ),
    );
  }

  BoxDecoration _card(TyColors ty, TyResponsive resp) => BoxDecoration(
        color: ty.surface,
        borderRadius: BorderRadius.circular(resp.w(18)),
        border: Border.all(color: ty.line),
      );

  Widget _legend(BuildContext context, Color c, String t) {
    final ty = context.ty;
    final resp = context.resp;
    return Row(mainAxisSize: MainAxisSize.min, children: [
      Container(width: resp.w(9), height: resp.w(9), decoration: BoxDecoration(color: c, shape: BoxShape.circle)),
      SizedBox(width: resp.w(6)),
      Text(t, style: TyType.sans(resp.sp(12), color: ty.ink2)),
    ]);
  }
}
