import 'package:flutter_test/flutter_test.dart';
import 'package:tyohaar/data/package_units.dart';

void main() {
  group('canonicalPackageUnit', () {
    test('passes catalogue values through', () {
      expect(canonicalPackageUnit('sets'), 'sets');
      expect(canonicalPackageUnit('sq ft'), 'sq ft');
    });

    test('folds legacy free-text spellings onto the catalogue', () {
      expect(canonicalPackageUnit('set'), 'sets');
      expect(canonicalPackageUnit('Set'), 'sets');
      expect(canonicalPackageUnit('  SETS '), 'sets');
      expect(canonicalPackageUnit('pcs'), 'pieces');
      expect(canonicalPackageUnit('pax'), 'persons');
      expect(canonicalPackageUnit('sqft'), 'sq ft');
    });

    test('rejects values that are not units', () {
      // Free-text entry let vendors type a quantity into the unit field;
      // those rows must not render as though "2" named a unit.
      expect(canonicalPackageUnit('2'), isNull);
      expect(canonicalPackageUnit(''), isNull);
      expect(canonicalPackageUnit('   '), isNull);
      expect(canonicalPackageUnit(null), isNull);
    });
  });

  group('packageUnitPer', () {
    test('says what a set-priced line is actually priced per', () {
      expect(packageUnitPer('sets'), 'per set');
      expect(packageUnitPer('set'), 'per set');
    });

    test('covers the rest of the catalogue', () {
      expect(packageUnitPer('pieces'), 'per piece');
      expect(packageUnitPer('hours'), 'per hour');
      expect(packageUnitPer('persons'), 'per person');
      expect(packageUnitPer('kg'), 'per kg');
      expect(packageUnitPer('sq ft'), 'per sq ft');
    });

    test('falls back when the line records no usable unit', () {
      expect(packageUnitPer(null), 'per unit');
      expect(packageUnitPer('2'), 'per unit');
    });
  });

  group('packageUnitQuantity', () {
    test('inflects to match the count', () {
      expect(packageUnitQuantity(1, 'sets'), '1 set');
      expect(packageUnitQuantity(3, 'sets'), '3 sets');
      expect(packageUnitQuantity(1, 'pieces'), '1 piece');
      expect(packageUnitQuantity(2, 'pieces'), '2 pieces');
    });

    test('leaves non-inflecting units alone', () {
      expect(packageUnitQuantity(1, 'kg'), '1 kg');
      expect(packageUnitQuantity(5, 'sq ft'), '5 sq ft');
    });

    test('drops to a bare count with no unit', () {
      expect(packageUnitQuantity(4, null), '4');
    });
  });

  group('packageUnitForPicker', () {
    test('only preselects values the dropdown offers', () {
      expect(packageUnitForPicker('set'), 'sets');
      expect(packageUnitForPicker('sets'), 'sets');
      // Unknown legacy text has no dropdown entry, so the picker starts
      // empty and re-saving the line cleans the row up.
      expect(packageUnitForPicker('bundles'), isNull);
      expect(packageUnitForPicker('2'), isNull);
      expect(packageUnitForPicker(null), isNull);
    });

    test('offers exactly the backend PackageUnit catalogue', () {
      expect(
        kPackageUnitOptions.map((o) => o.value).toList(),
        ['pieces', 'sets', 'hours', 'days', 'persons', 'plates', 'sq ft', 'kg'],
      );
    });
  });
}
