import 'package:flutter/material.dart';
import '../data/models.dart';
import '../data/services/package_service.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../widgets/common.dart';
import '../widgets/ty_button.dart';
import '../widgets/ty_chip.dart';

class PackageFilterScreen extends StatefulWidget {
  const PackageFilterScreen({
    super.key,
    this.initialSort,
    this.initialPriceRange,
    this.initialThemes,
  });

  final String? initialSort;
  final RangeValues? initialPriceRange;
  final List<String>? initialThemes;

  @override
  State<PackageFilterScreen> createState() => _PackageFilterScreenState();
}

class _PackageFilterScreenState extends State<PackageFilterScreen> {
  late RangeValues _priceRange = widget.initialPriceRange ?? const RangeValues(5000, 50000);
  late String _selectedSort = widget.initialSort ?? 'Popularity';
  late final List<String> _selectedThemes = List<String>.from(widget.initialThemes ?? []);

  // Themes are fetched from the same backend entity (OccasionTheme, via
  // PackageService.listThemes()) that Package.themeIds correlates to — the
  // chip's underlying id is what's actually matched against packages.
  final PackageService _packageService = PackageService();
  List<CelebrationTheme> _themes = [];

  @override
  void initState() {
    super.initState();
    _loadThemes();
  }

  Future<void> _loadThemes() async {
    try {
      final themes = await _packageService.listThemes();
      if (mounted) setState(() => _themes = themes);
    } catch (_) {
      // Non-fatal — the Themes section simply renders no chips if the
      // catalog fails to load, matching this screen's other filters still
      // being usable.
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return Scaffold(
      appBar: tyAppBar(context, title: 'Filter Packages'),
      body: Column(
        children: [
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(20),
              children: [
                _sectionTitle('Sort By'),
                Wrap(
                  spacing: 10,
                  children: ['Popularity', 'Price: Low to High', 'Price: High to Low'].map((s) {
                    return TyChip(
                      label: s,
                      active: _selectedSort == s,
                      onTap: () => setState(() => _selectedSort = s),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 32),
                _sectionTitle('Price Range (₹)'),
                RangeSlider(
                  values: _priceRange,
                  min: 0,
                  max: 100000,
                  divisions: 20,
                  activeColor: ty.saffron,
                  inactiveColor: ty.saffronSoft,
                  labels: RangeLabels(
                    '₹${(_priceRange.start / 1000).round()}K',
                    '₹${(_priceRange.end / 1000).round()}K',
                  ),
                  onChanged: (v) => setState(() => _priceRange = v),
                ),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('₹0', style: TyType.sans(12, color: ty.ink3)),
                    Text('₹100K+', style: TyType.sans(12, color: ty.ink3)),
                  ],
                ),
                const SizedBox(height: 32),
                if (_themes.isNotEmpty) ...[
                  _sectionTitle('Themes'),
                  Wrap(
                    spacing: 10,
                    runSpacing: 10,
                    children: _themes.map((t) {
                      final selected = _selectedThemes.contains(t.id);
                      return TyChip(
                        label: t.name,
                        active: selected,
                        onTap: () {
                          setState(() {
                            if (selected) {
                              _selectedThemes.remove(t.id);
                            } else {
                              _selectedThemes.add(t.id);
                            }
                          });
                        },
                      );
                    }).toList(),
                  ),
                ],
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(20),
            child: Row(
              children: [
                Expanded(
                  child: TyButton('Reset', kind: TyButtonKind.ghost, onTap: () {
                    setState(() {
                      _priceRange = const RangeValues(5000, 50000);
                      _selectedSort = 'Popularity';
                      _selectedThemes.clear();
                    });
                  }),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: TyButton('Apply Filters', onTap: () => Navigator.pop(context, {
                    'sort': _selectedSort,
                    'priceRange': _priceRange,
                    'themes': List<String>.from(_selectedThemes),
                  })),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _sectionTitle(String title) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Text(title, style: TyType.sans(16, color: context.ty.ink, weight: FontWeight.w700)),
    );
  }
}
