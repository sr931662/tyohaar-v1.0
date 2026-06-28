import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/models.dart';
import '../data/services/package_service.dart';
import '../widgets/photo_placeholder.dart';
import '../widgets/ty_chip.dart';
import '../widgets/common.dart';
import 'package:tyohaar/screens/package_detail_screen.dart';
import 'package:tyohaar/screens/package_filter_screen.dart';

class ExploreScreen extends StatefulWidget {
  const ExploreScreen({super.key});

  @override
  State<ExploreScreen> createState() => _ExploreScreenState();
}

class _ExploreScreenState extends State<ExploreScreen> {
  final PackageService _packageService = PackageService();
  String _catLabel = 'All';
  String _searchQuery = '';
  List<Package> _allPackages = [];
  bool _isLoading = true;

  final List<String> _cats = ['All', 'Life Events', 'Major Festivals', 'Minor Festivals'];

  @override
  void initState() {
    super.initState();
    _loadPackages();
  }

  Future<void> _loadPackages() async {
    setState(() => _isLoading = true);
    try {
      final packages = await _packageService.listPackages();
      setState(() {
        _allPackages = packages;
        _isLoading = false;
      });
    } catch (e) {
      debugPrint('Error loading packages: $e');
      setState(() => _isLoading = false);
    }
  }

  void _push(BuildContext context, Widget page) {
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => page));
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final topPadding = MediaQuery.of(context).padding.top + 70;
    
    // Filter logic
    List<Package> list = _allPackages.where((p) {
      final matchesQuery = p.name.toLowerCase().contains(_searchQuery.toLowerCase()) || 
                          p.theme.toLowerCase().contains(_searchQuery.toLowerCase());
      
      if (_catLabel == 'All') return matchesQuery;
      
      final categoryKey = _catLabel == 'Life Events' 
          ? 'life' 
          : _catLabel == 'Major Festivals' 
              ? 'major_festival' 
              : 'minor_festival';
      
      return matchesQuery && p.category == categoryKey;
    }).toList();

    final featured = list.take(3).toList();

    return Padding(
      padding: EdgeInsets.only(top: topPadding),
      child: Column(
        children: [
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
                          onChanged: (v) => setState(() => _searchQuery = v),
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
            child: _isLoading 
              ? const Center(child: CircularProgressIndicator())
              : list.isEmpty 
                ? _buildEmptyState(context)
                : ListView(
                    padding: const EdgeInsets.fromLTRB(18, 12, 18, 28),
                    children: [
                      if (featured.isNotEmpty && _searchQuery.isEmpty) ...[
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

  Widget _buildEmptyState(BuildContext context) {
    final ty = context.ty;
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.search_off_rounded, size: 64, color: ty.ink3),
          const SizedBox(height: 16),
          Text('No packages found', style: TyType.display(20, color: ty.ink)),
          const SizedBox(height: 8),
          Text('Try searching for something else or change categories.', 
            style: TyType.sans(14, color: ty.ink2)),
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
                ClipRRect(
                  borderRadius: BorderRadius.circular(20),
                  child: CachedNetworkImage(
                    imageUrl: p.coverImageUrl ?? '',
                    height: 140,
                    width: double.infinity,
                    fit: BoxFit.cover,
                    placeholder: (context, url) => PhotoPlaceholder(tint: p.tint, height: 140, arch: false),
                    errorWidget: (context, url, error) => PhotoPlaceholder(tint: p.tint, height: 140, arch: false),
                  ),
                ),
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
            Text(p.description ?? '',
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
              child: ClipRRect(
                borderRadius: BorderRadius.circular(16),
                child: CachedNetworkImage(
                  imageUrl: p.coverImageUrl ?? '',
                  fit: BoxFit.cover,
                  placeholder: (context, url) => PhotoPlaceholder(tint: p.tint, arch: false),
                  errorWidget: (context, url, error) => PhotoPlaceholder(tint: p.tint, arch: false),
                ),
              ),
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
