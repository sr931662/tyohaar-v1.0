import 'dart:io';
import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:image_picker/image_picker.dart';
import 'package:image_cropper/image_cropper.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/models.dart';
import '../data/services/user_service.dart';
import '../data/services/vendor_service.dart';
import '../data/services/media_service.dart';
import '../data/auth_manager.dart';
import '../widgets/ty_button.dart';
import '../widgets/common.dart';
import 'vendor/vendor_availability_screen.dart';

class MyProfileScreen extends StatefulWidget {
  const MyProfileScreen({super.key});

  @override
  State<MyProfileScreen> createState() => _MyProfileScreenState();
}

class _MyProfileScreenState extends State<MyProfileScreen> {
  final UserService _userService = UserService();
  final VendorService _vendorService = VendorService();
  final MediaService _mediaService = MediaService();
  User? _user;
  VendorProfile? _vendorProfile;
  bool _isLoading = true;
  bool _isSaving = false;
  bool _isUploading = false;
  String? _error;

  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _phoneController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    _phoneController.dispose();
    super.dispose();
  }

  Future<void> _loadProfile() async {
    setState(() { _isLoading = true; _error = null; });
    try {
      final user = await _userService.getMe();
      
      VendorProfile? vp;
      if (user.role == 'vendor') {
        vp = await _vendorService.getMyVendorProfile();
      }

      if (mounted) {
        setState(() {
          _user = user;
          _vendorProfile = vp;
          _nameController.text = user.fullName ?? user.firstName ?? '';
          _emailController.text = user.email ?? '';
          _phoneController.text = user.phone ?? '';
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) setState(() { _error = 'Could not load profile.'; _isLoading = false; });
    }
  }

  Future<void> _pickAndUploadImage() async {
    final picker = ImagePicker();
    final image = await picker.pickImage(source: ImageSource.gallery);
    
    if (image == null) return;

    final croppedFile = await ImageCropper().cropImage(
      sourcePath: image.path,
      aspectRatio: const CropAspectRatio(ratioX: 1, ratioY: 1),
      uiSettings: [
        AndroidUiSettings(
          toolbarTitle: 'Edit Profile Picture',
          toolbarColor: context.ty.ink,
          toolbarWidgetColor: Colors.white,
          initAspectRatio: CropAspectRatioPreset.square,
          lockAspectRatio: true,
        ),
        IOSUiSettings(
          title: 'Edit Profile Picture',
        ),
      ],
    );

    if (croppedFile == null) return;

    setState(() => _isUploading = true);
    try {
      final url = await _mediaService.uploadProfilePicture(File(croppedFile.path));
      await _userService.updateExtendedProfile(_user!.id, {'profile_photo_url': url});

      final updatedUser = await _userService.getMe();
      AuthManager.instance.setUser(updatedUser);
      
      if (mounted) {
        setState(() {
          _user = updatedUser;
          _isUploading = false;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Profile picture updated!')),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isUploading = false);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Failed to upload image.')),
        );
      }
    }
  }

  Future<void> _saveChanges() async {
    if (_isSaving) return;
    
    final name = _nameController.text.trim();
    final email = _emailController.text.trim();
    final phone = _phoneController.text.trim();

    if (name.isEmpty || phone.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Name and Phone are required')),
      );
      return;
    }

    setState(() => _isSaving = true);
    try {
      await _userService.updateProfile({
        'full_name': name,
        'email': email.isNotEmpty ? email : null,
        'phone': phone,
      });
      
      // Refresh user data
      final updatedUser = await _userService.getMe();
      AuthManager.instance.setUser(updatedUser);
      
      if (mounted) {
        setState(() {
          _user = updatedUser;
          _isSaving = false;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Profile updated successfully!')),
        );
      }
    } catch (e) {
      debugPrint('Error updating profile: $e');
      if (mounted) {
        setState(() => _isSaving = false);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Failed to update profile. Please try again.')),
        );
      }
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
            child: GestureDetector(
              onTap: _isUploading ? null : _pickAndUploadImage,
              child: Stack(
                children: [
                  ClipOval(
                    child: _isUploading
                      ? Container(
                          width: 100, height: 100,
                          color: ty.saffronSoft,
                          child: const Center(child: CircularProgressIndicator()),
                        )
                      : (_user?.profilePhotoUrl != null
                          ? CachedNetworkImage(
                              imageUrl: _user!.profilePhotoUrl!,
                              width: 100,
                              height: 100,
                              fit: BoxFit.cover,
                              placeholder: (context, url) => Container(color: ty.saffronSoft, width: 100, height: 100),
                              errorWidget: (context, url, error) => _buildInitials(ty),
                            )
                          : _buildInitials(ty)),
                  ),
                  Positioned(
                    bottom: 0,
                    right: 0,
                    child: Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(color: ty.ink, shape: BoxShape.circle, border: Border.all(color: ty.paper, width: 2)),
                      child: _isUploading
                          ? SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                          : const Icon(Icons.camera_alt_rounded, color: Colors.white, size: 16),
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 32),
          _editableField(context, 'Full Name', _nameController, hint: 'e.g. Rahul Sharma'),
          _editableField(context, 'Email Address', _emailController, hint: 'you@example.com', keyboardType: TextInputType.emailAddress),
          _editableField(context, 'Phone Number', _phoneController, hint: '+91 9876543210', keyboardType: TextInputType.phone),
          _field(context, 'Role', _user?.role.toUpperCase() ?? 'CUSTOMER'),
          
          if (_user?.role == 'vendor') ...[
            const SizedBox(height: 32),
            _sectionHeader('Business Availability'),
            const SizedBox(height: 16),
            _availabilityCard(context),
          ],

          const SizedBox(height: 40),
          TyButton(
            _isSaving ? 'Saving...' : 'Save Changes',
            full: true,
            enabled: !_isSaving,
            onTap: _saveChanges,
          ),
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
              color: ty.surface2,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: ty.line, width: 1),
            ),
            child: Text(value, style: TyType.sans(15, color: ty.ink3, weight: FontWeight.w600)),
          ),
        ],
      ),
    );
  }

  Widget _sectionHeader(String label) {
    return Text(label.toUpperCase(), style: TyType.eyebrow(11, color: context.ty.ink3));
  }

  Widget _availabilityCard(BuildContext context) {
    final ty = context.ty;
    // Simplified logic: Assume same hours for all working days for now
    final hours = _vendorProfile?.workingHours?['mon'] ?? {'open': '09:00', 'close': '21:00', 'is_open': true};
    final isOpen = hours['is_open'] == true;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: ty.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: ty.line),
      ),
      child: Column(
        children: [
          Row(
            children: [
              Icon(Icons.schedule_rounded, color: ty.saffron, size: 20),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Working Hours', style: TyType.sans(14.5, color: ty.ink, weight: FontWeight.w700)),
                    Text(isOpen ? '${hours['open']} AM - ${hours['close']} PM' : 'Closed Today', 
                        style: TyType.sans(12.5, color: ty.ink2)),
                  ],
                ),
              ),
              TyButton('Edit', kind: TyButtonKind.ghost, padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6), onTap: () {
                // Navigate to availability screen
                Navigator.of(context).push(MaterialPageRoute(builder: (_) => const VendorAvailabilityScreen()));
              }),
            ],
          ),
        ],
      ),
    );
  }

  Widget _editableField(
    BuildContext context,
    String label,
    TextEditingController controller, {
    String? hint,
    TextInputType keyboardType = TextInputType.text,
  }) {
    final ty = context.ty;
    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label.toUpperCase(), style: TyType.eyebrow(11, color: ty.ink3)),
          const SizedBox(height: 8),
          Container(
            decoration: BoxDecoration(
              color: ty.surface,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: ty.line, width: 1.5),
            ),
            child: TextField(
              controller: controller,
              keyboardType: keyboardType,
              style: TyType.sans(15, color: ty.ink, weight: FontWeight.w600),
              decoration: InputDecoration(
                hintText: hint,
                hintStyle: TyType.sans(15, color: ty.ink3.withValues(alpha: 0.5)),
                contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                border: InputBorder.none,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
