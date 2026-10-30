import 'package:flutter_test/flutter_test.dart';
import 'package:tyohaar/data/models.dart';
import 'package:tyohaar/screens/plan_flow/plan_logic.dart';
import 'package:tyohaar/utils/currency.dart';

/// These cases are the same numbers the server asserts in
/// server/tests/test_character_lines_and_totals.py — if one side changes its
/// rounding, the other side's test fails too.
void main() {
  group('PlanPricing matches the server', () {
    PlanPricing p({int base = 0, int included = 0, int addOns = 0, int discount = 0, bool gst = true}) =>
        PlanPricing(
          basePaise: base,
          includedPaise: included,
          addOnsPaise: addOns,
          discountPaise: discount,
          gstEnabled: gst,
        );

    test('no tax is charged while the admin has GST off', () {
      final r = p(base: toPaise(10000), discount: toPaise(1000), gst: false);
      expect(r.taxablePaise, 900000);
      expect(r.taxPaise, 0);
      expect(r.totalPaise, 900000);
    });

    test('GST is off unless asked for', () {
      const r = PlanPricing(basePaise: 100000, includedPaise: 0, addOnsPaise: 0, discountPaise: 0);
      expect(r.gstEnabled, isFalse);
      expect(r.totalPaise, 100000);
    });

    test('tax is on the post-discount base', () {
      final r = p(base: toPaise(10000), discount: toPaise(1000));
      expect(r.taxablePaise, 900000);
      expect(r.taxPaise, 162000);
      expect(r.totalPaise, 1062000);
    });

    test('tax rounds half-up to the paisa', () {
      // 0.25 * 18% = 0.045 -> 0.05 (banker's rounding would say 0.04).
      expect(p(base: 25).taxPaise, 5);
    });

    test('an oversized discount cannot make a negative total', () {
      final r = p(base: toPaise(500), discount: toPaise(900));
      expect([r.taxablePaise, r.taxPaise, r.totalPaise], [0, 0, 0]);
    });

    test('paise survive end to end', () {
      final r = p(base: toPaise(1999.99));
      expect(r.taxPaise, 36000);
      expect(r.totalPaise, 235999);
    });

    test('the rows add up to the total', () {
      // base + included + add-ons - discount + GST == total, always.
      final r = p(
          base: toPaise(1000),
          included: toPaise(200),
          addOns: toPaise(250.50),
          discount: toPaise(145.05));
      expect(r.subtotalPaise - r.discountPaise + r.taxPaise, r.totalPaise);
      expect(r.totalPaise, r.taxablePaise + r.taxPaise);
    });

    test('the scenario the booking test uses: 1000 + 2x100 + 250.50', () {
      final r = p(base: toPaise(1000), included: toPaise(200), addOns: toPaise(250.50));
      expect(r.subtotalPaise, 145050);
      expect(r.taxPaise, 26109);
      expect(r.totalPaise, 171159);
    });

    test('a negative discount is ignored', () {
      expect(p(base: 10000, discount: -500).discountPaise, 0);
    });
  });

  group('formatPaise', () {
    test('whole rupees have no decimals, with Indian grouping', () {
      expect(formatPaise(10620000), '₹1,06,200');
    });

    test('paise keep both decimals instead of rounding up', () {
      expect(formatPaise(171159), '₹1,711.59');
      expect(formatPaise(145050), '₹1,450.50');
    });
  });

  group('CharacterFormatter', () {
    TextEditingValue run(String text, {bool digits = true, int max = 20}) =>
        CharacterFormatter(allowDigits: digits, maxChars: max)
            .formatEditUpdate(TextEditingValue.empty, TextEditingValue(text: text));

    test('upper-cases and keeps names and numbers', () {
      expect(run('Anita 30').text, 'ANITA 30');
    });

    test('letters-only drops digits', () {
      expect(run('Anita 30', digits: false).text, 'ANITA ');
    });

    test('collapses spaces and trims the front', () {
      expect(run('   happy    birthday').text, 'HAPPY BIRTHDAY');
    });

    test('symbols and accents are dropped, not ordered', () {
      expect(run('Zoë & Ä!').text, 'ZO ');
    });

    test('the cap counts characters, not spaces', () {
      final v = run('A B C D E F', max: 4).text;
      expect(countBillableCharacters(v), 4);
      expect(v.replaceAll(' ', ''), 'ABCD');
    });

    test('the caret stays at the end', () {
      expect(run('abc').selection.baseOffset, 3);
    });
  });

  group('countBillableCharacters / models', () {
    test('spaces are free', () {
      expect(countBillableCharacters('ANITA 30'), 7);
      expect(countBillableCharacters(null), 0);
      expect(countBillableCharacters('  '), 0);
    });

    test('character_set parses, defaulting to digits', () {
      PackageItem item(Object? cs) => PackageItem.fromJson({
            'id': 'i1',
            'name': 'Foil letters',
            'base_price': '40.00',
            'quantity': 1,
            'is_mandatory': false,
            'is_customizable': true,
            'character_set': cs,
          });
      expect(item('alphanumeric').characterSet, 'alphanumeric');
      expect(item('LETTERS').characterSet, 'letters');
      expect(item(null).characterSet, 'digits');
      expect(item('emoji').characterSet, 'digits');
      expect(item('letters').takesLetters, isTrue);
      expect(item('digits').takesLetters, isFalse);
    });
  });
}
