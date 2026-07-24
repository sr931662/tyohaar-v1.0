import 'package:flutter/material.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/services/support_service.dart';
import '../widgets/common.dart';
import 'raise_ticket_screen.dart';
import 'ticket_detail_screen.dart';

class MyTicketsScreen extends StatefulWidget {
  const MyTicketsScreen({super.key});

  @override
  State<MyTicketsScreen> createState() => _MyTicketsScreenState();
}

class _MyTicketsScreenState extends State<MyTicketsScreen> {
  final SupportService _supportService = SupportService();
  List<SupportTicket> _tickets = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _isLoading = true; _error = null; });
    try {
      final tickets = await _supportService.listMyTickets();
      tickets.sort((a, b) => b.createdAt.compareTo(a.createdAt));
      if (mounted) setState(() { _tickets = tickets; _isLoading = false; });
    } catch (e) {
      if (mounted) setState(() { _error = 'Could not load your tickets.'; _isLoading = false; });
    }
  }

  Color _statusColor(BuildContext context, String status) {
    final ty = context.ty;
    switch (status) {
      case 'resolved':
      case 'closed':
        return ty.ink3;
      case 'in_progress':
      case 'waiting_on_customer':
        return ty.saffron;
      default:
        return const Color(0xFF3B82F6); // open — blue
    }
  }

  String _statusLabel(String status) => status.replaceAll('_', ' ');

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: 'My Tickets'),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: ty.saffron,
        foregroundColor: Colors.white,
        icon: const Icon(Icons.add_rounded),
        label: const Text('New Ticket'),
        onPressed: () async {
          await Navigator.of(context).push(MaterialPageRoute(builder: (_) => const RaiseTicketScreen()));
          _load();
        },
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Text(_error!, style: TyType.sans(14, color: ty.ink3)))
              : _tickets.isEmpty
                  ? _buildEmptyState(context)
                  : RefreshIndicator(
                      onRefresh: _load,
                      child: ListView.builder(
                        padding: const EdgeInsets.fromLTRB(18, 12, 18, 88),
                        itemCount: _tickets.length,
                        itemBuilder: (_, i) => _ticketCard(context, _tickets[i]),
                      ),
                    ),
    );
  }

  Widget _buildEmptyState(BuildContext context) {
    final ty = context.ty;
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.confirmation_number_outlined, size: 48, color: ty.ink3),
            const SizedBox(height: 16),
            Text('No support tickets yet', style: TyType.display(18, color: ty.ink)),
            const SizedBox(height: 8),
            Text(
              'Raised a ticket? It\'ll show up here so you can track replies.',
              textAlign: TextAlign.center,
              style: TyType.sans(13.5, color: ty.ink3),
            ),
          ],
        ),
      ),
    );
  }

  Widget _ticketCard(BuildContext context, SupportTicket ticket) {
    final ty = context.ty;
    return GestureDetector(
      onTap: () async {
        await Navigator.of(context).push(MaterialPageRoute(builder: (_) => TicketDetailScreen(ticket: ticket)));
        _load();
      },
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: ty.surface,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: ty.line),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(ticket.subject, style: TyType.sans(14.5, color: ty.ink, weight: FontWeight.w600)),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: _statusColor(context, ticket.status).withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    _statusLabel(ticket.status),
                    style: TyType.sans(11, color: _statusColor(context, ticket.status), weight: FontWeight.w700),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              ticket.description,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: TyType.sans(13, color: ty.ink2, height: 1.5),
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Text('#${ticket.ticketNumber}', style: TyType.sans(11, color: ty.ink3)),
                const Spacer(),
                Icon(Icons.chevron_right_rounded, size: 18, color: ty.ink3),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
