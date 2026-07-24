import 'dart:io';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../../../theme/colors.dart';
import '../../../theme/typography.dart';
import '../../../data/vendor_models.dart';
import '../../../data/services/vendor_service.dart';

class VendorPackageItemsScreen extends StatefulWidget {
  final VendorPackage package;
  const VendorPackageItemsScreen({super.key, required this.package});

  @override
  State<VendorPackageItemsScreen> createState() => _VendorPackageItemsScreenState();
}

class _VendorPackageItemsScreenState extends State<VendorPackageItemsScreen> {
  final _vendorService = VendorService();
  List<VendorPackageItem> _items = [];
  List<VendorGalleryItem> _gallery = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _isLoading = true);
    try {
      final results = await Future.wait([
        _vendorService.listPackageItems(widget.package.id),
        _vendorService.listPackageGallery(widget.package.id),
      ]);
      if (mounted) {
        setState(() {
          _items = results[0] as List<VendorPackageItem>;
          _gallery = results[1] as List<VendorGalleryItem>;
          _isLoading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _showItemForm({VendorPackageItem? existing}) async {
    final nameCtrl = TextEditingController(text: existing?.name ?? '');
    final priceCtrl = TextEditingController(text: existing?.basePrice.toStringAsFixed(0) ?? '');
    final qtyCtrl = TextEditingController(text: existing?.quantity.toString() ?? '1');
    final unitCtrl = TextEditingController(text: existing?.unit ?? '');
    final descCtrl = TextEditingController(text: existing?.description ?? '');
    bool isMandatory = existing?.isMandatory ?? true;

    final saved = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (context) => StatefulBuilder(
        builder: (context, setSheetState) => Padding(
          padding: EdgeInsets.only(
            left: 20, right: 20, top: 20,
            bottom: MediaQuery.of(context).viewInsets.bottom + 20,
          ),
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(existing == null ? 'Add Item' : 'Edit Item', style: TyType.display(20, color: context.ty.ink)),
                const SizedBox(height: 16),
                TextField(controller: nameCtrl, decoration: const InputDecoration(labelText: 'Name')),
                TextField(controller: priceCtrl, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Base Price')),
                Row(children: [
                  Expanded(child: TextField(controller: qtyCtrl, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Quantity'))),
                  const SizedBox(width: 12),
                  Expanded(child: TextField(controller: unitCtrl, decoration: const InputDecoration(labelText: 'Unit'))),
                ]),
                TextField(controller: descCtrl, maxLines: 2, decoration: const InputDecoration(labelText: 'Description')),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Mandatory'),
                  value: isMandatory,
                  onChanged: (v) => setSheetState(() => isMandatory = v),
                ),
                const SizedBox(height: 12),
                ElevatedButton(
                  onPressed: () => Navigator.pop(context, true),
                  child: const Text('Save'),
                ),
              ],
            ),
          ),
        ),
      ),
    );

    if (saved != true) return;
    final body = {
      'name': nameCtrl.text.trim(),
      'base_price': double.tryParse(priceCtrl.text.trim()) ?? 0,
      'quantity': int.tryParse(qtyCtrl.text.trim()) ?? 1,
      'unit': unitCtrl.text.trim().isEmpty ? null : unitCtrl.text.trim(),
      'description': descCtrl.text.trim().isEmpty ? null : descCtrl.text.trim(),
      'is_mandatory': isMandatory,
    };
    try {
      if (existing == null) {
        await _vendorService.addPackageItem(widget.package.id, body);
      } else {
        await _vendorService.updatePackageItem(widget.package.id, existing.id, body);
      }
      _load();
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Could not save item.')));
    }
  }

  Future<void> _deleteItem(VendorPackageItem item) async {
    try {
      await _vendorService.deletePackageItem(widget.package.id, item.id);
      _load();
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Could not delete item.')));
    }
  }

  Future<void> _addItemPhoto(VendorPackageItem item) async {
    final image = await ImagePicker().pickImage(source: ImageSource.gallery, imageQuality: 85);
    if (image == null) return;
    try {
      final url = await _vendorService.uploadImage(File(image.path), 'package_image');
      await _vendorService.addItemImage(widget.package.id, item.id, url);
      _load();
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Upload failed.')));
    }
  }

  Future<void> _addGalleryPhoto() async {
    final image = await ImagePicker().pickImage(source: ImageSource.gallery, imageQuality: 85);
    if (image == null) return;
    try {
      final url = await _vendorService.uploadImage(File(image.path), 'package_image');
      await _vendorService.addPackageGalleryItem(widget.package.id, url);
      _load();
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Upload failed.')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final locked = widget.package.status == 'pending_review';

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: AppBar(title: Text('${widget.package.name} — Items')),
      floatingActionButton: locked
          ? null
          : FloatingActionButton(onPressed: () => _showItemForm(), child: const Icon(Icons.add)),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(18),
              children: [
                if (locked)
                  Container(
                    padding: const EdgeInsets.all(12),
                    margin: const EdgeInsets.only(bottom: 12),
                    decoration: BoxDecoration(color: Colors.orange.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(10)),
                    child: Text('Items are locked while this package is under review.', style: TyType.sans(12.5, color: Colors.orange.shade800)),
                  ),
                Text('Items', style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
                const SizedBox(height: 10),
                ..._items.map((item) => Container(
                      margin: const EdgeInsets.only(bottom: 10),
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(12), border: Border.all(color: ty.line)),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(item.name, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w700)),
                                    Text('${item.isCommon ? "Common · " : ""}Qty ${item.quantity} · ₹${item.basePrice.toStringAsFixed(0)}',
                                        style: TyType.sans(12, color: ty.ink2)),
                                  ],
                                ),
                              ),
                            ],
                          ),
                          if (!locked) ...[
                            const SizedBox(height: 8),
                            Wrap(spacing: 8, children: [
                              TextButton(onPressed: () => _addItemPhoto(item), child: const Text('Photos')),
                              if (!item.isCommon) TextButton(onPressed: () => _showItemForm(existing: item), child: const Text('Edit')),
                              if (!item.isCommon)
                                TextButton(
                                  onPressed: () => _deleteItem(item),
                                  style: TextButton.styleFrom(foregroundColor: Colors.red),
                                  child: const Text('Delete'),
                                ),
                            ]),
                          ],
                        ],
                      ),
                    )),
                const SizedBox(height: 20),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('Gallery', style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
                    if (!locked) TextButton(onPressed: _addGalleryPhoto, child: const Text('+ Add Photo')),
                  ],
                ),
                const SizedBox(height: 10),
                if (_gallery.isNotEmpty)
                  GridView.count(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    crossAxisCount: 3,
                    mainAxisSpacing: 8,
                    crossAxisSpacing: 8,
                    children: _gallery.map((g) => ClipRRect(
                          borderRadius: BorderRadius.circular(10),
                          child: CachedNetworkImage(
                            imageUrl: g.mediaUrl,
                            fit: BoxFit.cover,
                            memCacheWidth: 300,
                            placeholder: (context, url) => Container(color: Colors.black12),
                            errorWidget: (context, url, error) => Container(color: Colors.black12, child: const Icon(Icons.broken_image_outlined, size: 20)),
                          ),
                        )).toList(),
                  ),
              ],
            ),
    );
  }
}
