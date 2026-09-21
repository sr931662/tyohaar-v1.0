import 'package:flutter/material.dart';

import '../data/package_units.dart';

/// Unit picker for a package item / service line.
///
/// Replaces the free-text field the vendor screens used to carry. The backend
/// constrains `unit` to its `PackageUnit` enum and both web portals have
/// always presented a dropdown, so free text here produced values the rest of
/// the stack could not price or pluralise — most visibly a "sets" line
/// reading as loose pieces in the customer app.
///
/// A line saved before the catalogue existed may hold a value outside it
/// (e.g. "pcs", or a stray quantity). [PackageUnitField] folds what it can
/// onto a catalogue value via [packageUnitForPicker] and otherwise starts
/// empty, so re-saving the line cleans the row up.
class PackageUnitField extends StatelessWidget {
  final String? value;
  final ValueChanged<String?> onChanged;
  final String labelText;
  final String? helperText;

  const PackageUnitField({
    super.key,
    required this.value,
    required this.onChanged,
    required this.labelText,
    this.helperText,
  });

  @override
  Widget build(BuildContext context) {
    return DropdownButtonFormField<String>(
      initialValue: packageUnitForPicker(value),
      isExpanded: true,
      decoration: InputDecoration(labelText: labelText, helperText: helperText),
      items: kPackageUnitOptions
          .map((o) => DropdownMenuItem(value: o.value, child: Text(o.label)))
          .toList(),
      onChanged: onChanged,
    );
  }
}
