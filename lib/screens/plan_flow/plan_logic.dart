import 'package:flutter/services.dart';

/// Rupees (as the API sends them) to integer paise.
int toPaise(num rupees) => (rupees * 100).round();

/// Every amount the customer is shown, in integer paise so nothing drifts
/// between rows and total. Mirrors the server's booking maths exactly:
/// tax is 18% of (subtotal - discount), rounded half-up to the paisa, and the
/// discount can never exceed the subtotal.
class PlanPricing {
  final int basePaise;
  final int includedPaise;
  final int addOnsPaise;
  final int discountPaise;

  const PlanPricing({
    required this.basePaise,
    required this.includedPaise,
    required this.addOnsPaise,
    required int discountPaise,
  }) : discountPaise = discountPaise < 0 ? 0 : discountPaise;

  int get subtotalPaise => basePaise + includedPaise + addOnsPaise;
  int get _clampedDiscount => discountPaise > subtotalPaise ? subtotalPaise : discountPaise;
  int get taxablePaise => subtotalPaise - _clampedDiscount;
  int get taxPaise => (taxablePaise * 18 + 50) ~/ 100;
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
