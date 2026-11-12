import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../data/services/event_service.dart';
import '../../data/services/invitation_service.dart' show invitationErrorMessage;
import '../../l10n/generated/app_localizations.dart';
import '../../theme/colors.dart';
import '../../theme/typography.dart';
import '../../widgets/event_ui.dart';
import '../../widgets/ty_button.dart';
import 'create_event_wizard.dart' show EventField;
import 'functions_editor.dart';

const _palettes = <(String, String, String)>[
  ('#5B1226', '#B8892F', '#FBF6EC'), // Burgundy & gold
  ('#7A1F3D', '#D08A3C', '#FDF5EE'), // Rani pink
  ('#1F4D3A', '#B8892F', '#F7F5EA'), // Mehendi green
  ('#1E2F5C', '#C49A45', '#F5F4EE'), // Royal navy
  ('#8A4B08', '#C8456B', '#FFF8EC'), // Marigold
];

/// Everything about how the invitation looks and behaves, on one page: what
/// guests read, the functions, the design, the RSVP questions and the shared
/// link. It lives in the dashboard's Invitation tab, so there is no separate
/// setup flow to find or finish. One Save stores it all; Preview and Publish
/// save first, so what you see is what guests get.
///
/// A booked customer's details arrive filled in, and changes here only change
/// what guests read, never the booking.
class InvitationSettingsPanel extends StatefulWidget {
  final EventDetail event;
  final EventService service;

  /// Reloads the event after anything changed on the server.
  final Future<void> Function() onChanged;

  /// Called once the invitation has gone live.
  final VoidCallback onPublished;

  const InvitationSettingsPanel({
    super.key,
    required this.event,
    required this.service,
    required this.onChanged,
    required this.onPublished,
  });

  @override
  State<InvitationSettingsPanel> createState() => _InvitationSettingsPanelState();
}

class _InvitationSettingsPanelState extends State<InvitationSettingsPanel> with AutomaticKeepAliveClientMixin {
  final _displayTitle = TextEditingController();
  final _displayVenue = TextEditingController();
  final _displayAddress = TextEditingController();
  final _instructions = TextEditingController();
  final _heading = TextEditingController();
  final _tagline = TextEditingController();
  final _message = TextEditingController();
  final _mealOptions = TextEditingController();

  String _template = 'classic';
  String _font = 'serif';
  int _palette = 0;
  String _invitationType = 'web';
  bool _allowMaybe = true, _allowEdit = true, _askCount = true, _askFood = false, _askAllergies = false, _askSpecial = false;
  DateTime? _deadline;
  List<Map<String, dynamic>> _questions = [];
  bool _busy = false;
  String? _error;

  @override
  bool get wantKeepAlive => true;

  EventDetail get _event => widget.event;

  @override
  void initState() {
    super.initState();
    final e = _event;
    final s = e.settings;
    _displayTitle.text = (s.display['title'] as String?) ?? e.title;
    _displayVenue.text = (s.display['venue_name'] as String?) ?? e.venueName ?? '';
    _displayAddress.text = (s.display['venue_address'] as String?) ?? e.venueAddress ?? '';
    _instructions.text = (s.display['instructions'] as String?) ?? '';
    _heading.text = (s.design['heading'] as String?) ?? '';
    _tagline.text = (s.design['tagline'] as String?) ?? '';
    _message.text = (s.design['message'] as String?) ?? '';
    _template = s.design['template'] as String? ?? 'classic';
    _font = s.design['font'] as String? ?? 'serif';
    final primary = (s.design['primary_color'] as String?)?.toUpperCase();
    final i = _palettes.indexWhere((p) => p.$1 == primary);
    _palette = i < 0 ? 0 : i;
    _invitationType = s.invitationType;
    _allowMaybe = s.rsvp['allow_maybe'] as bool? ?? true;
    _allowEdit = s.rsvp['allow_edit'] as bool? ?? true;
    _askCount = s.rsvp['ask_attendee_count'] as bool? ?? true;
    _askFood = s.rsvp['ask_food'] as bool? ?? false;
    _askAllergies = s.rsvp['ask_allergies'] as bool? ?? false;
    _askSpecial = s.rsvp['ask_special_requirements'] as bool? ?? false;
    _mealOptions.text = ((s.rsvp['meal_options'] as List?) ?? const []).join(', ');
    final deadline = s.rsvp['deadline'] as String?;
    _deadline = deadline == null ? null : DateTime.tryParse(deadline);
    _questions = ((s.rsvp['questions'] as List?) ?? const []).map((q) => Map<String, dynamic>.from(q as Map)).toList();
  }

  @override
  void dispose() {
    for (final c in [_displayTitle, _displayVenue, _displayAddress, _instructions, _heading, _tagline, _message, _mealOptions]) {
      c.dispose();
    }
    super.dispose();
  }

  String? _ymd(DateTime? d) => d == null ? null : DateFormat('yyyy-MM-dd').format(d);

  Map<String, dynamic> _payload() {
    final e = _event;
    final p = _palettes[_palette];
    String? clean(TextEditingController c) => c.text.trim().isEmpty ? null : c.text.trim();
    // Only what differs from the event record goes in as an override, so a
    // later change to the event still reaches the invitation.
    String? differs(TextEditingController c, String? original) => clean(c) == (original ?? '').trim() ? null : clean(c);
    return {
      'invitation_type': _invitationType,
      'display': {
        'title': differs(_displayTitle, e.title),
        'venue_name': differs(_displayVenue, e.venueName),
        'venue_address': differs(_displayAddress, e.venueAddress),
        'instructions': clean(_instructions),
      },
      'design': {
        'template': _template,
        'font': _font,
        'primary_color': p.$1,
        'accent_color': p.$2,
        'background_color': p.$3,
        'heading': clean(_heading),
        'tagline': clean(_tagline),
        'message': clean(_message),
      },
      'rsvp': {
        'allow_maybe': _allowMaybe,
        'allow_edit': _allowEdit,
        'ask_attendee_count': _askCount,
        'ask_food': _askFood,
        'ask_allergies': _askFood && _askAllergies,
        'ask_special_requirements': _askSpecial,
        'meal_options': _askFood
            ? _mealOptions.text.split(',').map((m) => m.trim()).where((m) => m.isNotEmpty).toList()
            : <String>[],
        'deadline': _ymd(_deadline),
        'questions': _questions,
      },
    };
  }

  void _snack(String m) {
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));
  }

  /// Runs [action] with the busy flag and a readable error, so every button
  /// here behaves the same way.
  Future<bool> _run(Future<void> Function() action) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await action();
      return true;
    } catch (e) {
      if (mounted) setState(() => _error = invitationErrorMessage(e));
      return false;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<bool> _save({bool announce = false}) async {
    final saved = AppLocalizations.of(context)!.evSaved;
    final ok = await _run(() async {
      await widget.service.saveSettings(_event.id, _payload());
      await widget.onChanged();
    });
    if (ok && announce) _snack(saved);
    return ok;
  }

  Future<void> _preview() async {
    final l10n = AppLocalizations.of(context)!;
    if (!await _save() || !mounted) return;
    try {
      await launchUrl(Uri.parse(await widget.service.previewLink(_event.id)), mode: LaunchMode.externalApplication);
    } catch (_) {
      if (mounted) setState(() => _error = l10n.evPreviewFailed);
    }
  }

  Future<void> _publish() async {
    if (!await _save() || !mounted) return;
    final ok = await _run(() async {
      await widget.service.publish(_event.id);
      await widget.onChanged();
    });
    if (ok && mounted) widget.onPublished();
  }

  Future<void> _addQuestion() async {
    final l10n = AppLocalizations.of(context)!;
    final label = TextEditingController();
    final options = TextEditingController();
    var kind = 'text';
    var required = false;
    final added = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, set) => AlertDialog(
          title: Text(l10n.evQuestionAdd),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              TextField(controller: label, maxLength: 200, decoration: InputDecoration(labelText: l10n.evQuestionLabel)),
              DropdownButton<String>(
                value: kind,
                isExpanded: true,
                items: [
                  DropdownMenuItem(value: 'text', child: Text(l10n.evQuestionKindText)),
                  DropdownMenuItem(value: 'yes_no', child: Text(l10n.evQuestionKindYesNo)),
                  DropdownMenuItem(value: 'choice', child: Text(l10n.evQuestionKindChoice)),
                ],
                onChanged: (v) => set(() => kind = v ?? 'text'),
              ),
              if (kind == 'choice') TextField(controller: options, decoration: InputDecoration(labelText: l10n.evQuestionOptions)),
              CheckboxListTile(
                contentPadding: EdgeInsets.zero,
                value: required,
                onChanged: (v) => set(() => required = v ?? false),
                title: Text(l10n.evQuestionRequired),
              ),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(l10n.commonCancel)),
            TextButton(onPressed: () => Navigator.pop(ctx, true), child: Text(l10n.evSave)),
          ],
        ),
      ),
    );
    final parsed = options.text.split(',').map((o) => o.trim()).where((o) => o.isNotEmpty).toList();
    final text = label.text.trim();
    label.dispose();
    options.dispose();
    if (added != true || text.isEmpty || (kind == 'choice' && parsed.isEmpty) || !mounted) return;
    setState(() => _questions.add({
          'id': 'q${DateTime.now().microsecondsSinceEpoch}',
          'label': text,
          'kind': kind,
          'options': kind == 'choice' ? parsed : <String>[],
          'required': required,
        }));
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final e = _event;
    return Column(children: [
      Expanded(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(18, 14, 18, 16),
          children: [
            _statusCard(context),
            const SizedBox(height: 14),
            _Section(
              icon: Icons.edit_note_rounded,
              title: l10n.evStepDetails,
              children: _detailsFields(context),
            ),
            _Section(
              icon: Icons.event_note_rounded,
              title: l10n.evStepFunctions,
              subtitle: e.functions.isEmpty ? l10n.evFunctionsEmpty : null,
              children: [
                FunctionsEditor(eventId: e.id, functions: e.functions, service: widget.service, onChanged: (_) => widget.onChanged()),
              ],
            ),
            _Section(
              icon: Icons.palette_outlined,
              title: l10n.evStepDesign,
              initiallyExpanded: !e.invitationsConfigured,
              children: _designFields(context),
            ),
            _Section(icon: Icons.how_to_reg_outlined, title: l10n.evStepRsvp, children: _rsvpFields(context)),
            _Section(icon: Icons.link_rounded, title: l10n.evGeneralLinkTitle, children: _generalLink(context)),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(_error!, style: TyType.sans(13.5, color: ty.rose, weight: FontWeight.w600)),
              ),
          ],
        ),
      ),
      SafeArea(
        top: false,
        child: Container(
          padding: const EdgeInsets.fromLTRB(18, 8, 18, 10),
          decoration: BoxDecoration(color: ty.paper, border: Border(top: BorderSide(color: ty.line))),
          child: TyButton(_busy ? l10n.invSaving : l10n.evSaveChanges, full: true, enabled: !_busy, onTap: () => _save(announce: true)),
        ),
      ),
    ]);
  }

  Widget _statusCard(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final e = _event;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: eventCardDecoration(ty),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Row(children: [
          Icon(e.isDraft ? Icons.drafts_outlined : Icons.public_rounded, size: 18, color: e.isDraft ? ty.ink3 : ty.leaf),
          const SizedBox(width: 8),
          Expanded(
            child: Text(e.isDraft ? l10n.evStatusDraftLine : l10n.evStatusPublishedLine,
                style: TyType.sans(13, color: ty.ink2, height: 1.4)),
          ),
        ]),
        const SizedBox(height: 12),
        Row(children: [
          Expanded(
            child: TyButton(l10n.evPreviewShort, kind: TyButtonKind.ghost, full: true, leadingIcon: Icons.visibility_outlined,
                enabled: !_busy, onTap: _preview),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: e.isDraft
                ? TyButton(l10n.evPublish, full: true, enabled: !_busy, onTap: _publish)
                : TyButton(l10n.evUnpublish, kind: TyButtonKind.ghost, full: true, enabled: !_busy, onTap: () async {
                    await _run(() async {
                      await widget.service.unpublish(e.id);
                      await widget.onChanged();
                    });
                  }),
          ),
        ]),
      ]),
    );
  }

  List<Widget> _detailsFields(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final e = _event;
    final time = eventTimeText(e.startTime);
    return [
      Text(e.isBooked ? l10n.evDetailsBookedIntro : l10n.evDetailsOwnIntro, style: TyType.sans(13, color: ty.ink2, height: 1.4)),
      const SizedBox(height: 8),
      Text(
        eventDateRange(context, e.date, e.endDate) + (time == null ? '' : ' · $time'),
        style: TyType.sans(14, color: ty.ink, weight: FontWeight.w700),
      ),
      if (e.booking != null)
        Text(l10n.evDetailsFromBooking(e.booking!.packageName ?? e.booking!.bookingNumber ?? ''), style: TyType.sans(12.5, color: ty.ink3)),
      const SizedBox(height: 12),
      EventField(controller: _displayTitle, label: l10n.evDisplayTitle, maxLength: 300),
      EventField(controller: _displayVenue, label: l10n.evFieldVenue, maxLength: 300),
      EventField(controller: _displayAddress, label: l10n.evFieldAddress, maxLength: 1000, maxLines: 2),
      EventField(controller: _instructions, label: l10n.evDisplayInstructions, maxLength: 2000, maxLines: 3),
      if (e.isBooked) Text(l10n.evDisplayBookingNote, style: TyType.sans(12, color: ty.ink3, height: 1.4)),
    ];
  }

  List<Widget> _designFields(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final canCustomise = _event.entitlements.customTemplates;
    final p = _palettes[_palette];
    Color hex(String h) => Color(int.parse('FF${h.substring(1)}', radix: 16));
    Widget label(String t) => Padding(
          padding: const EdgeInsets.only(top: 6, bottom: 8),
          child: Text(t, style: TyType.sans(13, color: ty.ink2, weight: FontWeight.w700)),
        );
    return [
      label(l10n.evDesignStyle),
      // Only what exists: the static card is the image made on the guest list.
      Wrap(spacing: 8, runSpacing: 8, children: [
        ChoiceChip(label: Text(l10n.evDesignStyleWeb), selected: _invitationType == 'web', onSelected: (_) => setState(() => _invitationType = 'web')),
        ChoiceChip(label: Text(l10n.evDesignStyleStatic), selected: _invitationType == 'static', onSelected: (_) => setState(() => _invitationType = 'static')),
      ]),
      const SizedBox(height: 10),
      label(l10n.evDesignTemplate),
      Wrap(spacing: 8, runSpacing: 8, children: [
        for (final t in const ['classic', 'royal', 'floral', 'minimal'])
          if (canCustomise || t == 'classic')
            ChoiceChip(
              label: Text(switch (t) {
                'royal' => l10n.evTemplateRoyal,
                'floral' => l10n.evTemplateFloral,
                'minimal' => l10n.evTemplateMinimal,
                _ => l10n.evTemplateClassic,
              }),
              selected: _template == t,
              onSelected: (_) => setState(() => _template = t),
            ),
      ]),
      const SizedBox(height: 10),
      label(l10n.evDesignColours),
      Wrap(spacing: 10, children: [
        for (var i = 0; i < _palettes.length; i++)
          Semantics(
            button: true,
            selected: _palette == i,
            label: l10n.evDesignPaletteLabel(i + 1),
            child: GestureDetector(
              onTap: () => setState(() => _palette = i),
              child: Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: hex(_palettes[i].$1),
                  shape: BoxShape.circle,
                  border: Border.all(color: _palette == i ? ty.ink : ty.line, width: _palette == i ? 2.5 : 1),
                ),
                child: _palette == i ? const Icon(Icons.check_rounded, color: Colors.white, size: 18) : null,
              ),
            ),
          ),
      ]),
      const SizedBox(height: 10),
      label(l10n.evDesignFont),
      Wrap(spacing: 8, runSpacing: 8, children: [
        ChoiceChip(label: Text(l10n.evFontSerif), selected: _font == 'serif', onSelected: (_) => setState(() => _font = 'serif')),
        ChoiceChip(label: Text(l10n.evFontTraditional), selected: _font == 'traditional', onSelected: (_) => setState(() => _font = 'traditional')),
        ChoiceChip(label: Text(l10n.evFontModern), selected: _font == 'modern', onSelected: (_) => setState(() => _font = 'modern')),
      ]),
      const SizedBox(height: 14),
      EventField(controller: _heading, label: l10n.evDesignHeading, hint: l10n.evDesignHeadingHint, maxLength: 120),
      EventField(controller: _tagline, label: l10n.evDesignTagline, hint: l10n.evDesignTaglineHint, maxLength: 60),
      EventField(controller: _message, label: l10n.evDesignMessage, hint: l10n.evDesignMessageHint, maxLength: 1500, maxLines: 4),
      Container(
        padding: const EdgeInsets.symmetric(vertical: 22, horizontal: 18),
        decoration: BoxDecoration(color: hex(p.$1), borderRadius: BorderRadius.circular(16)),
        child: Column(children: [
          Text((_heading.text.trim().isEmpty ? l10n.evDesignHeadingDefault : _heading.text.trim()).toUpperCase(),
              textAlign: TextAlign.center, style: TyType.eyebrow(10.5, color: Colors.white.withValues(alpha: 0.9))),
          const SizedBox(height: 8),
          Text(_displayTitle.text, textAlign: TextAlign.center, maxLines: 2, overflow: TextOverflow.ellipsis,
              style: TyType.display(22, color: Colors.white)),
          const SizedBox(height: 10),
          Container(width: 38, height: 1, color: hex(p.$2)),
        ]),
      ),
    ];
  }

  Widget _toggle(String title, bool value, ValueChanged<bool> onChanged, {String? subtitle}) {
    final ty = context.ty;
    return SwitchListTile.adaptive(
      contentPadding: EdgeInsets.zero,
      value: value,
      onChanged: onChanged,
      activeTrackColor: ty.saffron,
      title: Text(title, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w600)),
      subtitle: subtitle == null ? null : Text(subtitle, style: TyType.sans(12, color: ty.ink3)),
    );
  }

  List<Widget> _rsvpFields(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final ent = _event.entitlements;
    return [
      Text(l10n.evRsvpIntro, style: TyType.sans(13, color: ty.ink2, height: 1.4)),
      _toggle(l10n.evRsvpAllowMaybe, _allowMaybe, (v) => setState(() => _allowMaybe = v)),
      _toggle(l10n.evRsvpAskCount, _askCount, (v) => setState(() => _askCount = v), subtitle: l10n.evRsvpAskCountNote),
      _toggle(l10n.evRsvpAllowEdit, _allowEdit, (v) => setState(() => _allowEdit = v)),
      if (ent.foodPreferences) ...[
        _toggle(l10n.evRsvpAskFood, _askFood, (v) => setState(() => _askFood = v), subtitle: l10n.evRsvpAskFoodNote),
        if (_askFood) ...[
          _toggle(l10n.evRsvpAskAllergies, _askAllergies, (v) => setState(() => _askAllergies = v)),
          const SizedBox(height: 4),
          EventField(controller: _mealOptions, label: l10n.evRsvpMeals, hint: l10n.evRsvpMealsHint),
        ],
      ],
      _toggle(l10n.evRsvpAskSpecial, _askSpecial, (v) => setState(() => _askSpecial = v)),
      ListTile(
        contentPadding: EdgeInsets.zero,
        title: Text(l10n.evRsvpDeadline, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w600)),
        subtitle: Text(_deadline == null ? l10n.evRsvpNoDeadline : DateFormat('d MMM yyyy').format(_deadline!),
            style: TyType.sans(12.5, color: ty.ink3)),
        trailing: _deadline == null
            ? const Icon(Icons.event_rounded)
            : IconButton(icon: const Icon(Icons.close_rounded), tooltip: l10n.evRsvpClearDeadline, onPressed: () => setState(() => _deadline = null)),
        onTap: () async {
          final now = DateTime.now();
          final picked = await showDatePicker(
            context: context,
            initialDate: _deadline ?? now,
            firstDate: DateTime(now.year, now.month, now.day),
            lastDate: now.add(const Duration(days: 730)),
          );
          if (picked != null) setState(() => _deadline = picked);
        },
      ),
      if (ent.advancedRsvp) ...[
        const SizedBox(height: 6),
        Text(l10n.evRsvpQuestions, style: TyType.sans(13, color: ty.ink2, weight: FontWeight.w700)),
        for (final q in _questions)
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(q['label'] as String, style: TyType.sans(14, color: ty.ink)),
            trailing: IconButton(
              icon: Icon(Icons.close_rounded, color: ty.ink3),
              tooltip: l10n.evFunctionRemove,
              onPressed: () => setState(() => _questions.remove(q)),
            ),
          ),
        const SizedBox(height: 6),
        TyButton(l10n.evQuestionAdd, kind: TyButtonKind.ghost, full: true, leadingIcon: Icons.add_rounded, onTap: _addQuestion),
      ],
    ];
  }

  List<Widget> _generalLink(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final e = _event;
    final on = e.generalLinkUrl != null;
    return [
      Text(l10n.evGeneralLinkNote, style: TyType.sans(13, color: ty.ink2, height: 1.4)),
      SwitchListTile.adaptive(
        contentPadding: EdgeInsets.zero,
        value: on,
        activeTrackColor: ty.saffron,
        onChanged: _busy
            ? null
            : (v) => _run(() async {
                  await widget.service.setGeneralLink(e.id, enabled: v);
                  await widget.onChanged();
                }),
        title: Text(l10n.evGeneralLinkToggle, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w600)),
      ),
      if (on) ...[
        SelectableText(e.generalLinkUrl!, style: TyType.sans(12.5, color: ty.ink2)),
        const SizedBox(height: 10),
        Row(children: [
          Expanded(
            child: TyButton(l10n.invCopyLink, kind: TyButtonKind.ghost, full: true, onTap: () async {
              await Clipboard.setData(ClipboardData(text: e.generalLinkUrl!));
              _snack(l10n.evLinkCopied);
            }),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: TyButton(l10n.invShareSheet, kind: TyButtonKind.ghost, full: true,
                onTap: () => Share.share(l10n.evGeneralShareMessage(e.title, e.generalLinkUrl!))),
          ),
        ]),
        TextButton(
          onPressed: _busy
              ? null
              : () => _run(() async {
                    await widget.service.setGeneralLink(e.id, enabled: true, rotate: true);
                    await widget.onChanged();
                  }),
          child: Text(l10n.evGeneralLinkReplace),
        ),
      ],
    ];
  }
}

/// A collapsible block, so a page of settings reads as a short list of topics.
class _Section extends StatelessWidget {
  final IconData icon;
  final String title;
  final String? subtitle;
  final bool initiallyExpanded;
  final List<Widget> children;

  const _Section({
    required this.icon,
    required this.title,
    this.subtitle,
    this.initiallyExpanded = false,
    required this.children,
  });

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return EventTileCard(
      margin: const EdgeInsets.only(bottom: 10),
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          initiallyExpanded: initiallyExpanded,
          maintainState: true,
          shape: const Border(),
          collapsedShape: const Border(),
          leading: Icon(icon, color: ty.saffronDeep),
          title: Text(title, style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
          subtitle: subtitle == null ? null : Text(subtitle!, maxLines: 1, overflow: TextOverflow.ellipsis, style: TyType.sans(12, color: ty.ink3)),
          childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
          expandedCrossAxisAlignment: CrossAxisAlignment.stretch,
          children: children,
        ),
      ),
    );
  }
}
