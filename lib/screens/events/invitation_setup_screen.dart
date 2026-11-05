import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../data/services/event_service.dart';
import '../../data/services/invitation_service.dart' show invitationErrorMessage;
import '../../l10n/generated/app_localizations.dart';
import '../../theme/colors.dart';
import '../../theme/typography.dart';
import '../../widgets/common.dart';
import '../../widgets/event_ui.dart';
import '../../widgets/state_screens.dart';
import '../../widgets/ty_button.dart';
import 'create_event_wizard.dart' show EventField;
import 'event_dashboard_screen.dart';
import 'functions_editor.dart';

const _palettes = <(String, String, String)>[
  ('#5B1226', '#B8892F', '#FBF6EC'), // Burgundy & gold
  ('#7A1F3D', '#D08A3C', '#FDF5EE'), // Rani pink
  ('#1F4D3A', '#B8892F', '#F7F5EA'), // Mehendi green
  ('#1E2F5C', '#C49A45', '#F5F4EE'), // Royal navy
  ('#8A4B08', '#C8456B', '#FFF8EC'), // Marigold
];

/// One setup path for both journeys, opened on an existing event: confirm what
/// guests will read, the functions, the look, the questions, then preview and
/// publish. A booked customer never re-enters anything; their details arrive
/// filled in, and changing them here only changes the invitation, never the booking.
class InvitationSetupScreen extends StatefulWidget {
  final String eventId;
  final EventService? service;
  final int initialStep;
  const InvitationSetupScreen({super.key, required this.eventId, this.service, this.initialStep = 0});

  @override
  State<InvitationSetupScreen> createState() => _InvitationSetupScreenState();
}

class _InvitationSetupScreenState extends State<InvitationSetupScreen> {
  late final EventService _service = widget.service ?? EventService();
  late int _step = widget.initialStep;
  EventDetail? _event;
  bool _loading = true;
  bool _loadFailed = false;
  bool _saving = false;
  String? _error;

  final _displayTitle = TextEditingController();
  final _displayVenue = TextEditingController();
  final _displayAddress = TextEditingController();
  final _instructions = TextEditingController();
  final _heading = TextEditingController();
  final _message = TextEditingController();
  final _mealOptions = TextEditingController();

  String _template = 'classic';
  String _font = 'serif';
  int _palette = 0;
  String _invitationType = 'web';
  bool _allowMaybe = true, _allowEdit = true, _askCount = true, _askFood = false, _askAllergies = false, _askSpecial = false;
  DateTime? _deadline;
  List<Map<String, dynamic>> _questions = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    for (final c in [_displayTitle, _displayVenue, _displayAddress, _instructions, _heading, _message, _mealOptions]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _loadFailed = false;
    });
    try {
      final e = await _service.get(widget.eventId);
      if (!mounted) return;
      final s = e.settings;
      _displayTitle.text = (s.display['title'] as String?) ?? e.title;
      _displayVenue.text = (s.display['venue_name'] as String?) ?? e.venueName ?? '';
      _displayAddress.text = (s.display['venue_address'] as String?) ?? e.venueAddress ?? '';
      _instructions.text = (s.display['instructions'] as String?) ?? '';
      _heading.text = (s.design['heading'] as String?) ?? '';
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
      setState(() {
        _event = e;
        _loading = false;
      });
    } catch (_) {
      if (mounted) {
        setState(() {
          _loading = false;
          _loadFailed = true;
        });
      }
    }
  }

  List<String> get _steps {
    final l10n = AppLocalizations.of(context)!;
    return [l10n.evStepDetails, l10n.evStepFunctions, l10n.evStepDesign, l10n.evStepRsvp, l10n.evStepPublish];
  }

  String? _ymd(DateTime? d) => d == null ? null : DateFormat('yyyy-MM-dd').format(d);

  Map<String, dynamic> _settingsPayload() {
    final e = _event!;
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

  Future<bool> _saveSettings() async {
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final updated = await _service.saveSettings(widget.eventId, _settingsPayload());
      if (mounted) setState(() => _event = updated);
      return true;
    } catch (e) {
      if (mounted) setState(() => _error = invitationErrorMessage(e));
      return false;
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _next() async {
    if (!await _saveSettings() || !mounted) return;
    setState(() => _step += 1);
  }

  Future<void> _preview() async {
    final l10n = AppLocalizations.of(context)!;
    if (!await _saveSettings() || !mounted) return;
    try {
      final url = await _service.previewLink(widget.eventId);
      await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
    } catch (_) {
      if (mounted) setState(() => _error = l10n.evPreviewFailed);
    }
  }

  Future<void> _publish() async {
    if (!await _saveSettings() || !mounted) return;
    setState(() => _saving = true);
    try {
      await _service.publish(widget.eventId);
      if (!mounted) return;
      Navigator.of(context).pushReplacement(MaterialPageRoute(
        builder: (_) => EventDashboardScreen(eventId: widget.eventId, service: widget.service, justPublished: true),
      ));
    } catch (e) {
      if (mounted) setState(() => _error = invitationErrorMessage(e));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  void _addQuestion() async {
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
              if (kind == 'choice')
                TextField(controller: options, decoration: InputDecoration(labelText: l10n.evQuestionOptions)),
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
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    if (_loading) {
      return Scaffold(backgroundColor: ty.paper, body: const Center(child: CircularProgressIndicator()));
    }
    if (_loadFailed || _event == null) {
      return Scaffold(
        backgroundColor: ty.paper,
        appBar: tyAppBar(context, title: l10n.evSetupTitle),
        body: TyStateScreen.error(context, onAction: _load),
      );
    }
    final last = _step == _steps.length - 1;
    return PopScope(
      canPop: _step == 0,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) setState(() => _step -= 1);
      },
      child: Scaffold(
        backgroundColor: ty.paper,
        appBar: tyAppBar(context, title: l10n.evSetupTitle),
        body: Column(children: [
          _StepBar(steps: _steps, current: _step),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.fromLTRB(18, 10, 18, 20),
              children: [
                switch (_step) {
                  0 => _detailsStep(context),
                  1 => _functionsStep(context),
                  2 => _designStep(context),
                  3 => _rsvpStep(context),
                  _ => _publishStep(context),
                },
                if (_error != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 12),
                    child: Text(_error!, style: TyType.sans(13.5, color: ty.rose, weight: FontWeight.w600)),
                  ),
              ],
            ),
          ),
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(18, 8, 18, 12),
              child: Row(children: [
                if (_step > 0) ...[
                  Expanded(
                    child: TyButton(l10n.evBack, kind: TyButtonKind.ghost, full: true, enabled: !_saving, onTap: () => setState(() => _step -= 1)),
                  ),
                  const SizedBox(width: 10),
                ],
                Expanded(
                  flex: 2,
                  child: TyButton(
                    _saving ? l10n.invSaving : (last ? l10n.evPublish : l10n.evNext),
                    full: true,
                    enabled: !_saving,
                    onTap: last ? _publish : _next,
                  ),
                ),
              ]),
            ),
          ),
        ]),
      ),
    );
  }

  Widget _detailsStep(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final e = _event!;
    final time = eventTimeText(e.startTime);
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Align(alignment: Alignment.centerLeft, child: EventSourceBadge(booked: e.isBooked)),
      const SizedBox(height: 10),
      Text(e.isBooked ? l10n.evDetailsBookedIntro : l10n.evDetailsOwnIntro, style: TyType.sans(13.5, color: ty.ink2, height: 1.4)),
      const SizedBox(height: 12),
      Container(
        padding: const EdgeInsets.all(14),
        decoration: eventCardDecoration(ty),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(e.eventTypeLabel, style: TyType.eyebrow(10.5, color: ty.ink3)),
          const SizedBox(height: 4),
          Text(eventDateRange(context, e.date, e.endDate) + (time == null ? '' : ' · $time'),
              style: TyType.sans(14, color: ty.ink, weight: FontWeight.w700)),
          if (e.booking != null) ...[
            const SizedBox(height: 4),
            Text(l10n.evDetailsFromBooking(e.booking!.packageName ?? e.booking!.bookingNumber ?? ''),
                style: TyType.sans(12.5, color: ty.ink3)),
          ],
        ]),
      ),
      const SizedBox(height: 14),
      EventField(controller: _displayTitle, label: l10n.evDisplayTitle, maxLength: 300),
      EventField(controller: _displayVenue, label: l10n.evFieldVenue, maxLength: 300),
      EventField(controller: _displayAddress, label: l10n.evFieldAddress, maxLength: 1000, maxLines: 2),
      EventField(controller: _instructions, label: l10n.evDisplayInstructions, maxLength: 2000, maxLines: 3),
      if (e.isBooked) Text(l10n.evDisplayBookingNote, style: TyType.sans(12, color: ty.ink3, height: 1.4)),
    ]);
  }

  Widget _functionsStep(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Text(l10n.evFunctionsIntro, style: TyType.sans(13.5, color: ty.ink2, height: 1.4)),
      const SizedBox(height: 12),
      FunctionsEditor(
        eventId: widget.eventId,
        functions: _event!.functions,
        service: _service,
        onChanged: (_) {},
      ),
    ]);
  }

  Widget _designStep(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final canCustomise = _event!.entitlements.customTemplates;
    final p = _palettes[_palette];
    Color hex(String h) => Color(int.parse('FF${h.substring(1)}', radix: 16));
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Text(l10n.evDesignStyle, style: TyType.sans(13, color: ty.ink2, weight: FontWeight.w700)),
      const SizedBox(height: 8),
      // Only what exists. The static card is the image generated on the guest
      // list screen; there is no animated or video invitation to offer yet.
      Wrap(spacing: 8, runSpacing: 8, children: [
        ChoiceChip(label: Text(l10n.evDesignStyleWeb), selected: _invitationType == 'web', onSelected: (_) => setState(() => _invitationType = 'web')),
        ChoiceChip(label: Text(l10n.evDesignStyleStatic), selected: _invitationType == 'static', onSelected: (_) => setState(() => _invitationType = 'static')),
      ]),
      const SizedBox(height: 16),
      Text(l10n.evDesignTemplate, style: TyType.sans(13, color: ty.ink2, weight: FontWeight.w700)),
      const SizedBox(height: 8),
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
      const SizedBox(height: 16),
      Text(l10n.evDesignColours, style: TyType.sans(13, color: ty.ink2, weight: FontWeight.w700)),
      const SizedBox(height: 8),
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
      const SizedBox(height: 16),
      Text(l10n.evDesignFont, style: TyType.sans(13, color: ty.ink2, weight: FontWeight.w700)),
      const SizedBox(height: 8),
      Wrap(spacing: 8, runSpacing: 8, children: [
        ChoiceChip(label: Text(l10n.evFontSerif), selected: _font == 'serif', onSelected: (_) => setState(() => _font = 'serif')),
        ChoiceChip(label: Text(l10n.evFontTraditional), selected: _font == 'traditional', onSelected: (_) => setState(() => _font = 'traditional')),
        ChoiceChip(label: Text(l10n.evFontModern), selected: _font == 'modern', onSelected: (_) => setState(() => _font = 'modern')),
      ]),
      const SizedBox(height: 16),
      EventField(controller: _heading, label: l10n.evDesignHeading, hint: l10n.evDesignHeadingHint, maxLength: 120),
      EventField(controller: _message, label: l10n.evDesignMessage, hint: l10n.evDesignMessageHint, maxLength: 1500, maxLines: 4),
      Container(
        padding: const EdgeInsets.symmetric(vertical: 26, horizontal: 18),
        decoration: BoxDecoration(color: hex(p.$1), borderRadius: BorderRadius.circular(16)),
        child: Column(children: [
          Text((_heading.text.trim().isEmpty ? l10n.evDesignHeadingDefault : _heading.text.trim()).toUpperCase(),
              textAlign: TextAlign.center, style: TyType.eyebrow(10.5, color: Colors.white.withValues(alpha: 0.9))),
          const SizedBox(height: 8),
          Text(_displayTitle.text, textAlign: TextAlign.center, maxLines: 2, overflow: TextOverflow.ellipsis,
              style: TyType.display(24, color: Colors.white)),
          const SizedBox(height: 10),
          Container(width: 38, height: 1, color: hex(p.$2)),
        ]),
      ),
    ]);
  }

  Widget _toggle(String title, bool value, ValueChanged<bool>? onChanged, {String? subtitle}) {
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

  Widget _rsvpStep(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final ent = _event!.entitlements;
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Text(l10n.evRsvpIntro, style: TyType.sans(13.5, color: ty.ink2, height: 1.4)),
      const SizedBox(height: 6),
      _toggle(l10n.evRsvpAllowMaybe, _allowMaybe, (v) => setState(() => _allowMaybe = v)),
      _toggle(l10n.evRsvpAskCount, _askCount, (v) => setState(() => _askCount = v), subtitle: l10n.evRsvpAskCountNote),
      _toggle(l10n.evRsvpAllowEdit, _allowEdit, (v) => setState(() => _allowEdit = v)),
      if (ent.foodPreferences) ...[
        _toggle(l10n.evRsvpAskFood, _askFood, (v) => setState(() => _askFood = v), subtitle: l10n.evRsvpAskFoodNote),
        if (_askFood) ...[
          _toggle(l10n.evRsvpAskAllergies, _askAllergies, (v) => setState(() => _askAllergies = v)),
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
        const SizedBox(height: 8),
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
    ]);
  }

  Widget _publishStep(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Text(l10n.evPublishIntro, style: TyType.sans(13.5, color: ty.ink2, height: 1.4)),
      const SizedBox(height: 14),
      TyButton(l10n.evPreviewCta, kind: TyButtonKind.ghost, full: true, leadingIcon: Icons.visibility_outlined, enabled: !_saving, onTap: _preview),
      const SizedBox(height: 8),
      Text(l10n.evPreviewNote, textAlign: TextAlign.center, style: TyType.sans(12, color: ty.ink3)),
    ]);
  }
}

class _StepBar extends StatelessWidget {
  final List<String> steps;
  final int current;
  const _StepBar({required this.steps, required this.current});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    return Padding(
      padding: const EdgeInsets.fromLTRB(18, 2, 18, 6),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(l10n.evStepOf(current + 1, steps.length, steps[current]), style: TyType.sans(12.5, color: ty.ink2, weight: FontWeight.w700)),
        const SizedBox(height: 6),
        Row(children: [
          for (var i = 0; i < steps.length; i++) ...[
            Expanded(
              child: Container(
                height: 4,
                decoration: BoxDecoration(
                  color: i <= current ? ty.saffron : ty.line,
                  borderRadius: BorderRadius.circular(9),
                ),
              ),
            ),
            if (i < steps.length - 1) const SizedBox(width: 4),
          ],
        ]),
      ]),
    );
  }
}
