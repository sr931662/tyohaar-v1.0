import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../data/services/event_service.dart';
import '../../data/services/invitation_service.dart';
import '../../l10n/generated/app_localizations.dart';
import '../../theme/colors.dart';
import '../../theme/typography.dart';
import '../../widgets/common.dart';
import '../../widgets/event_ui.dart';
import '../../widgets/state_screens.dart';
import '../../widgets/ty_button.dart';
import 'create_event_wizard.dart' show EventField;

/// Families invited together, and who is invited to which function. A
/// household's link is its main contact's personal link, so no new credential
/// exists to share, rotate or lose.
class HouseholdsScreen extends StatefulWidget {
  final String eventId;
  final EventService? service;
  const HouseholdsScreen({super.key, required this.eventId, this.service});

  @override
  State<HouseholdsScreen> createState() => _HouseholdsScreenState();
}

class _HouseholdsScreenState extends State<HouseholdsScreen> {
  late final EventService _service = widget.service ?? EventService();
  final InvitationService _invites = InvitationService();
  EventDetail? _event;
  List<GuestInvitation> _guests = [];
  bool _loading = true;
  bool _error = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = _event == null;
      _error = false;
    });
    try {
      final results = await Future.wait([
        _service.get(widget.eventId),
        _invites.list(widget.eventId, pageSize: 100, sort: 'name', order: 'asc'),
      ]);
      if (!mounted) return;
      setState(() {
        _event = results[0] as EventDetail;
        _guests = (results[1] as InvitationPage).items.where((g) => !g.isRevoked).toList();
        _loading = false;
      });
    } catch (_) {
      if (mounted) {
        setState(() {
          _loading = false;
          _error = true;
        });
      }
    }
  }

  void _snack(String m) {
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));
  }

  Future<void> _editHousehold([GuestHousehold? existing]) async {
    final saved = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: context.ty.paper,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (_) => _HouseholdSheet(eventId: widget.eventId, existing: existing, guests: _guests, service: _service),
    );
    if (saved == true) _load();
  }

  Future<void> _deleteHousehold(GuestHousehold h) async {
    try {
      await _service.deleteGroup(widget.eventId, h.id);
      _load();
    } catch (e) {
      _snack(invitationErrorMessage(e));
    }
  }

  Future<void> _assignFunctions(GuestInvitation guest) async {
    final l10n = AppLocalizations.of(context)!;
    final functions = _event!.functions.where((f) => !f.isCancelled).toList();
    final chosen = functions.map((f) => f.id).toSet();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, set) => AlertDialog(
          title: Text(l10n.evAssignTitle(guest.name)),
          content: SizedBox(
            width: double.maxFinite,
            child: ListView(shrinkWrap: true, children: [
              for (final f in functions)
                CheckboxListTile(
                  contentPadding: EdgeInsets.zero,
                  value: chosen.contains(f.id),
                  title: Text(f.name),
                  onChanged: (v) => set(() => v == true ? chosen.add(f.id) : chosen.remove(f.id)),
                ),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(l10n.commonCancel)),
            TextButton(onPressed: chosen.isEmpty ? null : () => Navigator.pop(ctx, true), child: Text(l10n.evSave)),
          ],
        ),
      ),
    );
    if (ok != true) return;
    try {
      await _service.setGuestFunctions(widget.eventId, guestIds: [guest.id], functionIds: chosen.toList());
      _snack(l10n.evAssignSaved);
    } catch (e) {
      _snack(invitationErrorMessage(e));
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final event = _event;
    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: l10n.evHouseholdsTitle),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error || event == null
              ? TyStateScreen.error(context, onAction: _load)
              : ListView(
                  padding: EdgeInsets.fromLTRB(18, 8, 18, 28 + MediaQuery.paddingOf(context).bottom),
                  children: [
                    Text(l10n.evHouseholdsIntro, style: TyType.sans(13.5, color: ty.ink2, height: 1.4)),
                    const SizedBox(height: 12),
                    if (event.groups.isEmpty)
                      EventEmpty(icon: Icons.diversity_3_rounded, title: l10n.evHouseholdsEmpty)
                    else
                      for (final h in event.groups)
                        EventTileCard(
                          margin: const EdgeInsets.only(bottom: 8),
                          child: ListTile(
                            title: Text(h.name, style: TyType.sans(14.5, color: ty.ink, weight: FontWeight.w700)),
                            subtitle: Text(
                              [
                                h.members.map((m) => m.name).join(', '),
                                if (h.capacity != null) l10n.evHouseholdCapacityLine(h.capacity!),
                                h.responseMode == 'group' ? l10n.evHouseholdModeGroup : l10n.evHouseholdModeIndividual,
                              ].where((s) => s.isNotEmpty).join(' · '),
                              style: TyType.sans(12.5, color: ty.ink3),
                            ),
                            onTap: () => _editHousehold(h),
                            trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                              if (h.inviteUrl != null)
                                IconButton(
                                  tooltip: l10n.invCopyLink,
                                  icon: Icon(Icons.link_rounded, color: ty.ink2),
                                  onPressed: () async {
                                    await Clipboard.setData(ClipboardData(text: h.inviteUrl!));
                                    _snack(l10n.evLinkCopied);
                                  },
                                ),
                              IconButton(
                                tooltip: l10n.evFunctionRemove,
                                icon: Icon(Icons.delete_outline_rounded, color: ty.ink3),
                                onPressed: () => _deleteHousehold(h),
                              ),
                            ]),
                          ),
                        ),
                    const SizedBox(height: 4),
                    TyButton(l10n.evHouseholdAdd, kind: TyButtonKind.ghost, full: true, leadingIcon: Icons.add_rounded,
                        enabled: _guests.isNotEmpty, onTap: () => _editHousehold()),
                    if (_guests.isEmpty)
                      Padding(
                        padding: const EdgeInsets.only(top: 6),
                        child: Text(l10n.evHouseholdNeedsGuests, textAlign: TextAlign.center, style: TyType.sans(12, color: ty.ink3)),
                      ),
                    if (event.functions.isNotEmpty && _guests.isNotEmpty) ...[
                      const SizedBox(height: 22),
                      EventSection(
                        title: l10n.evAssignHeading,
                        subtitle: l10n.evAssignNote,
                        children: [
                          for (final g in _guests)
                            EventTileCard(
                              margin: const EdgeInsets.only(bottom: 6),
                              child: ListTile(
                                dense: true,
                                title: Text(g.name, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w600)),
                                trailing: Icon(Icons.tune_rounded, size: 18, color: ty.ink3),
                                onTap: () => _assignFunctions(g),
                              ),
                            ),
                        ],
                      ),
                    ],
                  ],
                ),
    );
  }
}

class _HouseholdSheet extends StatefulWidget {
  final String eventId;
  final GuestHousehold? existing;
  final List<GuestInvitation> guests;
  final EventService service;
  const _HouseholdSheet({required this.eventId, this.existing, required this.guests, required this.service});

  @override
  State<_HouseholdSheet> createState() => _HouseholdSheetState();
}

class _HouseholdSheetState extends State<_HouseholdSheet> {
  final _form = GlobalKey<FormState>();
  late final _name = TextEditingController(text: widget.existing?.name ?? '');
  late final _capacity = TextEditingController(text: widget.existing?.capacity?.toString() ?? '');
  late String _mode = widget.existing?.responseMode ?? 'group';
  late final Set<String> _members = (widget.existing?.members ?? const []).map((m) => m.id).toSet();
  late String? _primary = widget.existing?.primaryGuestId;
  bool _saving = false;
  String? _error;

  @override
  void dispose() {
    _name.dispose();
    _capacity.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final l10n = AppLocalizations.of(context)!;
    if (!_form.currentState!.validate()) return;
    if (_members.isEmpty) {
      setState(() => _error = l10n.evHouseholdChooseMembers);
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    final primary = _members.contains(_primary) ? _primary : _members.first;
    final capacity = int.tryParse(_capacity.text.trim());
    final body = <String, dynamic>{
      'name': _name.text.trim(),
      'invitation_capacity': capacity,
      'response_mode': _mode,
      'guest_ids': _members.toList(),
      'primary_guest_id': primary,
    };
    try {
      final existing = widget.existing;
      if (existing == null) {
        await widget.service.createGroup(widget.eventId, body);
      } else {
        await widget.service.updateGroup(widget.eventId, existing.id, body);
      }
      if (mounted) Navigator.of(context).pop(true);
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
    final available = widget.guests.where((g) => g.groupId == null || g.groupId == widget.existing?.id).toList();
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: Form(
        key: _form,
        child: ListView(
          shrinkWrap: true,
          padding: const EdgeInsets.fromLTRB(18, 18, 18, 24),
          children: [
            Text(widget.existing == null ? l10n.evHouseholdAdd : l10n.evHouseholdEdit, style: TyType.display(20, color: ty.ink)),
            const SizedBox(height: 14),
            EventField(controller: _name, label: l10n.evHouseholdName, hint: l10n.evHouseholdNameHint, maxLength: 200,
                validator: (v) => (v ?? '').trim().isEmpty ? l10n.evFieldNameRequired : null),
            EventField(controller: _capacity, label: l10n.evHouseholdCapacity, maxLength: 3, keyboardType: TextInputType.number),
            Text(l10n.evHouseholdResponses, style: TyType.sans(13, color: ty.ink2, weight: FontWeight.w700)),
            const SizedBox(height: 6),
            Wrap(spacing: 8, children: [
              ChoiceChip(label: Text(l10n.evHouseholdModeGroup), selected: _mode == 'group', onSelected: (_) => setState(() => _mode = 'group')),
              ChoiceChip(label: Text(l10n.evHouseholdModeIndividual), selected: _mode == 'individual', onSelected: (_) => setState(() => _mode = 'individual')),
            ]),
            const SizedBox(height: 14),
            Text(l10n.evHouseholdMembers, style: TyType.sans(13, color: ty.ink2, weight: FontWeight.w700)),
            for (final g in available)
              CheckboxListTile(
                contentPadding: EdgeInsets.zero,
                value: _members.contains(g.id),
                title: Text(g.name, style: TyType.sans(14, color: ty.ink)),
                subtitle: _primary == g.id ? Text(l10n.evHouseholdMainContact, style: TyType.sans(12, color: ty.saffronDeep)) : null,
                onChanged: (v) => setState(() {
                  if (v == true) {
                    _members.add(g.id);
                    _primary ??= g.id;
                  } else {
                    _members.remove(g.id);
                    if (_primary == g.id) _primary = _members.isEmpty ? null : _members.first;
                  }
                }),
              ),
            if (_members.length > 1) ...[
              const SizedBox(height: 8),
              DropdownButtonFormField<String>(
                initialValue: _members.contains(_primary) ? _primary : _members.first,
                decoration: InputDecoration(labelText: l10n.evHouseholdMainContact),
                items: [
                  for (final g in available.where((g) => _members.contains(g.id)))
                    DropdownMenuItem(value: g.id, child: Text(g.name)),
                ],
                onChanged: (v) => setState(() => _primary = v),
              ),
            ],
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(top: 10),
                child: Text(_error!, style: TyType.sans(13.5, color: ty.rose, weight: FontWeight.w600)),
              ),
            const SizedBox(height: 14),
            TyButton(_saving ? l10n.invSaving : l10n.evSave, full: true, enabled: !_saving, onTap: _save),
          ],
        ),
      ),
    );
  }
}
