import 'package:flutter/material.dart';
import 'package:flutter_contacts/flutter_contacts.dart';

import '../../data/services/invitation_service.dart';
import '../../l10n/generated/app_localizations.dart';
import '../../theme/colors.dart';
import '../../theme/typography.dart';
import '../../widgets/common.dart';
import '../../widgets/ty_button.dart';

/// Invite several guests in one go: paste "Name, phone" lines or pick
/// contacts, set one allowance for everyone, and get a per-guest result.
/// Retrying the same batch is safe — the server recognises it.
class BulkInviteScreen extends StatefulWidget {
  final String celebrationId;
  const BulkInviteScreen({super.key, required this.celebrationId});

  @override
  State<BulkInviteScreen> createState() => _BulkInviteScreenState();
}

class _Row {
  final String name;
  final String? phone;
  _Row(this.name, this.phone);
}

class _BulkInviteScreenState extends State<BulkInviteScreen> {
  static const _maxRows = 100;
  final _service = InvitationService();
  final _paste = TextEditingController();
  final List<_Row> _rows = [];
  int _plusOnes = 0;
  bool _saving = false;
  String? _error;
  BulkInviteResult? _result;
  String _batchId = newRequestId('bulk');

  @override
  void dispose() {
    _paste.dispose();
    super.dispose();
  }

  void _parsePaste() {
    final added = <_Row>[];
    for (final raw in _paste.text.split('\n')) {
      final line = raw.trim();
      if (line.isEmpty) continue;
      final parts = line.split(RegExp(r'[,\t;]'));
      final name = parts.first.trim();
      final phone = parts.length > 1 ? parts.sublist(1).join(' ').trim() : null;
      if (name.isNotEmpty) added.add(_Row(name, (phone ?? '').isEmpty ? null : phone));
    }
    setState(() {
      _rows.addAll(added.take(_maxRows - _rows.length));
      _paste.clear();
      _changed();
    });
  }

  Future<void> _addContact() async {
    final l10n = AppLocalizations.of(context)!;
    try {
      if (!await FlutterContacts.requestPermission(readonly: true)) {
        _snack(l10n.invContactsPermissionDenied);
        return;
      }
      final picked = await FlutterContacts.openExternalPick();
      if (picked == null) return;
      final c = await FlutterContacts.getContact(picked.id, withProperties: true) ?? picked;
      if (_rows.length >= _maxRows) return;
      setState(() {
        _rows.add(_Row(c.displayName, c.phones.isEmpty ? null : c.phones.first.number));
        _changed();
      });
    } catch (_) {
      _snack(l10n.invContactsUnavailable);
    }
  }

  /// A different list is a different batch.
  void _changed() {
    _batchId = newRequestId('bulk');
    _result = null;
  }

  void _snack(String m) {
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));
  }

  Future<void> _submit() async {
    if (_saving || _rows.isEmpty) return;
    final l10n = AppLocalizations.of(context)!;
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final result = await _service.bulkCreate(
        widget.celebrationId,
        [for (final r in _rows) InvitationDraft(name: r.name, phone: r.phone, plusOnesAllowed: _plusOnes)],
        clientRequestId: _batchId,
      );
      if (mounted) setState(() => _result = result);
    } catch (e) {
      if (mounted) setState(() => _error = isNoResponse(e) ? l10n.invSaveUncertain : invitationErrorMessage(e));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final result = _result;
    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: l10n.invBulkTitle),
      body: ListView(
        padding: EdgeInsets.fromLTRB(18, 8, 18, 24 + MediaQuery.paddingOf(context).bottom),
        children: [
          if (result == null) ...[
            Text(l10n.invBulkIntro, style: TyType.sans(13.5, color: ty.ink2, height: 1.45)),
            const SizedBox(height: 12),
            TextField(
              controller: _paste,
              minLines: 3,
              maxLines: 6,
              decoration: InputDecoration(
                hintText: l10n.invBulkPasteHint,
                filled: true,
                fillColor: ty.surface,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
              ),
            ),
            const SizedBox(height: 8),
            Row(children: [
              Expanded(child: OutlinedButton.icon(onPressed: _parsePaste, icon: const Icon(Icons.playlist_add_rounded), label: Text(l10n.invBulkAddLines))),
              const SizedBox(width: 8),
              Expanded(child: OutlinedButton.icon(onPressed: _addContact, icon: const Icon(Icons.contacts_outlined), label: Text(l10n.invBulkAddContact))),
            ]),
            const SizedBox(height: 16),
            Row(children: [
              Expanded(child: Text(l10n.invBulkAllowance, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w600))),
              IconButton(onPressed: _plusOnes > 0 ? () => setState(() { _plusOnes--; _changed(); }) : null,
                  tooltip: l10n.invAllowanceLess, icon: const Icon(Icons.remove_circle_outline_rounded)),
              Text('+$_plusOnes', style: TyType.sans(16, color: ty.ink, weight: FontWeight.w700)),
              IconButton(onPressed: _plusOnes < 10 ? () => setState(() { _plusOnes++; _changed(); }) : null,
                  tooltip: l10n.invAllowanceMore, icon: const Icon(Icons.add_circle_outline_rounded)),
            ]),
            const SizedBox(height: 8),
            Text(l10n.invBulkCount(_rows.length, _maxRows), style: TyType.eyebrow(11, color: ty.ink3)),
            const SizedBox(height: 6),
            for (var i = 0; i < _rows.length; i++)
              ListTile(
                dense: true,
                contentPadding: const EdgeInsets.symmetric(horizontal: 4),
                title: Text(_rows[i].name, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w600)),
                subtitle: Text(_rows[i].phone ?? l10n.invBulkNoPhone, style: TyType.sans(12, color: ty.ink3)),
                trailing: IconButton(
                  tooltip: l10n.invBulkRemove,
                  icon: const Icon(Icons.close_rounded, size: 20),
                  onPressed: _saving ? null : () => setState(() { _rows.removeAt(i); _changed(); }),
                ),
              ),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 10),
                child: Text(_error!, style: TyType.sans(13.5, color: ty.rose, weight: FontWeight.w600)),
              ),
            const SizedBox(height: 12),
            TyButton(
              _saving ? l10n.invSaving : l10n.invBulkSubmit(_rows.length),
              full: true,
              enabled: !_saving && _rows.isNotEmpty,
              onTap: _submit,
            ),
          ] else ...[
            Text(l10n.invBulkDone(result.created, result.skipped), style: TyType.display(19, color: ty.ink)),
            const SizedBox(height: 12),
            for (final r in result.results)
              ListTile(
                contentPadding: const EdgeInsets.symmetric(horizontal: 4),
                leading: Icon(
                  r.status == 'created' || r.status == 'existing' ? Icons.check_circle_rounded : Icons.error_outline_rounded,
                  color: r.status == 'created' || r.status == 'existing' ? ty.leaf : ty.rose,
                ),
                title: Text(r.index < _rows.length ? _rows[r.index].name : '#${r.index + 1}',
                    style: TyType.sans(14, color: ty.ink, weight: FontWeight.w600)),
                subtitle: Text(
                  switch (r.status) {
                    'created' => l10n.invBulkRowCreated,
                    'existing' => l10n.invBulkRowExisting,
                    _ => r.message ?? l10n.invBulkRowSkipped,
                  },
                  style: TyType.sans(12.5, color: ty.ink3),
                ),
              ),
            const SizedBox(height: 16),
            TyButton(l10n.invDone, full: true, onTap: () => Navigator.of(context).pop(result.created > 0)),
          ],
        ],
      ),
    );
  }
}
