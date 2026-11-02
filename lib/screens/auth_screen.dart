import 'dart:io' show Platform;

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:dio/dio.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../theme/responsive.dart';
import '../widgets/ty_button.dart';
import '../widgets/google_g_logo.dart';
import '../widgets/common.dart';
import '../data/app_state.dart';
import '../data/auth_manager.dart';
import '../data/models.dart';
import '../data/services/auth_service.dart';
import '../data/services/google_auth_service.dart';
// AuthCredentials is defined in auth_service.dart
import 'root_nav.dart';
import 'vendor/vendor_root_nav.dart';
import 'vendor/auth/vendor_register_screen.dart';
import 'vendor/auth/vendor_forgot_password_screen.dart';
import 'auth/code_sign_in_panel.dart';
import '../l10n/generated/app_localizations.dart';

class AuthScreen extends StatefulWidget {
  final VoidCallback? onAuthenticated;
  const AuthScreen({super.key, this.onAuthenticated});

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  final _loginEmailCtrl = TextEditingController();
  final _loginPasswordCtrl = TextEditingController();

  bool _isLoading = false;
  String _error = '';
  // Hidden until the server confirms a Google client ID is configured — an
  // always-visible button would be dead for every user until it is set.
  bool _googleEnabled = false;
  bool _loginObscure = true;
  // The code (email / mobile) is the main way in. Password sign-in is still
  // there for accounts that have one, one tap away.
  bool _showPassword = false;
  // Which code channels the server can deliver right now. Email works unless
  // the server says otherwise; phone waits for the server to confirm SMS.
  bool _emailCodes = true;
  bool _phoneCodes = false;

  @override
  void initState() {
    super.initState();
    _loadProviderConfig();
  }

  Future<void> _loadProviderConfig() async {
    try {
      final config = await context.read<AuthService>().getProviderConfig();
      if (!mounted) return;
      setState(() {
        _emailCodes = config.emailOtpEnabled;
        _phoneCodes = config.phoneOtpEnabled;
        // Google sign-in stays Android-only for now. On iOS it needs its own
        // OAuth client (GIDClientID + URL scheme in Info.plist) or the plugin
        // crashes, and App Store guideline 4.8 then also requires Sign in with
        // Apple alongside it.
        _googleEnabled = config.googleEnabled && (kIsWeb || !Platform.isIOS);
      });
    } catch (_) {
      // Keep the defaults: email codes on, phone and Google hidden. Offering
      // a control that can only fail is worse than omitting it.
    }
  }

  @override
  void dispose() {
    _loginEmailCtrl.dispose();
    _loginPasswordCtrl.dispose();
    super.dispose();
  }

  /// Signed in with a one-time code. A brand-new account gets one optional
  /// question, its name, before landing in the app.
  Future<void> _onCodeSignedIn(CodeSignInResult result) async {
    var creds = result.credentials;
    if (result.isNewUser) {
      final name = await _askName();
      if (!mounted) return;
      if (name != null && name.isNotEmpty) {
        try {
          await context.read<AuthService>().saveName(creds.accessToken, name);
          creds = AuthCredentials(
            accessToken: creds.accessToken,
            refreshToken: creds.refreshToken,
            user: User(
              id: creds.user.id,
              phone: creds.user.phone,
              email: creds.user.email,
              fullName: name,
              firstName: creds.user.firstName,
              lastName: creds.user.lastName,
              profilePhotoUrl: creds.user.profilePhotoUrl,
              role: creds.user.role,
              status: creds.user.status,
              emailVerified: creds.user.emailVerified,
              phoneVerified: creds.user.phoneVerified,
            ),
          );
        } catch (_) {
          // The name can be added later from the profile; never block sign-in.
        }
      }
    }
    if (!mounted) return;
    await _onSuccess(creds);
  }

  Future<String?> _askName() {
    final ctrl = TextEditingController();
    final l10n = AppLocalizations.of(context)!;
    return showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      isDismissible: false,
      backgroundColor: context.ty.paper,
      builder: (sheet) {
        final ty = sheet.ty;
        return Padding(
          padding: EdgeInsets.fromLTRB(24, 24, 24, 24 + MediaQuery.viewInsetsOf(sheet).bottom),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(l10n.codeSignInNameTitle, style: TyType.display(24, color: ty.ink)),
              const SizedBox(height: 6),
              Text(l10n.codeSignInNameSubtitle, style: TyType.sans(14, color: ty.ink2)),
              const SizedBox(height: 18),
              TextField(
                controller: ctrl,
                autofocus: true,
                textCapitalization: TextCapitalization.words,
                autofillHints: const [AutofillHints.name],
                textInputAction: TextInputAction.done,
                onSubmitted: (v) => Navigator.pop(sheet, v.trim()),
                decoration: InputDecoration(
                  hintText: l10n.authNameHint,
                  filled: true,
                  fillColor: ty.surface,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                ),
              ),
              const SizedBox(height: 18),
              TyButton(l10n.codeSignInNameSave, full: true, onTap: () => Navigator.pop(sheet, ctrl.text.trim())),
              Center(
                child: TextButton(
                  onPressed: () => Navigator.pop(sheet, ''),
                  child: Text(l10n.codeSignInNameSkip, style: TyType.sans(13.5, color: ty.ink3, weight: FontWeight.w600)),
                ),
              ),
            ],
          ),
        );
      },
    ).whenComplete(ctrl.dispose);
  }

  // [overrideDestination] is used only right after registration, to land on
  // the (skippable) EmailVerificationScreen instead of the normal shell —
  // login is otherwise never gated on verification status. Email
  // verification is only enforced later, at the point of booking an event.
  Future<void> _onSuccess(AuthCredentials creds, {Widget? overrideDestination}) async {
    // Resolve the POV (customer vs vendor) BEFORE flipping isAuthenticated —
    // AuthManager.login() triggers an immediate rebuild of whatever's
    // listening to it (the customer _AppStartup shell), so if pov were still
    // 'customer' at that instant, the customer home would flash for a frame
    // before AppState's own rebuild swaps in the vendor shell.
    AppState.instance.applyRole(creds.user.role);
    await AuthManager.instance.login(creds.accessToken, creds.refreshToken, creds.user);
    if (!mounted) return;
    final isVendor = creds.user.role == 'vendor';
    final destination = overrideDestination ?? (isVendor ? const VendorRootNav() : const RootNav());
    if (widget.onAuthenticated != null) {
      // Auth-gate flows (e.g. "start a celebration") only ever apply to the
      // customer shell — a vendor account hitting one of those gates is an
      // edge case we don't special-case here.
      Navigator.pop(context);
      if (overrideDestination != null) {
        Navigator.push(context, MaterialPageRoute(builder: (_) => destination));
      } else {
        widget.onAuthenticated!();
      }
    } else {
      // Clear the whole stack (not just replace) so a vendor login doesn't
      // leave the customer _AppStartup underneath — pushAndRemoveUntil
      // lands cleanly on the correct root shell for the resolved role.
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => destination),
        (route) => false,
      );
    }
  }

  Future<void> _handleGoogleAuth() async {
    if (_isLoading) return;
    setState(() { _isLoading = true; _error = ''; });
    try {
      final auth = context.read<AuthService>();
      final google = context.read<GoogleAuthService>();
      final config = await auth.getProviderConfig();
      if (!config.googleEnabled) {
        throw GoogleSignInFailure(GoogleSignInFailureKind.notConfigured);
      }
      final idToken = await google.obtainIdToken(config.googleClientId);
      final creds = await auth.signInWithGoogle(idToken);
      if (!mounted) return;
      // No overrideDestination: unlike email signup there is nothing to
      // verify — Google already vouched for the address, so the server marks
      // the account email-verified and the user lands straight on the shell.
      await _onSuccess(creds);
    } on GoogleSignInFailure catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        // Dismissing the account sheet is not an error — clear the row
        // instead of accusing the user of a failure.
        _error = e.isCancelled ? '' : _googleErrorText(e.kind);
      });
    } on DioException catch (e) {
      if (!mounted) return;
      final msg = authErrorMessage(e, AppLocalizations.of(context)!.authGoogleFailedError);
      setState(() { _isLoading = false; _error = msg; });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _error = AppLocalizations.of(context)!.authGoogleFailedError;
      });
    }
  }

  String _googleErrorText(GoogleSignInFailureKind kind) {
    final l10n = AppLocalizations.of(context)!;
    switch (kind) {
      case GoogleSignInFailureKind.notConfigured:
        return l10n.authGoogleNotConfiguredError;
      case GoogleSignInFailureKind.unsupported:
        return l10n.authGoogleUnsupportedError;
      case GoogleSignInFailureKind.noIdToken:
        return l10n.authGoogleNoIdTokenError;
      case GoogleSignInFailureKind.cancelled:
      case GoogleSignInFailureKind.failed:
        return l10n.authGoogleFailedError;
    }
  }

  Future<void> _handleLogin() async {
    if (_isLoading) return;
    final email = _loginEmailCtrl.text.trim();
    final password = _loginPasswordCtrl.text;
    if (email.isEmpty || password.isEmpty) {
      setState(() => _error = AppLocalizations.of(context)!.authLoginFillAllFieldsError);
      return;
    }

    setState(() { _isLoading = true; _error = ''; });
    try {
      final creds = await context.read<AuthService>().login(email, password);
      if (!mounted) return;
      await _onSuccess(creds);
    } on DioException catch (e) {
      if (!mounted) return;
      final msg = authErrorMessage(e, AppLocalizations.of(context)!.authLoginFailedError);
      setState(() { _isLoading = false; _error = msg; });
    } catch (_) {
      if (mounted) setState(() { _isLoading = false; _error = AppLocalizations.of(context)!.authUnexpectedError; });
    }
  }

  void _handleSkip() {
    AuthManager.instance.skip();
    Navigator.pushReplacement(
      context,
      MaterialPageRoute(builder: (_) => const RootNav()),
    );
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final resp = context.resp;
    final l10n = AppLocalizations.of(context)!;

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: l10n.authWelcomeTitle),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: EdgeInsets.symmetric(horizontal: resp.w(24)),
          child: AutofillGroup(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SizedBox(height: resp.h(24)),
                Text(l10n.authHeading, style: TyType.display(resp.sp(32), color: ty.ink)),
                SizedBox(height: resp.h(8)),
                Text(l10n.codeSignInSubheading, style: TyType.sans(resp.sp(15), color: ty.ink2, height: 1.4)),
                SizedBox(height: resp.h(28)),
                if (_showPassword)
                  _buildPasswordSection(ty, resp)
                else
                  CodeSignInPanel(
                    phoneEnabled: _phoneCodes,
                    emailEnabled: _emailCodes,
                    onSignedIn: _onCodeSignedIn,
                  ),
                SizedBox(height: resp.h(6)),
                Center(
                  child: TextButton(
                    onPressed: _isLoading
                        ? null
                        : () => setState(() { _showPassword = !_showPassword; _error = ''; }),
                    child: Text(
                      _showPassword ? l10n.codeSignInUseCodeInstead : l10n.codeSignInUsePasswordInstead,
                      style: TyType.sans(resp.sp(13.5), color: ty.saffronDeep, weight: FontWeight.w700),
                    ),
                  ),
                ),
                if (_googleEnabled) ...[
                  SizedBox(height: resp.h(16)),
                  _buildDivider(ty, resp),
                  SizedBox(height: resp.h(20)),
                  _buildGoogleButton(ty, resp),
                  if (_error.isNotEmpty && !_showPassword) ...[
                    SizedBox(height: resp.h(12)),
                    Text(_error, style: TyType.sans(resp.sp(13), color: ty.rose, weight: FontWeight.w600)),
                  ],
                ],
                if (widget.onAuthenticated == null) ...[
                  SizedBox(height: resp.h(16)),
                  _buildGuestLink(ty, resp),
                ],
                Center(
                  child: TextButton(
                    onPressed: () => Navigator.push(
                      context,
                      MaterialPageRoute(builder: (_) => const VendorRegisterScreen()),
                    ),
                    child: Text(l10n.authBusinessRegisterPromptLabel,
                        style: TyType.sans(resp.sp(13), color: ty.saffronDeep, weight: FontWeight.w600)),
                  ),
                ),
                SizedBox(height: resp.h(24)),
              ],
            ),
          ),
        ),
      ),
    );
  }

  /// Email + password, for accounts that have a password.
  Widget _buildPasswordSection(TyColors ty, TyResponsive resp) {
    final l10n = AppLocalizations.of(context)!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildField(ty, resp, l10n.authEmailLabel, l10n.authEmailHint, _loginEmailCtrl,
            icon: Icons.email_outlined, type: TextInputType.emailAddress),
        SizedBox(height: resp.h(20)),
        _buildField(ty, resp, l10n.authPasswordLabel, l10n.authPasswordHint, _loginPasswordCtrl,
            icon: Icons.lock_outline_rounded,
            obscure: _loginObscure,
            onToggleObscure: () => setState(() => _loginObscure = !_loginObscure)),
        Align(
          alignment: Alignment.centerRight,
          child: TextButton(
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const VendorForgotPasswordScreen()),
            ),
            child: Text(l10n.authForgotPasswordLabel, style: TyType.sans(resp.sp(13), color: ty.ink3, weight: FontWeight.w600)),
          ),
        ),
        if (_error.isNotEmpty) ...[
          SizedBox(height: resp.h(8)),
          Text(_error, style: TyType.sans(resp.sp(13), color: ty.rose, weight: FontWeight.w600)),
        ],
        SizedBox(height: resp.h(20)),
        TyButton(
          _isLoading ? l10n.authSigningInLabel : l10n.authSignInButtonLabel,
          full: true,
          onTap: _handleLogin,
          enabled: !_isLoading,
        ),
      ],
    );
  }

  /// Google mandates its own mark on a plain light surface, so this is a
  /// bespoke button rather than a TyButton (which only takes an IconData).
  Widget _buildGoogleButton(TyColors ty, TyResponsive resp) {
    final l10n = AppLocalizations.of(context)!;
    return Semantics(
      button: true,
      enabled: !_isLoading,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: _isLoading ? null : _handleGoogleAuth,
          borderRadius: BorderRadius.circular(16),
          child: Ink(
            width: double.infinity,
            padding: EdgeInsets.symmetric(vertical: resp.h(15)),
            decoration: BoxDecoration(
              color: ty.surface,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: _isLoading ? ty.line2 : ty.line, width: 1.5),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Opacity(
                  opacity: _isLoading ? 0.4 : 1,
                  child: GoogleGLogo(size: resp.w(20)),
                ),
                SizedBox(width: resp.w(12)),
                Text(
                  _isLoading ? l10n.authGoogleSigningInLabel : l10n.authGoogleSignInButtonLabel,
                  style: TyType.sans(
                    resp.sp(15),
                    color: _isLoading ? ty.ink3 : ty.ink,
                    weight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildGuestLink(TyColors ty, TyResponsive resp) {
    return Center(
      child: TextButton(
        onPressed: _handleSkip,
        child: Text(AppLocalizations.of(context)!.authContinueAsGuestLabel,
            style: TyType.sans(resp.sp(14), color: ty.ink3, weight: FontWeight.w600)),
      ),
    );
  }

  Widget _buildDivider(TyColors ty, TyResponsive resp) {
    return Row(
      children: [
        Expanded(child: Divider(color: ty.line)),
        Padding(
          padding: EdgeInsets.symmetric(horizontal: resp.w(16)),
          child: Text(AppLocalizations.of(context)!.authOrDividerLabel, style: TyType.eyebrow(resp.sp(10), color: ty.ink3)),
        ),
        Expanded(child: Divider(color: ty.line)),
      ],
    );
  }

  Widget _buildField(
    TyColors ty,
    TyResponsive resp,
    String label,
    String hint,
    TextEditingController ctrl, {
    IconData? icon,
    TextInputType type = TextInputType.text,
    bool? obscure,
    VoidCallback? onToggleObscure,
    String? helperText,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: TyType.eyebrow(resp.sp(11), color: ty.ink3)),
        SizedBox(height: resp.h(12)),
        Container(
          padding: EdgeInsets.symmetric(horizontal: resp.w(16), vertical: resp.h(8)),
          decoration: BoxDecoration(
            color: ty.surface,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: ty.line),
          ),
          child: Row(
            children: [
              if (icon != null) ...[
                Icon(icon, size: resp.w(20), color: ty.ink3),
                SizedBox(width: resp.w(12)),
              ],
              Expanded(
                child: TextField(
                  controller: ctrl,
                  keyboardType: type,
                  obscureText: obscure ?? false,
                  style: TyType.sans(resp.sp(16), color: ty.ink, weight: FontWeight.w600),
                  decoration: InputDecoration(
                    hintText: hint,
                    hintStyle: TyType.sans(resp.sp(16), color: ty.ink3.withValues(alpha: 0.5)),
                    border: InputBorder.none,
                    isDense: true,
                    contentPadding: EdgeInsets.symmetric(vertical: resp.h(10)),
                  ),
                ),
              ),
              if (onToggleObscure != null)
                GestureDetector(
                  onTap: onToggleObscure,
                  child: Icon(
                    (obscure ?? true) ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                    size: resp.w(20),
                    color: ty.ink3,
                  ),
                ),
            ],
          ),
        ),
        if (helperText != null) ...[
          SizedBox(height: resp.h(4)),
          Text(helperText, style: TyType.sans(resp.sp(11.5), color: ty.ink3)),
        ],
      ],
    );
  }
}
