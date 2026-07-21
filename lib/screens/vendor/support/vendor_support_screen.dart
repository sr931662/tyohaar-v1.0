import 'package:flutter/material.dart';

import '../../../theme/colors.dart';
import '../../../theme/typography.dart';
import '../../../data/services/support_service.dart';
import 'vendor_ticket_detail_screen.dart';

class VendorSupportScreen extends StatefulWidget {
  const VendorSupportScreen({super.key});

  @override
  State<VendorSupportScreen> createState() => _VendorSupportScreenState();
}

class _VendorSupportScreenState extends State<VendorSupportScreen> {
  final _supportService = SupportService();
  List<SupportTicket> _tickets = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _isLoading = true);
    try {
      final tickets = await _supportService.listMyTickets();
      if (mounted) setState(() { _tickets = tickets; _isLoading = false; });
    } catch (_) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _showNewTicketSheet() async {
    final subjectCtrl = TextEditingController();
    final descCtrl = TextEditingController();
    String category = 'general';

    final saved = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (context) => StatefulBuilder(
        builder: (context, setSheetState) => Padding(
          padding: EdgeInsets.only(left: 20, right: 20, top: 20, bottom: MediaQuery.of(context).viewInsets.bottom + 20),
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text('New Support Ticket', style: TyType.display(20, color: context.ty.ink)),
                const SizedBox(height: 16),
                DropdownButtonFormField<String>(
                  value: category,
                  decoration: const InputDecoration(labelText: 'Category'),
                  // ticketCategoryOptions maps several UI labels onto the same
                  // backend value (e.g. "Planning"/"Others" both -> "general")
                  // — dedupe by backend value so DropdownButton never sees
                  // two items sharing a value.
                  items: {for (final e in ticketCategoryOptions.entries) e.value: e.key}
                      .entries
                      .map((e) => DropdownMenuItem(value: e.key, child: Text(e.value)))
                      .toList(),
                  onChanged: (v) => setSheetState(() => category = v ?? category),
                ),
                TextField(controller: subjectCtrl, decoration: const InputDecoration(labelText: 'Subject')),
                TextField(controller: descCtrl, maxLines: 4, decoration: const InputDecoration(labelText: 'Description (min 20 characters)')),
                const SizedBox(height: 12),
                ElevatedButton(onPressed: () => Navigator.pop(context, true), child: const Text('Submit')),
              ],
            ),
          ),
        ),
      ),
    );

    if (saved != true) return;
    if (descCtrl.text.trim().length < 20) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Description must be at least 20 characters.')));
      return;
    }
    try {
      await _supportService.createTicket(category: category, subject: subjectCtrl.text.trim(), description: descCtrl.text.trim());
      _load();
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Could not create ticket.')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;

    return Scaffold(
      backgroundColor: Colors.transparent,
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _showNewTicketSheet, 
        icon: const Icon(Icons.add), 
        label: const Text('New Ticket'),
        backgroundColor: ty.saffron,
        foregroundColor: ty.onPrimary,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _tickets.isEmpty
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.support_agent_rounded, size: 48, color: ty.ink3.withOpacity(0.5)),
                      const SizedBox(height: 16),
                      Text('No support tickets yet', style: TyType.sans(14, color: ty.ink2)),
                    ],
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView.separated(
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
                    itemCount: _tickets.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 12),
                    itemBuilder: (context, i) {
                      final t = _tickets[i];
                      final statusColor = t.status.toLowerCase() == 'closed' ? ty.ink3 : ty.saffron;
                      return GestureDetector(
                        onTap: () => Navigator.of(context)
                            .push(MaterialPageRoute(builder: (_) => VendorTicketDetailScreen(ticketId: t.id)))
                            .then((_) => _load()),
                        child: Container(
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            color: ty.surface, 
                            borderRadius: BorderRadius.circular(16), 
                            border: Border.all(color: ty.line),
                            boxShadow: [
                              BoxShadow(color: Colors.black.withOpacity(0.02), blurRadius: 8, offset: const Offset(0, 2)),
                            ],
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  Expanded(child: Text(t.subject, style: TyType.sans(14.5, color: ty.ink, weight: FontWeight.w700))),
                                  const SizedBox(width: 8),
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                    decoration: BoxDecoration(color: statusColor.withOpacity(0.12), borderRadius: BorderRadius.circular(99)),
                                    child: Text(t.status.toUpperCase(), style: TyType.sans(10, color: statusColor, weight: FontWeight.w800, spacing: 0.5)),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 8),
                              Row(
                                children: [
                                  Icon(Icons.tag, size: 14, color: ty.ink3),
                                  const SizedBox(width: 4),
                                  Text(t.ticketNumber, style: TyType.sans(12, color: ty.ink3, weight: FontWeight.w600)),
                                  const SizedBox(width: 12),
                                  Icon(Icons.category_outlined, size: 14, color: ty.ink3),
                                  const SizedBox(width: 4),
                                  Text(t.category, style: TyType.sans(12, color: ty.ink3, weight: FontWeight.w600)),
                                ],
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ),
    );
  }
}
