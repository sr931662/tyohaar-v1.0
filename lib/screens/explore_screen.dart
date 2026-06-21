import 'package:flutter/material.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/sample_data.dart';
import '../data/models.dart';
import '../widgets/photo_placeholder.dart';
import '../widgets/ty_chip.dart';
import '../widgets/common.dart';
import 'package:tyohaar/screens/package_detail_screen.dart';
import 'package:tyohaar/screens/package_filter_screen.dart';

/// Discover packages — search, filter, and browse curated celebration bundles.
class ExploreScreen extends StatefulWidget {
  const ExploreScreen({super.key});

  @override
  State<ExploreScreen> createState() => _ExploreScreenState();
}

class _ExploreScreenState extends State<ExploreScreen> {
  String _catLabel = 'All';

  final List<String> _cats = ['All', 'Life Events', 'Major Festivals', 'Minor Festivals'];

  void _push(BuildContext context, Widget page) {
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => page));
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final topPadding = MediaQuery.of(context).padding.top + 70;
    
    // Filter logic
    final allPackages = [...TyData.packages, ...TyData.bestSellers];
    
    List<Package> list;
    if (_catLabel == 'All') {
      list = allPackages;
    } else {
      final categoryKey = _catLabel == 'Life Events' 
          ? 'life' 
          : _catLabel == 'Major Festivals' 
              ? 'major_festival' 
              : 'minor_festival';
      list = allPackages.where((p) => p.category == categoryKey).toList();
    }

    final featured = list.take(3).toList();

    return Padding(
      padding: EdgeInsets.only(top: topPadding),
      child: Column(
        children: [
          // header + search
          Padding(
            padding: const EdgeInsets.fromLTRB(18, 12, 18, 0),
            child: Column(
              children: [
                Row(
                  children: [
                    Expanded(
                        child: Text('Discover packages',
                            style: TyType.display(25, color: ty.ink))),
                    ChromeIconButton(
                      icon: Icons.tune_rounded,
                      onTap: () => _push(context, const PackageFilterScreen()),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14),
                  decoration: BoxDecoration(
                    color: ty.surface2,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: ty.line),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.search_rounded, size: 18, color: ty.ink3),
                      const SizedBox(width: 8),
                      Expanded(
                        child: TextField(
                          decoration: InputDecoration(
                            isDense: true,
                            border: InputBorder.none,
                            hintText: 'Search birthdays, weddings, Diwali…',
                            hintStyle: TyType.sans(14.5, color: ty.ink3),
                          ),
                          style: TyType.sans(14.5, color: ty.ink),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 14),
              ],
            ),
          ),
          // category chips
          SizedBox(
            height: 40,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 18),
              itemCount: _cats.length,
              separatorBuilder: (_, __) => const SizedBox(width: 8),
              itemBuilder: (context, i) => TyChip(
                label: _cats[i],
                active: _catLabel == _cats[i],
                onTap: () => setState(() => _catLabel = _cats[i]),
              ),
            ),
          ),
          const SizedBox(height: 6),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.fromLTRB(18, 12, 18, 28),
              children: [
                if (featured.isNotEmpty) ...[
                  const SectionHeader('Featured for you'),
                  SizedBox(
                    height: 230,
                    child: ListView.separated(
                      scrollDirection: Axis.horizontal,
                      itemCount: featured.length,
                      separatorBuilder: (_, __) => const SizedBox(width: 13),
                      itemBuilder: (context, i) => _packageFeatured(context, featured[i]),
                    ),
                  ),
                  const SizedBox(height: 24),
                ],
                const SectionHeader('Available Packages'),
                ...list.map((p) => _packageRow(context, p)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _packageFeatured(BuildContext context, Package p) {
    final ty = context.ty;
    return GestureDetector(
      onTap: () => _push(context, PackageDetailScreen(package: p)),
      child: SizedBox(
        width: 220,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Stack(
              children: [
                p.coverImage.startsWith('assets/')
                    ? ClipRRect(
                        borderRadius: BorderRadius.circular(20),
                        child: Image.asset(p.coverImage, height: 140, width: double.infinity, fit: BoxFit.cover),
                      )
                    : PhotoPlaceholder(tint: p.tint, height: 140, arch: false),
                Positioned(top: 10, left: 10, child: TyPill(p.theme)),
                Positioned(
                  top: 10,
                  right: 10,
                  child: TyPill('₹${(p.price / 1000).toStringAsFixed(0)}K'),
                ),
              ],
            ),
            const SizedBox(height: 9),
            Text(p.name, style: TyType.sans(15.5, color: ty.ink, weight: FontWeight.w700)),
            Text(p.description,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: TyType.sans(12.5, color: ty.ink2)),
          ],
        ),
      ),
    );
  }

  Widget _packageRow(BuildContext context, Package p) {
    final ty = context.ty;
    return GestureDetector(
      onTap: () => _push(context, PackageDetailScreen(package: p)),
      child: Container(
        margin: const EdgeInsets.only(bottom: 13),
        padding: const EdgeInsets.all(11),
        decoration: BoxDecoration(
          color: ty.surface,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: ty.line),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: 88,
              height: 88,
              child: p.coverImage.startsWith('assets/')
                  ? ClipRRect(
                      borderRadius: BorderRadius.circular(16),
                      child: Image.asset(p.coverImage, fit: BoxFit.cover),
                    )
                  : PhotoPlaceholder(tint: p.tint, arch: false),
            ),
            const SizedBox(width: 13),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(p.theme.toUpperCase(),
                      style: TyType.eyebrow(11, color: ty.saffronDeep)),
                  const SizedBox(height: 2),
                  Text(p.name, style: TyType.sans(16, color: ty.ink, weight: FontWeight.w700)),
                  const SizedBox(height: 1),
                  Text('${p.inclusions.length} Inclusions', style: TyType.sans(12.5, color: ty.ink2)),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Text('Starting from', style: TyType.sans(11, color: ty.ink3)),
                      const SizedBox(width: 4),
                      Text('₹${(p.price / 1000).toStringAsFixed(0)}K',
                          style: TyType.sans(14, color: ty.ink, weight: FontWeight.w800)),
                      const Spacer(),
                      Icon(Icons.chevron_right_rounded, color: ty.ink3, size: 18),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
