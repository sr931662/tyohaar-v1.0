import 'package:flutter/material.dart';
import 'package:dio/dio.dart';

import '../../../theme/colors.dart';
import '../../../theme/typography.dart';
import '../../../theme/responsive.dart';
import '../../../widgets/ty_button.dart';
import '../../../widgets/common.dart';
import '../../../data/app_state.dart';
import '../../../data/auth_manager.dart';
import '../../../data/services/auth_service.dart';
import '../vendor_root_nav.dart';

const _vendorTypes = [
  {'value': 'decorator', 'label': 'Decorator'},
  {'value': 'caterer', 'label': 'Caterer'},
  {'value': 'photographer', 'label': 'Photographer'},
  {'value': 'videographer', 'label': 'Videographer'},
  {'value': 'baker', 'label': 'Baker'},
  {'value': 'florist', 'label': 'Florist'},
  {'value': 'entertainer', 'label': 'Entertainer'},
  {'value': 'venue', 'label': 'Venue'},
  {'value': 'planner', 'label': 'Event Planner'},
  {'value': 'makeup_artist', 'label': 'Makeup Artist'},
  {'value': 'mehndi_artist', 'label': 'Mehndi Artist'},
  {'value': 'music', 'label': 'Music / DJ'},
  {'value': 'multi_service', 'label': 'Multi-Service'},
  {'value': 'other', 'label': 'Other'},
];

class VendorRegisterScreen extends StatefulWidget {
  const VendorRegisterScreen({super.key});

  @override
  State<VendorRegisterScreen> createState() => _VendorRegisterScreenState();
}

class _VendorRegisterScreenState extends State<VendorRegisterScreen> {
  final _nameCtrl = TextEditingController();
  final _emailCtrl = TextEditingController();
  final _phoneCtrl = TextEditingController();
  final _businessCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  final _confirmCtrl = TextEditingController();
  String _vendorType = 'decorator';
  bool _isLoading = false;
  String _error = '';
  bool _obscure = true;

  @override
  void dispose() {
    _nameCtrl.dispose();
    _emailCtrl.dispose();
    _phoneCtrl.dispose();
    _businessCtrl.dispose();
    _passwordCtrl.dispose();
    _confirmCtrl.dispose();
    super.dispose();
  }

  Future<void> _handleSubmit() async {
    if (_isLoading) return;
    if (_nameCtrl.text.trim().isEmpty ||
        _emailCtrl.text.trim().isEmpty ||
        _phoneCtrl.text.trim().isEmpty ||
        _businessCtrl.text.trim().isEmpty ||
        _passwordCtrl.text.isEmpty) {
      setState(() => _error = 'Please fill in all fields.');
      return;
    }
    if (_passwordCtrl.text != _confirmCtrl.text) {
      setState(() => _error = 'Passwords do not match.');
      return;
    }
    if (_passwordCtrl.text.length < 8) {
      setState(() => _error = 'Password must be at least 8 characters.');
      return;
    }

    setState(() { _isLoading = true; _error = ''; });
    try {
      final creds = await AuthService().vendorRegister(
        fullName: _nameCtrl.text.trim(),
        email: _emailCtrl.text.trim(),
        phone: _phoneCtrl.text.trim(),
        businessName: _businessCtrl.text.trim(),
        vendorType: _vendorType,
        password: _passwordCtrl.text,
      );
      // Set POV before flipping isAuthenticated so the customer shell never
      // gets a chance to render — see auth_screen.dart's _onSuccess for why.
      AppState.instance.applyRole(creds.user.role);
      await AuthManager.instance.login(creds.accessToken, creds.refreshToken, creds.user);
      if (!mounted) return;
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => const VendorRootNav()),
        (route) => false,
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

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final resp = context.resp;

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: 'Partner Registration'),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: EdgeInsets.symmetric(horizontal: resp.w(24)),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SizedBox(height: resp.h(20)),
              Text('List your business on Tyohaar', style: TyType.display(resp.sp(26), color: ty.ink)),
              SizedBox(height: resp.h(8)),
              Text(
                'Your account will be reviewed before it goes live.',
                style: TyType.sans(resp.sp(14), color: ty.ink2),
              ),
              SizedBox(height: resp.h(28)),
              _field(ty, resp, 'FULL NAME', _nameCtrl),
              SizedBox(height: resp.h(16)),
              _field(ty, resp, 'EMAIL', _emailCtrl, type: TextInputType.emailAddress),
              SizedBox(height: resp.h(16)),
              _field(ty, resp, 'PHONE', _phoneCtrl, type: TextInputType.phone),
              SizedBox(height: resp.h(16)),
              _field(ty, resp, 'BUSINESS NAME', _businessCtrl),
              SizedBox(height: resp.h(16)),
              Text('VENDOR TYPE', style: TyType.eyebrow(resp.sp(11), color: ty.ink3)),
              SizedBox(height: resp.h(8)),
              Container(
                padding: EdgeInsets.symmetric(horizontal: resp.w(16)),
                decoration: BoxDecoration(
                  color: ty.surface,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: ty.line),
                ),
                child: DropdownButtonHideUnderline(
                  child: DropdownButton<String>(
                    value: _vendorType,
                    isExpanded: true,
                    items: _vendorTypes
                        .map((t) => DropdownMenuItem(value: t['value'], child: Text(t['label']!)))
                        .toList(),
                    onChanged: (v) => setState(() => _vendorType = v ?? _vendorType),
                  ),
                ),
              ),
              SizedBox(height: resp.h(16)),
              _field(ty, resp, 'PASSWORD', _passwordCtrl,
                  obscure: _obscure, onToggle: () => setState(() => _obscure = !_obscure)),
              SizedBox(height: resp.h(16)),
              _field(ty, resp, 'CONFIRM PASSWORD', _confirmCtrl, obscure: _obscure),
              if (_error.isNotEmpty) ...[
                SizedBox(height: resp.h(16)),
                Text(_error, style: TyType.sans(resp.sp(13), color: ty.rose, weight: FontWeight.w600)),
              ],
              SizedBox(height: resp.h(32)),
              TyButton(
                _isLoading ? 'Submitting...' : 'Register as Partner',
                full: true,
                onTap: _handleSubmit,
                enabled: !_isLoading,
              ),
              SizedBox(height: resp.h(32)),
            ],
          ),
        ),
      ),
    );
  }

  Widget _field(TyColors ty, TyResponsive resp, String label, TextEditingController ctrl,
      {TextInputType type = TextInputType.text, bool? obscure, VoidCallback? onToggle}) {
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
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: ctrl,
                  keyboardType: type,
                  obscureText: obscure ?? false,
                  style: TyType.sans(resp.sp(15), color: ty.ink),
                  decoration: const InputDecoration(border: InputBorder.none, isDense: true, contentPadding: EdgeInsets.symmetric(vertical: 14)),
                ),
              ),
              if (onToggle != null)
                GestureDetector(
                  onTap: onToggle,
                  child: Icon(obscure! ? Icons.visibility_off_outlined : Icons.visibility_outlined, size: 20, color: ty.ink3),
                ),
            ],
          ),
        ),
      ],
    );
  }
}
