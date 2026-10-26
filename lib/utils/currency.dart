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

final NumberFormat _inrWhole =
    NumberFormat.currency(locale: 'en_IN', symbol: '₹', decimalDigits: 0);
final NumberFormat _inrPaise =
    NumberFormat.currency(locale: 'en_IN', symbol: '₹', decimalDigits: 2);

/// Formats an amount held in paise (integer hundredths of a rupee). Whole
/// rupees read as "₹1,450"; anything with paise keeps both decimals
/// ("₹1,450.50") so the figure on screen is exactly what is charged, never a
/// rounded-up neighbour of it.
String formatPaise(int paise) =>
    paise % 100 == 0 ? _inrWhole.format(paise ~/ 100) : _inrPaise.format(paise / 100);

/// Like [formatPrice] but never rounds away paise: ₹250.50 stays ₹250.50.
/// Use it wherever an amount is itemised or added up on screen.
String formatRupees(num rupees) => formatPaise((rupees * 100).round());
