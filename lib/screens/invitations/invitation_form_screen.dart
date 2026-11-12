import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_contacts/flutter_contacts.dart';

import '../../data/services/invitation_service.dart';
import '../../l10n/generated/app_localizations.dart';
import '../../theme/colors.dart';
import '../../theme/typography.dart';
import '../../widgets/common.dart';
import '../../widgets/ty_button.dart';

/// Create a guest invitation, or edit one ([existing] set).
///
/// The idempotency key is generated once per form, so tapping "Create" again
/// after a timeout can never produce a second invitation.
class InvitationFormScreen extends StatefulWidget {
  final String celebrationId;
  final GuestInvitation? existing;
  const InvitationFormScreen({super.key, required this.celebrationId, this.existing});

  @override
  State<InvitationFormScreen> createState() => _InvitationFormScreenState();
}

class _InvitationFormScreenState extends State<InvitationFormScreen> {
  final _service = InvitationService();
  final _formKey = GlobalKey<FormState>();
  late final String _requestId = newRequestId('inv');
  late final TextEditingController _name, _phone, _email, _notes;
  bool _saving = false;
  String? _error;

  bool get _editing => widget.existing != null;

  @override
  void initState() {
    super.initState();
    final e = widget.existing;
    _name = TextEditingController(text: e?.name ?? '');
    _phone = TextEditingController(text: e?.phone ?? '');
    _email = TextEditingController(text: e?.email ?? '');
    _notes = TextEditingController(text: e?.notes ?? '');
  }

  @override
  void dispose() {
    for (final c in [_name, _phone, _email, _notes]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _pickContact() async {
    final l10n = AppLocalizations.of(context)!;
    try {
      if (!await FlutterContacts.requestPermission(readonly: true)) {
        _snack(l10n.invContactsPermissionDenied);
        return;
      }
      final contact = await FlutterContacts.openExternalPick();
      if (contact == null) return;
      final full = await FlutterContacts.getContact(contact.id, withProperties: true) ?? contact;
      setState(() {
        if (full.displayName.isNotEmpty) _name.text = full.displayName;
        if (full.phones.isNotEmpty) _phone.text = full.phones.first.number;
        if (full.emails.isNotEmpty && _email.text.isEmpty) _email.text = full.emails.first.address;
      });
    } catch (_) {
      _snack(l10n.invContactsUnavailable);
    }
  }

  void _snack(String m) {
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));
  }

  Future<void> _submit() async {
    if (_saving || !_formKey.currentState!.validate()) return;
    final l10n = AppLocalizations.of(context)!;
    setState(() {
      _saving = true;
      _error = null;
    });
    // Allowance, arrival window, vehicle and group aren't asked for any more,
    // but a guest saved with them keeps them: an edit sends everything back.
    final old = widget.existing;
    final draft = InvitationDraft(
      name: _name.text,
      phone: _phone.text,
      email: _email.text,
      plusOnesAllowed: old?.plusOnesAllowed ?? 0,
      arrivalWindowStart: old?.arrivalWindowStart,
      arrivalWindowEnd: old?.arrivalWindowEnd,
      vehicleNumber: old?.vehicleNumber,
      groupTag: old?.groupTag,
      notes: _notes.text,
    );
    try {
      final result = _editing
          ? await _service.update(widget.celebrationId, widget.existing!.id, draft)
          : await _service.create(widget.celebrationId, draft, clientRequestId: _requestId);
      if (!mounted) return;
      Navigator.of(context).pop(result);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _saving = false;
        // Without a server answer we genuinely don't know whether it saved;
        // retrying is safe because the request id is reused.
        _error = isNoResponse(e) ? l10n.invSaveUncertain : invitationErrorMessage(e);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: _editing ? l10n.invEditTitle : l10n.invCreateTitle),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: EdgeInsets.fromLTRB(18, 8, 18, 24 + MediaQuery.paddingOf(context).bottom),
          children: [
            if (!_editing)
              Align(
                alignment: Alignment.centerLeft,
                child: TextButton.icon(
                  onPressed: _saving ? null : _pickContact,
                  icon: Icon(Icons.contacts_outlined, color: ty.saffronDeep, size: 20),
                  label: Text(l10n.invPickContact, style: TyType.sans(14, color: ty.saffronDeep, weight: FontWeight.w700)),
                ),
              ),
            _field(context, _name, l10n.invFieldName, required: true, capitalization: TextCapitalization.words,
                autofillHints: const [AutofillHints.name]),
            _field(context, _phone, l10n.invFieldPhone, hint: l10n.invFieldPhoneHint, keyboard: TextInputType.phone,
                autofillHints: const [AutofillHints.telephoneNumber], validator: (v) {
              final digits = (v ?? '').replaceAll(RegExp(r'[^0-9]'), '');
              if ((v ?? '').trim().isEmpty) return null;
              return digits.length < 7 || digits.length > 15 ? l10n.invFieldPhoneInvalid : null;
            }),
            _field(context, _email, l10n.invFieldEmail, keyboard: TextInputType.emailAddress,
                autofillHints: const [AutofillHints.email], validator: (v) {
              final t = (v ?? '').trim();
              if (t.isEmpty) return null;
              return RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(t) ? null : l10n.invFieldEmailInvalid;
            }),
            _field(context, _notes, l10n.invFieldNotes, hint: l10n.invFieldNotesHint, maxLines: 3),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Text(_error!, style: TyType.sans(13.5, color: ty.rose, weight: FontWeight.w600)),
              ),
            TyButton(
              _saving ? l10n.invSaving : (_editing ? l10n.invSaveChanges : l10n.invCreateButton),
              full: true,
              enabled: !_saving,
              onTap: _submit,
            ),
          ],
        ),
      ),
    );
  }

  Widget _field(
    BuildContext context,
    TextEditingController controller,
    String label, {
    String? hint,
    bool required = false,
    TextInputType? keyboard,
    TextCapitalization capitalization = TextCapitalization.none,
    int maxLines = 1,
    int? maxLength,
    Iterable<String>? autofillHints,
    String? Function(String?)? validator,
  }) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: TextFormField(
        controller: controller,
        enabled: !_saving,
        keyboardType: keyboard,
        textCapitalization: capitalization,
        maxLines: maxLines,
        autofillHints: autofillHints,
        inputFormatters: maxLength == null ? null : [LengthLimitingTextInputFormatter(maxLength)],
        style: TyType.sans(15, color: ty.ink),
        decoration: InputDecoration(
          labelText: required ? '$label *' : label,
          hintText: hint,
          filled: true,
          fillColor: ty.surface,
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide(color: ty.line)),
          enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide(color: ty.line)),
        ),
        validator: validator ??
            (required ? (v) => (v == null || v.trim().isEmpty) ? l10n.invFieldRequired : null : null),
      ),
    );
  }
}
