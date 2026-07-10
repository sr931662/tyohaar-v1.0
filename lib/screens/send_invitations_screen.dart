import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:share_plus/share_plus.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/api_client.dart';
import '../data/models.dart';
import '../data/services/celebration_service.dart';
import '../widgets/avatar.dart';
import '../widgets/ty_button.dart';
import '../widgets/common.dart';
import 'booking_confirmation_screen.dart';

/// Shown right after a successful payment when the customer added guests
/// during planning. Syncs those guests to the newly-active celebration, then
/// lets the customer tap through to WhatsApp (pre-filled) for each one.
///
/// WhatsApp has no public API for silently sending messages from a consumer
/// app without a paid WhatsApp Business API integration — this opens a real
/// WhatsApp chat pre-filled with the invite text per guest, which the
/// customer sends themselves with one tap. That's the practical ceiling
/// without the client signing up for WhatsApp Business API.
class SendInvitationsScreen extends StatefulWidget {
  final String celebrationId;
  final String bookingId;
  final String packageName;
  final String date;
  final List<PlannedGuest> plannedGuests;

  const SendInvitationsScreen({
    super.key,
    required this.celebrationId,
    required this.bookingId,
    required this.packageName,
    required this.date,
    required this.plannedGuests,
  });

  @override
  State<SendInvitationsScreen> createState() => _SendInvitationsScreenState();
}

class PlannedGuest {
  final String name;
  final String? phone;
  const PlannedGuest({required this.name, this.phone});
}

class _SendInvitationsScreenState extends State<SendInvitationsScreen> {
  final CelebrationService _celebrationService = CelebrationService();
  List<Guest> _guests = [];
  bool _syncing = true;
  final Set<String> _sent = {};

  @override
  void initState() {
    super.initState();
    _syncGuests();
  }

  Future<void> _syncGuests() async {
    final created = <Guest>[];
    for (final g in widget.plannedGuests) {
      try {
        final guest = await _celebrationService.addGuest(
          widget.celebrationId,
          name: g.name,
          phone: g.phone,
        );
        created.add(guest);
      } catch (_) {
        // Best-effort — one bad guest shouldn't block the rest.
      }
    }
    if (mounted) setState(() { _guests = created; _syncing = false; });
  }

  String _rsvpPageUrl(Guest g) {
    if (g.rsvpToken == null) return '';
    return '${ApiClient.baseUrl}public/rsvp/${g.rsvpToken}/page';
  }

  String _inviteMessage(Guest g) {
    final link = _rsvpPageUrl(g);
    return 'Hi ${g.name}! You\'re invited to ${widget.packageName} on ${widget.date} 🎉'
        '${link.isNotEmpty ? '\n\nPlease RSVP here: $link' : ''}';
  }

  Future<void> _sendWhatsApp(Guest g) async {
    final message = Uri.encodeComponent(_inviteMessage(g));
    final phone = g.phone?.replaceAll(RegExp(r'[^0-9+]'), '');
    if (phone != null && phone.isNotEmpty) {
      final uri = Uri.parse('https://wa.me/$phone?text=$message');
      final opened = await launchUrl(uri, mode: LaunchMode.externalApplication);
      if (opened) {
        setState(() => _sent.add(g.id));
        return;
      }
    }
    // No phone on file, or WhatsApp couldn't be opened — fall back to the
    // native share sheet so the customer can still send it some other way.
    await Share.share(_inviteMessage(g), subject: 'You\'re invited!');
    setState(() => _sent.add(g.id));
  }

  void _continue() {
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(
        builder: (_) => BookingConfirmationScreen(
          bookingId: widget.bookingId,
          packageName: widget.packageName,
          date: widget.date,
        ),
      ),
      (_) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: 'Send Invitations'),
      body: _syncing
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(20, 8, 20, 4),
                  child: Text(
                    _guests.isEmpty
                        ? 'No guests added yet — you can invite people anytime from the Guests tab.'
                        : 'Your booking is confirmed! Tap a guest to send their invite on WhatsApp.',
                    style: TyType.sans(13.5, color: ty.ink2, height: 1.4),
                  ),
                ),
                Expanded(
                  child: _guests.isEmpty
                      ? Center(
                          child: Icon(Icons.celebration_outlined, size: 56, color: ty.ink3),
                        )
                      : ListView.builder(
                          padding: const EdgeInsets.fromLTRB(20, 12, 20, 20),
                          itemCount: _guests.length,
                          itemBuilder: (context, i) {
                            final g = _guests[i];
                            final sent = _sent.contains(g.id);
                            return Container(
                              margin: const EdgeInsets.only(bottom: 10),
                              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                              decoration: BoxDecoration(
                                color: ty.surface,
                                borderRadius: BorderRadius.circular(16),
                                border: Border.all(color: ty.line),
                              ),
                              child: Row(
                                children: [
                                  TyAvatar(name: g.name, index: i, size: 40),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(g.name, style: TyType.sans(14.5, color: ty.ink, weight: FontWeight.w600)),
                                        if (g.phone != null)
                                          Text(g.phone!, style: TyType.sans(12, color: ty.ink2)),
                                      ],
                                    ),
                                  ),
                                  TyButton(
                                    sent ? 'Sent ✓' : 'WhatsApp',
                                    kind: sent ? TyButtonKind.ghost : TyButtonKind.primary,
                                    leadingIcon: sent ? null : Icons.chat_bubble_outline_rounded,
                                    onTap: () => _sendWhatsApp(g),
                                  ),
                                ],
                              ),
                            );
                          },
                        ),
                ),
                Padding(
                  padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
                  child: TyButton('Continue', full: true, icon: Icons.chevron_right_rounded, onTap: _continue),
                ),
              ],
            ),
    );
  }
}
