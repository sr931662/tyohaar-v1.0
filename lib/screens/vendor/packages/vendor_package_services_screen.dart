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

class VendorPackageServicesScreen extends StatefulWidget {
  final VendorPackage package;
  const VendorPackageServicesScreen({super.key, required this.package});

  @override
  State<VendorPackageServicesScreen> createState() => _VendorPackageServicesScreenState();
}

class _VendorPackageServicesScreenState extends State<VendorPackageServicesScreen> {
  final _vendorService = VendorService();
  List<VendorPackageService> _services = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _isLoading = true);
    try {
      final services = await _vendorService.listPackageServices(widget.package.id);
      if (mounted) setState(() { _services = services; _isLoading = false; });
    } catch (_) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _showServiceForm({VendorPackageService? existing}) async {
    final nameCtrl = TextEditingController(text: existing?.name ?? '');
    final priceCtrl = TextEditingController(text: existing?.basePrice.toStringAsFixed(0) ?? '');
    final qtyCtrl = TextEditingController(text: existing?.quantity.toString() ?? '1');
    final unitCtrl = TextEditingController(text: existing?.unit ?? '');
    final descCtrl = TextEditingController(text: existing?.description ?? '');
    bool isMandatory = existing?.isMandatory ?? true;
    final l10n = AppLocalizations.of(context)!;

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
                Text(existing == null ? l10n.vendorPackageServicesAddServiceTitle : l10n.vendorPackageServicesEditServiceTitle, style: TyType.display(20, color: context.ty.ink)),
                const SizedBox(height: 16),
                TextField(controller: nameCtrl, decoration: InputDecoration(labelText: l10n.vendorPackageServicesNameLabel)),
                TextField(controller: priceCtrl, keyboardType: TextInputType.number, decoration: InputDecoration(labelText: l10n.vendorPackageServicesBasePriceLabel, helperText: l10n.vendorPackageServicesBasePriceFormatHelperText)),
                Row(children: [
                  Expanded(child: TextField(controller: qtyCtrl, keyboardType: TextInputType.number, decoration: InputDecoration(labelText: l10n.vendorPackageServicesQuantityLabel))),
                  const SizedBox(width: 12),
                  Expanded(child: TextField(controller: unitCtrl, decoration: InputDecoration(labelText: l10n.vendorPackageServicesUnitLabel, helperText: l10n.vendorPackageServicesUnitFormatHelperText))),
                ]),
                TextField(controller: descCtrl, maxLines: 2, decoration: InputDecoration(labelText: l10n.vendorPackageServicesDescriptionLabel)),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text(l10n.vendorPackageServicesMandatoryLabel),
                  value: isMandatory,
                  onChanged: (v) => setSheetState(() => isMandatory = v),
                ),
                const SizedBox(height: 12),
                ElevatedButton(
                  onPressed: () => Navigator.pop(context, true),
                  child: Text(l10n.commonSave),
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
      };
      if (existing == null) {
        await _vendorService.addPackageService(widget.package.id, body);
      } else {
        await _vendorService.updatePackageService(widget.package.id, existing.id, body);
      }
      _load();
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l10n.vendorPackageServicesSaveError)));
    } finally {
      // Deferred a frame: showModalBottomSheet's returned Future can resolve
      // while the sheet's closing transition is still rendering, so disposing
      // these immediately races that still-mounted TextField tree and throws
      // "A TextEditingController was used after being disposed."
      WidgetsBinding.instance.addPostFrameCallback((_) {
        nameCtrl.dispose();
        priceCtrl.dispose();
        qtyCtrl.dispose();
        unitCtrl.dispose();
        descCtrl.dispose();
      });
    }
  }

  Future<void> _deleteService(VendorPackageService service) async {
    try {
      await _vendorService.deletePackageService(widget.package.id, service.id);
      _load();
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(AppLocalizations.of(context)!.vendorPackageServicesDeleteError)));
    }
  }

  Future<void> _addServicePhoto(VendorPackageService service) async {
    final image = await ImagePicker().pickImage(source: ImageSource.gallery, imageQuality: 85);
    if (image == null) return;
    try {
      final url = await _vendorService.uploadImage(File(image.path), 'package_image');
      await _vendorService.addServiceImage(widget.package.id, service.id, url);
      _load();
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(AppLocalizations.of(context)!.vendorMultimediaUploadFailedMessage)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final locked = widget.package.status == 'pending_review';

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: AppBar(
        title: Text(l10n.vendorPackageServicesTitle(widget.package.name), maxLines: 1, overflow: TextOverflow.ellipsis),
        actions: locked
            ? null
            : [
                ItemImportExportMenu(
                  getTemplate: (format) =>
                      _vendorService.getPackageServicesImportTemplate(widget.package.id, format: format),
                  exportItems: (format) =>
                      _vendorService.exportPackageServices(widget.package.id, format: format),
                  importItems: (file) => _vendorService.importPackageServices(widget.package.id, file),
                  onImported: _load,
                  importLabel: l10n.vendorPackageServicesImportMenuLabel,
                  exportLabel: l10n.vendorPackageServicesExportMenuLabel,
                  templateLabel: l10n.vendorPackageServicesTemplateMenuLabel,
                  chooseFormatTitle: l10n.vendorPackageServicesChooseFormatTitle,
                  importResultTitle: l10n.vendorPackageServicesImportResultTitle,
                  resultSummary: (created, updated, errors) =>
                      l10n.vendorPackageServicesImportResultSummary(created, updated, errors),
                  closeLabel: l10n.commonOk,
                  importFailedMessage: l10n.vendorPackageServicesImportError,
                  exportFailedMessage: l10n.vendorPackageServicesExportError,
                ),
              ],
      ),
      floatingActionButton: locked
          ? null
          : FloatingActionButton(onPressed: () => _showServiceForm(), child: const Icon(Icons.add)),
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
                    child: Text(l10n.vendorPackageServicesLockedMessage, style: TyType.sans(12.5, color: Colors.orange.shade800)),
                  ),
                Text(l10n.vendorPackageServicesSectionLabel, style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
                const SizedBox(height: 10),
                if (_services.isEmpty)
                  Text(l10n.vendorPackageServicesEmptyMessage, style: TyType.sans(13, color: ty.ink3))
                else
                  ..._services.map((service) => Container(
                        margin: const EdgeInsets.only(bottom: 10),
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(12), border: Border.all(color: ty.line)),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                if (service.coverImageUrl != null || service.imageUrls.isNotEmpty) ...[
                                  ClipRRect(
                                    borderRadius: BorderRadius.circular(8),
                                    child: CachedNetworkImage(
                                      imageUrl: service.coverImageUrl ?? service.imageUrls.first,
                                      width: 40, height: 40, fit: BoxFit.cover,
                                      errorWidget: (context, url, error) => Container(width: 40, height: 40, color: ty.line2),
                                    ),
                                  ),
                                  const SizedBox(width: 10),
                                ],
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Row(children: [
                                        Flexible(
                                          child: Text(service.name,
                                              maxLines: 1,
                                              overflow: TextOverflow.ellipsis,
                                              style: TyType.sans(14, color: ty.ink, weight: FontWeight.w700)),
                                        ),
                                        if (service.isCommon) ...[
                                          const SizedBox(width: 6),
                                          Text(l10n.vendorPackageServicesCommonPrefixLabel, style: TyType.sans(11, color: ty.saffron)),
                                        ],
                                        if (!service.isMandatory) ...[
                                          const SizedBox(width: 6),
                                          Text(l10n.vendorPackageServicesOptionalLabel, style: TyType.sans(11, color: ty.ink3)),
                                        ],
                                      ]),
                                      Text(l10n.vendorPackageServicesQtyPriceLabel(service.quantity.toString(), service.basePrice.toStringAsFixed(0)),
                                          style: TyType.sans(12, color: ty.ink2)),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                            if (!locked) ...[
                              const SizedBox(height: 8),
                              Wrap(spacing: 8, children: [
                                TextButton(onPressed: () => _addServicePhoto(service), child: Text(l10n.vendorPackageServicesPhotosButtonLabel)),
                                if (!service.isCommon) TextButton(onPressed: () => _showServiceForm(existing: service), child: Text(l10n.vendorPackageServicesEditButtonLabel)),
                                if (!service.isCommon)
                                  TextButton(
                                    onPressed: () => _deleteService(service),
                                    style: TextButton.styleFrom(foregroundColor: Colors.red),
                                    child: Text(l10n.vendorPackageServicesDeleteButtonLabel),
                                  ),
                              ]),
                            ],
                          ],
                        ),
                      )),
              ],
            ),
    );
  }
}
