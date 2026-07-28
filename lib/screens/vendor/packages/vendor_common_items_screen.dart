import 'dart:io';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../../../theme/colors.dart';
import '../../../theme/typography.dart';
import '../../../data/vendor_models.dart';
import '../../../data/services/vendor_service.dart';
import '../../../l10n/generated/app_localizations.dart';
import 'item_import_export_menu.dart';

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

  Future<void> _showItemForm({VendorCommonItem? existing}) async {
    final nameCtrl = TextEditingController(text: existing?.name ?? '');
    final priceCtrl = TextEditingController(text: existing?.basePrice.toStringAsFixed(0) ?? '');
    final qtyCtrl = TextEditingController(text: existing?.quantity.toString() ?? '1');
    final unitCtrl = TextEditingController(text: existing?.unit ?? '');
    final descCtrl = TextEditingController(text: existing?.description ?? '');
    bool isMandatory = existing?.isMandatory ?? true;
    bool isReturnable = existing?.isReturnable ?? false;
    String? coverImageUrl = existing?.coverImageUrl;
    bool isUploadingCover = false;

    final l10n = AppLocalizations.of(context)!;
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
                Text(existing == null ? l10n.vendorCommonItemsNewItemTitle : l10n.vendorCommonItemsEditItemTitle, style: TyType.display(20, color: context.ty.ink)),
                const SizedBox(height: 16),
                TextField(controller: nameCtrl, decoration: InputDecoration(labelText: l10n.vendorCommonItemsNameLabel)),
                TextField(controller: priceCtrl, keyboardType: TextInputType.number, decoration: InputDecoration(labelText: l10n.vendorCommonItemsBasePriceLabel)),
                Row(children: [
                  Expanded(child: TextField(controller: qtyCtrl, keyboardType: TextInputType.number, decoration: InputDecoration(labelText: l10n.vendorCommonItemsQuantityLabel))),
                  const SizedBox(width: 12),
                  Expanded(child: TextField(controller: unitCtrl, decoration: InputDecoration(labelText: l10n.vendorCommonItemsUnitLabel))),
                ]),
                TextField(controller: descCtrl, maxLines: 2, decoration: InputDecoration(labelText: l10n.vendorCommonItemsDescriptionLabel)),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text(l10n.vendorCommonItemsMandatoryLabel),
                  value: isMandatory,
                  onChanged: (v) => setSheetState(() => isMandatory = v),
                ),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text(l10n.vendorCommonItemsReturnableLabel),
                  value: isReturnable,
                  onChanged: (v) => setSheetState(() => isReturnable = v),
                ),
                const SizedBox(height: 8),
                Row(children: [
                  if (coverImageUrl != null) ...[
                    ClipRRect(
                      borderRadius: BorderRadius.circular(8),
                      child: CachedNetworkImage(imageUrl: coverImageUrl!, width: 44, height: 44, fit: BoxFit.cover),
                    ),
                    const SizedBox(width: 10),
                  ],
                  TextButton(
                    onPressed: isUploadingCover
                        ? null
                        : () async {
                            final image = await ImagePicker().pickImage(source: ImageSource.gallery, imageQuality: 85);
                            if (image == null) return;
                            setSheetState(() => isUploadingCover = true);
                            try {
                              final url = await _vendorService.uploadImage(File(image.path), 'package_image');
                              setSheetState(() { coverImageUrl = url; isUploadingCover = false; });
                            } catch (_) {
                              setSheetState(() => isUploadingCover = false);
                              if (context.mounted) {
                                ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l10n.vendorMultimediaUploadFailedMessage)));
                              }
                            }
                          },
                    child: Text(isUploadingCover
                        ? l10n.vendorCommonItemsUploadingLabel
                        : coverImageUrl == null
                            ? l10n.vendorCommonItemsAddCoverPhotoButtonLabel
                            : l10n.vendorCommonItemsChangeCoverPhotoButtonLabel),
                  ),
                ]),
                const SizedBox(height: 12),
                ElevatedButton(
                  onPressed: () => Navigator.pop(context, true),
                  child: Text(existing == null ? l10n.vendorCommonItemsCreateButtonLabel : l10n.vendorCommonItemsUpdateButtonLabel),
                ),
              ],
            ),
          ),
        ),
      ),
    );

    try {
      if (saved != true) return;
      final body = {
        'name': nameCtrl.text.trim(),
        'base_price': double.tryParse(priceCtrl.text.trim()) ?? 0,
        'quantity': int.tryParse(qtyCtrl.text.trim()) ?? 1,
        'unit': unitCtrl.text.trim().isEmpty ? null : unitCtrl.text.trim(),
        'description': descCtrl.text.trim().isEmpty ? null : descCtrl.text.trim(),
        'is_mandatory': isMandatory,
        'is_returnable': isReturnable,
        'cover_image_url': coverImageUrl,
      };
      if (existing == null) {
        await _vendorService.createCommonItem(body);
      } else {
        await _vendorService.updateCommonItem(existing.id, body);
      }
      _load();
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text(existing == null ? l10n.vendorCommonItemsCreateError : l10n.vendorCommonItemsUpdateError)));
      }
    } finally {
      nameCtrl.dispose();
      priceCtrl.dispose();
      qtyCtrl.dispose();
      unitCtrl.dispose();
      descCtrl.dispose();
    }
  }

  Future<void> _delete(VendorCommonItem item) async {
    final l10n = AppLocalizations.of(context)!;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: Text(l10n.vendorCommonItemsDeleteConfirmTitle),
        content: Text(l10n.vendorCommonItemsDeleteConfirmMessage(item.name)),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: Text(l10n.commonCancel)),
          TextButton(onPressed: () => Navigator.pop(context, true), child: Text(l10n.vendorCommonItemsDeleteButtonLabel)),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await _vendorService.deleteCommonItem(item.id);
      _load();
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l10n.vendorCommonItemsDeleteError)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    return Scaffold(
      backgroundColor: ty.paper,
      appBar: AppBar(
        title: Text(l10n.vendorCommonItemsTitle),
        actions: [
          ItemImportExportMenu(
            getTemplate: (format) => _vendorService.getCommonItemsImportTemplate(format: format),
            exportItems: (format) => _vendorService.exportCommonItems(format: format),
            importItems: (file) => _vendorService.importCommonItems(file),
            onImported: _load,
            importLabel: l10n.vendorCommonItemsImportMenuLabel,
            exportLabel: l10n.vendorCommonItemsExportMenuLabel,
            templateLabel: l10n.vendorCommonItemsTemplateMenuLabel,
            chooseFormatTitle: l10n.vendorCommonItemsChooseFormatTitle,
            importResultTitle: l10n.vendorCommonItemsImportResultTitle,
            resultSummary: (created, updated, errors) =>
                l10n.vendorCommonItemsImportResultSummary(created, updated, errors),
            closeLabel: l10n.commonOk,
            importFailedMessage: l10n.vendorCommonItemsImportError,
            exportFailedMessage: l10n.vendorCommonItemsExportError,
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(onPressed: () => _showItemForm(), child: const Icon(Icons.add)),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _items.isEmpty
              ? Center(child: Text(l10n.vendorCommonItemsEmptyMessage, style: TyType.sans(14, color: ty.ink2)))
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
                          if (item.coverImageUrl != null) ...[
                            ClipRRect(
                              borderRadius: BorderRadius.circular(8),
                              child: CachedNetworkImage(imageUrl: item.coverImageUrl!, width: 44, height: 44, fit: BoxFit.cover),
                            ),
                            const SizedBox(width: 12),
                          ],
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(children: [
                                  Text(item.name, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w700)),
                                  if (!item.isMandatory) ...[
                                    const SizedBox(width: 6),
                                    Text(l10n.vendorCommonItemsOptionalLabel, style: TyType.sans(11, color: ty.ink3)),
                                  ],
                                  if (item.isReturnable) ...[
                                    const SizedBox(width: 6),
                                    Text(l10n.vendorCommonItemsReturnableBadgeLabel, style: TyType.sans(11, color: ty.saffron)),
                                  ],
                                ]),
                                Text(l10n.vendorCommonItemsQtyPriceLabel(item.quantity.toString(), item.basePrice.toStringAsFixed(0)), style: TyType.sans(12, color: ty.ink2)),
                              ],
                            ),
                          ),
                          TextButton(onPressed: () => _showItemForm(existing: item), child: Text(l10n.vendorCommonItemsEditButtonLabel)),
                          IconButton(icon: const Icon(Icons.delete_outline, color: Colors.red), onPressed: () => _delete(item)),
                        ],
                      ),
                    );
                  },
                ),
    );
  }
}
