import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/services/vendor_service.dart';
import '../data/vendor_models.dart';
import '../utils/currency.dart';
import '../widgets/avatar.dart';
import '../widgets/photo_placeholder.dart';
import '../widgets/ty_button.dart';
import '../widgets/common.dart';

class VendorDetailScreen extends StatefulWidget {
  final String vendorId;
  final String? displayName;

  const VendorDetailScreen({super.key, required this.vendorId, this.displayName});

  @override
  State<VendorDetailScreen> createState() => _VendorDetailScreenState();
}

class _VendorDetailScreenState extends State<VendorDetailScreen> {
  final VendorService _vendorService = VendorService();

  VendorPublicDetail? _vendor;
  List<Map<String, dynamic>> _packages = [];
  List<PublicVendorReview> _reviews = [];
  int _selectedPkg = 0;
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() { _isLoading = true; _error = null; });
    try {
      final vendorFuture = _vendorService.getVendorById(widget.vendorId);
      final packagesFuture = _vendorService.getVendorPackages(widget.vendorId);
      final reviewsFuture = _vendorService.getPublicVendorReviews(widget.vendorId);

      final vendor = await vendorFuture;
      final packages = await packagesFuture;
      final reviews = await reviewsFuture;

      if (mounted) {
        setState(() {
          _vendor = vendor;
          _packages = packages;
          _reviews = reviews;
          _isLoading = false;
        });
      }
    } catch (e) {
      debugPrint('Error loading vendor detail: $e');
      if (mounted) setState(() { _error = 'Could not load vendor details.'; _isLoading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;

    if (_isLoading) {
      return Scaffold(
        backgroundColor: ty.paper,
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    if (_error != null || _vendor == null) {
      return Scaffold(
        backgroundColor: ty.paper,
        appBar: tyAppBar(context, title: widget.displayName ?? 'Vendor'),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.error_outline_rounded, size: 48, color: ty.rose),
              const SizedBox(height: 12),
              Text(_error ?? 'Vendor not found', style: TyType.sans(14, color: ty.ink2)),
              const SizedBox(height: 16),
              TextButton(
                onPressed: _loadData,
                child: Text('Try Again', style: TyType.sans(14, color: ty.saffron, weight: FontWeight.w700)),
              ),
            ],
          ),
        ),
      );
    }

    final v = _vendor!;
    final selectedPkgPrice = _selectedPkg < _packages.length
        ? _packages[_selectedPkg]['base_price'] ?? 0
        : 0;

    return Scaffold(
      backgroundColor: ty.paper,
      body: Stack(
        children: [
          ListView(
            padding: EdgeInsets.zero,
            children: [
              Stack(
                children: [
                  v.heroImageUrl != null
                      ? CachedNetworkImage(
                          imageUrl: v.heroImageUrl!,
                          height: 300,
                          width: double.infinity,
                          fit: BoxFit.cover,
                          placeholder: (context, url) => PhotoPlaceholder(tint: v.tint, height: 300, arch: false, radius: BorderRadius.zero),
                          errorWidget: (context, url, error) => PhotoPlaceholder(tint: v.tint, height: 300, arch: false, radius: BorderRadius.zero),
                        )
                      : PhotoPlaceholder(tint: v.tint, height: 300, arch: false, radius: BorderRadius.zero),
                  Positioned.fill(
                    child: DecoratedBox(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          begin: Alignment.bottomCenter,
                          end: Alignment.topCenter,
                          colors: [ty.paper, Colors.black.withOpacity(0.12)],
                          stops: const [0.02, 1],
                        ),
                      ),
                    ),
                  ),
                  Positioned(
                    top: MediaQuery.of(context).padding.top + 8,
                    left: 18,
                    right: 18,
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        _glassButton(Icons.chevron_left_rounded, () => Navigator.of(context).maybePop()),
                        _glassButton(Icons.share_outlined, () {}),
                      ],
                    ),
                  ),
                  if (v.galleryUrls.length > 1)
                    Positioned(
                      left: 18,
                      bottom: 14,
                      child: Row(
                        children: [
                          for (final url in v.galleryUrls.skip(1).take(3))
                            Padding(
                              padding: const EdgeInsets.only(right: 8),
                              child: ClipRRect(
                                borderRadius: BorderRadius.circular(11),
                                child: CachedNetworkImage(
                                  imageUrl: url,
                                  width: 46,
                                  height: 46,
                                  fit: BoxFit.cover,
                                  errorWidget: (_, __, ___) => PhotoPlaceholder(tint: v.tint, arch: false),
                                ),
                              ),
                            ),
                          if (v.galleryUrls.length > 4)
                            Container(
                              width: 46,
                              height: 46,
                              alignment: Alignment.center,
                              decoration: BoxDecoration(
                                color: Colors.white.withOpacity(0.22),
                                borderRadius: BorderRadius.circular(11),
                              ),
                              child: Text('+${v.galleryUrls.length - 4}',
                                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 12)),
                            ),
                        ],
                      ),
                    ),
                ],
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(18, 18, 18, 120),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (v.businessCategory != null)
                      Text(v.businessCategory!.toUpperCase(), style: TyType.eyebrow(11.5, color: ty.saffronDeep)),
                    const SizedBox(height: 3),
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(child: Text(v.businessName, style: TyType.display(30, color: ty.ink))),
                        if (v.rating != null)
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.end,
                            children: [
                              Row(children: [
                                Icon(Icons.star_rounded, color: ty.gold, size: 16),
                                const SizedBox(width: 3),
                                Text(v.rating!.toStringAsFixed(1), style: TyType.sans(16, color: ty.ink, weight: FontWeight.w800)),
                              ]),
                              if (v.totalReviews != null)
                                Text('${v.totalReviews} reviews', style: TyType.sans(11.5, color: ty.ink3)),
                            ],
                          ),
                      ],
                    ),
                    if (v.location != null) ...[
                      const SizedBox(height: 8),
                      Row(children: [
                        Icon(Icons.place_outlined, size: 15, color: ty.ink2),
                        const SizedBox(width: 6),
                        Text(v.location!, style: TyType.sans(13, color: ty.ink2)),
                      ]),
                    ],
                    const SizedBox(height: 18),
                    Row(
                      children: [
                        if (v.isVerified == true) _trust(context, Icons.verified_outlined, 'Verified'),
                        if (v.yearsInBusiness != null) ...[
                          const SizedBox(width: 10),
                          _trust(context, Icons.schedule_rounded, '${v.yearsInBusiness} yrs'),
                        ],
                        if (v.businessCategory != null) ...[
                          const SizedBox(width: 10),
                          _trust(context, Icons.workspace_premium_outlined, v.businessCategory!.split(' ').first),
                        ],
                      ],
                    ),
                    if (v.bio != null && v.bio!.isNotEmpty) ...[
                      const SizedBox(height: 26),
                      Text('About', style: TyType.sans(16, color: ty.ink, weight: FontWeight.w800)),
                      const SizedBox(height: 8),
                      Text(v.bio!, style: TyType.sans(14.5, color: ty.ink2, height: 1.6)),
                    ],
                    if (_packages.isNotEmpty) ...[
                      const SizedBox(height: 26),
                      Text('Packages', style: TyType.sans(16, color: ty.ink, weight: FontWeight.w800)),
                      const SizedBox(height: 10),
                      for (int i = 0; i < _packages.length; i++) _pkgRow(context, i),
                    ],
                    if (_reviews.isNotEmpty) ...[
                      const SizedBox(height: 26),
                      Text('What families say', style: TyType.sans(16, color: ty.ink, weight: FontWeight.w800)),
                      const SizedBox(height: 10),
                      ..._reviews.take(3).map((r) => _reviewCard(context, r)),
                    ],
                  ],
                ),
              ),
            ],
          ),
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: Container(
              padding: EdgeInsets.fromLTRB(18, 12, 18, MediaQuery.of(context).padding.bottom + 14),
              decoration: BoxDecoration(
                color: ty.paper.withOpacity(0.96),
                border: Border(top: BorderSide(color: ty.line2)),
              ),
              child: Row(
                children: [
                  Container(
                    width: 52,
                    height: 52,
                    decoration: BoxDecoration(
                      color: ty.surface,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: ty.line),
                    ),
                    child: Icon(Icons.chat_bubble_outline_rounded, color: ty.ink, size: 22),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TyButton(
                      _packages.isNotEmpty
                          ? 'Add to celebration · ${formatPrice(selectedPkgPrice)}'
                          : 'Contact Vendor',
                      full: true,
                      onTap: () => Navigator.of(context).maybePop(),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _glassButton(IconData icon, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 42,
        height: 42,
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.2),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Icon(icon, color: Colors.white, size: 20),
      ),
    );
  }

  Widget _trust(BuildContext context, IconData icon, String label) {
    final ty = context.ty;
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 13, horizontal: 6),
        decoration: BoxDecoration(
          color: ty.surface2,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: ty.line),
        ),
        child: Column(
          children: [
            Icon(icon, color: ty.saffron, size: 19),
            const SizedBox(height: 5),
            Text(label, style: TyType.sans(11.5, color: ty.ink, weight: FontWeight.w600)),
          ],
        ),
      ),
    );
  }

  Widget _pkgRow(BuildContext context, int i) {
    final ty = context.ty;
    final selected = _selectedPkg == i;
    final p = _packages[i];
    final name = p['name'] as String? ?? 'Package ${i + 1}';
    final desc = p['description'] as String? ?? '';
    final price = p['base_price'] ?? 0;

    return GestureDetector(
      onTap: () => setState(() => _selectedPkg = i),
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.all(15),
        decoration: BoxDecoration(
          color: selected ? ty.saffronSoft : ty.surface,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: selected ? ty.saffron : ty.line, width: selected ? 1.5 : 1),
        ),
        child: Row(
          children: [
            Container(
              width: 22,
              height: 22,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(color: selected ? ty.saffron : ty.line, width: selected ? 7 : 2),
              ),
            ),
            const SizedBox(width: 13),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(name, style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
                  if (desc.isNotEmpty) Text(desc, maxLines: 1, overflow: TextOverflow.ellipsis, style: TyType.sans(12.5, color: ty.ink2)),
                ],
              ),
            ),
            Text(formatPrice(price), style: TyType.sans(15, color: ty.ink, weight: FontWeight.w800)),
          ],
        ),
      ),
    );
  }

  Widget _reviewCard(BuildContext context, PublicVendorReview r) {
    final ty = context.ty;
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: ty.surface,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: ty.line),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              TyAvatar(name: r.reviewerName, index: 0, size: 36),
              const SizedBox(width: 10),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(r.reviewerName, style: TyType.sans(13.5, color: ty.ink, weight: FontWeight.w700)),
                  Text('★' * r.rating.round(), style: TextStyle(color: ty.gold, fontSize: 11)),
                ],
              ),
            ],
          ),
          if (r.comment != null && r.comment!.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text('"${r.comment!}"', style: TyType.sans(13.5, color: ty.ink2, height: 1.55)),
          ],
        ],
      ),
    );
  }
}
