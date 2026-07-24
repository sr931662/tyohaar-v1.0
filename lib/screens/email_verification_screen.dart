import 'dart:async';

import 'package:flutter/material.dart';
import 'package:dio/dio.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../theme/responsive.dart';
import '../widgets/ty_button.dart';
import '../widgets/common.dart';
import '../data/auth_manager.dart';
import '../data/services/auth_service.dart';
import '../data/services/user_service.dart';
import 'auth_screen.dart';
import 'root_nav.dart';

const _kResendCooldownSeconds = 30;

/// Two independent uses:
///  1. Right after registration (auth_screen.dart/_handleRegister) — a
///     skippable nudge; the customer can verify now or tap "Skip for now"
///     and use the app normally. Account creation itself is never blocked.
///  2. As a gate immediately before creating a booking (the only place
///     verification is actually required) — pushed for a result; on
///     success it pops back so the caller can resume the booking.
/// Only ever informs the user a code was sent; no OTP-system implementation
/// details are surfaced.
class EmailVerificationScreen extends StatefulWidget {
  final String email;
  /// True when the very first (registration-time) send attempt failed —
  /// shows an upfront "couldn't send" message with Resend immediately
  /// available instead of the initial cooldown.
  final bool initialSendFailed;
  /// True when opened as a booking gate: successful verification pops back
  /// to the caller with `true` instead of navigating into RootNav, and the
  /// "Skip for now" escape hatch is hidden (verification isn't optional here).
  final bool popOnVerify;

  const EmailVerificationScreen({
    super.key,
    required this.email,
    this.initialSendFailed = false,
    this.popOnVerify = false,
  });

  @override
  State<EmailVerificationScreen> createState() => _EmailVerificationScreenState();
}

class _EmailVerificationScreenState extends State<EmailVerificationScreen> {
  final _otpCtrl = TextEditingController();
  bool _isLoading = false;
  bool _isResending = false;
  String _error = '';
  String _notice = '';
  int _cooldownSeconds = 0;
  Timer? _cooldownTimer;

  @override
  void initState() {
    super.initState();
    if (widget.initialSendFailed) {
      _error = "We couldn't send the verification code. Tap Resend to try again.";
    } else {
      _startCooldown();
    }
  }

  @override
  void dispose() {
    _cooldownTimer?.cancel();
    _otpCtrl.dispose();
    super.dispose();
  }

  void _startCooldown() {
    _cooldownTimer?.cancel();
    setState(() => _cooldownSeconds = _kResendCooldownSeconds);
    _cooldownTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      setState(() => _cooldownSeconds--);
      if (_cooldownSeconds <= 0) timer.cancel();
    });
  }

  Future<void> _resend() async {
    if (_isResending || _cooldownSeconds > 0) return;
    setState(() { _isResending = true; _error = ''; _notice = ''; });
    try {
      await AuthService().requestEmailVerificationOtp(widget.email);
      if (!mounted) return;
      setState(() { _isResending = false; _notice = 'A new code has been sent.'; });
      _startCooldown();
    } on DioException catch (e) {
      final detail = e.response?.data;
      String msg = 'Could not send the code. Please try again.';
      if (detail is Map) msg = detail['detail'] as String? ?? msg;
      if (mounted) setState(() { _isResending = false; _error = msg; });
    } catch (_) {
      if (mounted) setState(() { _isResending = false; _error = 'An unexpected error occurred.'; });
    }
  }

  Future<void> _verify() async {
    if (_isLoading) return;
    final code = _otpCtrl.text.trim();
    if (code.length != 6) {
      setState(() => _error = 'Enter the 6-digit code.');
      return;
    }
    setState(() { _isLoading = true; _error = ''; _notice = ''; });
    try {
      await AuthService().verifyEmailOtp(widget.email, code);
      // The account is already authenticated at this point (login happens
      // immediately at registration/sign-in) — just refresh the cached
      // user so emailVerified flips to true, then continue into the app.
      final updatedUser = await UserService().getMe();
      AuthManager.instance.setUser(updatedUser);
      if (!mounted) return;
      if (widget.popOnVerify) {
        Navigator.of(context).pop(true);
      } else {
        Navigator.of(context).pushAndRemoveUntil(
          MaterialPageRoute(builder: (_) => const RootNav()),
          (route) => false,
        );
      }
    } on DioException catch (e) {
      final detail = e.response?.data;
      String msg = 'Verification failed. Please try again.';
      if (detail is Map) msg = detail['detail'] as String? ?? msg;
      if (mounted) setState(() { _isLoading = false; _error = msg; });
    } catch (_) {
      if (mounted) setState(() { _isLoading = false; _error = 'An unexpected error occurred.'; });
    }
  }

  void _skip() {
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const RootNav()),
      (route) => false,
    );
  }

  Future<void> _logout() async {
    await AuthManager.instance.logout();
    // AuthManager.logout() only unmounts _AppStartup's own AuthScreen swap
    // when this screen is rendered *inside* that ListenableBuilder (the
    // cold-start gate case). When reached via a pushAndRemoveUntil after
    // registration/login, _AppStartup's route no longer exists to react to
    // it, so navigate explicitly in both cases.
    if (mounted) {
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => const AuthScreen()),
        (route) => false,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final resp = context.resp;

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: 'Verify Your Email'),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: EdgeInsets.symmetric(horizontal: resp.w(24), vertical: resp.h(24)),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(Icons.mark_email_read_outlined, color: ty.saffron, size: 48),
              SizedBox(height: resp.h(16)),
              Text('Check your email', style: TyType.display(resp.sp(22), color: ty.ink)),
              SizedBox(height: resp.h(8)),
              Text(
                "We've sent a 6-digit verification code to ${widget.email}. Enter it below to verify your account.",
                style: TyType.sans(resp.sp(14), color: ty.ink2, height: 1.5),
              ),
              SizedBox(height: resp.h(24)),
              Text('VERIFICATION CODE', style: TyType.eyebrow(resp.sp(11), color: ty.ink3)),
              SizedBox(height: resp.h(8)),
              Container(
                padding: EdgeInsets.symmetric(horizontal: resp.w(16)),
                decoration: BoxDecoration(
                  color: ty.surface,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: ty.line),
                ),
                child: TextField(
                  controller: _otpCtrl,
                  keyboardType: TextInputType.number,
                  maxLength: 6,
                  style: TyType.sans(resp.sp(20), color: ty.ink, weight: FontWeight.w700).copyWith(letterSpacing: 6),
                  decoration: const InputDecoration(
                    border: InputBorder.none,
                    counterText: '',
                    isDense: true,
                    contentPadding: EdgeInsets.symmetric(vertical: 14),
                  ),
                ),
              ),
              SizedBox(height: resp.h(12)),
              Align(
                alignment: Alignment.centerLeft,
                child: TextButton(
                  onPressed: (_cooldownSeconds > 0 || _isResending) ? null : _resend,
                  child: Text(
                    _isResending
                        ? 'Sending...'
                        : (_cooldownSeconds > 0 ? 'Resend code in ${_cooldownSeconds}s' : 'Resend code'),
                    style: TyType.sans(resp.sp(13), color: ty.saffronDeep, weight: FontWeight.w600),
                  ),
                ),
              ),
              if (_notice.isNotEmpty) ...[
                SizedBox(height: resp.h(4)),
                Text(_notice, style: TyType.sans(resp.sp(13), color: ty.ink2, weight: FontWeight.w600)),
              ],
              if (_error.isNotEmpty) ...[
                SizedBox(height: resp.h(12)),
                Text(_error, style: TyType.sans(resp.sp(13), color: ty.rose, weight: FontWeight.w600)),
              ],
              SizedBox(height: resp.h(24)),
              TyButton(
                _isLoading ? 'Verifying...' : 'Verify',
                full: true,
                onTap: _verify,
                enabled: !_isLoading,
              ),
              if (!widget.popOnVerify) ...[
                SizedBox(height: resp.h(16)),
                Center(
                  child: TextButton(
                    onPressed: _skip,
                    child: Text('Skip for now', style: TyType.sans(resp.sp(13), color: ty.saffronDeep, weight: FontWeight.w600)),
                  ),
                ),
              ],
              SizedBox(height: resp.h(8)),
              Center(
                child: TextButton(
                  onPressed: _logout,
                  child: Text('Log out', style: TyType.sans(resp.sp(13), color: ty.ink3, weight: FontWeight.w600)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
