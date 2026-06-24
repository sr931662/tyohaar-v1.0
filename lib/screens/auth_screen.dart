import 'package:flutter/material.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../widgets/ty_button.dart';
import '../widgets/common.dart';
import '../data/auth_manager.dart';
import 'root_nav.dart';

enum AuthMode { login, signup }

class AuthScreen extends StatefulWidget {
  final VoidCallback? onAuthenticated;
  const AuthScreen({super.key, this.onAuthenticated});

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  AuthMode _mode = AuthMode.login;
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  final TextEditingController _nameController = TextEditingController();
  bool _isLoading = false;
  bool _obscurePassword = true;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    _nameController.dispose();
    super.dispose();
  }

  void _toggleMode() {
    setState(() {
      _mode = _mode == AuthMode.login ? AuthMode.signup : AuthMode.login;
    });
  }

  Future<void> _handleSubmit() async {
    if (_emailController.text.isEmpty || _passwordController.text.isEmpty) return;
    if (_mode == AuthMode.signup && _nameController.text.isEmpty) return;

    setState(() => _isLoading = true);
    
    // Simulate API call
    await Future.delayed(const Duration(seconds: 1));
    
    if (!mounted) return;
    setState(() => _isLoading = false);

    AuthManager.instance.login();

    if (widget.onAuthenticated != null) {
      widget.onAuthenticated!();
      Navigator.pop(context);
    } else {
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => const RootNav()),
      );
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
      appBar: tyAppBar(context, title: _mode == AuthMode.login ? 'Sign In' : 'Create Account'),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 32),
              Text(
                _mode == AuthMode.login ? 'Welcome Back' : 'Join Tyohaar',
                style: TyType.display(32, color: ty.ink),
              ),
              const SizedBox(height: 8),
              Text(
                _mode == AuthMode.login 
                  ? 'Sign in to manage your celebrations and discover new trends.' 
                  : 'Start your journey of creating unforgettable moments with us.',
                style: TyType.sans(15, color: ty.ink2, height: 1.5),
              ),
              const SizedBox(height: 40),
              
              if (_mode == AuthMode.signup) ...[
                _buildField(ty, 'FULL NAME', 'Aarav Sharma', _nameController, icon: Icons.person_outline_rounded),
                const SizedBox(height: 20),
              ],
              
              _buildField(ty, 'EMAIL ADDRESS', 'name@example.com', _emailController, icon: Icons.mail_outline_rounded, type: TextInputType.emailAddress),
              const SizedBox(height: 20),
              
              _buildField(
                ty, 
                'PASSWORD', 
                '••••••••', 
                _passwordController, 
                icon: Icons.lock_outline_rounded, 
                isPassword: true,
                obscure: _obscurePassword,
                onToggleObscure: () => setState(() => _obscurePassword = !_obscurePassword),
              ),
              
              const SizedBox(height: 40),
              
              TyButton(
                _mode == AuthMode.login ? 'Sign In' : 'Create Account',
                full: true,
                onTap: _handleSubmit,
                enabled: !_isLoading,
              ),
              
              const SizedBox(height: 16),
              
              Center(
                child: TextButton(
                  onPressed: _toggleMode,
                  child: RichText(
                    text: TextSpan(
                      style: TyType.sans(14, color: ty.ink2),
                      children: [
                        TextSpan(text: _mode == AuthMode.login ? 'Don\'t have an account? ' : 'Already have an account? '),
                        TextSpan(
                          text: _mode == AuthMode.login ? 'Sign Up' : 'Log In',
                          style: TyType.sans(14, color: ty.saffron, weight: FontWeight.w700),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              
              if (widget.onAuthenticated == null) ...[
                const SizedBox(height: 24),
                Row(
                  children: [
                    Expanded(child: Divider(color: ty.line)),
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      child: Text('OR', style: TyType.eyebrow(10, color: ty.ink3)),
                    ),
                    Expanded(child: Divider(color: ty.line)),
                  ],
                ),
                const SizedBox(height: 24),
                Center(
                  child: TextButton(
                    onPressed: _handleSkip,
                    child: Text(
                      'Continue as Guest',
                      style: TyType.sans(14, color: ty.ink3, weight: FontWeight.w600),
                    ),
                  ),
                ),
              ],
              const SizedBox(height: 32),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildField(
    TyColors ty, 
    String label, 
    String hint, 
    TextEditingController ctrl, {
    IconData? icon,
    bool isPassword = false,
    bool obscure = false,
    VoidCallback? onToggleObscure,
    TextInputType type = TextInputType.text,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: TyType.eyebrow(11, color: ty.ink3)),
        const SizedBox(height: 12),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
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
                  obscureText: obscure,
                  keyboardType: type,
                  style: TyType.sans(16, color: ty.ink, weight: FontWeight.w600),
                  decoration: InputDecoration(
                    hintText: hint,
                    hintStyle: TyType.sans(16, color: ty.ink3.withOpacity(0.5)),
                    border: InputBorder.none,
                  ),
                ),
              ),
              if (isPassword)
                IconButton(
                  onPressed: onToggleObscure,
                  icon: Icon(
                    obscure ? Icons.visibility_off_outlined : Icons.visibility_outlined,
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
