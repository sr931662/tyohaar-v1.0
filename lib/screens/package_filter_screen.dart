import 'package:flutter/material.dart';
import '../l10n/generated/app_localizations.dart';
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
  });

  final String? initialSort;
  final RangeValues? initialPriceRange;

  @override
  State<PackageFilterScreen> createState() => _PackageFilterScreenState();
}

class _PackageFilterScreenState extends State<PackageFilterScreen> {
  late RangeValues _priceRange = widget.initialPriceRange ?? const RangeValues(5000, 50000);
  late String _selectedSort = widget.initialSort ?? 'Popularity';

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    // Internal sort values are kept in English and match ExploreScreen's
    // switch statement (which consumes the value returned via Navigator.pop)
    // — only the displayed chip label is localized.
    final sortOptions = <String, String>{
      'Popularity': l10n.packageFilterSortPopularity,
      'Price: Low to High': l10n.packageFilterSortPriceLowToHigh,
      'Price: High to Low': l10n.packageFilterSortPriceHighToLow,
    };
    return Scaffold(
      appBar: tyAppBar(context, title: l10n.packageFilterTitle),
      body: Column(
        children: [
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(20),
              children: [
                _sectionTitle(context, l10n.packageFilterSortByLabel),
                Wrap(
                  spacing: 10,
                  children: sortOptions.entries.map((e) {
                    return TyChip(
                      label: e.value,
                      active: _selectedSort == e.key,
                      onTap: () => setState(() => _selectedSort = e.key),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 32),
                _sectionTitle(context, l10n.packageFilterPriceRangeLabel),
                RangeSlider(
                  values: _priceRange,
                  min: 0,
                  max: 100000,
                  divisions: 20,
                  activeColor: ty.saffron,
                  inactiveColor: ty.saffronSoft,
                  labels: RangeLabels(
                    l10n.packageFilterPriceKLabel('${(_priceRange.start / 1000).round()}'),
                    l10n.packageFilterPriceKLabel('${(_priceRange.end / 1000).round()}'),
                  ),
                  onChanged: (v) => setState(() => _priceRange = v),
                ),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(l10n.packageFilterPriceMinLabel, style: TyType.sans(12, color: ty.ink3)),
                    Text(l10n.packageFilterPriceMaxLabel, style: TyType.sans(12, color: ty.ink3)),
                  ],
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(20),
            child: Row(
              children: [
                Expanded(
                  child: TyButton(l10n.packageFilterResetButtonLabel, kind: TyButtonKind.ghost, onTap: () {
                    setState(() {
                      _priceRange = const RangeValues(5000, 50000);
                      _selectedSort = 'Popularity';
                    });
                  }),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: TyButton(l10n.packageFilterApplyButtonLabel, onTap: () => Navigator.pop(context, {
                    'sort': _selectedSort,
                    'priceRange': _priceRange,
                  })),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _sectionTitle(BuildContext context, String title) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Text(title, style: TyType.sans(16, color: context.ty.ink, weight: FontWeight.w700)),
    );
  }
}
