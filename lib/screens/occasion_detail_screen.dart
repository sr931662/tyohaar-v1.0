import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';

import 'package:tyohaar/theme/assets.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/models.dart';
import '../data/services/package_service.dart';
import '../widgets/common.dart';
import '../widgets/photo_placeholder.dart';
import '../widgets/ty_button.dart';
import 'plan_flow/plan_flow_screen.dart';
import 'package_detail_screen.dart';

class OccasionDetailScreen extends StatefulWidget {
  final Occasion occasion;
  const OccasionDetailScreen({super.key, required this.occasion});

  @override
  State<OccasionDetailScreen> createState() => _OccasionDetailScreenState();
}

class _OccasionDetailScreenState extends State<OccasionDetailScreen> {
  final PackageService _packageService = PackageService();
  List<Package> _packages = [];
  bool _isLoadingPackages = true;

  @override
  void initState() {
    super.initState();
    _loadPackages();
  }

  Future<void> _loadPackages() async {
    try {
      final packages = await _packageService.listPackages(occasionId: widget.occasion.id);
      if (mounted) setState(() { _packages = packages; _isLoadingPackages = false; });
    } catch (e) {
      debugPrint('Error loading packages for occasion: $e');
      if (mounted) setState(() => _isLoadingPackages = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final occasion = widget.occasion;
    final color = ty.tint(occasion.tint);

    return Scaffold(
      backgroundColor: ty.paper,
      body: CustomScrollView(
        slivers: [
          SliverAppBar(
            expandedHeight: 240,
            pinned: true,
            leading: Padding(
              padding: const EdgeInsets.all(8.0),
              child: ChromeIconButton(
                icon: Icons.chevron_left_rounded,
                onTap: () => Navigator.pop(context),
              ),
            ),
            flexibleSpace: FlexibleSpaceBar(
              background: Stack(
                fit: StackFit.expand,
                children: [
                  CachedNetworkImage(
                    imageUrl: occasion.heroImageUrl ?? '',
                    fit: BoxFit.cover,
                    placeholder: (context, url) => PhotoPlaceholder(tint: occasion.tint, arch: false),
                    errorWidget: (context, url, error) {
                      final local = OccasionAssets.getRelatedBackground(occasion.name);
                      if (local != null) return Image.asset(local, fit: BoxFit.cover);
                      return PhotoPlaceholder(tint: occasion.tint, arch: false);
                    },
                  ),
                  DecoratedBox(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.bottomCenter,
                        end: Alignment.topCenter,
                        colors: [
                          ty.paper,
                          ty.paper.withOpacity(0.0),
                          Colors.black.withOpacity(0.4),
                        ],
                        stops: const [0.0, 0.5, 1.0],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  TyPill(
                    occasion.category.replaceAll('_', ' ').toUpperCase(),
                    background: color.withOpacity(0.12),
                    foreground: color,
                  ),
                  const SizedBox(height: 12),
                  Text(occasion.name, style: TyType.display(32, color: ty.ink)),
                  const SizedBox(height: 8),
                  Text(
                    occasion.description ?? '',
                    style: TyType.sans(16, color: ty.ink2, height: 1.5),
                  ),
                  const SizedBox(height: 32),
                  const SectionHeader('Curated Packages'),
                  if (_isLoadingPackages)
                    const Padding(
                      padding: EdgeInsets.symmetric(vertical: 24),
                      child: Center(child: CircularProgressIndicator()),
                    )
                  else if (_packages.isEmpty)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 24),
                      child: Text(
                        'No packages available for this occasion yet.',
                        style: TyType.sans(14, color: ty.ink2),
                      ),
                    )
                  else
                    ..._packages.map((p) => _packageCard(context, p)),
                  const SizedBox(height: 40),
                  TyButton(
                    'Plan this celebration',
                    full: true,
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute(builder: (_) => const PlanFlowScreen()),
                    ),
                  ),
                  const SizedBox(height: 40),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _packageCard(BuildContext context, Package p) {
    final ty = context.ty;
    return GestureDetector(
      onTap: () => Navigator.of(context).push(
        MaterialPageRoute(builder: (_) => PackageDetailScreen(package: p)),
      ),
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: ty.surface,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: ty.line),
        ),
        child: Row(
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: CachedNetworkImage(
                imageUrl: p.coverImageUrl ?? '',
                width: 64,
                height: 64,
                fit: BoxFit.cover,
                placeholder: (context, url) => PhotoPlaceholder(tint: p.tint, arch: false),
                errorWidget: (context, url, error) => PhotoPlaceholder(tint: p.tint, arch: false),
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(p.name, style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
                  if (p.description != null && p.description!.isNotEmpty)
                    Text(p.description!, maxLines: 1, overflow: TextOverflow.ellipsis, style: TyType.sans(12, color: ty.ink3)),
                ],
              ),
            ),
            Text(
              '₹${(p.price / 1000).toStringAsFixed(0)}K',
              style: TyType.sans(16, color: ty.ink, weight: FontWeight.w800),
            ),
          ],
        ),
      ),
    );
  }
}
