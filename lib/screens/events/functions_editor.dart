import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../data/services/event_service.dart';
import '../../data/services/invitation_service.dart' show invitationErrorMessage;
import '../../l10n/generated/app_localizations.dart';
import '../../theme/colors.dart';
import '../../theme/typography.dart';
import '../../widgets/event_ui.dart';
import '../../widgets/ty_button.dart';
import 'create_event_wizard.dart' show EventField;

/// Add, edit, reorder and remove an event's functions. Optional: an event with
/// none is one gathering, and everything else works the same.
class FunctionsEditor extends StatefulWidget {
  final String eventId;
  final List<EventFunction> functions;
  final EventService service;
  final ValueChanged<List<EventFunction>> onChanged;

  const FunctionsEditor({
    super.key,
    required this.eventId,
    required this.functions,
    required this.service,
    required this.onChanged,
  });

  @override
  State<FunctionsEditor> createState() => _FunctionsEditorState();
}

class _FunctionsEditorState extends State<FunctionsEditor> {
  late List<EventFunction> _items = List.of(widget.functions);

  @override
  void didUpdateWidget(FunctionsEditor old) {
    super.didUpdateWidget(old);
    if (old.functions != widget.functions) _items = List.of(widget.functions);
  }

  void _snack(String m) {
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));
  }

  void _publish() => widget.onChanged(List.of(_items));

  Future<void> _edit([EventFunction? existing]) async {
    final saved = await showModalBottomSheet<EventFunction>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: context.ty.paper,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (_) => _FunctionSheet(eventId: widget.eventId, existing: existing, service: widget.service),
    );
    if (saved == null || !mounted) return;
    setState(() {
      final i = _items.indexWhere((f) => f.id == saved.id);
      if (i >= 0) {
        _items[i] = saved;
      } else {
        _items.add(saved);
      }
    });
    _publish();
  }

  Future<void> _remove(EventFunction f) async {
    final l10n = AppLocalizations.of(context)!;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(l10n.evFunctionRemoveTitle(f.name)),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(l10n.commonCancel)),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: Text(l10n.evFunctionRemove)),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await widget.service.deleteFunction(widget.eventId, f.id);
      if (!mounted) return;
      setState(() => _items.removeWhere((x) => x.id == f.id));
      _publish();
    } catch (e) {
      _snack(invitationErrorMessage(e));
    }
  }

  Future<void> _reorder(int from, int to) async {
    if (to > from) to -= 1;
    final before = List.of(_items);
    setState(() => _items.insert(to, _items.removeAt(from)));
    try {
      await widget.service.reorderFunctions(widget.eventId, _items.map((f) => f.id).toList());
      _publish();
    } catch (e) {
      if (mounted) setState(() => _items = before);
      _snack(invitationErrorMessage(e));
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      if (_items.isEmpty)
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 10),
          child: Text(l10n.evFunctionsEmpty, style: TyType.sans(13.5, color: ty.ink3, height: 1.4)),
        )
      else
        ReorderableListView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          buildDefaultDragHandles: false,
          itemCount: _items.length,
          onReorder: _reorder,
          itemBuilder: (context, i) {
            final f = _items[i];
            final time = eventTimeText(f.startTime);
            final sub = [
              if (f.date != null) DateFormat('EEE, d MMM').format(f.date!),
              if (time != null) time,
              if (f.isCancelled) l10n.evFunctionCancelled,
            ].join(' · ');
            return EventTileCard(
              key: ValueKey(f.id),
              margin: const EdgeInsets.only(bottom: 8),
              child: ListTile(
                contentPadding: const EdgeInsets.only(left: 6, right: 4),
                leading: ReorderableDragStartListener(
                  index: i,
                  child: Padding(
                    padding: const EdgeInsets.all(8),
                    child: Icon(Icons.drag_indicator_rounded, color: ty.ink3, semanticLabel: l10n.evFunctionReorder),
                  ),
                ),
                title: Text(f.name, style: TyType.sans(14.5, color: ty.ink, weight: FontWeight.w700)),
                subtitle: Text(sub, style: TyType.sans(12.5, color: ty.ink3)),
                onTap: () => _edit(f),
                trailing: IconButton(
                  tooltip: l10n.evFunctionRemove,
                  icon: Icon(Icons.delete_outline_rounded, color: ty.ink3),
                  onPressed: () => _remove(f),
                ),
              ),
            );
          },
        ),
      const SizedBox(height: 4),
      TyButton(l10n.evFunctionAdd, kind: TyButtonKind.ghost, full: true, leadingIcon: Icons.add_rounded, onTap: () => _edit()),
    ]);
  }
}

class _FunctionSheet extends StatefulWidget {
  final String eventId;
  final EventFunction? existing;
  final EventService service;
  const _FunctionSheet({required this.eventId, this.existing, required this.service});

  @override
  State<_FunctionSheet> createState() => _FunctionSheetState();
}

class _FunctionSheetState extends State<_FunctionSheet> {
  final _form = GlobalKey<FormState>();
  late final _name = TextEditingController(text: widget.existing?.name ?? '');
  late final _venue = TextEditingController(text: widget.existing?.venueName ?? '');
  late final _address = TextEditingController(text: widget.existing?.venueAddress ?? '');
  late final _description = TextEditingController(text: widget.existing?.description ?? '');
  late final _dress = TextEditingController(text: widget.existing?.dressCode ?? '');
  late DateTime? _date = widget.existing?.date;
  late TimeOfDay? _time = _parse(widget.existing?.startTime);
  late bool _cancelled = widget.existing?.isCancelled ?? false;
  bool _inviteAll = true;
  bool _saving = false;
  String? _error;

  static TimeOfDay? _parse(String? hhmm) {
    if (hhmm == null || hhmm.length < 5) return null;
    final p = hhmm.split(':');
    return TimeOfDay(hour: int.parse(p[0]), minute: int.parse(p[1]));
  }

  String? get _timeText =>
      _time == null ? null : '${_time!.hour.toString().padLeft(2, '0')}:${_time!.minute.toString().padLeft(2, '0')}';

  @override
  void dispose() {
    for (final c in [_name, _venue, _address, _description, _dress]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _save() async {
    final l10n = AppLocalizations.of(context)!;
    if (!_form.currentState!.validate()) return;
    if (_date == null) {
      setState(() => _error = l10n.evWizardChooseDate);
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    final draft = FunctionDraft(
      name: _name.text,
      date: _date!,
      startTime: _timeText,
      venueName: _venue.text.trim().isEmpty ? null : _venue.text.trim(),
      venueAddress: _address.text.trim().isEmpty ? null : _address.text.trim(),
      description: _description.text.trim().isEmpty ? null : _description.text.trim(),
      dressCode: _dress.text.trim().isEmpty ? null : _dress.text.trim(),
      inviteAllGuests: _inviteAll,
    );
    try {
      final existing = widget.existing;
      final saved = existing == null
          ? await widget.service.addFunction(widget.eventId, draft)
          : await widget.service.updateFunction(widget.eventId, existing.id, {
              ...draft.toJson()..remove('invite_all_guests'),
              'is_cancelled': _cancelled,
            });
      if (mounted) Navigator.of(context).pop(saved);
    } catch (e) {
      if (mounted) setState(() => _error = invitationErrorMessage(e));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final now = DateTime.now();
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: Form(
        key: _form,
        child: ListView(
          shrinkWrap: true,
          padding: const EdgeInsets.fromLTRB(18, 18, 18, 24),
          children: [
            Text(widget.existing == null ? l10n.evFunctionAdd : l10n.evFunctionEdit, style: TyType.display(20, color: ty.ink)),
            const SizedBox(height: 14),
            EventField(controller: _name, label: l10n.evFunctionName, hint: l10n.evFunctionNameHint, maxLength: 120,
                validator: (v) => (v ?? '').trim().isEmpty ? l10n.evFieldNameRequired : null),
            Row(children: [
              Expanded(
                child: OutlinedButton.icon(
                  icon: const Icon(Icons.event_rounded, size: 18),
                  label: Text(_date == null ? l10n.evFieldDate : DateFormat('d MMM yyyy').format(_date!)),
                  onPressed: () async {
                    final picked = await showDatePicker(
                      context: context,
                      initialDate: _date ?? now,
                      firstDate: _date != null && _date!.isBefore(now) ? _date! : DateTime(now.year, now.month, now.day),
                      lastDate: now.add(const Duration(days: 730)),
                    );
                    if (picked != null) setState(() => _date = picked);
                  },
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: OutlinedButton.icon(
                  icon: const Icon(Icons.schedule_rounded, size: 18),
                  label: Text(_time?.format(context) ?? l10n.evFieldTime),
                  onPressed: () async {
                    final picked = await showTimePicker(context: context, initialTime: _time ?? const TimeOfDay(hour: 18, minute: 0));
                    if (picked != null) setState(() => _time = picked);
                  },
                ),
              ),
            ]),
            const SizedBox(height: 14),
            EventField(controller: _venue, label: l10n.evFieldVenue, hint: l10n.evFunctionVenueHint, maxLength: 300),
            EventField(controller: _address, label: l10n.evFieldAddress, maxLength: 1000, maxLines: 2),
            EventField(controller: _description, label: l10n.evFieldDescription, maxLength: 2000, maxLines: 2),
            EventField(controller: _dress, label: l10n.evFunctionDress, maxLength: 200),
            if (widget.existing == null)
              SwitchListTile.adaptive(
                contentPadding: EdgeInsets.zero,
                value: _inviteAll,
                onChanged: (v) => setState(() => _inviteAll = v),
                title: Text(l10n.evFunctionInviteAll, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w600)),
              )
            else
              SwitchListTile.adaptive(
                contentPadding: EdgeInsets.zero,
                value: _cancelled,
                onChanged: (v) => setState(() => _cancelled = v),
                title: Text(l10n.evFunctionCancelLabel, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w600)),
              ),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Text(_error!, style: TyType.sans(13.5, color: ty.rose, weight: FontWeight.w600)),
              ),
            const SizedBox(height: 6),
            TyButton(_saving ? l10n.invSaving : l10n.evSave, full: true, enabled: !_saving, onTap: _save),
          ],
        ),
      ),
    );
  }
}
