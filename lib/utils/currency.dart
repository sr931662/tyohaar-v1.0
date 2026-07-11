import 'package:intl/intl.dart';

/// Full-precision Indian Rupee formatter — no "k"/"L" abbreviation.
/// Customers must always see the actual price they'll pay.
final NumberFormat _inr = NumberFormat.currency(
  locale: 'en_IN',
  symbol: '₹',
  decimalDigits: 0,
);

/// Formats [amount] as "₹1,50,000" (Indian digit grouping, no decimals).
String formatPrice(num amount) => _inr.format(amount);

/// Same as [formatPrice] but without the currency symbol, e.g. "1,50,000".
String formatAmount(num amount) => NumberFormat.decimalPattern('en_IN').format(amount);
