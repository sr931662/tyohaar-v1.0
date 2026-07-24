import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';

import '../../../theme/colors.dart';
import '../../../theme/typography.dart';
import '../../../data/models.dart';
import '../../../data/vendor_models.dart';
import '../../../data/services/vendor_service.dart';
import '../../../data/services/package_service.dart';

/// Create/edit a package — mirrors the web PackageFormModal.
class VendorPackageFormScreen extends StatefulWidget {
  final VendorPackage? existing;
  const VendorPackageFormScreen({super.key, this.existing});

  @override
  State<VendorPackageFormScreen> createState() => _VendorPackageFormScreenState();
}

class _VendorPackageFormScreenState extends State<VendorPackageFormScreen> {
  final _vendorService = VendorService();
  final _packageService = PackageService();

  final _nameCtrl = TextEditingController();
  final _shortDescCtrl = TextEditingController();
  final _descCtrl = TextEditingController();
  final _priceCtrl = TextEditingController();
  final _minGuestsCtrl = TextEditingController();
  final _maxGuestsCtrl = TextEditingController();
  final _durationCtrl = TextEditingController();
  final _cityCtrl = TextEditingController();
  bool _isCustomizable = false;
  String? _coverImageUrl;
  bool _uploadingCover = false;
  final Set<String> _selectedOccasionIds = {};
  final Set<String> _selectedThemeIds = {};
  List<Occasion> _occasions = [];
  List<CelebrationTheme> _themes = [];
  bool _isSaving = false;
  bool _isLoadingOccasions = true;
  bool _isLoadingThemes = true;

  @override
  void initState() {
    super.initState();
    final p = widget.existing;
    if (p != null) {
      _nameCtrl.text = p.name;
      _shortDescCtrl.text = p.shortDescription ?? '';
      _descCtrl.text = p.description ?? '';
      _priceCtrl.text = p.basePrice.toStringAsFixed(0);
      _minGuestsCtrl.text = p.minGuests?.toString() ?? '';
      _maxGuestsCtrl.text = p.maxGuests?.toString() ?? '';
      _durationCtrl.text = p.durationHours?.toString() ?? '';
      _cityCtrl.text = p.citySlug ?? '';
      _isCustomizable = p.isCustomizable;
      _coverImageUrl = p.coverImageUrl;
      _selectedOccasionIds.addAll(p.occasionIds);
      _selectedThemeIds.addAll(p.themeIds);
    }
    _loadData();
  }

  Future<void> _loadData() async {
    _loadOccasions();
    _loadThemes();
  }

  Future<void> _loadOccasions() async {
    try {
      final occasions = await _packageService.listOccasions();
      if (mounted) setState(() { _occasions = occasions; _isLoadingOccasions = false; });
    } catch (_) {
      if (mounted) setState(() => _isLoadingOccasions = false);
    }
  }

  Future<void> _loadThemes() async {
    try {
      final themes = await _packageService.listThemes();
      if (mounted) setState(() { _themes = themes; _isLoadingThemes = false; });
    } catch (_) {
      if (mounted) setState(() => _isLoadingThemes = false);
    }
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    _shortDescCtrl.dispose();
    _descCtrl.dispose();
    _priceCtrl.dispose();
    _minGuestsCtrl.dispose();
    _maxGuestsCtrl.dispose();
    _durationCtrl.dispose();
    _cityCtrl.dispose();
    super.dispose();
  }

  Future<void> _pickCoverImage() async {
    try {
      final image = await ImagePicker().pickImage(source: ImageSource.gallery, imageQuality: 85);
      if (image == null) return;
      setState(() => _uploadingCover = true);
      final url = await _vendorService.uploadImage(File(image.path), 'package_image');
      if (mounted) setState(() { _coverImageUrl = url; _uploadingCover = false; });
    } on PlatformException {
      if (mounted) {
        setState(() => _uploadingCover = false);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Permission needed — enable photo access in Settings.')),
        );
      }
    } catch (_) {
      if (mounted) {
        setState(() => _uploadingCover = false);
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Upload failed.')));
      }
    }
  }

  Future<void> _save() async {
    if (_nameCtrl.text.trim().isEmpty || _priceCtrl.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Name and base price are required.')));
      return;
    }
    setState(() => _isSaving = true);
    final body = {
      'name': _nameCtrl.text.trim(),
      'short_description': _shortDescCtrl.text.trim().isEmpty ? null : _shortDescCtrl.text.trim(),
      'description': _descCtrl.text.trim().isEmpty ? null : _descCtrl.text.trim(),
      'base_price': double.tryParse(_priceCtrl.text.trim()) ?? 0,
      'pricing_type': 'fixed',
      'occasion_ids': _selectedOccasionIds.toList(),
      if (_minGuestsCtrl.text.trim().isNotEmpty) 'min_guests': int.tryParse(_minGuestsCtrl.text.trim()),
      if (_maxGuestsCtrl.text.trim().isNotEmpty) 'max_guests': int.tryParse(_maxGuestsCtrl.text.trim()),
      if (_durationCtrl.text.trim().isNotEmpty) 'duration_hours': double.tryParse(_durationCtrl.text.trim()),
      if (_coverImageUrl != null) 'cover_image_url': _coverImageUrl,
      if (_cityCtrl.text.trim().isNotEmpty) 'city_slug': _cityCtrl.text.trim(),
      'is_customizable': _isCustomizable,
      'theme_ids': _isCustomizable ? _selectedThemeIds.toList() : [],
    };
    try {
      if (widget.existing == null) {
        await _vendorService.createPackage(body);
      } else {
        await _vendorService.updatePackage(widget.existing!.id, body);
      }
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      if (mounted) {
        setState(() => _isSaving = false);
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Could not save package.')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final isEdit = widget.existing != null;

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: AppBar(title: Text(isEdit ? 'Edit Package' : 'New Package')),
      body: ListView(
        padding: EdgeInsets.fromLTRB(18, 18, 18, 18 + MediaQuery.of(context).padding.bottom),
        children: [
          _labeled(ty, 'Cover Image', GestureDetector(
            onTap: _uploadingCover ? null : _pickCoverImage,
            child: Container(
              height: 140,
              decoration: BoxDecoration(
                color: ty.surface,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: ty.line),
                image: _coverImageUrl != null ? DecorationImage(image: NetworkImage(_coverImageUrl!), fit: BoxFit.cover) : null,
              ),
              child: _uploadingCover
                  ? const Center(child: CircularProgressIndicator())
                  : _coverImageUrl == null
                      ? Center(child: Icon(Icons.add_a_photo_outlined, color: ty.ink3, size: 32))
                      : null,
            ),
          )),
          _textField(ty, 'Name *', _nameCtrl),
          _textField(ty, 'Short Description', _shortDescCtrl),
          _textField(ty, 'Description', _descCtrl, maxLines: 4),
          _textField(ty, 'Base Price (₹) *', _priceCtrl, keyboardType: TextInputType.number),
          Row(children: [
            Expanded(child: _textField(ty, 'Min Guests', _minGuestsCtrl, keyboardType: TextInputType.number)),
            const SizedBox(width: 12),
            Expanded(child: _textField(ty, 'Max Guests', _maxGuestsCtrl, keyboardType: TextInputType.number)),
          ]),
          _textField(ty, 'Duration (hours)', _durationCtrl, keyboardType: TextInputType.number),
          _textField(ty, 'City Slug', _cityCtrl),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: Text('Customizable', style: TyType.sans(14, color: ty.ink)),
            value: _isCustomizable,
            onChanged: (v) => setState(() => _isCustomizable = v),
          ),
          const SizedBox(height: 8),
          Text('Occasions', style: TyType.sans(13, color: ty.ink2, weight: FontWeight.w600)),
          const SizedBox(height: 8),
          _isLoadingOccasions
              ? const CircularProgressIndicator()
              : Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: _occasions.map((o) {
                    final selected = _selectedOccasionIds.contains(o.id);
                    return FilterChip(
                      label: Text(o.name),
                      selected: selected,
                      onSelected: (v) => setState(() {
                        if (v) {
                          _selectedOccasionIds.add(o.id);
                        } else {
                          _selectedOccasionIds.remove(o.id);
                        }
                      }),
                    );
                  }).toList(),
                ),
          if (_isCustomizable) ...[
            const SizedBox(height: 24),
            Text('Theme', style: TyType.sans(13, color: ty.ink2, weight: FontWeight.w600)),
            const SizedBox(height: 8),
            Text('Pick the one theme you\'ll actually deliver for this package — customers will see this exact theme when booking.', style: TyType.sans(12, color: ty.ink3)),
            const SizedBox(height: 12),
            _isLoadingThemes
                ? const Center(child: CircularProgressIndicator())
                : GridView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 2,
                      mainAxisSpacing: 10,
                      crossAxisSpacing: 10,
                      mainAxisExtent: 86,
                    ),
                    itemCount: _themes.length,
                    itemBuilder: (context, i) {
                      final t = _themes[i];
                      final selected = _selectedThemeIds.contains(t.id);
                      return _ThemeCard(
                        theme: t,
                        selected: selected,
                        // Single-select: a package is delivered in exactly one
                        // theme — picking a new one replaces any prior pick.
                        onTap: () => setState(() {
                          _selectedThemeIds.clear();
                          if (!selected) _selectedThemeIds.add(t.id);
                        }),
                      );
                    },
                  ),
          ],
          const SizedBox(height: 32),
          ElevatedButton(
            onPressed: _isSaving ? null : _save,
            child: Text(_isSaving ? 'Saving…' : (isEdit ? 'Save Changes' : 'Create Package')),
          ),
        ],
      ),
    );
  }

  Widget _labeled(TyColors ty, String label, Widget child) => Padding(
        padding: const EdgeInsets.only(bottom: 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: TyType.sans(13, color: ty.ink2, weight: FontWeight.w600)),
            const SizedBox(height: 8),
            child,
          ],
        ),
      );

  Widget _textField(TyColors ty, String label, TextEditingController ctrl, {int maxLines = 1, TextInputType? keyboardType}) {
    return _labeled(
      ty,
      label,
      TextField(
        controller: ctrl,
        maxLines: maxLines,
        keyboardType: keyboardType,
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

class _ThemeCard extends StatelessWidget {
  final CelebrationTheme theme;
  final bool selected;
  final VoidCallback onTap;

  const _ThemeCard({required this.theme, required this.selected, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;

    Color hexToColor(String? hex) {
      if (hex == null || hex.isEmpty) return Colors.transparent;
      final h = hex.replaceAll('#', '');
      final value = int.tryParse('FF$h', radix: 16);
      return value != null ? Color(value) : Colors.transparent;
    }

    // Themes may define 1, 2, or 4 colors — only render the ones present.
    final swatches = [
      theme.colors['primary'],
      theme.colors['secondary'],
      theme.colors['accent'],
      theme.colors['background'],
    ].where((h) => h != null && h.isNotEmpty).map(hexToColor).toList();

    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: selected ? ty.saffron.withOpacity(0.08) : ty.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: selected ? ty.saffron : ty.line),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: swatches.map((c) => Container(
                width: 14,
                height: 14,
                margin: const EdgeInsets.only(right: 4),
                decoration: BoxDecoration(
                  color: c,
                  shape: BoxShape.circle,
                  border: Border.all(color: Colors.black12, width: 0.5),
                ),
              )).toList(),
            ),
            const Spacer(),
            Text(
              theme.name,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TyType.sans(12.5, color: selected ? ty.saffron : ty.ink, weight: FontWeight.w600),
            ),
          ],
        ),
      ),
    );
  }
}
