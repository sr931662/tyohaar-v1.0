import 'package:flutter/material.dart';

import '../../data/auth_manager.dart';
import '../../data/services/event_service.dart';
import '../../l10n/generated/app_localizations.dart';
import '../../theme/colors.dart';
import '../../theme/responsive.dart';
import '../../theme/typography.dart';
import '../../utils/log.dart';
import '../../widgets/event_ui.dart';
import '../../widgets/state_screens.dart';
import '../event_hub_screen.dart';
import 'create_event_wizard.dart';

/// The Events tab: every celebration in one place, booked or independent.
/// This is where the old "Your Next Celebration" home card moved to.
class MyEventsScreen extends StatefulWidget {
  /// Bump to make an already-built tab reload when it is shown again.
  final int refreshSignal;
  final EventService? service;
  const MyEventsScreen({super.key, this.refreshSignal = 0, this.service});

  @override
  State<MyEventsScreen> createState() => _MyEventsScreenState();
}

class _MyEventsScreenState extends State<MyEventsScreen> {
  late final EventService _service = widget.service ?? EventService();
  EventLists? _lists;
  bool _loading = true;
  bool _error = false;
  String _tab = 'upcoming';

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void didUpdateWidget(MyEventsScreen old) {
    super.didUpdateWidget(old);
    if (old.refreshSignal != widget.refreshSignal) _load();
  }

  Future<void> _load() async {
    if (!AuthManager.instance.isAuthenticated && widget.service == null) {
      setState(() => _loading = false);
      return;
    }
    setState(() {
      _loading = _lists == null;
      _error = false;
    });
    try {
      final lists = await _service.list();
      if (!mounted) return;
      setState(() {
        _lists = lists;
        _loading = false;
        // Land somewhere useful: an event in progress beats an empty tab.
        if (lists.ongoing.isNotEmpty && lists.upcoming.isEmpty) _tab = 'ongoing';
      });
    } catch (e) {
      logDebug('Error loading events: $e');
      if (mounted) {
        setState(() {
          _loading = false;
          _error = _lists == null;
        });
      }
    }
  }

  Future<void> _open(Widget screen) async {
    await Navigator.of(context).push(MaterialPageRoute(builder: (_) => screen));
    if (mounted) _load();
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final resp = context.resp;
    final l10n = AppLocalizations.of(context)!;
    final topPadding = MediaQuery.of(context).padding.top + resp.h(85);
    final lists = _lists;
    final tabItems = switch (_tab) {
      'ongoing' => lists?.ongoing,
      'completed' => lists?.completed,
      _ => lists?.upcoming,
    };

    return RefreshIndicator(
      onRefresh: _load,
      displacement: topPadding,
      color: ty.saffron,
      child: ListView(
        padding: EdgeInsets.fromLTRB(resp.w(18), topPadding, resp.w(18), resp.h(28) + MediaQuery.of(context).padding.bottom),
        children: [
          Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(l10n.evTitle, style: TyType.display(resp.sp(26), color: ty.ink)),
                const SizedBox(height: 2),
                Text(l10n.evSubtitle, style: TyType.sans(13.5, color: ty.ink3)),
              ]),
            ),
            const SizedBox(width: 8),
            TextButton.icon(
              onPressed: () => _open(const CreateEventWizard()),
              icon: Icon(Icons.add_rounded, size: 18, color: ty.saffronDeep),
              label: Text(l10n.evCreateShortcut, style: TyType.sans(13, color: ty.saffronDeep, weight: FontWeight.w700)),
            ),
          ]),
          if (lists != null && lists.upcoming.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(_summary(l10n, lists), style: TyType.sans(13, color: ty.ink2, weight: FontWeight.w600)),
          ],
          const SizedBox(height: 14),
          _Segments(
            value: _tab,
            options: {
              'upcoming': _withCount(l10n.evTabUpcoming, lists?.upcoming.length),
              'ongoing': _withCount(l10n.evTabOngoing, lists?.ongoing.length),
              'completed': _withCount(l10n.evTabCompleted, lists?.completed.length),
            },
            onChanged: (v) => setState(() => _tab = v),
          ),
          const SizedBox(height: 14),
          if (_loading)
            const Padding(padding: EdgeInsets.only(top: 60), child: Center(child: CircularProgressIndicator()))
          else if (_error)
            SizedBox(height: 460, child: TyStateScreen.error(context, onAction: _load))
          else if (tabItems == null || tabItems.isEmpty)
            EventEmpty(
              icon: Icons.celebration_outlined,
              title: switch (_tab) {
                'ongoing' => l10n.evEmptyOngoing,
                'completed' => l10n.evEmptyCompleted,
                _ => l10n.evEmptyUpcoming,
              },
              message: _tab == 'upcoming' ? l10n.evEmptyUpcomingMessage : null,
              action: _tab == 'upcoming' ? l10n.evCreateEvent : null,
              onAction: _tab == 'upcoming' ? () => _open(const CreateEventWizard()) : null,
            )
          else
            ...tabItems.map((e) => EventCard(
                  event: e,
                  actionLabel: l10n.evManageEvent,
                  onTap: () => _open(EventHubScreen(celebrationId: e.id)),
                )),
        ],
      ),
    );
  }

  String _withCount(String label, int? count) => count == null || count == 0 ? label : '$label ($count)';

  String _summary(AppLocalizations l10n, EventLists lists) {
    final next = lists.upcoming.first;
    final days = next.daysRemaining;
    return days == null || days < 2
        ? l10n.evSummaryCount(lists.upcoming.length)
        : l10n.evSummaryNext(lists.upcoming.length, next.title, days);
  }
}

class _Segments extends StatelessWidget {
  final String value;
  final Map<String, String> options;
  final ValueChanged<String> onChanged;
  const _Segments({required this.value, required this.options, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(color: ty.surface2, borderRadius: BorderRadius.circular(14), border: Border.all(color: ty.line)),
      child: Row(
        children: options.entries.map((o) {
          final active = o.key == value;
          return Expanded(
            child: Semantics(
              button: true,
              selected: active,
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: () => onChanged(o.key),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 160),
                  constraints: const BoxConstraints(minHeight: 42),
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: active ? ty.surface : Colors.transparent,
                    borderRadius: BorderRadius.circular(11),
                    border: active ? Border.all(color: ty.line) : null,
                  ),
                  child: Text(o.value,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TyType.sans(13, color: active ? ty.ink : ty.ink3, weight: active ? FontWeight.w700 : FontWeight.w600)),
                ),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }
}
