import 'package:flutter/material.dart';

import '../../../theme/colors.dart';
import '../../../theme/typography.dart';
import '../../../data/vendor_models.dart';
import '../../../data/services/vendor_service.dart';

/// Vendor-wide reusable item templates, attachable to any of the vendor's
/// own packages instead of being recreated per package.
class VendorCommonItemsScreen extends StatefulWidget {
  const VendorCommonItemsScreen({super.key});

  @override
  State<VendorCommonItemsScreen> createState() => _VendorCommonItemsScreenState();
}

class _VendorCommonItemsScreenState extends State<VendorCommonItemsScreen> {
  final _vendorService = VendorService();
  List<VendorCommonItem> _items = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _isLoading = true);
    try {
      final items = await _vendorService.listCommonItems();
      if (mounted) setState(() { _items = items; _isLoading = false; });
    } catch (_) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _showCreateForm() async {
    final nameCtrl = TextEditingController();
    final priceCtrl = TextEditingController();
    final qtyCtrl = TextEditingController(text: '1');
    final unitCtrl = TextEditingController();
    final descCtrl = TextEditingController();

    final saved = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (context) => Padding(
        padding: EdgeInsets.only(left: 20, right: 20, top: 20, bottom: MediaQuery.of(context).viewInsets.bottom + 20),
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('New Common Item', style: TyType.display(20, color: context.ty.ink)),
              const SizedBox(height: 16),
              TextField(controller: nameCtrl, decoration: const InputDecoration(labelText: 'Name')),
              TextField(controller: priceCtrl, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Base Price')),
              Row(children: [
                Expanded(child: TextField(controller: qtyCtrl, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Quantity'))),
                const SizedBox(width: 12),
                Expanded(child: TextField(controller: unitCtrl, decoration: const InputDecoration(labelText: 'Unit'))),
              ]),
              TextField(controller: descCtrl, maxLines: 2, decoration: const InputDecoration(labelText: 'Description')),
              const SizedBox(height: 12),
              ElevatedButton(onPressed: () => Navigator.pop(context, true), child: const Text('Create')),
            ],
          ),
        ),
      ),
    );

    if (saved != true) return;
    try {
      await _vendorService.createCommonItem({
        'name': nameCtrl.text.trim(),
        'base_price': double.tryParse(priceCtrl.text.trim()) ?? 0,
        'quantity': int.tryParse(qtyCtrl.text.trim()) ?? 1,
        'unit': unitCtrl.text.trim().isEmpty ? null : unitCtrl.text.trim(),
        'description': descCtrl.text.trim().isEmpty ? null : descCtrl.text.trim(),
      });
      _load();
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Could not create item.')));
    }
  }

  Future<void> _delete(VendorCommonItem item) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Delete common item?'),
        content: Text('This removes "${item.name}" from all packages it\'s attached to.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(context, true), child: const Text('Delete')),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await _vendorService.deleteCommonItem(item.id);
      _load();
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Could not delete item.')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return Scaffold(
      backgroundColor: ty.paper,
      appBar: AppBar(title: const Text('Common Items')),
      floatingActionButton: FloatingActionButton(onPressed: _showCreateForm, child: const Icon(Icons.add)),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _items.isEmpty
              ? Center(child: Text('No common items yet', style: TyType.sans(14, color: ty.ink2)))
              : ListView.separated(
                  padding: const EdgeInsets.all(18),
                  itemCount: _items.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 10),
                  itemBuilder: (context, i) {
                    final item = _items[i];
                    return Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(12), border: Border.all(color: ty.line)),
                      child: Row(
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(item.name, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w700)),
                                Text('Qty ${item.quantity} · ₹${item.basePrice.toStringAsFixed(0)}', style: TyType.sans(12, color: ty.ink2)),
                              ],
                            ),
                          ),
                          IconButton(icon: const Icon(Icons.delete_outline, color: Colors.red), onPressed: () => _delete(item)),
                        ],
                      ),
                    );
                  },
                ),
    );
  }
}
