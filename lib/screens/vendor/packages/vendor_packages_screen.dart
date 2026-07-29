import 'package:flutter/material.dart';

import '../../../theme/colors.dart';
import '../../../theme/typography.dart';
import '../../../data/vendor_models.dart';
import '../../../data/services/vendor_service.dart';
import '../../../l10n/generated/app_localizations.dart';
import 'vendor_package_form_screen.dart';
import 'vendor_package_items_screen.dart';
import 'vendor_package_gallery_screen.dart';
import 'vendor_common_items_screen.dart';

/// Mirrors the web VendorPackagesPage: table/list of the vendor's own
/// packages with status, + create/edit/items/common-items/delete/publish.
class VendorPackagesScreen extends StatefulWidget {
  const VendorPackagesScreen({super.key});

  @override
  State<VendorPackagesScreen> createState() => _VendorPackagesScreenState();
}

class _VendorPackagesScreenState extends State<VendorPackagesScreen> {
  final _vendorService = VendorService();
  List<VendorPackage> _packages = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _isLoading = true);
    try {
      final packages = await _vendorService.listMyPackages();
      if (mounted) setState(() { _packages = packages; _isLoading = false; });
    } catch (_) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _submitForReview(VendorPackage p) async {
    final l10n = AppLocalizations.of(context)!;
    try {
      await _vendorService.submitPackageForReview(p.id);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l10n.vendorPackagesSubmittedForReviewMessage)));
        _load();
      }
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l10n.vendorPackagesSubmitError)));
    }
  }

  Future<void> _unpublish(VendorPackage p) async {
    final l10n = AppLocalizations.of(context)!;
    try {
      await _vendorService.unpublishPackage(p.id);
      if (mounted) { ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l10n.vendorPackagesUnpublishedMessage))); _load(); }
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l10n.vendorPackagesUnpublishError)));
    }
  }

  Future<void> _delete(VendorPackage p) async {
    final l10n = AppLocalizations.of(context)!;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: Text(l10n.vendorPackagesDeleteConfirmTitle),
        content: Text(l10n.vendorPackagesDeleteConfirmMessage(p.name)),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: Text(l10n.commonCancel)),
          TextButton(onPressed: () => Navigator.pop(context, true), child: Text(l10n.vendorPackagesDeleteButtonLabel)),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await _vendorService.deletePackage(p.id);
      if (mounted) { ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l10n.vendorPackagesDeletedMessage))); _load(); }
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l10n.vendorPackagesDeleteRestrictedError)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;

    return Scaffold(
      backgroundColor: Colors.transparent,
      floatingActionButton: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          FloatingActionButton.extended(
            heroTag: 'vendorPackagesCommonItems',
            onPressed: () => Navigator.of(context)
                .push(MaterialPageRoute(builder: (_) => const VendorCommonItemsScreen())),
            icon: const Icon(Icons.inventory_2_outlined),
            label: Text(l10n.vendorPackagesCommonItemsButtonLabel),
          ),
          const SizedBox(height: 12),
          FloatingActionButton.extended(
            heroTag: 'vendorPackagesNewPackage',
            onPressed: () => Navigator.of(context)
                .push(MaterialPageRoute(builder: (_) => const VendorPackageFormScreen()))
                .then((_) => _load()),
            icon: const Icon(Icons.add),
            label: Text(l10n.vendorPackagesNewPackageButtonLabel),
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _packages.isEmpty
              ? Center(child: Text(l10n.vendorPackagesEmptyMessage, style: TyType.sans(14, color: ty.ink2)))
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView.separated(
                    padding: const EdgeInsets.all(18),
                    itemCount: _packages.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 10),
                    itemBuilder: (context, i) => _packageCard(ty, _packages[i]),
                  ),
                ),
    );
  }

  Widget _packageCard(TyColors ty, VendorPackage p) {
    final l10n = AppLocalizations.of(context)!;
    final statusColor = {
      'draft': Colors.grey,
      'pending_review': Colors.orange,
      'active': Colors.green,
      'inactive': Colors.red,
      'archived': Colors.grey,
    }[p.status] ?? ty.ink3;

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(14), border: Border.all(color: ty.line)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(p.name, style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
                    Text('₹${p.basePrice.toStringAsFixed(0)}', style: TyType.sans(13, color: ty.saffronDeep, weight: FontWeight.w600)),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(color: statusColor.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(99)),
                child: Text(p.status.replaceAll('_', ' '), style: TyType.sans(11, color: statusColor, weight: FontWeight.w700)),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              OutlinedButton(
                onPressed: () => Navigator.of(context)
                    .push(MaterialPageRoute(builder: (_) => VendorPackageFormScreen(existing: p)))
                    .then((_) => _load()),
                child: Text(l10n.vendorPackagesEditButtonLabel),
              ),
              OutlinedButton(
                onPressed: p.status == 'pending_review'
                    ? null
                    : () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => VendorPackageItemsScreen(package: p))),
                child: Text(l10n.vendorPackagesItemsButtonLabel),
              ),
              OutlinedButton(
                onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => VendorPackageGalleryScreen(package: p))),
                child: Text(l10n.vendorPackagesPhotosButtonLabel),
              ),
              if (p.status == 'draft')
                ElevatedButton(onPressed: () => _submitForReview(p), child: Text(l10n.vendorPackagesSubmitButtonLabel)),
              if (p.status == 'active')
                OutlinedButton(onPressed: () => _unpublish(p), child: Text(l10n.vendorPackagesUnpublishButtonLabel)),
              if (p.status == 'draft' || p.status == 'inactive' || p.status == 'archived')
                TextButton(
                  onPressed: () => _delete(p),
                  style: TextButton.styleFrom(foregroundColor: Colors.red),
                  child: Text(l10n.vendorPackagesDeleteButtonLabel),
                ),
            ],
          ),
        ],
      ),
    );
  }
}
