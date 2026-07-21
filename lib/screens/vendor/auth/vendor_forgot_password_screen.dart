import 'package:flutter/material.dart';
import 'package:dio/dio.dart';

import '../../../theme/colors.dart';
import '../../../theme/typography.dart';
import '../../../theme/responsive.dart';
import '../../../widgets/ty_button.dart';
import '../../../widgets/common.dart';
import '../../../data/services/auth_service.dart';

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

  Future<void> _requestOtp() async {
    if (_emailCtrl.text.trim().isEmpty) {
      setState(() => _error = 'Please enter your email.');
      return;
    }
    setState(() { _isLoading = true; _error = ''; });
    try {
      await AuthService().requestPasswordResetOtp(_emailCtrl.text.trim());
      if (mounted) setState(() { _otpSent = true; _isLoading = false; });
    } catch (_) {
      if (mounted) setState(() { _isLoading = false; _error = 'Could not send the code. Please try again.'; });
    }
  }

  Future<void> _confirmReset() async {
    if (_otpCtrl.text.trim().isEmpty || _newPasswordCtrl.text.isEmpty) {
      setState(() => _error = 'Please fill in all fields.');
      return;
    }
    if (_newPasswordCtrl.text.length < 8) {
      setState(() => _error = 'Password must be at least 8 characters.');
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
      String msg = 'Reset failed. Please check the code and try again.';
      if (detail is Map) msg = detail['detail'] as String? ?? msg;
      if (mounted) setState(() { _isLoading = false; _error = msg; });
    } catch (_) {
      if (mounted) setState(() { _isLoading = false; _error = 'An unexpected error occurred.'; });
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final resp = context.resp;

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: 'Reset Password'),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: EdgeInsets.symmetric(horizontal: resp.w(24), vertical: resp.h(24)),
          child: _done
              ? Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.check_circle_rounded, color: ty.saffron, size: 48),
                    SizedBox(height: resp.h(16)),
                    Text('Password reset', style: TyType.display(resp.sp(22), color: ty.ink)),
                    SizedBox(height: resp.h(8)),
                    Text('You can now sign in with your new password.', style: TyType.sans(resp.sp(14), color: ty.ink2)),
                    SizedBox(height: resp.h(24)),
                    TyButton('Back to Login', full: true, onTap: () => Navigator.of(context).pop()),
                  ],
                )
              : Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(_otpSent ? 'Enter the code we sent you' : 'Forgot your password?',
                        style: TyType.display(resp.sp(22), color: ty.ink)),
                    SizedBox(height: resp.h(20)),
                    _field(ty, resp, 'EMAIL', _emailCtrl, enabled: !_otpSent, type: TextInputType.emailAddress),
                    if (_otpSent) ...[
                      SizedBox(height: resp.h(16)),
                      _field(ty, resp, 'OTP CODE', _otpCtrl, type: TextInputType.number),
                      SizedBox(height: resp.h(16)),
                      _field(ty, resp, 'NEW PASSWORD', _newPasswordCtrl, obscure: true),
                      SizedBox(height: resp.h(8)),
                      TextButton(
                        onPressed: _isLoading ? null : () => setState(() => _otpSent = false),
                        child: const Text('Change email'),
                      ),
                    ],
                    if (_error.isNotEmpty) ...[
                      SizedBox(height: resp.h(12)),
                      Text(_error, style: TyType.sans(resp.sp(13), color: ty.rose, weight: FontWeight.w600)),
                    ],
                    SizedBox(height: resp.h(24)),
                    TyButton(
                      _isLoading ? 'Please wait...' : (_otpSent ? 'Reset Password' : 'Send Code'),
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
      {TextInputType type = TextInputType.text, bool obscure = false, bool enabled = true}) {
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
      ],
    );
  }
}
