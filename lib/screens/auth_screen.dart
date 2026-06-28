import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:dio/dio.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../widgets/ty_button.dart';
import '../widgets/common.dart';
import '../data/auth_manager.dart';
import '../data/services/auth_service.dart';
// AuthCredentials is defined in auth_service.dart
import 'root_nav.dart';

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

  Future<void> _onSuccess(AuthCredentials creds) async {
    await AuthManager.instance.login(creds.accessToken, creds.refreshToken, creds.user);
    if (!mounted) return;
    if (widget.onAuthenticated != null) {
      Navigator.pop(context);
      widget.onAuthenticated!();
    } else {
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => const RootNav()),
      );
    }
  }

  Future<void> _handleLogin() async {
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
      await _onSuccess(creds);
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

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: 'Welcome'),
      body: SafeArea(
        child: Column(
          children: [
            const SizedBox(height: 24),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Join Tyohaar', style: TyType.display(32, color: ty.ink)),
                  const SizedBox(height: 8),
                  Text(
                    'Start your journey of creating unforgettable moments.',
                    style: TyType.sans(15, color: ty.ink2, height: 1.5),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 32),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: Container(
                height: 44,
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
                  labelStyle: TyType.sans(14, weight: FontWeight.w700),
                  unselectedLabelStyle: TyType.sans(14, weight: FontWeight.w500),
                  labelColor: Colors.white,
                  unselectedLabelColor: ty.ink2,
                  tabs: const [Tab(text: 'Login'), Tab(text: 'Register')],
                ),
              ),
            ),
            const SizedBox(height: 4),
            Expanded(
              child: TabBarView(
                controller: _tabController,
                children: [_buildLoginTab(ty), _buildRegisterTab(ty)],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLoginTab(TyColors ty) {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 28),
          _buildField(ty, 'EMAIL', 'you@example.com', _loginEmailCtrl,
              icon: Icons.email_outlined, type: TextInputType.emailAddress),
          const SizedBox(height: 20),
          _buildField(ty, 'PASSWORD', '••••••••', _loginPasswordCtrl,
              icon: Icons.lock_outline_rounded,
              obscure: _loginObscure,
              onToggleObscure: () => setState(() => _loginObscure = !_loginObscure)),
          if (_error.isNotEmpty) ...[
            const SizedBox(height: 16),
            Text(_error, style: TyType.sans(13, color: ty.rose, weight: FontWeight.w600)),
          ],
          const SizedBox(height: 36),
          TyButton(
            _isLoading ? 'Signing in...' : 'Sign In',
            full: true,
            onTap: _handleLogin,
            enabled: !_isLoading,
          ),
          if (widget.onAuthenticated == null) ...[
            const SizedBox(height: 28),
            _buildDivider(ty),
            const SizedBox(height: 28),
            Center(
              child: TextButton(
                onPressed: _handleSkip,
                child: Text('Continue as Guest',
                    style: TyType.sans(14, color: ty.ink3, weight: FontWeight.w600)),
              ),
            ),
          ],
          const SizedBox(height: 32),
        ],
      ),
    );
  }

  Widget _buildRegisterTab(TyColors ty) {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 28),
          _buildField(ty, 'FULL NAME (OPTIONAL)', 'Rahul Sharma', _regNameCtrl,
              icon: Icons.person_outline_rounded),
          const SizedBox(height: 20),
          _buildField(ty, 'EMAIL', 'you@example.com', _regEmailCtrl,
              icon: Icons.email_outlined, type: TextInputType.emailAddress),
          const SizedBox(height: 20),
          _buildField(ty, 'PASSWORD', '••••••••', _regPasswordCtrl,
              icon: Icons.lock_outline_rounded,
              obscure: _regObscure,
              onToggleObscure: () => setState(() => _regObscure = !_regObscure)),
          const SizedBox(height: 20),
          _buildField(ty, 'CONFIRM PASSWORD', '••••••••', _regConfirmCtrl,
              icon: Icons.lock_outline_rounded,
              obscure: _regConfirmObscure,
              onToggleObscure: () => setState(() => _regConfirmObscure = !_regConfirmObscure)),
          if (_error.isNotEmpty) ...[
            const SizedBox(height: 16),
            Text(_error, style: TyType.sans(13, color: ty.rose, weight: FontWeight.w600)),
          ],
          const SizedBox(height: 36),
          TyButton(
            _isLoading ? 'Creating account...' : 'Create Account',
            full: true,
            onTap: _handleRegister,
            enabled: !_isLoading,
          ),
          const SizedBox(height: 32),
        ],
      ),
    );
  }

  Widget _buildDivider(TyColors ty) {
    return Row(
      children: [
        Expanded(child: Divider(color: ty.line)),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Text('OR', style: TyType.eyebrow(10, color: ty.ink3)),
        ),
        Expanded(child: Divider(color: ty.line)),
      ],
    );
  }

  Widget _buildField(
    TyColors ty,
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
        Text(label, style: TyType.eyebrow(11, color: ty.ink3)),
        const SizedBox(height: 12),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          decoration: BoxDecoration(
            color: ty.surface,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: ty.line),
          ),
          child: Row(
            children: [
              if (icon != null) ...[
                Icon(icon, size: 20, color: ty.ink3),
                const SizedBox(width: 12),
              ],
              Expanded(
                child: TextField(
                  controller: ctrl,
                  keyboardType: type,
                  obscureText: obscure ?? false,
                  style: TyType.sans(16, color: ty.ink, weight: FontWeight.w600),
                  decoration: InputDecoration(
                    hintText: hint,
                    hintStyle: TyType.sans(16, color: ty.ink3.withValues(alpha: 0.5)),
                    border: InputBorder.none,
                  ),
                ),
              ),
              if (onToggleObscure != null)
                GestureDetector(
                  onTap: onToggleObscure,
                  child: Icon(
                    (obscure ?? true) ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                    size: 20,
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
