import 'package:flutter/material.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/sample_data.dart';
import '../data/models.dart';
import '../widgets/avatar.dart';
import '../widgets/ty_button.dart';
import '../widgets/ty_chip.dart';
import '../widgets/common.dart';

/// Guest list — RSVP tracking, households, headcounts and invitations.
class GuestsScreen extends StatefulWidget {
  const GuestsScreen({super.key});

  @override
  State<GuestsScreen> createState() => _GuestsScreenState();
}

class _GuestsScreenState extends State<GuestsScreen> {
  final List<Guest> _guests = TyData.seedGuests();
  String _filter = 'All';

  int _sum(String rsvp) =>
      _guests.where((g) => g.rsvp == rsvp).fold<int>(0, (s, g) => s + g.count);

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final total = _guests.fold<int>(0, (s, g) => s + g.count);
    final yes = _sum('yes'), maybe = _sum('maybe'), pending = _sum('pending');

    final shown = _filter == 'All'
        ? _guests
        : _guests
            .where((g) => _filter == 'Coming' ? g.rsvp == 'yes' : g.rsvp == 'pending')
            .toList();

    return Scaffold(
      appBar: tyAppBar(context, title: 'Guest list', actions: [
        Padding(
          padding: const EdgeInsets.only(right: 16), 
          child: ChromeIconButton(
            icon: Icons.qr_code_rounded,
            onTap: () => _showQRCheckin(context),
          ),
        ),
      ]),
      body: Column(
        children: [
          Expanded(
            child: ListView(
              padding: const EdgeInsets.fromLTRB(18, 4, 18, 20),
              children: [
                // summary
                Container(
                  padding: const EdgeInsets.all(18),
                  decoration: _card(ty),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Text('$total', style: TyType.display(42, color: ty.ink)),
                          const SizedBox(width: 6),
                          Padding(
                            padding: const EdgeInsets.only(bottom: 6),
                            child: Text('guests · ${_guests.length} households',
                                style: TyType.sans(13, color: ty.ink2)),
                          ),
                        ],
                      ),
                      const SizedBox(height: 14),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(6),
                        child: Row(children: [
                          Expanded(flex: yes == 0 ? 1 : yes, child: Container(height: 9, color: ty.leaf)),
                          const SizedBox(width: 2),
                          Expanded(flex: maybe == 0 ? 1 : maybe, child: Container(height: 9, color: ty.saffron)),
                          const SizedBox(width: 2),
                          Expanded(flex: pending == 0 ? 1 : pending, child: Container(height: 9, color: ty.surface2)),
                        ]),
                      ),
                      const SizedBox(height: 11),
                      Wrap(spacing: 16, runSpacing: 6, children: [
                        _legend(context, ty.leaf, '$yes coming'),
                        _legend(context, ty.saffron, '$maybe maybe'),
                        _legend(context, ty.ink3, '$pending pending'),
                      ]),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                Text('INVITE VIA', style: TyType.eyebrow(11, color: ty.ink3)),
                const SizedBox(height: 12),
                Row(
                  children: [
                    _inviteMethod(context, Icons.person_add_outlined, 'Manual'),
                    _inviteMethod(context, Icons.upload_file_rounded, 'CSV'),
                    _inviteMethod(context, Icons.contacts_outlined, 'Contacts'),
                    _inviteMethod(context, Icons.chat_bubble_outline_rounded, 'WhatsApp'),
                  ],
                ),
                const SizedBox(height: 16),
                // add field
                Row(
                  children: [
                    Expanded(
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 14),
                        decoration: BoxDecoration(
                          color: ty.surface2,
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(color: ty.line),
                        ),
                        child: Row(children: [
                          Icon(Icons.search_rounded, size: 17, color: ty.ink3),
                          const SizedBox(width: 8),
                          Expanded(
                            child: TextField(
                              decoration: InputDecoration(
                                isDense: true,
                                border: InputBorder.none,
                                hintText: 'Add or search a household…',
                                hintStyle: TyType.sans(14, color: ty.ink3),
                              ),
                              style: TyType.sans(14, color: ty.ink),
                            ),
                          ),
                        ]),
                      ),
                    ),
                    const SizedBox(width: 10),
                    TyButton('', icon: Icons.add_rounded, onTap: () {}),
                  ],
                ),
                const SizedBox(height: 16),
                Row(children: [
                  for (final f in const ['All', 'Coming', 'Pending'])
                    Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: TyChip(
                          label: f,
                          active: _filter == f,
                          onTap: () => setState(() => _filter = f)),
                    ),
                ]),
                const SizedBox(height: 14),
                ...shown.asMap().entries.map((e) => _guestRow(context, e.value, e.key)),
              ],
            ),
          ),
          // sticky CTA
          Container(
            padding: EdgeInsets.fromLTRB(
                18, 12, 18, MediaQuery.of(context).padding.bottom + 14),
            decoration: BoxDecoration(
              color: ty.paper.withOpacity(0.96),
              border: Border(top: BorderSide(color: ty.line2)),
            ),
            child: TyButton('Send invitations',
                full: true, leadingIcon: Icons.send_rounded, onTap: () {}),
          ),
        ],
      ),
    );
  }

  Widget _guestRow(BuildContext context, Guest g, int i) {
    final ty = context.ty;
    final map = {
      'yes': [ty.leaf, 'Coming'],
      'maybe': [ty.saffron, 'Maybe'],
      'pending': [ty.ink3, 'Pending'],
    };
    final c = map[g.rsvp]![0] as Color;
    final lbl = map[g.rsvp]![1] as String;
    return Container(
      margin: const EdgeInsets.only(bottom: 9),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: _card(ty),
      child: Row(
        children: [
          TyAvatar(name: g.name, index: i, size: 40),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(g.name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TyType.sans(14.5, color: ty.ink, weight: FontWeight.w600)),
                const SizedBox(height: 4),
                GestureDetector(
                  onTap: () => setState(() {
                    g.rsvp = g.rsvp == 'yes'
                        ? 'maybe'
                        : g.rsvp == 'maybe'
                            ? 'pending'
                            : 'yes';
                  }),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                    decoration: BoxDecoration(
                      color: c.withOpacity(0.16),
                      borderRadius: BorderRadius.circular(999),
                    ),
                    child: Text(lbl,
                        style: TextStyle(
                            color: c, fontSize: 11.5, fontWeight: FontWeight.w700)),
                  ),
                ),
              ],
            ),
          ),
          Row(children: [
            Icon(Icons.group_outlined, size: 16, color: ty.ink2),
            const SizedBox(width: 4),
            Text('${g.count}',
                style: TyType.sans(13, color: ty.ink2, weight: FontWeight.w700)),
          ]),
        ],
      ),
    );
  }

  Widget _inviteMethod(BuildContext context, IconData icon, String label) {
    final ty = context.ty;
    return Expanded(
      child: Column(
        children: [
          Container(
            width: 50, height: 50,
            decoration: BoxDecoration(color: ty.surface2, borderRadius: BorderRadius.circular(14)),
            child: Icon(icon, color: ty.ink2, size: 22),
          ),
          const SizedBox(height: 6),
          Text(label, style: TyType.sans(10, color: ty.ink2)),
        ],
      ),
    );
  }

  void _showQRCheckin(BuildContext context) {
    final ty = context.ty;
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: ty.surface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(28)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: ty.saffron.withOpacity(0.1),
                borderRadius: BorderRadius.circular(24),
              ),
              child: Icon(Icons.qr_code_2_rounded, size: 200, color: ty.ink),
            ),
            const SizedBox(height: 24),
            Text('Digital Check-in', style: TyType.display(24, color: ty.ink)),
            const SizedBox(height: 12),
            Text(
              'Share this QR with your guests for quick entry and live RSVP tracking at the venue.',
              textAlign: TextAlign.center,
              style: TyType.sans(14, color: ty.ink2, height: 1.5),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('Close', style: TyType.sans(14, color: ty.saffron, weight: FontWeight.w700)),
          ),
        ],
      ),
    );
  }

  BoxDecoration _card(TyColors ty) => BoxDecoration(
        color: ty.surface,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: ty.line),
      );

  Widget _legend(BuildContext context, Color c, String t) {
    final ty = context.ty;
    return Row(mainAxisSize: MainAxisSize.min, children: [
      Container(width: 9, height: 9, decoration: BoxDecoration(color: c, shape: BoxShape.circle)),
      const SizedBox(width: 6),
      Text(t, style: TyType.sans(12, color: ty.ink2)),
    ]);
  }
}
