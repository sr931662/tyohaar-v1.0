import 'package:flutter/material.dart';
import 'package:share_plus/share_plus.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/models.dart';
import '../data/services/celebration_service.dart';
import '../utils/log.dart';
import '../widgets/invitation_card.dart';
import '../widgets/state_screens.dart';
import '../widgets/ty_button.dart';
import '../widgets/common.dart';
import '../l10n/generated/app_localizations.dart';

class InvitationManagementScreen extends StatefulWidget {
  const InvitationManagementScreen({super.key});

  @override
  State<InvitationManagementScreen> createState() => _InvitationManagementScreenState();
}

class _InvitationManagementScreenState extends State<InvitationManagementScreen> {
  final CelebrationService _celebrationService = CelebrationService();
  final GlobalKey _cardKey = GlobalKey();

  List<Celebration> _celebrations = [];
  Celebration? _selected;
  List<Guest> _guests = [];
  bool _isLoading = true;
  bool _error = false;
  bool _isSharing = false;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() { _isLoading = true; _error = false; });
    try {
      final celebrations = await _celebrationService.listCelebrations();
      if (celebrations.isNotEmpty) {
        final selected = _selected != null
            ? celebrations.firstWhere((c) => c.id == _selected!.id, orElse: () => celebrations.first)
            : celebrations.first;
        final guests = await _celebrationService.listGuests(selected.id);
        if (mounted) {
          setState(() {
            _celebrations = celebrations;
            _selected = selected;
            _guests = guests;
            _isLoading = false;
          });
        }
      } else {
        if (mounted) setState(() { _celebrations = []; _isLoading = false; });
      }
    } catch (e) {
      logDebug('Error loading invitation data: $e');
      if (mounted) setState(() { _isLoading = false; _error = true; });
    }
  }

  Future<void> _selectCelebration(Celebration c) async {
    setState(() { _selected = c; _isLoading = true; });
    try {
      final guests = await _celebrationService.listGuests(c.id);
      if (mounted) setState(() { _guests = guests; _isLoading = false; });
    } catch (_) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _shareCard() async {
    final l10n = AppLocalizations.of(context)!;
    setState(() => _isSharing = true);
    try {
      final bytes = await InvitationCard.captureCard(_cardKey);
      if (bytes == null) throw Exception('Could not render invitation card.');
      final title = _selected?.title ?? l10n.invitationManagementCelebrationFallback;
      await Share.shareXFiles(
        [XFile.fromData(bytes, mimeType: 'image/png', name: 'invitation.png')],
        text: l10n.invitationManagementShareTextMessage(title),
        subject: l10n.invitationManagementShareSubject(title),
      );
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(l10n.invitationManagementShareError)),
        );
      }
    } finally {
      if (mounted) setState(() => _isSharing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;

    if (_isLoading && _celebrations.isEmpty) {
      return Scaffold(backgroundColor: ty.paper, body: const Center(child: CircularProgressIndicator()));
    }

    if (_error && _celebrations.isEmpty) {
      return Scaffold(
        backgroundColor: ty.paper,
        appBar: tyAppBar(context, title: l10n.invitationManagementAppBarTitle),
        body: TyStateScreen.error(context, onAction: _loadData),
      );
    }

    if (_celebrations.isEmpty) {
      return Scaffold(
        backgroundColor: ty.paper,
        appBar: tyAppBar(context, title: l10n.invitationManagementAppBarTitle),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(32),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.celebration_outlined, size: 48, color: ty.ink3),
                const SizedBox(height: 16),
                Text(l10n.invitationManagementNoEventsTitle, style: TyType.display(18, color: ty.ink)),
                const SizedBox(height: 8),
                Text(
                  l10n.invitationManagementNoEventsMessage,
                  textAlign: TextAlign.center,
                  style: TyType.sans(13.5, color: ty.ink3),
                ),
              ],
            ),
          ),
        ),
      );
    }

    final sent = _guests.length;
    final opened = _guests.where((g) => g.invitationOpenedAt != null).length;
    final rsvpd = _guests.where((g) => g.rsvpStatus != 'pending').length;
    final selected = _selected!;

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: l10n.invitationManagementAppBarTitle),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(18, 12, 18, 28),
        children: [
          if (_celebrations.length > 1) ...[
            Text(l10n.invitationManagementEventLabel, style: TyType.eyebrow(11, color: ty.ink3)),
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14),
              decoration: BoxDecoration(
                color: ty.surface2,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: ty.line),
              ),
              child: DropdownButtonHideUnderline(
                child: DropdownButton<String>(
                  value: selected.id,
                  isExpanded: true,
                  items: _celebrations
                      .map((c) => DropdownMenuItem(value: c.id, child: Text(c.title, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w600))))
                      .toList(),
                  onChanged: (id) {
                    final c = _celebrations.firstWhere((c) => c.id == id);
                    _selectCelebration(c);
                  },
                ),
              ),
            ),
            const SizedBox(height: 24),
          ],
          Center(child: InvitationCard(celebration: selected, boundaryKey: _cardKey)),
          const SizedBox(height: 32),
          Text(l10n.invitationManagementGuestStatusLabel, style: TyType.eyebrow(11, color: ty.ink3)),
          const SizedBox(height: 16),
          Row(
            children: [
              _stat(context, '$sent', l10n.invitationManagementInvitedLabel, ty.ink2),
              const SizedBox(width: 12),
              _stat(context, '$opened', l10n.invitationManagementOpenedLabel, ty.saffron),
              const SizedBox(width: 12),
              _stat(context, '$rsvpd', l10n.invitationManagementRsvpdLabel, ty.leaf),
            ],
          ),
          const SizedBox(height: 40),
          TyButton(
            _isSharing ? l10n.invitationManagementPreparingLabel : l10n.invitationManagementShareButtonLabel,
            full: true,
            enabled: !_isSharing,
            leadingIcon: Icons.ios_share_rounded,
            onTap: _shareCard,
          ),
          const SizedBox(height: 8),
          Text(
            l10n.invitationManagementShareHintMessage,
            textAlign: TextAlign.center,
            style: TyType.sans(12, color: ty.ink3),
          ),
        ],
      ),
    );
  }

  Widget _stat(BuildContext context, String value, String label, Color color) {
    final ty = context.ty;
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 20),
        decoration: BoxDecoration(
          color: ty.surface,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: ty.line),
        ),
        child: Column(
          children: [
            Text(value, style: TyType.display(24, color: color)),
            const SizedBox(height: 4),
            Text(label, style: TyType.sans(12, color: ty.ink3, weight: FontWeight.w600)),
          ],
        ),
      ),
    );
  }
}
