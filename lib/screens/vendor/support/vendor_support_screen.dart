import 'package:flutter/material.dart';

import '../../../theme/colors.dart';
import '../../../theme/typography.dart';
import '../../../data/services/support_service.dart';
import '../../../l10n/generated/app_localizations.dart';
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
        builder: (context, setSheetState) {
          final l = AppLocalizations.of(context)!;
          return Padding(
            padding: EdgeInsets.only(left: 20, right: 20, top: 20, bottom: MediaQuery.of(context).viewInsets.bottom + 20),
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(l.vendorSupportNewTicketSheetTitle, style: TyType.display(20, color: context.ty.ink)),
                  const SizedBox(height: 16),
                  DropdownButtonFormField<String>(
                    initialValue: category,
                    decoration: InputDecoration(labelText: l.vendorSupportCategoryLabel),
                    // ticketCategoryOptions maps several UI labels onto the same
                    // backend value (e.g. "Planning"/"Others" both -> "general")
                    // — dedupe by backend value so DropdownButton never sees
                    // two items sharing a value.
                    items: {for (final e in ticketCategoryOptions(context).entries) e.value: e.key}
                        .entries
                        .map((e) => DropdownMenuItem(value: e.key, child: Text(e.value)))
                        .toList(),
                    onChanged: (v) => setSheetState(() => category = v ?? category),
                  ),
                  TextField(controller: subjectCtrl, decoration: InputDecoration(labelText: l.vendorSupportSubjectLabel)),
                  TextField(controller: descCtrl, maxLines: 4, decoration: InputDecoration(labelText: l.vendorSupportDescriptionMinCharsLabel, helperText: l.vendorSupportDescriptionFormatHelperText)),
                  const SizedBox(height: 12),
                  ElevatedButton(onPressed: () => Navigator.pop(context, true), child: Text(l.vendorPackagesSubmitButtonLabel)),
                ],
              ),
            ),
          );
        },
      ),
    );

    try {
      if (saved != true) return;
      if (descCtrl.text.trim().length < 20) {
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(AppLocalizations.of(context)!.vendorSupportDescriptionTooShortError)));
        return;
      }
      await _supportService.createTicket(category: category, subject: subjectCtrl.text.trim(), description: descCtrl.text.trim());
      _load();
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(AppLocalizations.of(context)!.vendorSupportCreateTicketError)));
    } finally {
      // Deferred a frame: showModalBottomSheet's returned Future can resolve
      // while the sheet's closing transition is still rendering, so disposing
      // these immediately races that still-mounted TextField tree and throws
      // "A TextEditingController was used after being disposed."
      WidgetsBinding.instance.addPostFrameCallback((_) {
        subjectCtrl.dispose();
        descCtrl.dispose();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l = AppLocalizations.of(context)!;

    return Scaffold(
      backgroundColor: Colors.transparent,
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _showNewTicketSheet,
        icon: const Icon(Icons.add),
        label: Text(l.vendorSupportNewTicketButtonLabel),
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
                      Icon(Icons.support_agent_rounded, size: 48, color: ty.ink3.withValues(alpha: 0.5)),
                      const SizedBox(height: 16),
                      Text(l.vendorSupportEmptyMessage, style: TyType.sans(14, color: ty.ink2)),
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
                              BoxShadow(color: Colors.black.withValues(alpha: 0.02), blurRadius: 8, offset: const Offset(0, 2)),
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
                                    decoration: BoxDecoration(color: statusColor.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(99)),
                                    child: Text(t.status.toUpperCase(), style: TyType.sans(10, color: statusColor, weight: FontWeight.w800, spacing: 0.5)),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 8),
                              Row(
                                children: [
                                  Icon(Icons.tag, size: 14, color: ty.ink3),
                                  const SizedBox(width: 4),
                                  Flexible(
                                    child: Text(t.ticketNumber,
                                        maxLines: 1, overflow: TextOverflow.ellipsis, style: TyType.sans(12, color: ty.ink3, weight: FontWeight.w600)),
                                  ),
                                  const SizedBox(width: 12),
                                  Icon(Icons.category_outlined, size: 14, color: ty.ink3),
                                  const SizedBox(width: 4),
                                  Flexible(
                                    child: Text(t.category,
                                        maxLines: 1, overflow: TextOverflow.ellipsis, style: TyType.sans(12, color: ty.ink3, weight: FontWeight.w600)),
                                  ),
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
