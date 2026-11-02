import 'package:flutter/services.dart';

/// Rupees (as the API sends them) to integer paise.
int toPaise(num rupees) => (rupees * 100).round();

/// Every amount the customer is shown, in integer paise so nothing drifts
/// between rows and total. Mirrors the server's booking maths exactly:
/// tax is 18% of (subtotal - discount), rounded half-up to the paisa, and the
/// discount can never exceed the subtotal. Tax is only charged while the admin
/// has GST switched on ([gstEnabled]); with it off the total is the taxable
/// amount.
class PlanPricing {
  final int basePaise;
  final int includedPaise;
  final int addOnsPaise;
  final int discountPaise;
  final bool gstEnabled;

  const PlanPricing({
    required this.basePaise,
    required this.includedPaise,
    required this.addOnsPaise,
    required int discountPaise,
    this.gstEnabled = false,
  }) : discountPaise = discountPaise < 0 ? 0 : discountPaise;

  int get subtotalPaise => basePaise + includedPaise + addOnsPaise;
  int get _clampedDiscount => discountPaise > subtotalPaise ? subtotalPaise : discountPaise;
  int get taxablePaise => subtotalPaise - _clampedDiscount;
  int get taxPaise => gstEnabled ? (taxablePaise * 18 + 50) ~/ 100 : 0;
  int get totalPaise => taxablePaise + taxPaise;
}

/// Keeps only what a customisable line may contain: upper-case A-Z when
/// [allowLetters], 0-9 when [allowDigits], single spaces between words when
/// [allowSpaces], at most [maxChars] billable characters. Mirrors the server's
/// normalisation, so what is shown is what is stored and billed.
class CharacterFormatter extends TextInputFormatter {
  final bool allowLetters;
  final bool allowDigits;
  final bool allowSpaces;
  final int maxChars;
  const CharacterFormatter({
    this.allowLetters = true,
    required this.allowDigits,
    this.allowSpaces = true,
    required this.maxChars,
  });

  @override
  TextEditingValue formatEditUpdate(TextEditingValue oldValue, TextEditingValue newValue) {
    final out = StringBuffer();
    var count = 0;
    var lastWasSpace = true; // no leading space
    for (final ch in newValue.text.toUpperCase().split('')) {
      if (ch.trim().isEmpty) {
        if (allowSpaces && !lastWasSpace) {
          out.write(' ');
          lastWasSpace = true;
        }
        continue;
      }
      final unit = ch.codeUnitAt(0);
      final isLetter = ch.length == 1 && unit >= 0x41 && unit <= 0x5A;
      final isDigit = ch.length == 1 && unit >= 0x30 && unit <= 0x39;
      if (!((allowLetters && isLetter) || (allowDigits && isDigit))) continue;
      if (count >= maxChars) break;
      out.write(ch);
      count++;
      lastWasSpace = false;
    }
    final text = out.toString();
    return TextEditingValue(text: text, selection: TextSelection.collapsed(offset: text.length));
  }
}

// ── Balloon colour proportions ───────────────────────────────────────────────
//
// A customer with 2-4 balloon colours can say how much of each they want. The
// bars move in steps of [kBalloonRatioStep]%, no colour goes below
// [kBalloonRatioMin]%, and the LAST colour is never set directly: it is always
// whatever is left, so the mix adds up to 100 by construction. The server
// enforces the same rules (BookingCreate.validate_balloon_colors).

const int kBalloonRatioStep = 5;
const int kBalloonRatioMin = 5;

/// An even starting mix: 2 -> [50, 50], 3 -> [30, 30, 40], 4 -> [25 x 4].
/// Fewer than two colours have nothing to proportion.
List<int> evenBalloonProportions(int count) {
  if (count < 2) return const [];
  final share = (100 ~/ count) ~/ kBalloonRatioStep * kBalloonRatioStep;
  return [for (var i = 0; i < count - 1; i++) share, 100 - share * (count - 1)];
}

/// The highest value colour [index] may take while every other adjustable
/// colour keeps its share and the last colour keeps at least the minimum.
int maxBalloonProportion(List<int> ratios, int index) {
  var others = 0;
  for (var i = 0; i < ratios.length - 1; i++) {
    if (i != index) others += ratios[i];
  }
  return 100 - others - kBalloonRatioMin;
}

/// [ratios] with colour [index] set to [value] (snapped to the step and
/// clamped), and the last colour recomputed as the remainder. Asking to set
/// the last colour, or an index out of range, returns [ratios] unchanged.
List<int> setBalloonProportion(List<int> ratios, int index, int value) {
  if (ratios.length < 2 || index < 0 || index >= ratios.length - 1) return ratios;
  final snapped = ((value / kBalloonRatioStep).round() * kBalloonRatioStep)
      .clamp(kBalloonRatioMin, maxBalloonProportion(ratios, index));
  final next = List<int>.of(ratios)..[index] = snapped;
  var used = 0;
  for (var i = 0; i < next.length - 1; i++) {
    used += next[i];
  }
  next[next.length - 1] = 100 - used;
  return next;
}
