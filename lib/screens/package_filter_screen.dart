import 'package:flutter/material.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../widgets/common.dart';
import '../widgets/ty_button.dart';
import '../widgets/ty_chip.dart';

class PackageFilterScreen extends StatefulWidget {
  const PackageFilterScreen({super.key});

  @override
  State<PackageFilterScreen> createState() => _PackageFilterScreenState();
}

class _PackageFilterScreenState extends State<PackageFilterScreen> {
  RangeValues _priceRange = const RangeValues(5000, 50000);
  String _selectedSort = 'Popularity';
  final List<String> _selectedThemes = [];

  final List<String> _themes = ['Traditional', 'Modern', 'Minimal', 'Luxury', 'Themed', 'Royal'];

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
                  children: ['Popularity', 'Price: Low to High', 'Price: High to Low', 'Newest'].map((s) {
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
                _sectionTitle('Themes'),
                Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  children: _themes.map((t) {
                    final selected = _selectedThemes.contains(t);
                    return TyChip(
                      label: t,
                      active: selected,
                      onTap: () {
                        setState(() {
                          if (selected) {
                            _selectedThemes.remove(t);
                          } else {
                            _selectedThemes.add(t);
                          }
                        });
                      },
                    );
                  }).toList(),
                ),
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
                  child: TyButton('Apply Filters', onTap: () => Navigator.pop(context)),
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
