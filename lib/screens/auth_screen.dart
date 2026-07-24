import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:dio/dio.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../theme/responsive.dart';
import '../widgets/ty_button.dart';
import '../widgets/common.dart';
import '../data/app_state.dart';
import '../data/auth_manager.dart';
import '../data/services/auth_service.dart';
// AuthCredentials is defined in auth_service.dart
import 'root_nav.dart';
import 'vendor/vendor_root_nav.dart';
import 'vendor/auth/vendor_register_screen.dart';
import 'vendor/auth/vendor_forgot_password_screen.dart';
import 'email_verification_screen.dart';

class AuthScreen extends StatefulWidget {
  final VoidCallback? onAuthenticated;
  const AuthScreen({super.key, this.onAuthenticated});

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> with SingleTickerProviderStateMixin {
  late final TabController _tabController;

  final _loginEmailCtrl = TextEditingController();
  final _loginPasswordCtrl = TextEditingController();

  final _regNameCtrl = TextEditingController();
  final _regEmailCtrl = TextEditingController();
  final _regPasswordCtrl = TextEditingController();
  final _regConfirmCtrl = TextEditingController();

  bool _isLoading = false;
  String _error = '';
  bool _loginObscure = true;
  bool _regObscure = true;
  bool _regConfirmObscure = true;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _tabController.addListener(() => setState(() => _error = ''));
  }

  @override
  void dispose() {
    _tabController.dispose();
    _loginEmailCtrl.dispose();
    _loginPasswordCtrl.dispose();
    _regNameCtrl.dispose();
    _regEmailCtrl.dispose();
    _regPasswordCtrl.dispose();
    _regConfirmCtrl.dispose();
    super.dispose();
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

  Future<void> _handleLogin() async {
    if (_isLoading) return;
    final email = _loginEmailCtrl.text.trim();
    final password = _loginPasswordCtrl.text;
    if (email.isEmpty || password.isEmpty) {
      setState(() => _error = 'Please fill in all fields.');
      return;
    }

    setState(() { _isLoading = true; _error = ''; });
    try {
      final creds = await context.read<AuthService>().login(email, password);
      if (!mounted) return;
      await _onSuccess(creds);
    } on DioException catch (e) {
      final detail = e.response?.data;
      String msg = 'Login failed. Please try again.';
      if (detail is Map) {
        msg = detail['detail'] as String? ?? detail['message'] as String? ?? msg;
      } else if (detail is String) {
        msg = detail;
      }
      if (mounted) setState(() { _isLoading = false; _error = msg; });
    } catch (_) {
      if (mounted) setState(() { _isLoading = false; _error = 'An unexpected error occurred.'; });
    }
  }

  Future<void> _handleRegister() async {
    if (_isLoading) return;
    final name = _regNameCtrl.text.trim();
    final email = _regEmailCtrl.text.trim();
    final password = _regPasswordCtrl.text;
    final confirm = _regConfirmCtrl.text;

    if (email.isEmpty || password.isEmpty) {
      setState(() => _error = 'Please fill in all required fields.');
      return;
    }
    if (password != confirm) {
      setState(() => _error = 'Passwords do not match.');
      return;
    }
    if (password.length < 8) {
      setState(() => _error = 'Password must be at least 8 characters.');
      return;
    }

    setState(() { _isLoading = true; _error = ''; });
    try {
      final creds = await context.read<AuthService>().register(email, password, name: name);
      if (!mounted) return;
      await _onSuccess(
        creds,
        overrideDestination: EmailVerificationScreen(
          email: creds.user.email ?? email,
          initialSendFailed: !creds.emailVerificationSent,
        ),
      );
    } on DioException catch (e) {
      final detail = e.response?.data;
      String msg = 'Registration failed. Please try again.';
      if (detail is Map) {
        msg = detail['detail'] as String? ?? detail['message'] as String? ?? msg;
      } else if (detail is String) {
        msg = detail;
      }
      if (mounted) setState(() { _isLoading = false; _error = msg; });
    } catch (_) {
      if (mounted) setState(() { _isLoading = false; _error = 'An unexpected error occurred.'; });
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

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: 'Welcome'),
      body: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) {
            // Smart height calculation: if the screen is too short, 
            // we'll make the header section smaller and the overall layout more compact.
            final isSmall = constraints.maxHeight < 600;
            
            return Column(
              children: [
                SizedBox(height: resp.h(isSmall ? 12 : 24)),
                Padding(
                  padding: EdgeInsets.symmetric(horizontal: resp.w(24)),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Join Tyohaar', style: TyType.display(resp.sp(32), color: ty.ink)),
                      SizedBox(height: resp.h(8)),
                      Text(
                        'Start your journey of creating unforgettable moments.',
                        style: TyType.sans(resp.sp(15), color: ty.ink2, height: 1.4),
                      ),
                    ],
                  ),
                ),
                SizedBox(height: resp.h(isSmall ? 16 : 32)),
                Padding(
                  padding: EdgeInsets.symmetric(horizontal: resp.w(24)),
                  child: Container(
                    height: resp.h(44),
                    decoration: BoxDecoration(
                      color: ty.surface,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: ty.line),
                    ),
                    child: TabBar(
                      controller: _tabController,
                      indicator: BoxDecoration(
                        color: ty.saffron,
                        borderRadius: BorderRadius.circular(10),
                      ),
                      indicatorSize: TabBarIndicatorSize.tab,
                      dividerColor: Colors.transparent,
                      labelStyle: TyType.sans(resp.sp(14), weight: FontWeight.w700),
                      unselectedLabelStyle: TyType.sans(resp.sp(14), weight: FontWeight.w500),
                      labelColor: Colors.white,
                      unselectedLabelColor: ty.ink2,
                      tabs: const [Tab(text: 'Login'), Tab(text: 'Register')],
                    ),
                  ),
                ),
                SizedBox(height: resp.h(4)),
                Expanded(
                  child: TabBarView(
                    controller: _tabController,
                    children: [_buildLoginTab(ty, resp), _buildRegisterTab(ty, resp)],
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }

  Widget _buildLoginTab(TyColors ty, TyResponsive resp) {
    return SingleChildScrollView(
      padding: EdgeInsets.symmetric(horizontal: resp.w(24)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(height: resp.h(28)),
          _buildField(ty, resp, 'EMAIL', 'you@example.com', _loginEmailCtrl,
              icon: Icons.email_outlined, type: TextInputType.emailAddress),
          SizedBox(height: resp.h(20)),
          _buildField(ty, resp, 'PASSWORD', '••••••••', _loginPasswordCtrl,
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
              child: Text('Forgot password?', style: TyType.sans(resp.sp(13), color: ty.ink3, weight: FontWeight.w600)),
            ),
          ),
          if (_error.isNotEmpty) ...[
            SizedBox(height: resp.h(16)),
            Text(_error, style: TyType.sans(resp.sp(13), color: ty.rose, weight: FontWeight.w600)),
          ],
          SizedBox(height: resp.h(36)),
          TyButton(
            _isLoading ? 'Signing in...' : 'Sign In',
            full: true,
            onTap: _handleLogin,
            enabled: !_isLoading,
          ),
          if (widget.onAuthenticated == null) ...[
            SizedBox(height: resp.h(28)),
            _buildDivider(ty, resp),
            SizedBox(height: resp.h(28)),
            Center(
              child: TextButton(
                onPressed: _handleSkip,
                child: Text('Continue as Guest',
                    style: TyType.sans(resp.sp(14), color: ty.ink3, weight: FontWeight.w600)),
              ),
            ),
          ],
          SizedBox(height: resp.h(32)),
        ],
      ),
    );
  }

  Widget _buildRegisterTab(TyColors ty, TyResponsive resp) {
    return SingleChildScrollView(
      padding: EdgeInsets.symmetric(horizontal: resp.w(24)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(height: resp.h(28)),
          _buildField(ty, resp, 'FULL NAME (OPTIONAL)', 'Rahul Sharma', _regNameCtrl,
              icon: Icons.person_outline_rounded),
          SizedBox(height: resp.h(20)),
          _buildField(ty, resp, 'EMAIL', 'you@example.com', _regEmailCtrl,
              icon: Icons.email_outlined, type: TextInputType.emailAddress),
          SizedBox(height: resp.h(20)),
          _buildField(ty, resp, 'PASSWORD', '••••••••', _regPasswordCtrl,
              icon: Icons.lock_outline_rounded,
              obscure: _regObscure,
              onToggleObscure: () => setState(() => _regObscure = !_regObscure)),
          SizedBox(height: resp.h(20)),
          _buildField(ty, resp, 'CONFIRM PASSWORD', '••••••••', _regConfirmCtrl,
              icon: Icons.lock_outline_rounded,
              obscure: _regConfirmObscure,
              onToggleObscure: () => setState(() => _regConfirmObscure = !_regConfirmObscure)),
          if (_error.isNotEmpty) ...[
            SizedBox(height: resp.h(16)),
            Text(_error, style: TyType.sans(resp.sp(13), color: ty.rose, weight: FontWeight.w600)),
          ],
          SizedBox(height: resp.h(36)),
          TyButton(
            _isLoading ? 'Creating account...' : 'Create Account',
            full: true,
            onTap: _handleRegister,
            enabled: !_isLoading,
          ),
          SizedBox(height: resp.h(20)),
          Center(
            child: TextButton(
              onPressed: () => Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const VendorRegisterScreen()),
              ),
              child: Text('Are you a business? Register as a Partner',
                  style: TyType.sans(resp.sp(13), color: ty.saffronDeep, weight: FontWeight.w600)),
            ),
          ),
          SizedBox(height: resp.h(12)),
        ],
      ),
    );
  }

  Widget _buildDivider(TyColors ty, TyResponsive resp) {
    return Row(
      children: [
        Expanded(child: Divider(color: ty.line)),
        Padding(
          padding: EdgeInsets.symmetric(horizontal: resp.w(16)),
          child: Text('OR', style: TyType.eyebrow(resp.sp(10), color: ty.ink3)),
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
      ],
    );
  }
}
