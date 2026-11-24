import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../../data/services/auth_service.dart';
import '../../data/sign_in_identifier.dart';
import '../../l10n/generated/app_localizations.dart';
import '../../theme/colors.dart';
import '../../theme/responsive.dart';
import '../../theme/typography.dart';
import '../../widgets/ty_button.dart';

/// Sign in or sign up with a one-time code, in two short steps:
///
///  1. type a mobile number or an email address (one box, either works);
///  2. type the 6-digit code that arrives by SMS / email, and as a push
///     notification on any device already signed in to that account.
///
/// There is no separate "register" path: a first sign-in creates the account,
/// already verified, because receiving the code proves the number or address
/// is the person's own.
class CodeSignInPanel extends StatefulWidget {
  final bool phoneEnabled;
  final bool emailEnabled;
  final Future<void> Function(CodeSignInResult result) onSignedIn;

  const CodeSignInPanel({
    super.key,
    required this.onSignedIn,
    this.phoneEnabled = true,
    this.emailEnabled = true,
  });

  @override
  State<CodeSignInPanel> createState() => _CodeSignInPanelState();
}

class _CodeSignInPanelState extends State<CodeSignInPanel> {
  static const _resendSeconds = 30;

  final _phoneCtrl = TextEditingController();
  final _emailCtrl = TextEditingController();
  final _codeCtrl = TextEditingController();
  final _codeFocus = FocusNode();

  // Mobile and email are separate tabs so each gets the right keyboard: a
  // number pad for a phone number, the '@' keyboard only for an email. One
  // shared box forced the email keyboard on everybody.
  late bool _mobileMode = widget.phoneEnabled;
  bool _modeChosenByUser = false;

  SignInIdentifier? _sentTo;
  bool _busy = false;
  String _error = '';
  int _cooldown = 0;
  Timer? _timer;

  @override
  void didUpdateWidget(CodeSignInPanel old) {
    super.didUpdateWidget(old);
    // Provider config arrives after first paint. Once mobile sign-in turns out
    // to be available, lead with it, unless the person already picked a tab.
    if (!old.phoneEnabled && widget.phoneEnabled && !_modeChosenByUser && _sentTo == null) {
      setState(() => _mobileMode = true);
    }
    if (old.phoneEnabled && !widget.phoneEnabled && _mobileMode) {
      setState(() => _mobileMode = false);
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    _phoneCtrl.dispose();
    _emailCtrl.dispose();
    _codeCtrl.dispose();
    _codeFocus.dispose();
    super.dispose();
  }

  void _startCooldown() {
    _timer?.cancel();
    setState(() => _cooldown = _resendSeconds);
    _timer = Timer.periodic(const Duration(seconds: 1), (t) {
      if (!mounted) return t.cancel();
      setState(() => _cooldown--);
      if (_cooldown <= 0) t.cancel();
    });
  }

  SignInIdentifier _typed() => SignInIdentifier.parse(_mobileMode ? _phoneCtrl.text : _emailCtrl.text);

  String? _validate(SignInIdentifier id) {
    final l10n = AppLocalizations.of(context)!;
    if (_mobileMode) {
      if (!widget.phoneEnabled) return l10n.codeSignInPhoneUnavailable;
      if (!id.isPhone) return l10n.codeSignInPhoneIncomplete;
    } else {
      if (!widget.emailEnabled) return l10n.codeSignInEmailUnavailable;
      if (!id.isEmail) return l10n.codeSignInEmailInvalid;
    }
    return null;
  }

  Future<void> _send({bool resend = false}) async {
    if (_busy) return;
    final id = resend ? _sentTo! : _typed();
    final problem = resend ? null : _validate(id);
    if (problem != null) {
      setState(() => _error = problem);
      return;
    }
    // Put the keyboard away: the next screen is the code step, which brings up
    // its own number pad, and on failure the message must not stay hidden
    // behind a keyboard that never went down.
    FocusScope.of(context).unfocus();
    setState(() { _busy = true; _error = ''; });
    try {
      await context.read<AuthService>().requestSignInCode(id);
      if (!mounted) return;
      setState(() { _sentTo = id; _busy = false; });
      _codeCtrl.clear();
      _startCooldown();
      _codeFocus.requestFocus();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _error = authErrorMessage(e, AppLocalizations.of(context)!.codeSignInSendFailed);
      });
    }
  }

  Future<void> _verify() async {
    final code = _codeCtrl.text.trim();
    if (_busy || _sentTo == null) return;
    if (code.length != 6) {
      setState(() => _error = AppLocalizations.of(context)!.codeSignInEnterCode);
      return;
    }
    FocusScope.of(context).unfocus();
    setState(() { _busy = true; _error = ''; });
    try {
      final result = await context.read<AuthService>().verifySignInCode(_sentTo!, code);
      if (!mounted) return;
      await widget.onSignedIn(result);
      if (mounted) setState(() => _busy = false);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _error = authErrorMessage(e, AppLocalizations.of(context)!.codeSignInVerifyFailed);
        _codeCtrl.clear();
      });
      _codeFocus.requestFocus();
    }
  }

  void _changeIdentifier() {
    _timer?.cancel();
    setState(() { _sentTo = null; _error = ''; _cooldown = 0; _codeCtrl.clear(); });
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 200),
      child: _sentTo == null ? _identifierStep(context) : _codeStep(context),
    );
  }

  Widget _identifierStep(BuildContext context) {
    final ty = context.ty;
    final resp = context.resp;
    final l10n = AppLocalizations.of(context)!;
    return Column(
      key: const ValueKey('identifier'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _modeTabs(context),
        SizedBox(height: resp.h(16)),
        _box(
          context,
          child: _mobileMode
              ? TextField(
                  key: const ValueKey('phone-field'),
                  controller: _phoneCtrl,
                  keyboardType: TextInputType.phone,
                  autofillHints: const [AutofillHints.telephoneNumberNational],
                  inputFormatters: [FilteringTextInputFormatter.digitsOnly, LengthLimitingTextInputFormatter(10)],
                  textInputAction: TextInputAction.done,
                  onSubmitted: (_) => _send(),
                  onTapOutside: (_) => FocusScope.of(context).unfocus(),
                  onChanged: (_) => _error.isEmpty ? null : setState(() => _error = ''),
                  style: TyType.sans(resp.sp(16), color: ty.ink, weight: FontWeight.w600).copyWith(letterSpacing: 0.6),
                  decoration: _decoration(context, l10n.codeSignInMobileHint, Icons.phone_iphone_rounded).copyWith(
                    prefixText: '+91  ',
                    prefixStyle: TyType.sans(resp.sp(16), color: ty.ink2, weight: FontWeight.w700),
                  ),
                )
              : TextField(
                  key: const ValueKey('email-field'),
                  controller: _emailCtrl,
                  keyboardType: TextInputType.emailAddress,
                  autofillHints: const [AutofillHints.email],
                  autocorrect: false,
                  enableSuggestions: false,
                  textInputAction: TextInputAction.done,
                  onSubmitted: (_) => _send(),
                  onTapOutside: (_) => FocusScope.of(context).unfocus(),
                  onChanged: (_) => _error.isEmpty ? null : setState(() => _error = ''),
                  style: TyType.sans(resp.sp(16), color: ty.ink, weight: FontWeight.w600),
                  decoration: _decoration(context, l10n.codeSignInEmailHint, Icons.alternate_email_rounded),
                ),
        ),
        SizedBox(height: resp.h(6)),
        Text(_mobileMode ? l10n.codeSignInMobileHelp : l10n.codeSignInEmailHelp,
            style: TyType.sans(resp.sp(11.5), color: ty.ink3)),
        if (_error.isNotEmpty) _errorText(context),
        SizedBox(height: resp.h(22)),
        TyButton(
          _busy ? l10n.codeSignInSending : l10n.codeSignInSendCode,
          full: true,
          onTap: _send,
          enabled: !_busy,
        ),
      ],
    );
  }

  Widget _modeTabs(BuildContext context) {
    final ty = context.ty;
    final resp = context.resp;
    final l10n = AppLocalizations.of(context)!;

    Widget tab(String label, bool selected, VoidCallback onTap, {bool soon = false}) {
      return Expanded(
        child: GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTap: onTap,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 180),
            padding: EdgeInsets.symmetric(vertical: resp.h(11)),
            decoration: BoxDecoration(
              color: selected ? ty.saffron : Colors.transparent,
              borderRadius: BorderRadius.circular(12),
            ),
            alignment: Alignment.center,
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(label,
                    style: TyType.sans(resp.sp(14),
                        color: selected ? ty.onPrimary : (soon ? ty.ink3 : ty.ink2), weight: FontWeight.w700)),
                if (soon) ...[
                  SizedBox(width: resp.w(6)),
                  Container(
                    padding: EdgeInsets.symmetric(horizontal: resp.w(6), vertical: resp.h(2)),
                    decoration: BoxDecoration(color: ty.surface2, borderRadius: BorderRadius.circular(6)),
                    child: Text(l10n.codeSignInSoonBadge,
                        style: TyType.sans(resp.sp(10), color: ty.ink3, weight: FontWeight.w700)),
                  ),
                ],
              ],
            ),
          ),
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: ty.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: ty.line),
      ),
      child: Row(
        children: [
          tab(l10n.codeSignInTabMobile, _mobileMode, () {
            if (!widget.phoneEnabled) {
              // Not deliverable yet: say so up front instead of letting
              // someone type a whole number to be told it cannot work.
              setState(() => _error = l10n.codeSignInPhoneUnavailable);
              return;
            }
            _modeChosenByUser = true;
            setState(() { _mobileMode = true; _error = ''; });
          }, soon: !widget.phoneEnabled),
          tab(l10n.codeSignInTabEmail, !_mobileMode, () {
            _modeChosenByUser = true;
            setState(() { _mobileMode = false; _error = ''; });
          }),
        ],
      ),
    );
  }

  Widget _codeStep(BuildContext context) {
    final ty = context.ty;
    final resp = context.resp;
    final l10n = AppLocalizations.of(context)!;
    final sentTo = _sentTo!;
    return Column(
      key: const ValueKey('code'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(l10n.codeSignInCodeSentTo(sentTo.display),
            style: TyType.sans(resp.sp(14.5), color: ty.ink, weight: FontWeight.w600)),
        TextButton(
          onPressed: _busy ? null : _changeIdentifier,
          style: TextButton.styleFrom(padding: EdgeInsets.zero, minimumSize: const Size(0, 32)),
          child: Text(l10n.codeSignInChange,
              style: TyType.sans(resp.sp(13), color: ty.saffronDeep, weight: FontWeight.w700)),
        ),
        SizedBox(height: resp.h(8)),
        _box(
          context,
          child: TextField(
            controller: _codeCtrl,
            focusNode: _codeFocus,
            keyboardType: TextInputType.number,
            autofillHints: const [AutofillHints.oneTimeCode],
            inputFormatters: [FilteringTextInputFormatter.digitsOnly, LengthLimitingTextInputFormatter(6)],
            textAlign: TextAlign.center,
            onChanged: (v) {
              if (_error.isNotEmpty) setState(() => _error = '');
              if (v.length == 6) _verify(); // no extra tap once the code is in
            },
            style: TyType.sans(resp.sp(26), color: ty.ink, weight: FontWeight.w800)
                .copyWith(letterSpacing: 10),
            decoration: _decoration(context, '••••••', null),
          ),
        ),
        SizedBox(height: resp.h(8)),
        Row(children: [
          Icon(Icons.notifications_active_outlined, size: resp.w(16), color: ty.ink3),
          SizedBox(width: resp.w(6)),
          Expanded(
            child: Text(l10n.codeSignInPushHint, style: TyType.sans(resp.sp(11.5), color: ty.ink3)),
          ),
        ]),
        if (_error.isNotEmpty) _errorText(context),
        SizedBox(height: resp.h(22)),
        TyButton(
          _busy ? l10n.codeSignInVerifying : l10n.codeSignInVerify,
          full: true,
          onTap: _verify,
          enabled: !_busy,
        ),
        SizedBox(height: resp.h(8)),
        Center(
          child: TextButton(
            onPressed: _busy || _cooldown > 0 ? null : () => _send(resend: true),
            child: Text(
              _cooldown > 0 ? l10n.codeSignInResendIn(_cooldown) : l10n.codeSignInResend,
              style: TyType.sans(resp.sp(13), color: _cooldown > 0 ? ty.ink3 : ty.saffronDeep, weight: FontWeight.w600),
            ),
          ),
        ),
      ],
    );
  }

  Widget _errorText(BuildContext context) => Padding(
        padding: EdgeInsets.only(top: context.resp.h(12)),
        child: Text(_error, style: TyType.sans(context.resp.sp(13), color: context.ty.rose, weight: FontWeight.w600)),
      );

  Widget _box(BuildContext context, {required Widget child}) {
    final ty = context.ty;
    final resp = context.resp;
    return Container(
      padding: EdgeInsets.symmetric(horizontal: resp.w(16), vertical: resp.h(8)),
      decoration: BoxDecoration(
        color: ty.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: ty.line),
      ),
      child: child,
    );
  }

  InputDecoration _decoration(BuildContext context, String hint, IconData? icon) {
    final ty = context.ty;
    final resp = context.resp;
    return InputDecoration(
      hintText: hint,
      hintStyle: TyType.sans(resp.sp(16), color: ty.ink3.withValues(alpha: 0.5)),
      border: InputBorder.none,
      isDense: true,
      counterText: '',
      prefixIcon: icon == null ? null : Icon(icon, size: resp.w(20), color: ty.ink3),
      prefixIconConstraints: BoxConstraints(minWidth: resp.w(32)),
      contentPadding: EdgeInsets.symmetric(vertical: resp.h(10)),
    );
  }
}
