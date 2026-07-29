import 'package:flutter/material.dart';
import 'package:dio/dio.dart';

import '../../../theme/colors.dart';
import '../../../theme/typography.dart';
import '../../../theme/responsive.dart';
import '../../../widgets/ty_button.dart';
import '../../../widgets/common.dart';
import '../../../data/services/auth_service.dart';
import '../../../l10n/generated/app_localizations.dart';

/// Two-step OTP reset, mirroring the web vendor portal's
/// VendorForgotPasswordPage (request OTP by email → confirm OTP + new password).
class VendorForgotPasswordScreen extends StatefulWidget {
  const VendorForgotPasswordScreen({super.key});

  @override
  State<VendorForgotPasswordScreen> createState() => _VendorForgotPasswordScreenState();
}

class _VendorForgotPasswordScreenState extends State<VendorForgotPasswordScreen> {
  final _emailCtrl = TextEditingController();
  final _otpCtrl = TextEditingController();
  final _newPasswordCtrl = TextEditingController();
  bool _otpSent = false;
  bool _isLoading = false;
  bool _done = false;
  String _error = '';

  @override
  void dispose() {
    _emailCtrl.dispose();
    _otpCtrl.dispose();
    _newPasswordCtrl.dispose();
    super.dispose();
  }

  Future<void> _requestOtp() async {
    final l10n = AppLocalizations.of(context)!;
    if (_emailCtrl.text.trim().isEmpty) {
      setState(() => _error = l10n.vendorForgotPasswordEnterEmailError);
      return;
    }
    setState(() { _isLoading = true; _error = ''; });
    try {
      await AuthService().requestPasswordResetOtp(_emailCtrl.text.trim());
      if (mounted) setState(() { _otpSent = true; _isLoading = false; });
    } catch (_) {
      if (mounted) setState(() { _isLoading = false; _error = l10n.vendorForgotPasswordSendCodeError; });
    }
  }

  Future<void> _confirmReset() async {
    final l10n = AppLocalizations.of(context)!;
    if (_otpCtrl.text.trim().isEmpty || _newPasswordCtrl.text.isEmpty) {
      setState(() => _error = l10n.vendorForgotPasswordFillAllFieldsError);
      return;
    }
    if (_newPasswordCtrl.text.length < 8) {
      setState(() => _error = l10n.vendorForgotPasswordPasswordTooShortError);
      return;
    }
    setState(() { _isLoading = true; _error = ''; });
    try {
      await AuthService().resetPasswordWithOtp(
        _emailCtrl.text.trim(),
        _otpCtrl.text.trim(),
        _newPasswordCtrl.text,
      );
      if (mounted) setState(() { _done = true; _isLoading = false; });
    } on DioException catch (e) {
      final detail = e.response?.data;
      String msg = l10n.vendorForgotPasswordResetFailedError;
      if (detail is Map) msg = detail['detail'] as String? ?? msg;
      if (mounted) setState(() { _isLoading = false; _error = msg; });
    } catch (_) {
      if (mounted) setState(() { _isLoading = false; _error = l10n.vendorForgotPasswordUnexpectedError; });
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final resp = context.resp;
    final l10n = AppLocalizations.of(context)!;

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: l10n.vendorForgotPasswordTitle),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: EdgeInsets.symmetric(horizontal: resp.w(24), vertical: resp.h(24)),
          child: _done
              ? Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.check_circle_rounded, color: ty.saffron, size: 48),
                    SizedBox(height: resp.h(16)),
                    Text(l10n.vendorForgotPasswordDoneHeading, style: TyType.display(resp.sp(22), color: ty.ink)),
                    SizedBox(height: resp.h(8)),
                    Text(l10n.vendorForgotPasswordDoneMessage, style: TyType.sans(resp.sp(14), color: ty.ink2)),
                    SizedBox(height: resp.h(24)),
                    TyButton(l10n.vendorForgotPasswordBackToLoginLabel, full: true, onTap: () => Navigator.of(context).pop()),
                  ],
                )
              : Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(_otpSent ? l10n.vendorForgotPasswordEnterCodeHeading : l10n.vendorForgotPasswordHeading,
                        style: TyType.display(resp.sp(22), color: ty.ink)),
                    SizedBox(height: resp.h(20)),
                    _field(ty, resp, l10n.vendorForgotPasswordEmailLabel, _emailCtrl, enabled: !_otpSent, type: TextInputType.emailAddress, helperText: l10n.vendorForgotPasswordEmailFormatHelperText),
                    if (_otpSent) ...[
                      SizedBox(height: resp.h(16)),
                      _field(ty, resp, l10n.vendorForgotPasswordOtpCodeLabel, _otpCtrl, type: TextInputType.number, helperText: l10n.vendorForgotPasswordOtpFormatHelperText),
                      SizedBox(height: resp.h(16)),
                      _field(ty, resp, l10n.vendorForgotPasswordNewPasswordLabel, _newPasswordCtrl, obscure: true),
                      SizedBox(height: resp.h(8)),
                      TextButton(
                        onPressed: _isLoading ? null : () => setState(() => _otpSent = false),
                        child: Text(l10n.vendorForgotPasswordChangeEmailLabel),
                      ),
                    ],
                    if (_error.isNotEmpty) ...[
                      SizedBox(height: resp.h(12)),
                      Text(_error, style: TyType.sans(resp.sp(13), color: ty.rose, weight: FontWeight.w600)),
                    ],
                    SizedBox(height: resp.h(24)),
                    TyButton(
                      _isLoading ? l10n.vendorForgotPasswordPleaseWaitLabel : (_otpSent ? l10n.vendorForgotPasswordResetPasswordLabel : l10n.vendorForgotPasswordSendCodeLabel),
                      full: true,
                      onTap: _otpSent ? _confirmReset : _requestOtp,
                      enabled: !_isLoading,
                    ),
                  ],
                ),
        ),
      ),
    );
  }

  Widget _field(TyColors ty, TyResponsive resp, String label, TextEditingController ctrl,
      {TextInputType type = TextInputType.text, bool obscure = false, bool enabled = true, String? helperText}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: TyType.eyebrow(resp.sp(11), color: ty.ink3)),
        SizedBox(height: resp.h(8)),
        Container(
          padding: EdgeInsets.symmetric(horizontal: resp.w(16)),
          decoration: BoxDecoration(
            color: ty.surface,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: ty.line),
          ),
          child: TextField(
            controller: ctrl,
            keyboardType: type,
            obscureText: obscure,
            enabled: enabled,
            style: TyType.sans(resp.sp(15), color: ty.ink),
            decoration: const InputDecoration(border: InputBorder.none, isDense: true, contentPadding: EdgeInsets.symmetric(vertical: 14)),
          ),
        ),
        if (helperText != null) ...[
          SizedBox(height: resp.h(4)),
          Text(helperText, style: TyType.sans(resp.sp(11), color: ty.ink3)),
        ],
      ],
    );
  }
}
