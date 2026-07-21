import 'package:flutter/material.dart';

import '../../../theme/colors.dart';
import '../../../theme/typography.dart';
import '../../../data/vendor_models.dart';
import '../../../data/services/vendor_service.dart';
import '../profile/vendor_profile_screen.dart';
import '../packages/vendor_packages_screen.dart';

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
      backgroundColor: ty.paper,
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.all(18),
          children: [
            Row(
              children: [
                _pill(ty, _vendor!.verificationStatus, _vendor!.verificationStatus == 'verified'),
                const SizedBox(width: 8),
                _pill(ty, _vendor!.status, _vendor!.status == 'active'),
              ],
            ),
            const SizedBox(height: 16),
            Text(_vendor!.businessName, style: TyType.display(24, color: ty.ink)),
            const SizedBox(height: 20),
            GridView.count(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisCount: 2,
              mainAxisSpacing: 12,
              crossAxisSpacing: 12,
              childAspectRatio: 1.5,
              children: [
                _statCard(ty, '⭐ ${_vendor!.averageRating.toStringAsFixed(1)}', '${_vendor!.reviewCount} reviews'),
                _statCard(ty, '$active', 'Active Packages'),
                _statCard(ty, '$pending', 'Pending Review'),
                _statCard(ty, '$draft', 'Drafts'),
              ],
            ),
            const SizedBox(height: 20),
            Text('Quick Actions', style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => Navigator.of(context)
                        .push(MaterialPageRoute(builder: (_) => const VendorPackagesScreen()))
                        .then((_) => _load()),
                    child: const Text('Add Package'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => Navigator.of(context)
                        .push(MaterialPageRoute(builder: (_) => const VendorProfileScreen()))
                        .then((_) => _load()),
                    child: const Text('Edit Profile'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(16), border: Border.all(color: ty.line)),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Business Info', style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
                  const SizedBox(height: 12),
                  _infoRow(ty, 'Type', _vendor!.vendorType.replaceAll('_', ' ')),
                  _infoRow(ty, 'Experience', '${_vendor!.yearsOfExperience ?? '—'} yrs'),
                  _infoRow(ty, 'Service Radius', '${_vendor!.serviceRadiusKm ?? '—'} km'),
                  _infoRow(ty, 'Acceptance Rate', '${_vendor!.acceptanceRatePct.toStringAsFixed(0)}%'),
                  _infoRow(ty, 'Completed Bookings', '${_vendor!.completionCount}'),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _pill(TyColors ty, String label, bool positive) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          color: (positive ? Colors.green : Colors.orange).withOpacity(0.12),
          borderRadius: BorderRadius.circular(99),
        ),
        child: Text(label.replaceAll('_', ' '),
            style: TyType.sans(11.5, color: positive ? Colors.green.shade700 : Colors.orange.shade700, weight: FontWeight.w700)),
      );

  Widget _statCard(TyColors ty, String value, String label) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(14), border: Border.all(color: ty.line)),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(value, style: TyType.display(20, color: ty.ink)),
            const SizedBox(height: 4),
            Text(label, style: TyType.sans(12, color: ty.ink2)),
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
