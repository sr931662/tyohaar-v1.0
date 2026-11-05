import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../data/services/event_service.dart';
import '../../data/services/invitation_service.dart' show invitationErrorMessage;
import '../../l10n/generated/app_localizations.dart';
import '../../theme/colors.dart';
import '../../theme/typography.dart';
import '../../utils/whatsapp.dart';
import '../../widgets/common.dart';
import '../../widgets/event_ui.dart';
import '../../widgets/state_screens.dart';
import '../invitations/invitation_labels.dart';

/// Nudging people who haven't answered. The host taps, and the message goes
/// from their own WhatsApp: nothing here sends automatically, because automated
/// messages are only allowed through the WhatsApp Business Platform, which
/// isn't set up. Anyone who has answered, including with a no, isn't listed.
class RemindersScreen extends StatefulWidget {
  final EventSummaryCard event;
  final EventService? service;
  const RemindersScreen({super.key, required this.event, this.service});

  @override
  State<RemindersScreen> createState() => _RemindersScreenState();
}

class _RemindersScreenState extends State<RemindersScreen> {
  late final EventService _service = widget.service ?? EventService();
  ReminderList? _list;
  bool _error = false;
  bool _dueOnly = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _error = false);
    try {
      final list = await _service.reminders(widget.event.id);
      if (mounted) setState(() => _list = list);
    } catch (_) {
      if (mounted) setState(() => _error = true);
    }
  }

  Future<void> _remind(ReminderCandidate c) async {
    final l10n = AppLocalizations.of(context)!;
    final message = l10n.evReminderMessage(c.guestName, widget.event.title, c.inviteUrl ?? '');
    final opened = await launchUrl(whatsAppLink(c.phone, message), mode: LaunchMode.externalApplication);
    if (!opened) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l10n.evReminderNoWhatsapp)));
      return;
    }
    try {
      await _service.recordReminder(widget.event.id, [c.guestId], 'whatsapp');
      if (mounted) _load();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(invitationErrorMessage(e))));
    }
  }

  String _reason(AppLocalizations l10n, String r) => switch (r) {
        'visited_no_rsvp' => l10n.evReasonVisited,
        'not_responded' => l10n.evReasonNotResponded,
        'deadline_soon' => l10n.evReasonDeadline,
        _ => r,
      };

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final labels = InvitationLabels(context);
    final list = _list;
    final candidates = list == null
        ? const <ReminderCandidate>[]
        : (_dueOnly ? list.candidates.where((c) => c.reasons.isNotEmpty).toList() : list.candidates);
    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: l10n.evRemindersTitle),
      body: _error
          ? TyStateScreen.error(context, onAction: _load)
          : list == null
              ? const Center(child: CircularProgressIndicator())
              : RefreshIndicator(
                  onRefresh: _load,
                  color: ty.saffron,
                  child: ListView(
                    padding: EdgeInsets.fromLTRB(18, 8, 18, 28 + MediaQuery.paddingOf(context).bottom),
                    children: [
                      Text(l10n.evRemindersIntro, style: TyType.sans(13.5, color: ty.ink2, height: 1.4)),
                      const SizedBox(height: 8),
                      if (list.candidates.isNotEmpty)
                        SwitchListTile.adaptive(
                          contentPadding: EdgeInsets.zero,
                          value: _dueOnly,
                          activeTrackColor: ty.saffron,
                          onChanged: (v) => setState(() => _dueOnly = v),
                          title: Text(l10n.evRemindersDueOnly, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w600)),
                        ),
                      if (candidates.isEmpty)
                        EventEmpty(
                          icon: Icons.task_alt_rounded,
                          title: l10n.evRemindersEmpty,
                          message: list.candidates.isEmpty ? l10n.evRemindersEmptyMessage : null,
                        )
                      else
                        for (final c in candidates)
                          EventTileCard(
                            margin: const EdgeInsets.only(bottom: 8),
                            child: ListTile(
                              title: Text(c.guestName, style: TyType.sans(14.5, color: ty.ink, weight: FontWeight.w700)),
                              subtitle: Text(
                                [
                                  ...c.reasons.map((r) => _reason(l10n, r)),
                                  if (c.lastRemindedAt != null) l10n.evRemindedOn(labels.when(c.lastRemindedAt!)),
                                  if (c.reasons.isEmpty && c.lastRemindedAt == null) l10n.evReasonNoReply,
                                ].join(' · '),
                                style: TyType.sans(12.5, color: ty.ink3),
                              ),
                              trailing: TextButton(onPressed: () => _remind(c), child: Text(l10n.evRemind)),
                            ),
                          ),
                    ],
                  ),
                ),
    );
  }
}
