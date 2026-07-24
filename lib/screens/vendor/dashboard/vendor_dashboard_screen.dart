import 'package:flutter/material.dart';

import '../../../theme/colors.dart';
import '../../../theme/typography.dart';
import '../../../data/vendor_models.dart';
import '../../../data/services/vendor_service.dart';
import '../profile/vendor_profile_screen.dart';
import '../packages/vendor_packages_screen.dart';
import '../packages/vendor_package_form_screen.dart';

/// Mirrors the web vendor portal's Overview page: status/verification
/// pills, stat cards, quick actions, business-info card.
class VendorDashboardScreen extends StatefulWidget {
  const VendorDashboardScreen({super.key});

  @override
  State<VendorDashboardScreen> createState() => _VendorDashboardScreenState();
}

class _VendorDashboardScreenState extends State<VendorDashboardScreen> {
  final _vendorService = VendorService();
  VendorBusinessProfile? _vendor;
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
      final vendor = await _vendorService.getMe();
      List<VendorPackage> packages = [];
      if (vendor != null) {
        packages = await _vendorService.listMyPackages();
      }
      if (mounted) setState(() { _vendor = vendor; _packages = packages; _isLoading = false; });
    } catch (_) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;

    if (_isLoading) {
      return Scaffold(backgroundColor: ty.paper, body: const Center(child: CircularProgressIndicator()));
    }

    if (_vendor == null) {
      return Scaffold(
        backgroundColor: ty.paper,
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.storefront_outlined, size: 56, color: ty.ink3),
                const SizedBox(height: 16),
                Text('Set up your business profile', style: TyType.display(22, color: ty.ink)),
                const SizedBox(height: 8),
                Text('Create your vendor profile to start listing packages and receiving bookings.',
                    textAlign: TextAlign.center, style: TyType.sans(14, color: ty.ink2)),
                const SizedBox(height: 20),
                ElevatedButton(
                  onPressed: () => Navigator.of(context)
                      .push(MaterialPageRoute(builder: (_) => const VendorProfileScreen()))
                      .then((_) => _load()),
                  child: const Text('Create Profile'),
                ),
              ],
            ),
          ),
        ),
      );
    }

    final active = _packages.where((p) => p.status == 'active').length;
    final pending = _packages.where((p) => p.status == 'pending_review').length;
    final draft = _packages.where((p) => p.status == 'draft').length;

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: RefreshIndicator(
        onRefresh: _load,
        displacement: 20,
        color: ty.saffron,
        child: ListView(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
          children: [
            Row(
              children: [
                _pill(ty, _vendor!.verificationStatus, _vendor!.verificationStatus == 'verified', true),
                const SizedBox(width: 8),
                _pill(ty, _vendor!.status, _vendor!.status == 'active', false),
              ],
            ),
            const SizedBox(height: 16),
            Text(_vendor!.businessName, style: TyType.display(26, color: ty.ink)),
            const SizedBox(height: 24),
            GridView.count(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisCount: 2,
              mainAxisSpacing: 16,
              crossAxisSpacing: 16,
              childAspectRatio: 1.4,
              children: [
                _statCard(ty, '⭐ ${_vendor!.averageRating.toStringAsFixed(1)}', '${_vendor!.reviewCount} reviews', Icons.star_rounded),
                _statCard(ty, '$active', 'Active Packages', Icons.inventory_2_outlined),
                _statCard(ty, '$pending', 'Pending Review', Icons.hourglass_empty_rounded),
                _statCard(ty, '$draft', 'Drafts', Icons.edit_note_rounded),
              ],
            ),
            const SizedBox(height: 32),
            Text('Quick Actions', style: TyType.sans(16, color: ty.ink, weight: FontWeight.w800)),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () => Navigator.of(context)
                        .push(MaterialPageRoute(builder: (_) => const VendorPackageFormScreen()))
                        .then((_) => _load()),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: ty.saffron,
                      foregroundColor: ty.onPrimary,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                    icon: const Icon(Icons.add_circle_outline, size: 20),
                    label: const Text('Add Package'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => Navigator.of(context)
                        .push(MaterialPageRoute(builder: (_) => const VendorProfileScreen()))
                        .then((_) => _load()),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      side: BorderSide(color: ty.line),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                    icon: const Icon(Icons.edit_outlined, size: 20),
                    label: const Text('Edit Profile'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 32),
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: ty.surface, 
                borderRadius: BorderRadius.circular(20), 
                border: Border.all(color: ty.line),
                boxShadow: [
                  BoxShadow(color: Colors.black.withOpacity(0.03), blurRadius: 10, offset: const Offset(0, 4)),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Business Info', style: TyType.sans(16, color: ty.ink, weight: FontWeight.w800)),
                  const SizedBox(height: 16),
                  _infoRow(ty, 'Type', _vendor!.vendorType.replaceAll('_', ' ')),
                  _infoRow(ty, 'Experience', '${_vendor!.yearsOfExperience ?? '—'} yrs'),
                  _infoRow(ty, 'Service Radius', '${_vendor!.serviceRadiusKm ?? '—'} km'),
                  _infoRow(ty, 'Acceptance Rate', '${_vendor!.acceptanceRatePct.toStringAsFixed(0)}%'),
                  _infoRow(ty, 'Completed Bookings', '${_vendor!.completionCount}'),
                ],
              ),
            ),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }

  Widget _pill(TyColors ty, String label, bool positive, bool isVerification) {
    final color = positive ? ty.leaf : (isVerification ? ty.rose : ty.saffron);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(99),
        border: Border.all(color: color.withOpacity(0.2)),
      ),
      child: Text(
        label.replaceAll('_', ' ').toUpperCase(),
        style: TyType.sans(10.5, color: color, weight: FontWeight.w800, spacing: 0.5),
      ),
    );
  }

  Widget _statCard(TyColors ty, String value, String label, IconData icon) => Container(
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
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 20, color: ty.saffron),
            const SizedBox(height: 10),
            Text(value, style: TyType.display(22, color: ty.ink)),
            const SizedBox(height: 2),
            Text(label, style: TyType.sans(12.5, color: ty.ink2, weight: FontWeight.w600)),
          ],
        ),
      );

  Widget _infoRow(TyColors ty, String label, String value) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label, style: TyType.sans(13, color: ty.ink2)),
            Text(value, style: TyType.sans(13, color: ty.ink, weight: FontWeight.w600)),
          ],
        ),
      );
}
