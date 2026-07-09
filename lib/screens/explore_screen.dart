import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';

import 'package:tyohaar/theme/assets.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/models.dart';
import '../data/services/package_service.dart';
import '../widgets/photo_placeholder.dart';
import '../widgets/ty_chip.dart';
import '../widgets/common.dart';
import '../widgets/tutorial/tutorial_overlay.dart';
import 'package:tyohaar/screens/package_detail_screen.dart';
import 'package:tyohaar/screens/package_filter_screen.dart';

// Session-level city preference. Resets on app restart (no dependency needed).
class _CityPref {
  static String? selected;
}

// Serviceable cities with display name → slug mapping.
const List<(String, String)> _kCities = [
  ('All Cities', ''),
  ('Noida', 'noida'),
  ('Delhi', 'delhi'),
  ('Gurgaon', 'gurgaon'),
  ('Mumbai', 'mumbai'),
  ('Pune', 'pune'),
  ('Bengaluru', 'bengaluru'),
  ('Hyderabad', 'hyderabad'),
  ('Chennai', 'chennai'),
  ('Kolkata', 'kolkata'),
  ('Jaipur', 'jaipur'),
  ('Ahmedabad', 'ahmedabad'),
  ('Lucknow', 'lucknow'),
  ('Chandigarh', 'chandigarh'),
  ('Indore', 'indore'),
];

class ExploreScreen extends StatefulWidget {
  const ExploreScreen({super.key});

  @override
  State<ExploreScreen> createState() => _ExploreScreenState();
}

class _ExploreScreenState extends State<ExploreScreen> {
  final PackageService _packageService = PackageService();

  // Category state — fetched from API on first load
  List<PackageCategory> _categories = [];
  String? _selectedCategoryId;

  String _searchQuery = '';
  List<Package> _allPackages = [];
  bool _isLoading = true;
  bool _categoriesLoaded = false;
  final GlobalKey _searchKey = GlobalKey();

  String get _selectedCitySlug => _CityPref.selected ?? '';
  String get _selectedCityLabel {
    if (_selectedCitySlug.isEmpty) return 'All Cities';
    final match = _kCities.where((c) => c.$2 == _selectedCitySlug).firstOrNull;
    return match?.$1 ?? _selectedCitySlug;
  }

  @override
  void initState() {
    super.initState();
    _loadCategories();
    _loadPackages();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      TutorialOverlay.show(context, screenKey: 'explore', steps: [
        TutorialStep(
          targetKey: _searchKey,
          title: 'Find the perfect package',
          description: 'Search by occasion, or use the filter and city picker above to narrow things down.',
        ),
      ]);
    });
  }

  Future<void> _loadCategories() async {
    if (_categoriesLoaded) return;
    try {
      final cats = await _packageService.listCategories();
      if (mounted) {
        setState(() {
          _categories = cats;
          _categoriesLoaded = true;
        });
      }
    } catch (e) {
      debugPrint('Error loading categories: $e');
    }
  }

  Future<void> _loadPackages() async {
    setState(() => _isLoading = true);
    try {
      final city = _selectedCitySlug.isEmpty ? null : _selectedCitySlug;
      final packages = await _packageService.listPackages(
        city: city,
        categoryId: _selectedCategoryId,
      );
      setState(() {
        _allPackages = packages;
        _isLoading = false;
      });
    } catch (e) {
      debugPrint('Error loading packages: $e');
      setState(() => _isLoading = false);
    }
  }

  void _showCityPicker() {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        final ty = ctx.ty;
        return Container(
          decoration: BoxDecoration(
            color: ty.paper,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const SizedBox(height: 12),
              Container(
                width: 40, height: 4,
                decoration: BoxDecoration(color: ty.line2, borderRadius: BorderRadius.circular(2)),
              ),
              const SizedBox(height: 16),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Row(
                  children: [
                    Text('Select Your City', style: TyType.display(20, color: ty.ink)),
                    const Spacer(),
                    IconButton(
                      icon: Icon(Icons.close, color: ty.ink2),
                      onPressed: () => Navigator.pop(ctx),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 8),
              Flexible(
                child: ListView.builder(
                  shrinkWrap: true,
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 32),
                  itemCount: _kCities.length,
                  itemBuilder: (_, i) {
                    final (label, slug) = _kCities[i];
                    final isSelected = slug == _selectedCitySlug;
                    return ListTile(
                      onTap: () {
                        Navigator.pop(ctx);
                        setState(() {
                          _CityPref.selected = slug.isEmpty ? null : slug;
                        });
                        _loadPackages();
                      },
                      contentPadding: const EdgeInsets.symmetric(horizontal: 8),
                      leading: Icon(
                        slug.isEmpty ? Icons.public_rounded : Icons.location_city_rounded,
                        color: isSelected ? ty.saffron : ty.ink3,
                        size: 20,
                      ),
                      title: Text(
                        label,
                        style: TyType.sans(15, color: isSelected ? ty.saffron : ty.ink,
                            weight: isSelected ? FontWeight.w700 : FontWeight.normal),
                      ),
                      trailing: isSelected
                          ? Icon(Icons.check_circle_rounded, color: ty.saffron, size: 18)
                          : null,
                    );
                  },
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  void _push(BuildContext context, Widget page) {
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => page));
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final topPadding = MediaQuery.of(context).padding.top + 70;

    // Client-side search filter only — category and city are applied server-side.
    final List<Package> list = _allPackages.where((p) {
      return p.name.toLowerCase().contains(_searchQuery.toLowerCase()) ||
          (p.slug ?? '').toLowerCase().contains(_searchQuery.toLowerCase());
    }).toList();

    final featured = list.where((p) => p.isFeatured).take(5).toList();

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
                    // City picker button
                    GestureDetector(
                      onTap: _showCityPicker,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                        decoration: BoxDecoration(
                          color: _selectedCitySlug.isEmpty ? ty.surface2 : ty.saffron.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(
                            color: _selectedCitySlug.isEmpty ? ty.line : ty.saffron.withOpacity(0.4),
                          ),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.location_on_rounded,
                                size: 14,
                                color: _selectedCitySlug.isEmpty ? ty.ink3 : ty.saffron),
                            const SizedBox(width: 4),
                            Text(_selectedCityLabel,
                                style: TyType.sans(13,
                                    color: _selectedCitySlug.isEmpty ? ty.ink2 : ty.saffron,
                                    weight: FontWeight.w600)),
                            const SizedBox(width: 3),
                            Icon(Icons.keyboard_arrow_down_rounded,
                                size: 14,
                                color: _selectedCitySlug.isEmpty ? ty.ink3 : ty.saffron),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    ChromeIconButton(
                      icon: Icons.tune_rounded,
                      onTap: () => _push(context, const PackageFilterScreen()),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Container(
                  key: _searchKey,
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
              itemCount: _categories.length + 1,
              separatorBuilder: (_, __) => const SizedBox(width: 8),
              itemBuilder: (context, i) {
                if (i == 0) {
                  return TyChip(
                    label: 'All',
                    active: _selectedCategoryId == null,
                    onTap: () {
                      if (_selectedCategoryId != null) {
                        setState(() => _selectedCategoryId = null);
                        _loadPackages();
                      }
                    },
                  );
                }
                final cat = _categories[i - 1];
                return TyChip(
                  label: cat.name,
                  active: _selectedCategoryId == cat.id,
                  onTap: () {
                    if (_selectedCategoryId != cat.id) {
                      setState(() => _selectedCategoryId = cat.id);
                      _loadPackages();
                    }
                  },
                );
              },
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
                                itemBuilder: (context, i) =>
                                    _packageFeatured(context, featured[i]),
                              ),
                            ),
                            const SizedBox(height: 24),
                          ],
                          SectionHeader(
                            _selectedCitySlug.isEmpty
                                ? 'Available Packages'
                                : 'Packages in $_selectedCityLabel',
                          ),
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
          Text(
            _selectedCitySlug.isEmpty
                ? 'No packages found'
                : 'No packages in $_selectedCityLabel',
            style: TyType.display(20, color: ty.ink),
          ),
          const SizedBox(height: 8),
          Text(
            _selectedCitySlug.isEmpty
                ? 'Try searching for something else or change categories.'
                : 'Try a different city or browse all cities.',
            style: TyType.sans(14, color: ty.ink2),
            textAlign: TextAlign.center,
          ),
          if (_selectedCitySlug.isNotEmpty) ...[
            const SizedBox(height: 16),
            GestureDetector(
              onTap: () {
                setState(() => _CityPref.selected = null);
                _loadPackages();
              },
              child: Text('Browse all cities',
                  style: TyType.sans(14, color: ty.saffron, weight: FontWeight.w600)),
            ),
          ],
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
                    placeholder: (context, url) =>
                        PhotoPlaceholder(tint: p.tint, height: 140, arch: false),
                    errorWidget: (context, url, error) =>
                        OccasionAssets.getFallback(p.name, tint: p.tint, arch: false),
                  ),
                ),
                Positioned(
                  top: 10,
                  right: 10,
                  child: TyPill('₹${(p.price / 1000).toStringAsFixed(0)}K'),
                ),
              ],
            ),
            const SizedBox(height: 9),
            Text(p.name,
                style: TyType.sans(15.5, color: ty.ink, weight: FontWeight.w700)),
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
                  placeholder: (context, url) =>
                      PhotoPlaceholder(tint: p.tint, arch: false),
                  errorWidget: (context, url, error) =>
                      OccasionAssets.getFallback(p.name, tint: p.tint, arch: false),
                ),
              ),
            ),
            const SizedBox(width: 13),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (p.citySlug != null)
                    Align(
                      alignment: Alignment.centerRight,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: ty.surface2,
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: ty.line),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.location_on_rounded, size: 10, color: ty.ink3),
                            const SizedBox(width: 2),
                            Text(p.citySlug!,
                                style: TyType.sans(10, color: ty.ink3)),
                          ],
                        ),
                      ),
                    ),
                  const SizedBox(height: 2),
                  Text(p.name,
                      style: TyType.sans(16, color: ty.ink, weight: FontWeight.w700)),
                  const SizedBox(height: 1),
                  Text('${p.inclusionsCount} Inclusions',
                      style: TyType.sans(12.5, color: ty.ink2)),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Text('Starting from', style: TyType.sans(11, color: ty.ink3)),
                      const SizedBox(width: 4),
                      Text('₹${(p.price / 1000).toStringAsFixed(0)}K',
                          style: TyType.sans(14,
                              color: ty.ink, weight: FontWeight.w800)),
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
