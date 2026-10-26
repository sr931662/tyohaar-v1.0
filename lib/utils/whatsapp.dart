/// Builds the digits-only international number `wa.me` expects, or null if
/// [phone] can't be a real number.
///
/// wa.me wants "919876543210": no '+', spaces, dashes or leading zeros. Guests
/// are usually typed in as local numbers, so a bare 10-digit number (or one
/// with the 0 trunk prefix) gets [defaultCountryCode] — Tyohaar serves India.
/// A number that already carries '+' or '00' is trusted as international.
String? whatsAppNumber(String? phone, {String defaultCountryCode = '91'}) {
  final raw = (phone ?? '').trim();
  var digits = raw.replaceAll(RegExp(r'[^0-9]'), '');
  if (digits.isEmpty) return null;

  if (!raw.startsWith('+')) {
    if (digits.startsWith('00')) {
      digits = digits.substring(2);
    } else {
      digits = digits.replaceFirst(RegExp(r'^0+'), '');
      if (digits.length == 10) digits = '$defaultCountryCode$digits';
    }
  }
  return digits.length >= 8 && digits.length <= 15 ? digits : null;
}

/// A chat link with [message] pre-filled; opens a number picker when [phone]
/// is unusable. Returns a URI for url_launcher's external-application mode.
Uri whatsAppLink(String? phone, String message) {
  final number = whatsAppNumber(phone);
  final text = Uri.encodeComponent(message);
  return Uri.parse(
      number == null ? 'https://wa.me/?text=$text' : 'https://wa.me/$number?text=$text');
}
