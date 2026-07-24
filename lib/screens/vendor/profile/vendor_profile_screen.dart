import 'dart:io';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';

import '../../../theme/colors.dart';
import '../../../theme/typography.dart';
import '../../../data/auth_manager.dart';
import '../../../data/vendor_models.dart';
import '../../../data/services/vendor_service.dart';

const _vendorTypes = [
  'decorator', 'caterer', 'photographer', 'videographer', 'baker', 'florist',
  'entertainer', 'venue', 'planner', 'makeup_artist', 'mehndi_artist', 'music',
  'multi_service', 'other',
];

const _docTypes = {
  'gst_certificate': 'GST Certificate',
  'pan_card': 'PAN Card',
  'aadhar': 'Aadhaar Card',
  'cancelled_cheque': 'Cancelled Cheque',
  'shop_act_license': 'Shop Act License',
  'incorporation_certificate': 'Incorporation Certificate',
  'other': 'Other',
};

class VendorProfileScreen extends StatefulWidget {
  const VendorProfileScreen({super.key});

  @override
  State<VendorProfileScreen> createState() => _VendorProfileScreenState();
}

class _VendorProfileScreenState extends State<VendorProfileScreen> {
  final _vendorService = VendorService();

  VendorBusinessProfile? _vendor;
  bool _isLoading = true;
  bool _isSaving = false;
  bool _isNew = false;

  final _businessNameCtrl = TextEditingController();
  String _vendorType = 'decorator';
  final _legalNameCtrl = TextEditingController();
  final _gstCtrl = TextEditingController();
  final _panCtrl = TextEditingController();
  final _yearsCtrl = TextEditingController();
  final _establishedCtrl = TextEditingController();
  final _radiusCtrl = TextEditingController();
  final _taglineCtrl = TextEditingController();
  final _aboutCtrl = TextEditingController();
  final _citiesCtrl = TextEditingController();
  final _websiteCtrl = TextEditingController();

  List<VendorGalleryItem> _gallery = [];
  List<VendorDocument> _documents = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _isLoading = true);
    try {
      final vendor = await _vendorService.getMe();
      if (vendor == null) {
        setState(() { _isNew = true; _isLoading = false; });
        return;
      }
      _businessNameCtrl.text = vendor.businessName;
      _vendorType = vendor.vendorType;
      _legalNameCtrl.text = vendor.legalName ?? '';
      _gstCtrl.text = vendor.gstNumber ?? '';
      _panCtrl.text = vendor.panNumber ?? '';
      _yearsCtrl.text = vendor.yearsOfExperience?.toString() ?? '';
      _establishedCtrl.text = vendor.establishedYear?.toString() ?? '';
      _radiusCtrl.text = vendor.serviceRadiusKm?.toString() ?? '';
      _taglineCtrl.text = vendor.profile?.tagline ?? '';
      _aboutCtrl.text = vendor.profile?.about ?? '';
      _citiesCtrl.text = vendor.profile?.operatingCities.join(', ') ?? '';
      _websiteCtrl.text = vendor.profile?.websiteUrl ?? '';

      final results = await Future.wait([
        _vendorService.listGallery(vendor.id),
        _vendorService.listDocuments(vendor.id),
      ]);
      if (mounted) {
        setState(() {
          _vendor = vendor;
          _gallery = results[0] as List<VendorGalleryItem>;
          _documents = results[1] as List<VendorDocument>;
          _isLoading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _save() async {
    if (_businessNameCtrl.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Business name is required.')));
      return;
    }
    setState(() => _isSaving = true);
    try {
      if (_isNew) {
        final userId = AuthManager.instance.currentUser?.id;
        final vendor = await _vendorService.create({
          'user_id': userId,
          'business_name': _businessNameCtrl.text.trim(),
          'vendor_type': _vendorType,
          if (_legalNameCtrl.text.trim().isNotEmpty) 'legal_name': _legalNameCtrl.text.trim(),
          if (_gstCtrl.text.trim().isNotEmpty) 'gst_number': _gstCtrl.text.trim().toUpperCase(),
          if (_panCtrl.text.trim().isNotEmpty) 'pan_number': _panCtrl.text.trim().toUpperCase(),
          if (_yearsCtrl.text.trim().isNotEmpty) 'years_of_experience': int.tryParse(_yearsCtrl.text.trim()),
          if (_establishedCtrl.text.trim().isNotEmpty) 'established_year': int.tryParse(_establishedCtrl.text.trim()),
          if (_radiusCtrl.text.trim().isNotEmpty) 'service_radius_km': double.tryParse(_radiusCtrl.text.trim()),
        });
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Vendor profile created!')));
          setState(() { _vendor = vendor; _isNew = false; });
        }
      } else {
        await Future.wait([
          _vendorService.update(_vendor!.id, {
            'legal_name': _legalNameCtrl.text.trim().isEmpty ? null : _legalNameCtrl.text.trim(),
            'gst_number': _gstCtrl.text.trim().isEmpty ? null : _gstCtrl.text.trim().toUpperCase(),
            'pan_number': _panCtrl.text.trim().isEmpty ? null : _panCtrl.text.trim().toUpperCase(),
            'years_of_experience': int.tryParse(_yearsCtrl.text.trim()),
            'established_year': int.tryParse(_establishedCtrl.text.trim()),
            'service_radius_km': double.tryParse(_radiusCtrl.text.trim()),
          }),
          _vendorService.updateProfile(_vendor!.id, {
            'tagline': _taglineCtrl.text.trim().isEmpty ? null : _taglineCtrl.text.trim(),
            'about': _aboutCtrl.text.trim().isEmpty ? null : _aboutCtrl.text.trim(),
            'operating_cities': _citiesCtrl.text.split(',').map((c) => c.trim()).where((c) => c.isNotEmpty).toList(),
            'website_url': _websiteCtrl.text.trim().isEmpty ? null : _websiteCtrl.text.trim(),
          }),
        ]);
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Profile updated.')));
      }
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Could not save profile.')));
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  Future<void> _addGalleryPhoto() async {
    if (_vendor == null) return;
    try {
      final image = await ImagePicker().pickImage(source: ImageSource.gallery, imageQuality: 85);
      if (image == null) return;
      final url = await _vendorService.uploadImage(File(image.path), 'vendor_gallery');
      await _vendorService.addGalleryItem(_vendor!.id, {'media_url': url, 'media_type': 'image'});
      _load();
    } on PlatformException {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Permission needed — enable photo access in Settings.')),
        );
      }
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Upload failed.')));
    }
  }

  Future<void> _deleteGalleryItem(VendorGalleryItem item) async {
    if (_vendor == null) return;
    try {
      await _vendorService.deleteGalleryItem(_vendor!.id, item.id);
      _load();
    } catch (_) {}
  }

  Future<void> _addDocument(String docType) async {
    if (_vendor == null) return;
    try {
      final image = await ImagePicker().pickImage(source: ImageSource.gallery, imageQuality: 85);
      if (image == null) return;
      final url = await _vendorService.uploadImage(File(image.path), 'vendor_document');
      await _vendorService.addDocument(_vendor!.id, documentType: docType, documentUrl: url);
      _load();
    } on PlatformException {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Permission needed — enable photo access in Settings.')),
        );
      }
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Upload failed.')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;

    if (_isLoading) {
      return const Scaffold(backgroundColor: Colors.transparent, body: Center(child: CircularProgressIndicator()));
    }

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: ListView(
        padding: const EdgeInsets.all(18),
        children: [
          Text('Business Information', style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
          const SizedBox(height: 10),
          _field(ty, 'Business Name *', _businessNameCtrl, enabled: _isNew),
          _labeled(ty, 'Vendor Type', DropdownButtonFormField<String>(
            value: _vendorType,
            items: _vendorTypes.map((t) => DropdownMenuItem(value: t, child: Text(t.replaceAll('_', ' ')))).toList(),
            onChanged: _isNew ? (v) => setState(() => _vendorType = v ?? _vendorType) : null,
          )),
          _field(ty, 'Legal Name', _legalNameCtrl),
          _field(ty, 'GST Number', _gstCtrl),
          _field(ty, 'PAN Number', _panCtrl),
          Row(children: [
            Expanded(child: _field(ty, 'Years of Experience', _yearsCtrl, keyboardType: TextInputType.number)),
            const SizedBox(width: 12),
            Expanded(child: _field(ty, 'Established Year', _establishedCtrl, keyboardType: TextInputType.number)),
          ]),
          _field(ty, 'Service Radius (km)', _radiusCtrl, keyboardType: TextInputType.number),
          const SizedBox(height: 16),
          Text('About Your Business', style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
          const SizedBox(height: 10),
          _field(ty, 'Tagline', _taglineCtrl),
          _field(ty, 'About', _aboutCtrl, maxLines: 4),
          const SizedBox(height: 16),
          Text('Location & Online Presence', style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
          const SizedBox(height: 10),
          _field(ty, 'Operating Cities (comma-separated)', _citiesCtrl),
          _field(ty, 'Website URL', _websiteCtrl),
          const SizedBox(height: 20),
          ElevatedButton(
            onPressed: _isSaving ? null : _save,
            child: Text(_isSaving ? 'Saving…' : (_isNew ? 'Create Profile' : 'Save Changes')),
          ),
          if (!_isNew) ...[
            const SizedBox(height: 28),
            Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
              Text('Business Gallery', style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
              TextButton(onPressed: _addGalleryPhoto, child: const Text('+ Add Photo')),
            ]),
            const SizedBox(height: 10),
            if (_gallery.isEmpty)
              Text('No photos yet', style: TyType.sans(13, color: ty.ink2))
            else
              GridView.count(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                crossAxisCount: 3,
                mainAxisSpacing: 8,
                crossAxisSpacing: 8,
                children: _gallery.map((g) => Stack(
                      children: [
                        Positioned.fill(child: ClipRRect(borderRadius: BorderRadius.circular(10), child: CachedNetworkImage(
                          imageUrl: g.mediaUrl,
                          fit: BoxFit.cover,
                          memCacheWidth: 300,
                          placeholder: (context, url) => Container(color: Colors.black12),
                          errorWidget: (context, url, error) => Container(color: Colors.black12, child: const Icon(Icons.broken_image_outlined, size: 20)),
                        ))),
                        Positioned(
                          top: 2, right: 2,
                          child: GestureDetector(
                            onTap: () => _deleteGalleryItem(g),
                            child: const CircleAvatar(radius: 11, backgroundColor: Colors.black54, child: Icon(Icons.close, size: 14, color: Colors.white)),
                          ),
                        ),
                      ],
                    )).toList(),
              ),
            const SizedBox(height: 28),
            Text('Business Documents', style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
            const SizedBox(height: 10),
            if (_documents.isEmpty)
              Text('No documents uploaded yet', style: TyType.sans(13, color: ty.ink2))
            else
              ..._documents.map((d) => Container(
                    margin: const EdgeInsets.only(bottom: 8),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(10), border: Border.all(color: ty.line)),
                    child: Row(
                      children: [
                        const Icon(Icons.description_outlined),
                        const SizedBox(width: 10),
                        Expanded(child: Text(_docTypes[d.documentType] ?? d.documentType, style: TyType.sans(13, color: ty.ink))),
                        Text(d.verificationStatus, style: TyType.sans(11, color: ty.ink3)),
                      ],
                    ),
                  )),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8, runSpacing: 8,
              children: _docTypes.entries.map((e) => OutlinedButton(
                    onPressed: () => _addDocument(e.key),
                    child: Text('+ ${e.value}'),
                  )).toList(),
            ),
          ],
        ],
      ),
    );
  }

  Widget _labeled(TyColors ty, String label, Widget child) => Padding(
        padding: const EdgeInsets.only(bottom: 14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: TyType.sans(12.5, color: ty.ink2, weight: FontWeight.w600)),
            const SizedBox(height: 6),
            child,
          ],
        ),
      );

  Widget _field(TyColors ty, String label, TextEditingController ctrl, {int maxLines = 1, TextInputType? keyboardType, bool enabled = true}) {
    return _labeled(
      ty, label,
      TextField(
        controller: ctrl,
        maxLines: maxLines,
        keyboardType: keyboardType,
        enabled: enabled,
        decoration: InputDecoration(
          filled: true,
          fillColor: ty.surface,
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: ty.line)),
          isDense: true,
        ),
      ),
    );
  }
}
