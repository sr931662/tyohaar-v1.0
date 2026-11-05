import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:intl/intl.dart';

import '../../data/services/event_service.dart';
import '../../data/services/invitation_service.dart' show invitationErrorMessage, isNoResponse, newRequestId;
import '../../data/services/media_service.dart';
import '../../l10n/generated/app_localizations.dart';
import '../../theme/colors.dart';
import '../../theme/typography.dart';
import '../../widgets/common.dart';
import '../../widgets/ty_button.dart';
import 'invitation_setup_screen.dart';

String eventTypeName(AppLocalizations l10n, String type) => switch (type) {
      'wedding' => l10n.evTypeWedding,
      'birthday' => l10n.evTypeBirthday,
      'anniversary' => l10n.evTypeAnniversary,
      'engagement' => l10n.evTypeEngagement,
      'baby_shower' => l10n.evTypeBabyShower,
      'housewarming' => l10n.evTypeHousewarming,
      'religious' => l10n.evTypeReligious,
      'corporate' => l10n.evTypeCorporate,
      _ => l10n.evTypeCustom,
    };

/// Journey B, first step: tell us about your event. Nothing here asks about a
/// booking. Saving creates a draft and moves on to the invitation itself, so
/// leaving part-way loses nothing and guests see nothing until it is published.
class CreateEventWizard extends StatefulWidget {
  final EventService? service;
  const CreateEventWizard({super.key, this.service});

  @override
  State<CreateEventWizard> createState() => _CreateEventWizardState();
}

class _CreateEventWizardState extends State<CreateEventWizard> {
  late final EventService _service = widget.service ?? EventService();
  final _form = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _custom = TextEditingController();
  final _host = TextEditingController();
  final _venue = TextEditingController();
  final _address = TextEditingController();
  final _description = TextEditingController();
  final _contactName = TextEditingController();
  final _contactPhone = TextEditingController();
  late final String _requestId = newRequestId('evt');

  String? _type;
  DateTime? _date;
  TimeOfDay? _time;
  File? _cover;
  bool _saving = false;
  String? _error;

  @override
  void dispose() {
    for (final c in [_name, _custom, _host, _venue, _address, _description, _contactName, _contactPhone]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _pickDate() async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: _date ?? now.add(const Duration(days: 30)),
      firstDate: DateTime(now.year, now.month, now.day),
      lastDate: now.add(const Duration(days: 730)),
    );
    if (picked != null) setState(() => _date = picked);
  }

  Future<void> _pickTime() async {
    final picked = await showTimePicker(context: context, initialTime: _time ?? const TimeOfDay(hour: 18, minute: 0));
    if (picked != null) setState(() => _time = picked);
  }

  Future<void> _pickCover() async {
    final picked = await ImagePicker().pickImage(source: ImageSource.gallery, maxWidth: 1800, imageQuality: 85);
    if (picked != null) setState(() => _cover = File(picked.path));
  }

  Future<void> _submit() async {
    final l10n = AppLocalizations.of(context)!;
    final valid = _form.currentState!.validate();
    if (_type == null || _date == null) {
      setState(() => _error = _type == null ? l10n.evWizardChooseCategory : l10n.evWizardChooseDate);
      return;
    }
    if (!valid) return;
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      String? coverUrl;
      if (_cover != null) coverUrl = await MediaService().uploadInvitationCover(_cover!);
      final time = _time == null
          ? null
          : '${_time!.hour.toString().padLeft(2, '0')}:${_time!.minute.toString().padLeft(2, '0')}';
      final event = await _service.create(
        EventDraft(
          title: _name.text,
          eventType: _type!,
          customEventType: _type == 'custom' ? _custom.text.trim() : null,
          hostName: _host.text.trim(),
          date: _date!,
          startTime: time,
          venueName: _venue.text.trim(),
          venueAddress: _address.text.trim(),
          description: _description.text.trim(),
          coverImageUrl: coverUrl,
          contactName: _contactName.text.trim(),
          contactPhone: _contactPhone.text.trim(),
        ),
        clientRequestId: _requestId,
      );
      if (!mounted) return;
      Navigator.of(context).pushReplacement(MaterialPageRoute(
        builder: (_) => InvitationSetupScreen(eventId: event.id, service: widget.service),
      ));
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
    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: l10n.evWizardTitle),
      body: Form(
        key: _form,
        child: ListView(
          padding: EdgeInsets.fromLTRB(18, 6, 18, 28 + MediaQuery.paddingOf(context).bottom),
          children: [
            Text(l10n.evWizardIntro, style: TyType.sans(13.5, color: ty.ink2, height: 1.4)),
            const SizedBox(height: 16),
            EventField(controller: _name, label: l10n.evFieldName, hint: l10n.evFieldNameHint, maxLength: 300,
                validator: (v) => (v ?? '').trim().isEmpty ? l10n.evFieldNameRequired : null),
            Text(l10n.evFieldCategory, style: TyType.sans(13, color: ty.ink2, weight: FontWeight.w700)),
            const SizedBox(height: 8),
            Wrap(spacing: 8, runSpacing: 8, children: [
              for (final t in kEventTypes)
                ChoiceChip(
                  label: Text(eventTypeName(l10n, t)),
                  selected: _type == t,
                  onSelected: (_) => setState(() {
                    _type = t;
                    _error = null;
                  }),
                ),
            ]),
            const SizedBox(height: 14),
            if (_type == 'custom')
              EventField(controller: _custom, label: l10n.evFieldCustomType, hint: l10n.evFieldCustomTypeHint, maxLength: 80,
                  validator: (v) => (v ?? '').trim().isEmpty ? l10n.evFieldCustomTypeRequired : null),
            EventField(controller: _host, label: l10n.evFieldHost, hint: l10n.evFieldHostHint, maxLength: 200),
            Row(children: [
              Expanded(
                child: _PickerTile(
                  icon: Icons.event_rounded,
                  label: l10n.evFieldDate,
                  value: _date == null ? null : DateFormat('d MMM yyyy').format(_date!),
                  onTap: _pickDate,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _PickerTile(
                  icon: Icons.schedule_rounded,
                  label: l10n.evFieldTime,
                  value: _time?.format(context),
                  onTap: _pickTime,
                ),
              ),
            ]),
            const SizedBox(height: 14),
            EventField(controller: _venue, label: l10n.evFieldVenue, hint: l10n.evFieldVenueHint, maxLength: 300),
            EventField(controller: _address, label: l10n.evFieldAddress, maxLength: 1000, maxLines: 2),
            EventField(controller: _description, label: l10n.evFieldDescription, maxLength: 4000, maxLines: 3),
            Text(l10n.evFieldCover, style: TyType.sans(13, color: ty.ink2, weight: FontWeight.w700)),
            const SizedBox(height: 8),
            InkWell(
              borderRadius: BorderRadius.circular(14),
              onTap: _pickCover,
              child: Container(
                height: _cover == null ? 72 : 150,
                clipBehavior: Clip.antiAlias,
                decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(14), border: Border.all(color: ty.line)),
                child: _cover != null
                    ? Image.file(_cover!, fit: BoxFit.cover, width: double.infinity)
                    : Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                        Icon(Icons.add_photo_alternate_outlined, color: ty.ink3),
                        const SizedBox(width: 8),
                        Text(l10n.evFieldCoverAdd, style: TyType.sans(13.5, color: ty.ink2, weight: FontWeight.w600)),
                      ]),
              ),
            ),
            const SizedBox(height: 16),
            Text(l10n.evFieldContactHeading, style: TyType.sans(13, color: ty.ink2, weight: FontWeight.w700)),
            const SizedBox(height: 2),
            Text(l10n.evFieldContactNote, style: TyType.sans(12, color: ty.ink3)),
            const SizedBox(height: 8),
            EventField(controller: _contactName, label: l10n.evFieldContactName, maxLength: 200),
            EventField(controller: _contactPhone, label: l10n.evFieldContactPhone, maxLength: 20, keyboardType: TextInputType.phone),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Text(_error!, style: TyType.sans(13.5, color: ty.rose, weight: FontWeight.w600)),
              ),
            TyButton(_saving ? l10n.invSaving : l10n.evWizardContinue, full: true, enabled: !_saving, onTap: _submit),
          ],
        ),
      ),
    );
  }
}

class _PickerTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final String? value;
  final VoidCallback onTap;
  const _PickerTile({required this.icon, required this.label, this.value, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return InkWell(
      borderRadius: BorderRadius.circular(14),
      onTap: onTap,
      child: Container(
        constraints: const BoxConstraints(minHeight: 58),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
        decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(14), border: Border.all(color: ty.line)),
        child: Row(children: [
          Icon(icon, size: 18, color: ty.saffronDeep),
          const SizedBox(width: 8),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(label, style: TyType.sans(11.5, color: ty.ink3, weight: FontWeight.w600)),
              Text(value ?? '—', maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: TyType.sans(14, color: ty.ink, weight: FontWeight.w700)),
            ]),
          ),
        ]),
      ),
    );
  }
}

/// The text field used across the event forms.
class EventField extends StatelessWidget {
  final TextEditingController controller;
  final String label;
  final String? hint;
  final int? maxLength;
  final int maxLines;
  final TextInputType? keyboardType;
  final String? Function(String?)? validator;

  const EventField({
    super.key,
    required this.controller,
    required this.label,
    this.hint,
    this.maxLength,
    this.maxLines = 1,
    this.keyboardType,
    this.validator,
  });

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: TextFormField(
        controller: controller,
        maxLength: maxLength,
        maxLines: maxLines,
        keyboardType: keyboardType,
        validator: validator,
        textCapitalization: keyboardType == null ? TextCapitalization.sentences : TextCapitalization.none,
        buildCounter: (_, {required currentLength, required isFocused, maxLength}) => null,
        decoration: InputDecoration(
          labelText: label,
          hintText: hint,
          filled: true,
          fillColor: ty.surface,
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide(color: ty.line)),
          enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide(color: ty.line)),
        ),
      ),
    );
  }
}
