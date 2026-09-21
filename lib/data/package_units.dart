/// Quantity units for PackageItem / PackageServiceLine lines.
///
/// This mirrors the backend's `PackageUnit` enum
/// (server/app/models/enums.py) and the web portals' PACKAGE_UNIT_OPTIONS
/// (client/src/constants/packageUnits.js) value-for-value. The app was the
/// only surface still accepting free text here, which is how a line priced
/// per *set* in the portal ended up reading as a loose per-piece quantity in
/// the app.
///
/// Canonical values are the plural forms the backend stores. Anything shown
/// to a user goes through [packageUnitPer] or [packageUnitQuantity] so a
/// "sets" line never renders as "each" or "1 sets".
library;

/// A selectable unit: the value written to the API and its display label.
class PackageUnitOption {
  final String value;
  final String label;

  const PackageUnitOption(this.value, this.label);
}

/// The full catalogue, in the same order the portals present it.
const List<PackageUnitOption> kPackageUnitOptions = [
  PackageUnitOption('pieces', 'Pieces'),
  PackageUnitOption('sets', 'Sets'),
  PackageUnitOption('hours', 'Hours'),
  PackageUnitOption('days', 'Days'),
  PackageUnitOption('persons', 'Persons'),
  PackageUnitOption('plates', 'Plates'),
  PackageUnitOption('sq ft', 'Sq. ft.'),
  PackageUnitOption('kg', 'Kg'),
];

/// Singular form per canonical value. Units that do not inflect (`sq ft`,
/// `kg`) map to themselves.
const Map<String, String> _singular = {
  'pieces': 'piece',
  'sets': 'set',
  'hours': 'hour',
  'days': 'day',
  'persons': 'person',
  'plates': 'plate',
  'sq ft': 'sq ft',
  'kg': 'kg',
};

/// Legacy free-text spellings found in existing rows, mapped onto the
/// catalogue. Unit entry was an open TextField in the app before this list
/// existed, so stored values include singulars, abbreviations and casing
/// variants that all mean one of the eight canonical units.
const Map<String, String> _aliases = {
  'piece': 'pieces',
  'pcs': 'pieces',
  'pc': 'pieces',
  'nos': 'pieces',
  'no': 'pieces',
  'unit': 'pieces',
  'units': 'pieces',
  'set': 'sets',
  'hour': 'hours',
  'hr': 'hours',
  'hrs': 'hours',
  'day': 'days',
  'person': 'persons',
  'pax': 'persons',
  'people': 'persons',
  'guest': 'persons',
  'guests': 'persons',
  'plate': 'plates',
  'sqft': 'sq ft',
  'sq.ft': 'sq ft',
  'sq.ft.': 'sq ft',
  'square feet': 'sq ft',
  'kgs': 'kg',
  'kilogram': 'kg',
  'kilograms': 'kg',
};

/// Folds [raw] onto a canonical catalogue value.
///
/// Returns null when [raw] is empty or is not a unit at all — vendors used to
/// type quantities such as "2" into the free-text field, and those must not
/// be echoed back as if they named a unit.
String? canonicalPackageUnit(String? raw) {
  final v = raw?.trim().toLowerCase();
  if (v == null || v.isEmpty) return null;
  if (_singular.containsKey(v)) return v;
  final aliased = _aliases[v];
  if (aliased != null) return aliased;
  // A bare number is leftover bad data, not a unit.
  if (double.tryParse(v) != null) return null;
  return v;
}

/// The value to preselect in a unit dropdown, or null to leave it unset.
/// Only returns a value the dropdown actually offers.
String? packageUnitForPicker(String? raw) {
  final c = canonicalPackageUnit(raw);
  if (c == null) return null;
  return kPackageUnitOptions.any((o) => o.value == c) ? c : null;
}

/// Singular unit for per-unit pricing: "set", "piece", "hour".
/// Falls back to [fallback] when the line carries no usable unit.
String packageUnitSingular(String? raw, {String fallback = 'unit'}) {
  final c = canonicalPackageUnit(raw);
  if (c == null) return fallback;
  return _singular[c] ?? c;
}

/// Unit phrase for a price, e.g. "per set" — never "each", which silently
/// asserts the line is priced per piece.
String packageUnitPer(String? raw, {String fallback = 'unit'}) =>
    'per ${packageUnitSingular(raw, fallback: fallback)}';

/// A quantity with its unit, correctly inflected: "1 set", "3 sets",
/// "2 sq ft". Returns the bare count when no unit is recorded.
String packageUnitQuantity(int quantity, String? raw) {
  final c = canonicalPackageUnit(raw);
  if (c == null) return '$quantity';
  final word = quantity == 1 ? (_singular[c] ?? c) : c;
  return '$quantity $word';
}

/// Display label for a unit on its own, e.g. "Sets".
String packageUnitLabel(String? raw, {String fallback = ''}) {
  final c = canonicalPackageUnit(raw);
  if (c == null) return fallback;
  for (final o in kPackageUnitOptions) {
    if (o.value == c) return o.label;
  }
  return c;
}
