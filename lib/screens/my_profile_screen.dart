import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/models.dart';
import '../data/services/user_service.dart';
import '../widgets/ty_button.dart';
import '../widgets/common.dart';

class MyProfileScreen extends StatefulWidget {
  const MyProfileScreen({super.key});

  @override
  State<MyProfileScreen> createState() => _MyProfileScreenState();
}

class _MyProfileScreenState extends State<MyProfileScreen> {
  final UserService _userService = UserService();
  User? _user;
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  Future<void> _loadProfile() async {
    setState(() { _isLoading = true; _error = null; });
    try {
      final user = await _userService.getMe();
      if (mounted) setState(() { _user = user; _isLoading = false; });
    } catch (e) {
      if (mounted) setState(() { _error = 'Could not load profile.'; _isLoading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    
    if (_isLoading) {
      return Scaffold(backgroundColor: ty.paper, body: const Center(child: CircularProgressIndicator()));
    }

    if (_error != null) {
      return Scaffold(
        backgroundColor: ty.paper,
        appBar: tyAppBar(context, title: 'My Profile'),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.error_outline_rounded, size: 48, color: ty.rose),
              const SizedBox(height: 12),
              Text(_error!, style: TyType.sans(14, color: ty.ink2)),
              const SizedBox(height: 16),
              TextButton(
                onPressed: _loadProfile,
                child: Text('Try Again', style: TyType.sans(14, color: ty.saffron, weight: FontWeight.w700)),
              ),
            ],
          ),
        ),
      );
    }

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: 'My Profile'),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
        children: [
          Center(
            child: Stack(
              children: [
                ClipOval(
                  child: _user?.profilePhotoUrl != null
                    ? CachedNetworkImage(
                        imageUrl: _user!.profilePhotoUrl!,
                        width: 100,
                        height: 100,
                        fit: BoxFit.cover,
                        placeholder: (context, url) => Container(color: ty.saffronSoft, width: 100, height: 100),
                        errorWidget: (context, url, error) => _buildInitials(ty),
                      )
                    : _buildInitials(ty),
                ),
                Positioned(
                  bottom: 0,
                  right: 0,
                  child: Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(color: ty.ink, shape: BoxShape.circle, border: Border.all(color: ty.paper, width: 2)),
                    child: const Icon(Icons.camera_alt_rounded, color: Colors.white, size: 16),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 32),
          _field(context, 'Full Name', _user?.displayName ?? 'Not set'),
          _field(context, 'Email Address', _user?.email ?? 'Not set'),
          _field(context, 'Phone Number', _user?.phone ?? 'Not set'),
          _field(context, 'Role', _user?.role.toUpperCase() ?? 'CUSTOMER'),
          _field(context, 'Account Status', _user?.status.toUpperCase() ?? 'ACTIVE'),
          const SizedBox(height: 40),
          TyButton('Save Changes', full: true, onTap: () => Navigator.pop(context)),
        ],
      ),
    );
  }

  Widget _buildInitials(TyColors ty) {
    final initial = _user?.displayName.substring(0, 1).toUpperCase() ?? '?';
    return Container(
      width: 100,
      height: 100,
      alignment: Alignment.center,
      decoration: BoxDecoration(color: ty.saffron, shape: BoxShape.circle),
      child: Text(initial, style: TextStyle(color: ty.onPrimary, fontWeight: FontWeight.w800, fontSize: 40)),
    );
  }

  Widget _field(BuildContext context, String label, String value) {
    final ty = context.ty;
    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label.toUpperCase(), style: TyType.eyebrow(11, color: ty.ink3)),
          const SizedBox(height: 8),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            decoration: BoxDecoration(
              color: ty.surface,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: ty.line, width: 1.5),
            ),
            child: Text(value, style: TyType.sans(15, color: ty.ink, weight: FontWeight.w600)),
          ),
        ],
      ),
    );
  }
}
