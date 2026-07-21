import 'package:flutter/material.dart';

import '../../../theme/colors.dart';
import '../../../theme/typography.dart';
import '../../../data/vendor_models.dart';
import '../../../data/services/vendor_service.dart';

class VendorBankScreen extends StatefulWidget {
  const VendorBankScreen({super.key});

  @override
  State<VendorBankScreen> createState() => _VendorBankScreenState();
}

class _VendorBankScreenState extends State<VendorBankScreen> {
  final _vendorService = VendorService();
  String? _vendorId;
  List<VendorBankAccount> _accounts = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _isLoading = true);
    try {
      final vendor = await _vendorService.getMe();
      if (vendor == null) {
        setState(() => _isLoading = false);
        return;
      }
      final accounts = await _vendorService.listBankAccounts(vendor.id);
      if (mounted) setState(() { _vendorId = vendor.id; _accounts = accounts; _isLoading = false; });
    } catch (_) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _showAddSheet() async {
    if (_vendorId == null) return;
    final holderCtrl = TextEditingController();
    final numberCtrl = TextEditingController();
    final ifscCtrl = TextEditingController();
    final bankCtrl = TextEditingController();
    final branchCtrl = TextEditingController();
    bool isPrimary = _accounts.isEmpty;

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
                Text('Add Bank Account', style: TyType.display(20, color: context.ty.ink)),
                const SizedBox(height: 16),
                TextField(controller: holderCtrl, decoration: const InputDecoration(labelText: 'Account Holder Name')),
                TextField(controller: numberCtrl, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Account Number')),
                TextField(controller: ifscCtrl, decoration: const InputDecoration(labelText: 'IFSC Code')),
                TextField(controller: bankCtrl, decoration: const InputDecoration(labelText: 'Bank Name')),
                TextField(controller: branchCtrl, decoration: const InputDecoration(labelText: 'Branch Name (optional)')),
                CheckboxListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Set as primary'),
                  value: isPrimary,
                  onChanged: (v) => setSheetState(() => isPrimary = v ?? false),
                ),
                const SizedBox(height: 12),
                ElevatedButton(onPressed: () => Navigator.pop(context, true), child: const Text('Add Account')),
              ],
            ),
          ),
        ),
      ),
    );

    if (saved != true) return;
    try {
      await _vendorService.addBankAccount(_vendorId!, {
        'account_holder_name': holderCtrl.text.trim(),
        'account_number': numberCtrl.text.trim(),
        'ifsc_code': ifscCtrl.text.trim().toUpperCase(),
        'bank_name': bankCtrl.text.trim(),
        'branch_name': branchCtrl.text.trim().isEmpty ? null : branchCtrl.text.trim(),
        'is_primary': isPrimary,
      });
      _load();
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Could not add account.')));
    }
  }

  Future<void> _delete(VendorBankAccount account) async {
    if (_vendorId == null) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Remove bank account?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(context, true), child: const Text('Remove')),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await _vendorService.deleteBankAccount(_vendorId!, account.id);
      _load();
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Could not remove account.')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: AppBar(title: const Text('Bank Accounts')),
      floatingActionButton: _accounts.length >= 3 ? null : FloatingActionButton(onPressed: _showAddSheet, child: const Icon(Icons.add)),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _accounts.isEmpty
              ? Center(child: Text('No bank accounts added yet', style: TyType.sans(14, color: ty.ink2)))
              : ListView.separated(
                  padding: const EdgeInsets.all(18),
                  itemCount: _accounts.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 10),
                  itemBuilder: (context, i) {
                    final a = _accounts[i];
                    return Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(14), border: Border.all(color: ty.line)),
                      child: Row(
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(children: [
                                  Text(a.bankName, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w700)),
                                  if (a.isPrimary) ...[
                                    const SizedBox(width: 6),
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                      decoration: BoxDecoration(color: Colors.green.withOpacity(0.15), borderRadius: BorderRadius.circular(6)),
                                      child: Text('Primary', style: TyType.sans(10, color: Colors.green.shade700, weight: FontWeight.w700)),
                                    ),
                                  ],
                                ]),
                                Text(a.accountHolderName, style: TyType.sans(12.5, color: ty.ink2)),
                                Text(a.maskedAccountNumber, style: TyType.sans(12.5, color: ty.ink3)),
                              ],
                            ),
                          ),
                          IconButton(icon: const Icon(Icons.delete_outline, color: Colors.red), onPressed: () => _delete(a)),
                        ],
                      ),
                    );
                  },
                ),
    );
  }
}
