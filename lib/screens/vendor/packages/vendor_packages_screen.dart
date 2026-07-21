import 'package:flutter/material.dart';

import '../../../theme/colors.dart';
import '../../../theme/typography.dart';
import '../../../data/vendor_models.dart';
import '../../../data/services/vendor_service.dart';
import 'vendor_package_form_screen.dart';
import 'vendor_package_items_screen.dart';
import 'vendor_common_items_screen.dart';
import 'vendor_package_gallery_screen.dart';

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
    try {
      await _vendorService.submitPackageForReview(p.id);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Submitted for review.')));
        _load();
      }
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Could not submit.')));
    }
  }

  Future<void> _unpublish(VendorPackage p) async {
    try {
      await _vendorService.unpublishPackage(p.id);
      if (mounted) { ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Unpublished.'))); _load(); }
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Could not unpublish.')));
    }
  }

  Future<void> _delete(VendorPackage p) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Delete package?'),
        content: Text('This will permanently delete "${p.name}".'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(context, true), child: const Text('Delete')),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await _vendorService.deletePackage(p.id);
      if (mounted) { ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Deleted.'))); _load(); }
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Could not delete — only draft/inactive packages can be deleted.')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;

    return Scaffold(
      backgroundColor: Colors.transparent,
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => Navigator.of(context)
            .push(MaterialPageRoute(builder: (_) => const VendorPackageFormScreen()))
            .then((_) => _load()),
        icon: const Icon(Icons.add),
        label: const Text('New Package'),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _packages.isEmpty
              ? Center(child: Text('No packages yet', style: TyType.sans(14, color: ty.ink2)))
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
                decoration: BoxDecoration(color: statusColor.withOpacity(0.12), borderRadius: BorderRadius.circular(99)),
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
                child: const Text('Edit'),
              ),
              OutlinedButton(
                onPressed: p.status == 'pending_review'
                    ? null
                    : () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => VendorPackageItemsScreen(package: p))),
                child: const Text('Items'),
              ),
              OutlinedButton(
                onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => VendorPackageGalleryScreen(package: p))),
                child: const Text('Photos'),
              ),
              if (p.status == 'draft')
                ElevatedButton(onPressed: () => _submitForReview(p), child: const Text('Submit')),
              if (p.status == 'active')
                OutlinedButton(onPressed: () => _unpublish(p), child: const Text('Unpublish')),
              if (p.status == 'draft' || p.status == 'inactive' || p.status == 'archived')
                TextButton(
                  onPressed: () => _delete(p),
                  style: TextButton.styleFrom(foregroundColor: Colors.red),
                  child: const Text('Delete'),
                ),
            ],
          ),
        ],
      ),
    );
  }
}
