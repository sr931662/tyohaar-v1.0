import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../data/services/invitation_service.dart';
import '../../l10n/generated/app_localizations.dart';
import '../../theme/colors.dart';
import '../../utils/whatsapp.dart';
import '../../theme/typography.dart';
import '../../widgets/common.dart';
import '../../widgets/state_screens.dart';
import '../../widgets/ty_button.dart';
import 'invitation_form_screen.dart';
import 'invitation_labels.dart';

/// One guest's invitation: status, pass (QR + code), sharing, edit,
/// reissue, cancel, and the full activity trail.
class InvitationDetailScreen extends StatefulWidget {
  final String celebrationId;
  final String guestId;
  final String celebrationTitle;
  const InvitationDetailScreen({
    super.key,
    required this.celebrationId,
    required this.guestId,
    required this.celebrationTitle,
  });

  @override
  State<InvitationDetailScreen> createState() => _InvitationDetailScreenState();
}

class _InvitationDetailScreenState extends State<InvitationDetailScreen> {
  final _service = InvitationService();
  InvitationDetail? _detail;
  DeliveryCapabilities? _caps;
  bool _loading = true;
  Object? _error;
  bool _busy = false;
  bool _changed = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = _detail == null;
      _error = null;
    });
    try {
      final results = await Future.wait([
        _service.detail(widget.celebrationId, widget.guestId),
        _caps == null ? _service.capabilities() : Future.value(_caps),
      ]);
      if (!mounted) return;
      setState(() {
        _detail = results[0] as InvitationDetail;
        _caps = results[1] as DeliveryCapabilities?;
        _loading = false;
      });
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e;
          _loading = false;
        });
      }
    }
  }

  void _snack(String m) {
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));
  }

  Future<void> _run(Future<void> Function() action) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      await action();
      _changed = true;
    } catch (e) {
      _snack(invitationErrorMessage(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  String _message(GuestInvitation inv) {
    final l10n = AppLocalizations.of(context)!;
    return l10n.invShareMessage(inv.name, widget.celebrationTitle, inv.inviteUrl ?? '');
  }

  /// Records the share only when the platform reports it went through.
  Future<void> _shareSheet(GuestInvitation inv) async {
    final l10n = AppLocalizations.of(context)!;
    final result = await Share.share(_message(inv), subject: l10n.invShareSubject(widget.celebrationTitle));
    if (result.status == ShareResultStatus.success) {
      await _run(() async => await _service.markShared(widget.celebrationId, inv.id, 'share_sheet'));
      await _load();
    }
  }

  Future<void> _whatsapp(GuestInvitation inv) async {
    final l10n = AppLocalizations.of(context)!;
    final opened = await launchUrl(whatsAppLink(inv.phone, _message(inv)), mode: LaunchMode.externalApplication);
    if (!opened) {
      _snack(l10n.invWhatsappUnavailable);
      return;
    }
    // WhatsApp opened with the message — we can't know it was sent.
    await _run(() async => await _service.markShared(widget.celebrationId, inv.id, 'whatsapp'));
    await _load();
  }

  Future<void> _copy(GuestInvitation inv) async {
    final copied = AppLocalizations.of(context)!.invLinkCopied;
    await Clipboard.setData(ClipboardData(text: inv.inviteUrl ?? ''));
    _snack(copied);
    await _run(() async => await _service.markShared(widget.celebrationId, inv.id, 'copy_link'));
    await _load();
  }

  Future<void> _email(GuestInvitation inv) async {
    await _run(() async {
      final result = await _service.sendEmail(widget.celebrationId, inv.id);
      _snack(result.message);
    });
    await _load();
  }

  Future<void> _edit(GuestInvitation inv) async {
    final updated = await Navigator.of(context).push<GuestInvitation>(
      MaterialPageRoute(builder: (_) => InvitationFormScreen(celebrationId: widget.celebrationId, existing: inv)),
    );
    if (updated != null && mounted) {
      _changed = true;
      _snack(AppLocalizations.of(context)!.invUpdated);
      await _load();
    }
  }

  Future<void> _rotate(GuestInvitation inv) async {
    final l10n = AppLocalizations.of(context)!;
    final ok = await _confirm(l10n.invRotateTitle, l10n.invRotateMessage, l10n.invRotateConfirm);
    if (ok != true) return;
    await _run(() async {
      await _service.rotate(widget.celebrationId, inv.id);
      _snack(l10n.invRotated);
    });
    await _load();
  }

  Future<void> _revoke(GuestInvitation inv) async {
    final l10n = AppLocalizations.of(context)!;
    final reason = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(l10n.invRevokeTitle),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(l10n.invRevokeMessage(inv.name)),
            const SizedBox(height: 12),
            TextField(
              controller: reason,
              maxLength: 300,
              decoration: InputDecoration(labelText: l10n.invRevokeReason),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(l10n.commonCancel)),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: Text(l10n.invRevokeConfirm, style: TextStyle(color: context.ty.rose, fontWeight: FontWeight.w700)),
          ),
        ],
      ),
    );
    final text = reason.text;
    reason.dispose();
    if (ok != true) return;
    await _run(() async {
      await _service.revoke(widget.celebrationId, inv.id, reason: text);
      _snack(l10n.invRevoked);
    });
    await _load();
  }

  Future<bool?> _confirm(String title, String message, String confirm) => showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: Text(title),
          content: Text(message),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(AppLocalizations.of(ctx)!.commonCancel)),
            TextButton(onPressed: () => Navigator.pop(ctx, true), child: Text(confirm)),
          ],
        ),
      );

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) Navigator.of(context).pop(_changed);
      },
      child: Scaffold(
        backgroundColor: ty.paper,
        appBar: tyAppBar(context, title: l10n.invDetailTitle),
        body: _loading
            ? const Center(child: CircularProgressIndicator())
            : _detail == null
                ? TyStateScreen.error(context, onAction: _load)
                : RefreshIndicator(onRefresh: _load, color: ty.saffron, child: _body(context, _detail!)),
      ),
    );
  }

  Widget _body(BuildContext context, InvitationDetail detail) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final labels = InvitationLabels(context);
    final inv = detail.invitation;
    final window = labels.window(inv.arrivalWindowStart, inv.arrivalWindowEnd);

    return ListView(
      padding: EdgeInsets.fromLTRB(18, 8, 18, 28 + MediaQuery.paddingOf(context).bottom),
      children: [
        if (_error != null)
          Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: Text(invitationErrorMessage(_error!), style: TyType.sans(13, color: ty.rose)),
          ),
        Text(inv.name, style: TyType.display(24, color: ty.ink)),
        const SizedBox(height: 8),
        Wrap(spacing: 8, runSpacing: 8, children: [
          _pill(labels.passState(inv.passState), labels.passColor(inv.passState)),
          _pill(labels.rsvp(inv.rsvpStatus), labels.rsvpColor(inv.rsvpStatus)),
          if (inv.invitationOpenedAt == null && !inv.isRevoked) _pill(l10n.invNotOpened, ty.ink3),
        ]),
        const SizedBox(height: 18),

        if (!inv.isRevoked && inv.qrPayload != null) ...[
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(22), border: Border.all(color: ty.line)),
            child: Column(children: [
              Semantics(
                label: l10n.invQrSemantics(inv.name),
                image: true,
                child: Container(
                  padding: const EdgeInsets.all(10),
                  color: Colors.white, // QR needs a light quiet zone in both themes
                  child: QrImageView(data: inv.qrPayload!, size: 180, backgroundColor: Colors.white),
                ),
              ),
              const SizedBox(height: 12),
              SelectableText(inv.entryCode ?? '',
                  style: TextStyle(fontFamily: 'monospace', fontSize: 22, letterSpacing: 3, fontWeight: FontWeight.w800, color: ty.ink)),
              const SizedBox(height: 4),
              Text(l10n.invPassHint, textAlign: TextAlign.center, style: TyType.sans(12, color: ty.ink3)),
            ]),
          ),
          const SizedBox(height: 14),
          Text(l10n.invShareHeading, style: TyType.eyebrow(11, color: ty.ink3)),
          const SizedBox(height: 10),
          Row(children: [
            Expanded(child: _shareButton(Icons.ios_share_rounded, l10n.invShareSheet, () => _shareSheet(inv))),
            const SizedBox(width: 8),
            Expanded(child: _shareButton(Icons.chat_rounded, l10n.invChannelWhatsapp, () => _whatsapp(inv))),
            const SizedBox(width: 8),
            Expanded(child: _shareButton(Icons.link_rounded, l10n.invCopyLink, () => _copy(inv))),
          ]),
          if ((_caps?.email ?? false) && (inv.email ?? '').isNotEmpty) ...[
            const SizedBox(height: 8),
            _shareButton(Icons.mail_outline_rounded, l10n.invSendEmail, () => _email(inv)),
          ],
          const SizedBox(height: 8),
          Text(
            inv.lastSharedAt == null
                ? l10n.invNeverShared
                : l10n.invLastShared(labels.channel(inv.lastSharedChannel), labels.when(inv.lastSharedAt!)),
            style: TyType.sans(12, color: ty.ink3),
          ),
          const SizedBox(height: 20),
        ],

        if (inv.isRevoked)
          Container(
            padding: const EdgeInsets.all(14),
            margin: const EdgeInsets.only(bottom: 18),
            decoration: BoxDecoration(color: ty.rose.withValues(alpha: 0.10), borderRadius: BorderRadius.circular(14)),
            child: Text(
              inv.revokedReason == null ? l10n.invRevokedBanner : l10n.invRevokedBannerReason(inv.revokedReason!),
              style: TyType.sans(13.5, color: ty.rose, weight: FontWeight.w600),
            ),
          ),

        Text(l10n.invDetailsHeading, style: TyType.eyebrow(11, color: ty.ink3)),
        const SizedBox(height: 8),
        _card(ty, [
          _row(Icons.confirmation_number_outlined, l10n.invFieldAllowance, labels.allowance(inv.plusOnesAllowed)),
          if (inv.rsvpPartySize != null) _row(Icons.groups_2_outlined, l10n.invRsvpParty, '${inv.rsvpPartySize}'),
          if (window != null) _row(Icons.schedule_rounded, l10n.invFieldArrival, window),
          if (inv.phone != null) _row(Icons.phone_outlined, l10n.invFieldPhone, inv.phone!),
          if (inv.email != null) _row(Icons.mail_outline_rounded, l10n.invFieldEmail, inv.email!),
          if (inv.vehicleNumber != null) _row(Icons.directions_car_outlined, l10n.invFieldVehicle, inv.vehicleNumber!),
          if (inv.groupTag != null) _row(Icons.label_outline_rounded, l10n.invFieldGroup, inv.groupTag!),
          if (inv.checkedInAt != null)
            _row(Icons.login_rounded, l10n.invCheckedInAt,
                '${labels.when(inv.checkedInAt!)}${inv.checkedInPartySize != null ? ' · ${inv.checkedInPartySize}' : ''}'),
          if (inv.checkedOutAt != null) _row(Icons.logout_rounded, l10n.invCheckedOutAt, labels.when(inv.checkedOutAt!)),
          if (inv.guestNote != null) _row(Icons.chat_bubble_outline_rounded, l10n.invGuestNote, inv.guestNote!),
          if (inv.notes != null) _row(Icons.lock_outline_rounded, l10n.invFieldNotes, inv.notes!),
        ]),
        const SizedBox(height: 18),

        if (!inv.isRevoked) ...[
          TyButton(l10n.invEditButton, full: true, kind: TyButtonKind.soft, leadingIcon: Icons.edit_outlined,
              enabled: !_busy, onTap: () => _edit(inv)),
          const SizedBox(height: 10),
          TyButton(l10n.invRotateButton, full: true, kind: TyButtonKind.ghost, leadingIcon: Icons.autorenew_rounded,
              enabled: !_busy, onTap: () => _rotate(inv)),
          const SizedBox(height: 10),
          TextButton.icon(
            onPressed: _busy ? null : () => _revoke(inv),
            icon: Icon(Icons.block_rounded, color: ty.rose),
            label: Text(l10n.invRevokeButton, style: TyType.sans(14.5, color: ty.rose, weight: FontWeight.w700)),
          ),
          const SizedBox(height: 12),
        ],

        Text(l10n.invActivityHeading, style: TyType.eyebrow(11, color: ty.ink3)),
        const SizedBox(height: 8),
        ..._activity(context, detail, labels),
      ],
    );
  }

  List<Widget> _activity(BuildContext context, InvitationDetail detail, InvitationLabels labels) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final items = <({DateTime at, String title, String? by, Color color})>[
      for (final h in detail.history)
        (
          at: h.occurredAt,
          title: labels.historyEvent(h.eventType, newStatus: h.newStatus, details: h.details),
          by: h.actorLabel,
          color: ty.saffron,
        ),
      // Failed gate attempts aren't in the history (nothing changed) but the
      // host should still see that a pass was presented and refused.
      for (final e in detail.entries.where((e) => e.result != 'checked_in' && e.result != 'checked_out'))
        (at: e.occurredAt, title: l10n.invGateAttempt(labels.gateResult(e.result)), by: e.operatorLabel, color: ty.rose),
    ]..sort((a, b) => b.at.compareTo(a.at));

    if (items.isEmpty) return [Text(l10n.invNoActivity, style: TyType.sans(13, color: ty.ink3))];
    return [
      for (final item in items)
        Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Container(
              margin: const EdgeInsets.only(top: 5),
              width: 8,
              height: 8,
              decoration: BoxDecoration(color: item.color, shape: BoxShape.circle),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(item.title, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w600)),
                Text([labels.when(item.at), if (item.by != null) item.by!].join(' · '),
                    style: TyType.sans(12, color: ty.ink3)),
              ]),
            ),
          ]),
        ),
    ];
  }

  Widget _pill(String text, Color color) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(color: color.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(999)),
        child: Text(text, style: TyType.sans(12, color: color, weight: FontWeight.w700)),
      );

  Widget _shareButton(IconData icon, String label, VoidCallback onTap) {
    final ty = context.ty;
    return Material(
      color: ty.surface,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: _busy ? null : onTap,
        child: Container(
          constraints: const BoxConstraints(minHeight: 56),
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 10),
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(14), border: Border.all(color: ty.line)),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Icon(icon, color: ty.saffronDeep, size: 22),
            const SizedBox(height: 4),
            Text(label, maxLines: 1, overflow: TextOverflow.ellipsis,
                style: TyType.sans(12, color: ty.ink, weight: FontWeight.w600)),
          ]),
        ),
      ),
    );
  }

  Widget _card(TyColors ty, List<Widget> rows) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
        decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(18), border: Border.all(color: ty.line)),
        child: Column(children: rows),
      );

  Widget _row(IconData icon, String label, String value) {
    final ty = context.ty;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 9),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Icon(icon, size: 19, color: ty.ink3),
        const SizedBox(width: 12),
        SizedBox(width: 104, child: Text(label, style: TyType.sans(13, color: ty.ink3))),
        Expanded(child: Text(value, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w600))),
      ]),
    );
  }
}
