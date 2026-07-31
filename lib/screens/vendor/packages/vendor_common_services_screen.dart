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

/// Vendor-wide reusable service templates (Photography, DJ, Makeup, etc.),
/// attachable to any of the vendor's own packages instead of being recreated
/// per package. Mirrors VendorCommonItemsScreen exactly, minus the returnable
/// flag (doesn't apply to a labor service).
class VendorCommonServicesScreen extends StatefulWidget {
  const VendorCommonServicesScreen({super.key});

  @override
  State<VendorCommonServicesScreen> createState() => _VendorCommonServicesScreenState();
}

class _VendorCommonServicesScreenState extends State<VendorCommonServicesScreen> {
  final _vendorService = VendorService();
  List<VendorCommonService> _services = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _isLoading = true);
    try {
      final services = await _vendorService.listCommonServices();
      if (mounted) setState(() { _services = services; _isLoading = false; });
    } catch (_) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _showServiceForm({VendorCommonService? existing}) async {
    final nameCtrl = TextEditingController(text: existing?.name ?? '');
    final priceCtrl = TextEditingController(text: existing?.basePrice.toStringAsFixed(0) ?? '');
    final qtyCtrl = TextEditingController(text: existing?.quantity.toString() ?? '1');
    final unitCtrl = TextEditingController(text: existing?.unit ?? '');
    final descCtrl = TextEditingController(text: existing?.description ?? '');
    bool isMandatory = existing?.isMandatory ?? true;
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
                Text(existing == null ? l10n.vendorCommonServicesNewServiceTitle : l10n.vendorCommonServicesEditServiceTitle, style: TyType.display(20, color: context.ty.ink)),
                const SizedBox(height: 16),
                TextField(controller: nameCtrl, decoration: InputDecoration(labelText: l10n.vendorCommonServicesNameLabel)),
                TextField(controller: priceCtrl, keyboardType: TextInputType.number, decoration: InputDecoration(labelText: l10n.vendorCommonServicesBasePriceLabel, helperText: l10n.vendorCommonServicesBasePriceFormatHelperText)),
                Row(children: [
                  Expanded(child: TextField(controller: qtyCtrl, keyboardType: TextInputType.number, decoration: InputDecoration(labelText: l10n.vendorCommonServicesQuantityLabel))),
                  const SizedBox(width: 12),
                  Expanded(child: TextField(controller: unitCtrl, decoration: InputDecoration(labelText: l10n.vendorCommonServicesUnitLabel, helperText: l10n.vendorCommonServicesUnitFormatHelperText))),
                ]),
                TextField(controller: descCtrl, maxLines: 2, decoration: InputDecoration(labelText: l10n.vendorCommonServicesDescriptionLabel)),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text(l10n.vendorCommonServicesMandatoryLabel),
                  value: isMandatory,
                  onChanged: (v) => setSheetState(() => isMandatory = v),
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
                        ? l10n.vendorCommonServicesUploadingLabel
                        : coverImageUrl == null
                            ? l10n.vendorCommonServicesAddCoverPhotoButtonLabel
                            : l10n.vendorCommonServicesChangeCoverPhotoButtonLabel),
                  ),
                ]),
                const SizedBox(height: 12),
                ElevatedButton(
                  onPressed: () => Navigator.pop(context, true),
                  child: Text(existing == null ? l10n.vendorCommonServicesCreateButtonLabel : l10n.vendorCommonServicesUpdateButtonLabel),
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
        'cover_image_url': coverImageUrl,
      };
      if (existing == null) {
        await _vendorService.createCommonService(body);
      } else {
        await _vendorService.updateCommonService(existing.id, body);
      }
      _load();
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text(existing == null ? l10n.vendorCommonServicesCreateError : l10n.vendorCommonServicesUpdateError)));
      }
    } finally {
      nameCtrl.dispose();
      priceCtrl.dispose();
      qtyCtrl.dispose();
      unitCtrl.dispose();
      descCtrl.dispose();
    }
  }

  Future<void> _delete(VendorCommonService service) async {
    final l10n = AppLocalizations.of(context)!;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: Text(l10n.vendorCommonServicesDeleteConfirmTitle),
        content: Text(l10n.vendorCommonServicesDeleteConfirmMessage(service.name)),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: Text(l10n.commonCancel)),
          TextButton(onPressed: () => Navigator.pop(context, true), child: Text(l10n.vendorCommonServicesDeleteButtonLabel)),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await _vendorService.deleteCommonService(service.id);
      _load();
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l10n.vendorCommonServicesDeleteError)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    return Scaffold(
      backgroundColor: ty.paper,
      appBar: AppBar(
        title: Text(l10n.vendorCommonServicesTitle),
        actions: [
          ItemImportExportMenu(
            getTemplate: (format) => _vendorService.getCommonServicesImportTemplate(format: format),
            exportItems: (format) => _vendorService.exportCommonServices(format: format),
            importItems: (file) => _vendorService.importCommonServices(file),
            onImported: _load,
            importLabel: l10n.vendorCommonServicesImportMenuLabel,
            exportLabel: l10n.vendorCommonServicesExportMenuLabel,
            templateLabel: l10n.vendorCommonServicesTemplateMenuLabel,
            chooseFormatTitle: l10n.vendorCommonServicesChooseFormatTitle,
            importResultTitle: l10n.vendorCommonServicesImportResultTitle,
            resultSummary: (created, updated, errors) =>
                l10n.vendorCommonServicesImportResultSummary(created, updated, errors),
            closeLabel: l10n.commonOk,
            importFailedMessage: l10n.vendorCommonServicesImportError,
            exportFailedMessage: l10n.vendorCommonServicesExportError,
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(onPressed: () => _showServiceForm(), child: const Icon(Icons.add)),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _services.isEmpty
              ? Center(child: Text(l10n.vendorCommonServicesEmptyMessage, style: TyType.sans(14, color: ty.ink2)))
              : ListView.separated(
                  padding: const EdgeInsets.all(18),
                  itemCount: _services.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 10),
                  itemBuilder: (context, i) {
                    final service = _services[i];
                    return Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(12), border: Border.all(color: ty.line)),
                      child: Row(
                        children: [
                          if (service.coverImageUrl != null) ...[
                            ClipRRect(
                              borderRadius: BorderRadius.circular(8),
                              child: CachedNetworkImage(imageUrl: service.coverImageUrl!, width: 44, height: 44, fit: BoxFit.cover),
                            ),
                            const SizedBox(width: 12),
                          ],
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(children: [
                                  Text(service.name, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w700)),
                                  if (!service.isMandatory) ...[
                                    const SizedBox(width: 6),
                                    Text(l10n.vendorCommonServicesOptionalLabel, style: TyType.sans(11, color: ty.ink3)),
                                  ],
                                ]),
                                Text(l10n.vendorCommonServicesQtyPriceLabel(service.quantity.toString(), service.basePrice.toStringAsFixed(0)), style: TyType.sans(12, color: ty.ink2)),
                              ],
                            ),
                          ),
                          TextButton(onPressed: () => _showServiceForm(existing: service), child: Text(l10n.vendorCommonServicesEditButtonLabel)),
                          IconButton(icon: const Icon(Icons.delete_outline, color: Colors.red), onPressed: () => _delete(service)),
                        ],
                      ),
                    );
                  },
                ),
    );
  }
}
