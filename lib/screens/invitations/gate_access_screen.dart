import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:share_plus/share_plus.dart';

import '../../data/services/invitation_service.dart';
import '../../l10n/generated/app_localizations.dart';
import '../../theme/colors.dart';
import '../../theme/typography.dart';
import '../../widgets/common.dart';
import '../../widgets/ty_button.dart';
import 'invitation_labels.dart';

/// Links for entry staff (society guards, family at the door). Each one opens
/// a web gate console for this celebration only — no Tyohaar account, no
/// access to anything else — and expires with the event or when revoked.
class GateAccessScreen extends StatefulWidget {
  final String celebrationId;
  final String celebrationTitle;
  const GateAccessScreen({super.key, required this.celebrationId, required this.celebrationTitle});

  @override
  State<GateAccessScreen> createState() => _GateAccessScreenState();
}

class _GateAccessScreenState extends State<GateAccessScreen> {
  final _service = InvitationService();
  List<GateAccess>? _items;
  String? _error;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final items = await _service.gateAccesses(widget.celebrationId);
      if (mounted) setState(() => _items = items);
    } catch (e) {
      if (mounted) setState(() => _error = invitationErrorMessage(e));
    }
  }

  Future<void> _create() async {
    final l10n = AppLocalizations.of(context)!;
    final label = TextEditingController();
    int hours = 24;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setLocal) => AlertDialog(
          title: Text(l10n.invGateAccessCreateTitle),
          content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            TextField(
              controller: label,
              autofocus: true,
              maxLength: 120,
              textCapitalization: TextCapitalization.sentences,
              decoration: InputDecoration(labelText: l10n.invGateAccessLabel, hintText: l10n.invGateAccessLabelHint),
            ),
            const SizedBox(height: 4),
            Text(l10n.invGateAccessValidFor, style: TyType.sans(13, color: ctx.ty.ink2)),
            Wrap(spacing: 8, children: [
              for (final h in const [6, 12, 24, 72])
                ChoiceChip(label: Text(l10n.invHours(h)), selected: hours == h, onSelected: (_) => setLocal(() => hours = h)),
            ]),
            const SizedBox(height: 8),
            Text(l10n.invGateAccessExpiryNote, style: TyType.sans(12, color: ctx.ty.ink3)),
          ]),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(l10n.commonCancel)),
            TextButton(
              onPressed: () => label.text.trim().length >= 2 ? Navigator.pop(ctx, true) : null,
              child: Text(l10n.invGateAccessCreate),
            ),
          ],
        ),
      ),
    );
    final text = label.text.trim();
    label.dispose();
    if (ok != true || _busy) return;
    setState(() => _busy = true);
    try {
      final access = await _service.createGateAccess(widget.celebrationId, text, validHours: hours);
      await _load();
      if (mounted && access.consoleUrl != null) await _showLinkOnce(access);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(invitationErrorMessage(e))));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  /// The server returns the link exactly once; it can't be shown again.
  Future<void> _showLinkOnce(GateAccess access) async {
    final l10n = AppLocalizations.of(context)!;
    final url = access.consoleUrl!;
    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        title: Text(l10n.invGateAccessReadyTitle),
        content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(l10n.invGateAccessReadyMessage(access.label)),
          const SizedBox(height: 12),
          SelectableText(url, style: TyType.sans(12.5, color: ctx.ty.ink2)),
        ]),
        actions: [
          TextButton(
            onPressed: () async {
              await Clipboard.setData(ClipboardData(text: url));
              if (ctx.mounted) {
                ScaffoldMessenger.of(ctx).showSnackBar(SnackBar(content: Text(l10n.invLinkCopied)));
              }
            },
            child: Text(l10n.invCopyLink),
          ),
          TextButton(
            onPressed: () => Share.share(l10n.invGateAccessShareMessage(widget.celebrationTitle, url)),
            child: Text(l10n.invShareSheet),
          ),
          TextButton(onPressed: () => Navigator.pop(ctx), child: Text(l10n.invDone)),
        ],
      ),
    );
  }

  Future<void> _revoke(GateAccess access) async {
    final l10n = AppLocalizations.of(context)!;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(l10n.invGateAccessRevokeTitle),
        content: Text(l10n.invGateAccessRevokeMessage(access.label)),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(l10n.commonCancel)),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: Text(l10n.invGateAccessRevoke, style: TextStyle(color: ctx.ty.rose, fontWeight: FontWeight.w700)),
          ),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await _service.revokeGateAccess(widget.celebrationId, access.id);
      await _load();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(invitationErrorMessage(e))));
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final labels = InvitationLabels(context);
    final items = _items;
    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: l10n.invGateAccessTitle),
      body: RefreshIndicator(
        onRefresh: _load,
        color: ty.saffron,
        child: ListView(
          padding: EdgeInsets.fromLTRB(18, 8, 18, 24 + MediaQuery.paddingOf(context).bottom),
          children: [
            Text(l10n.invGateAccessIntro, style: TyType.sans(13.5, color: ty.ink2, height: 1.45)),
            const SizedBox(height: 16),
            TyButton(_busy ? l10n.invSaving : l10n.invGateAccessNew, full: true, enabled: !_busy,
                leadingIcon: Icons.add_link_rounded, onTap: _create),
            const SizedBox(height: 20),
            if (_error != null) Text(_error!, style: TyType.sans(13, color: ty.rose)),
            if (items == null && _error == null) const Center(child: CircularProgressIndicator()),
            if (items != null && items.isEmpty)
              Text(l10n.invGateAccessEmpty, style: TyType.sans(13.5, color: ty.ink3)),
            for (final a in items ?? const <GateAccess>[])
              Container(
                margin: const EdgeInsets.only(bottom: 10),
                padding: const EdgeInsets.fromLTRB(14, 12, 6, 12),
                decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(16), border: Border.all(color: ty.line)),
                child: Row(children: [
                  Icon(Icons.badge_outlined, color: a.isActive ? ty.leaf : ty.ink3),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(a.label, style: TyType.sans(14.5, color: ty.ink, weight: FontWeight.w700)),
                      Text(
                        a.revokedAt != null
                            ? l10n.invGateAccessRevoked
                            : a.isActive
                                ? l10n.invGateAccessActiveUntil(labels.when(a.expiresAt!))
                                : l10n.invGateAccessExpired,
                        style: TyType.sans(12.5, color: a.isActive ? ty.leaf : ty.ink3),
                      ),
                      if (a.lastUsedAt != null)
                        Text(l10n.invGateAccessLastUsed(labels.when(a.lastUsedAt!)), style: TyType.sans(12, color: ty.ink3)),
                    ]),
                  ),
                  if (a.isActive)
                    TextButton(
                      onPressed: () => _revoke(a),
                      child: Text(l10n.invGateAccessRevoke, style: TextStyle(color: ty.rose, fontWeight: FontWeight.w700)),
                    ),
                ]),
              ),
          ],
        ),
      ),
    );
  }
}
