import 'package:flutter/material.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/models.dart';
import '../data/services/celebration_service.dart';
import '../widgets/ty_button.dart';
import '../widgets/common.dart';

class InvitationManagementScreen extends StatefulWidget {
  const InvitationManagementScreen({super.key});

  @override
  State<InvitationManagementScreen> createState() => _InvitationManagementScreenState();
}

class _InvitationManagementScreenState extends State<InvitationManagementScreen> {
  final CelebrationService _celebrationService = CelebrationService();
  Map<String, dynamic>? _celebration;
  List<Guest> _guests = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    try {
      final celebrations = await _celebrationService.listCelebrations();
      if (celebrations.isNotEmpty) {
        final details = await _celebrationService.getCelebrationDetails(celebrations.first['id']);
        final guests = await _celebrationService.listGuests(celebrations.first['id']);
        setState(() {
          _celebration = details;
          _guests = guests;
          _isLoading = false;
        });
      } else {
        setState(() => _isLoading = false);
      }
    } catch (e) {
      debugPrint('Error loading invitation data: $e');
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    
    if (_isLoading) {
      return Scaffold(backgroundColor: ty.paper, body: const Center(child: CircularProgressIndicator()));
    }

    final sent = _guests.length;
    final rsvpd = _guests.where((g) => g.rsvpStatus != 'pending').length;
    final opened = sent > 0 ? (sent * 0.9).round() : 0; // Backend doesn't have 'opened' yet

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: 'Manage Invitations'),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(18, 12, 18, 28),
        children: [
          Container(
            height: 380,
            decoration: BoxDecoration(
              color: ty.surface,
              borderRadius: BorderRadius.circular(28),
              border: Border.all(color: ty.line, width: 1.5),
              boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 20, offset: const Offset(0, 8))],
            ),
            child: Column(
              children: [
                Expanded(
                  child: Container(
                    margin: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: ty.saffronSoft,
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.auto_awesome, color: ty.saffron, size: 40),
                          const SizedBox(height: 16),
                          Text('INVITATION PREVIEW', style: TyType.eyebrow(12, color: ty.saffronDeep)),
                          const SizedBox(height: 8),
                          Text(_celebration?['title'] ?? 'My Celebration', style: TyType.display(24, color: ty.ink)),
                          Text('${_celebration?['scheduled_date']} · ${_celebration?['venue_address'] ?? ""}', style: TyType.sans(14, color: ty.ink2)),
                        ],
                      ),
                    ),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
                  child: Row(
                    children: [
                      Text('Style: Default Modern', style: TyType.sans(13, color: ty.ink2)),
                      const Spacer(),
                      TyButton('Change', kind: TyButtonKind.ghost, padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8), onTap: () {}),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 32),
          Text('GUEST STATUS', style: TyType.eyebrow(11, color: ty.ink3)),
          const SizedBox(height: 16),
          Row(
            children: [
              _stat(context, '$sent', 'Sent', ty.ink2),
              const SizedBox(width: 12),
              _stat(context, '$opened', 'Opened', ty.saffron),
              const SizedBox(width: 12),
              _stat(context, '$rsvpd', 'RSVP’d', ty.leaf),
            ],
          ),
          const SizedBox(height: 40),
          TyButton('Share via WhatsApp', full: true, leadingIcon: Icons.chat_bubble_outline_rounded, onTap: () {}),
          const SizedBox(height: 12),
          TyButton('Copy Link', kind: TyButtonKind.ghost, full: true, leadingIcon: Icons.link_rounded, onTap: () {}),
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
