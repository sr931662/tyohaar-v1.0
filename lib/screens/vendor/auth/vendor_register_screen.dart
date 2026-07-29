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
import '../../../l10n/generated/app_localizations.dart';

const _vendorTypeValues = [
  'decorator',
  'caterer',
  'photographer',
  'videographer',
  'baker',
  'florist',
  'entertainer',
  'venue',
  'planner',
  'makeup_artist',
  'mehndi_artist',
  'music',
  'multi_service',
  'other',
];

String _vendorTypeLabel(BuildContext context, String value) {
  final l10n = AppLocalizations.of(context)!;
  switch (value) {
    case 'decorator':
      return l10n.vendorRegisterTypeDecorator;
    case 'caterer':
      return l10n.vendorRegisterTypeCaterer;
    case 'photographer':
      return l10n.vendorRegisterTypePhotographer;
    case 'videographer':
      return l10n.vendorRegisterTypeVideographer;
    case 'baker':
      return l10n.vendorRegisterTypeBaker;
    case 'florist':
      return l10n.vendorRegisterTypeFlorist;
    case 'entertainer':
      return l10n.vendorRegisterTypeEntertainer;
    case 'venue':
      return l10n.vendorRegisterTypeVenue;
    case 'planner':
      return l10n.vendorRegisterTypePlanner;
    case 'makeup_artist':
      return l10n.vendorRegisterTypeMakeupArtist;
    case 'mehndi_artist':
      return l10n.vendorRegisterTypeMehndiArtist;
    case 'music':
      return l10n.vendorRegisterTypeMusic;
    case 'multi_service':
      return l10n.vendorRegisterTypeMultiService;
    case 'other':
      return l10n.vendorRegisterTypeOther;
    default:
      return value;
  }
}

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
    final l10n = AppLocalizations.of(context)!;
    if (_nameCtrl.text.trim().isEmpty ||
        _emailCtrl.text.trim().isEmpty ||
        _phoneCtrl.text.trim().isEmpty ||
        _businessCtrl.text.trim().isEmpty ||
        _passwordCtrl.text.isEmpty) {
      setState(() => _error = l10n.vendorRegisterFillAllFieldsError);
      return;
    }
    if (_passwordCtrl.text != _confirmCtrl.text) {
      setState(() => _error = l10n.vendorRegisterPasswordMismatchError);
      return;
    }
    if (_passwordCtrl.text.length < 8) {
      setState(() => _error = l10n.vendorRegisterPasswordTooShortError);
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
      String msg = l10n.vendorRegisterFailedError;
      if (detail is Map) {
        msg = detail['detail'] as String? ?? detail['message'] as String? ?? msg;
      } else if (detail is String) {
        msg = detail;
      }
      if (mounted) setState(() { _isLoading = false; _error = msg; });
    } catch (_) {
      if (mounted) setState(() { _isLoading = false; _error = l10n.vendorRegisterUnexpectedError; });
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final resp = context.resp;
    final l10n = AppLocalizations.of(context)!;

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: l10n.vendorRegisterTitle),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: EdgeInsets.symmetric(horizontal: resp.w(24)),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SizedBox(height: resp.h(20)),
              Text(l10n.vendorRegisterHeading, style: TyType.display(resp.sp(26), color: ty.ink)),
              SizedBox(height: resp.h(8)),
              Text(
                l10n.vendorRegisterSubheading,
                style: TyType.sans(resp.sp(14), color: ty.ink2),
              ),
              SizedBox(height: resp.h(28)),
              _field(ty, resp, l10n.vendorRegisterFullNameLabel, _nameCtrl),
              SizedBox(height: resp.h(16)),
              _field(ty, resp, l10n.vendorRegisterEmailLabel, _emailCtrl, type: TextInputType.emailAddress, helperText: l10n.vendorRegisterEmailFormatHelperText),
              SizedBox(height: resp.h(16)),
              _field(ty, resp, l10n.vendorRegisterPhoneLabel, _phoneCtrl, type: TextInputType.phone, helperText: l10n.vendorRegisterPhoneFormatHelperText),
              SizedBox(height: resp.h(16)),
              _field(ty, resp, l10n.vendorRegisterBusinessNameLabel, _businessCtrl),
              SizedBox(height: resp.h(16)),
              Text(l10n.vendorRegisterVendorTypeLabel, style: TyType.eyebrow(resp.sp(11), color: ty.ink3)),
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
                    items: _vendorTypeValues
                        .map((v) => DropdownMenuItem(value: v, child: Text(_vendorTypeLabel(context, v))))
                        .toList(),
                    onChanged: (v) => setState(() => _vendorType = v ?? _vendorType),
                  ),
                ),
              ),
              SizedBox(height: resp.h(16)),
              _field(ty, resp, l10n.vendorRegisterPasswordLabel, _passwordCtrl,
                  obscure: _obscure, onToggle: () => setState(() => _obscure = !_obscure)),
              SizedBox(height: resp.h(16)),
              _field(ty, resp, l10n.vendorRegisterConfirmPasswordLabel, _confirmCtrl, obscure: _obscure),
              if (_error.isNotEmpty) ...[
                SizedBox(height: resp.h(16)),
                Text(_error, style: TyType.sans(resp.sp(13), color: ty.rose, weight: FontWeight.w600)),
              ],
              SizedBox(height: resp.h(32)),
              TyButton(
                _isLoading ? l10n.vendorRegisterSubmittingLabel : l10n.vendorRegisterSubmitLabel,
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
      {TextInputType type = TextInputType.text, bool? obscure, VoidCallback? onToggle, String? helperText}) {
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
        if (helperText != null) ...[
          SizedBox(height: resp.h(4)),
          Text(helperText, style: TyType.sans(resp.sp(11), color: ty.ink3)),
        ],
      ],
    );
  }
}
