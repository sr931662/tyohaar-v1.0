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
  late final TextEditingController _name, _phone, _email, _vehicle, _group, _notes;
  late int _plusOnes;
  TimeOfDay? _arriveFrom, _arriveTo;
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
    _vehicle = TextEditingController(text: e?.vehicleNumber ?? '');
    _group = TextEditingController(text: e?.groupTag ?? '');
    _notes = TextEditingController(text: e?.notes ?? '');
    _plusOnes = e?.plusOnesAllowed ?? 0;
    _arriveFrom = _parse(e?.arrivalWindowStart);
    _arriveTo = _parse(e?.arrivalWindowEnd);
  }

  @override
  void dispose() {
    for (final c in [_name, _phone, _email, _vehicle, _group, _notes]) {
      c.dispose();
    }
    super.dispose();
  }

  static TimeOfDay? _parse(String? hhmm) {
    if (hhmm == null || hhmm.length < 5) return null;
    final p = hhmm.split(':');
    return TimeOfDay(hour: int.parse(p[0]), minute: int.parse(p[1]));
  }

  static String? _fmt(TimeOfDay? t) =>
      t == null ? null : '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';

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

  Future<void> _pickTime(bool start) async {
    final picked = await showTimePicker(
      context: context,
      initialTime: (start ? _arriveFrom : _arriveTo) ?? const TimeOfDay(hour: 19, minute: 0),
    );
    if (picked == null) return;
    setState(() {
      if (start) {
        _arriveFrom = picked;
        _arriveTo ??= TimeOfDay(hour: (picked.hour + 2) % 24, minute: picked.minute);
      } else {
        _arriveTo = picked;
        _arriveFrom ??= TimeOfDay(hour: (picked.hour + 22) % 24, minute: picked.minute);
      }
    });
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
    final draft = InvitationDraft(
      name: _name.text,
      phone: _phone.text,
      email: _email.text,
      plusOnesAllowed: _plusOnes,
      arrivalWindowStart: _fmt(_arriveFrom),
      arrivalWindowEnd: _fmt(_arriveTo),
      vehicleNumber: _vehicle.text,
      groupTag: _group.text,
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
    final windowText = _arriveFrom == null
        ? l10n.invArrivalNotSet
        : '${_arriveFrom!.format(context)} – ${_arriveTo!.format(context)}';

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
            const SizedBox(height: 6),
            _sectionLabel(context, l10n.invFieldAllowance),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
              decoration: _box(ty),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      _plusOnes == 0 ? l10n.invAllowanceSolo : l10n.invAllowancePlus(_plusOnes),
                      style: TyType.sans(14.5, color: ty.ink, weight: FontWeight.w600),
                    ),
                  ),
                  IconButton(
                    tooltip: l10n.invAllowanceLess,
                    onPressed: _plusOnes > 0 ? () => setState(() => _plusOnes--) : null,
                    icon: const Icon(Icons.remove_circle_outline_rounded),
                  ),
                  Text('$_plusOnes', style: TyType.sans(16, color: ty.ink, weight: FontWeight.w700)),
                  IconButton(
                    tooltip: l10n.invAllowanceMore,
                    onPressed: _plusOnes < 10 ? () => setState(() => _plusOnes++) : null,
                    icon: const Icon(Icons.add_circle_outline_rounded),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),
            _sectionLabel(context, l10n.invFieldArrival),
            Container(
              padding: const EdgeInsets.fromLTRB(14, 4, 4, 4),
              decoration: _box(ty),
              child: Row(
                children: [
                  Expanded(child: Text(windowText, style: TyType.sans(14.5, color: _arriveFrom == null ? ty.ink3 : ty.ink))),
                  TextButton(onPressed: () => _pickTime(true), child: Text(l10n.invArrivalFrom)),
                  TextButton(onPressed: () => _pickTime(false), child: Text(l10n.invArrivalTo)),
                  if (_arriveFrom != null)
                    IconButton(
                      tooltip: l10n.invArrivalClear,
                      onPressed: () => setState(() => _arriveFrom = _arriveTo = null),
                      icon: const Icon(Icons.close_rounded, size: 20),
                    ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.only(top: 6, left: 4),
              child: Text(l10n.invArrivalHelp, style: TyType.sans(12, color: ty.ink3)),
            ),
            const SizedBox(height: 10),
            _field(context, _vehicle, l10n.invFieldVehicle, capitalization: TextCapitalization.characters, maxLength: 20),
            _field(context, _group, l10n.invFieldGroup, hint: l10n.invFieldGroupHint, capitalization: TextCapitalization.words),
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

  BoxDecoration _box(TyColors ty) =>
      BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(14), border: Border.all(color: ty.line));

  Widget _sectionLabel(BuildContext context, String text) => Padding(
        padding: const EdgeInsets.only(bottom: 8, left: 4),
        child: Text(text, style: TyType.sans(13, color: context.ty.ink2, weight: FontWeight.w600)),
      );

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
