/// What a person typed into the single "mobile number or email" sign-in box.
///
/// One field instead of two tabs: anything with an '@' is an email, anything
/// else is read as an Indian mobile number and normalised to E.164 (+91…),
/// which is the only phone format the server accepts.
enum SignInKind { email, phone, invalid }

class SignInIdentifier {
  final SignInKind kind;

  /// The value to send to the server: a lower-cased email or a +91 number.
  final String value;

  const SignInIdentifier._(this.kind, this.value);

  static const invalid = SignInIdentifier._(SignInKind.invalid, '');

  bool get isEmail => kind == SignInKind.email;
  bool get isPhone => kind == SignInKind.phone;
  bool get isValid => kind != SignInKind.invalid;

  /// The OTP delivery channel the server expects for this identifier.
  String get channel => isEmail ? 'email' : 'sms';

  /// "+91 98765 43210" for display; emails unchanged.
  String get display => isPhone ? '+91 ${value.substring(3, 8)} ${value.substring(8)}' : value;

  static final RegExp _email = RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]{2,}$');
  static final RegExp _indianMobile = RegExp(r'^[6-9]\d{9}$');

  static SignInIdentifier parse(String raw) {
    final text = raw.trim();
    if (text.isEmpty) return invalid;
    if (text.contains('@')) {
      final email = text.toLowerCase();
      return _email.hasMatch(email) ? SignInIdentifier._(SignInKind.email, email) : invalid;
    }
    var digits = text.replaceAll(RegExp(r'[\s\-().]'), '');
    if (digits.startsWith('+91')) {
      digits = digits.substring(3);
    } else if (digits.startsWith('0091')) {
      digits = digits.substring(4);
    } else if (digits.length == 12 && digits.startsWith('91')) {
      digits = digits.substring(2);
    } else if (digits.length == 11 && digits.startsWith('0')) {
      digits = digits.substring(1);
    }
    return _indianMobile.hasMatch(digits) ? SignInIdentifier._(SignInKind.phone, '+91$digits') : invalid;
  }
}
