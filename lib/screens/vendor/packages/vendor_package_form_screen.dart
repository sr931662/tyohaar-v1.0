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
import '../../../l10n/generated/app_localizations.dart';

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
  List<Occasion> _occasions = [];
  bool _isSaving = false;
  bool _isLoadingOccasions = true;

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
    }
    _loadOccasions();
  }

  Future<void> _loadOccasions() async {
    try {
      final occasions = await _packageService.listOccasions();
      if (mounted) setState(() { _occasions = occasions; _isLoadingOccasions = false; });
    } catch (_) {
      if (mounted) setState(() => _isLoadingOccasions = false);
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
          SnackBar(content: Text(AppLocalizations.of(context)!.vendorMultimediaPermissionNeededMessage)),
        );
      }
    } catch (_) {
      if (mounted) {
        setState(() => _uploadingCover = false);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(AppLocalizations.of(context)!.vendorMultimediaUploadFailedMessage)));
      }
    }
  }

  Future<void> _save() async {
    if (_nameCtrl.text.trim().isEmpty || _priceCtrl.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(AppLocalizations.of(context)!.vendorPackageFormNameAndPriceRequiredError)));
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
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(AppLocalizations.of(context)!.vendorPackageFormSaveError)));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final isEdit = widget.existing != null;

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: AppBar(title: Text(isEdit ? l10n.vendorPackageFormEditTitle : l10n.vendorPackageFormNewTitle)),
      body: ListView(
        padding: EdgeInsets.fromLTRB(18, 18, 18, 18 + MediaQuery.of(context).padding.bottom),
        children: [
          _labeled(ty, l10n.vendorPackageFormCoverImageLabel, GestureDetector(
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
          _textField(ty, l10n.vendorPackageFormNameLabel, _nameCtrl),
          _textField(ty, l10n.vendorPackageFormShortDescriptionLabel, _shortDescCtrl),
          _textField(ty, l10n.vendorPackageFormDescriptionLabel, _descCtrl, maxLines: 4),
          _textField(ty, l10n.vendorPackageFormBasePriceLabel, _priceCtrl, keyboardType: TextInputType.number, helperText: l10n.vendorPackageFormBasePriceFormatHelperText),
          Row(children: [
            Expanded(child: _textField(ty, l10n.vendorPackageFormMinGuestsLabel, _minGuestsCtrl, keyboardType: TextInputType.number)),
            const SizedBox(width: 12),
            Expanded(child: _textField(ty, l10n.vendorPackageFormMaxGuestsLabel, _maxGuestsCtrl, keyboardType: TextInputType.number)),
          ]),
          _textField(ty, l10n.vendorPackageFormDurationLabel, _durationCtrl, keyboardType: TextInputType.number, helperText: l10n.vendorPackageFormDurationFormatHelperText),
          _textField(ty, l10n.vendorPackageFormCitySlugLabel, _cityCtrl, helperText: l10n.vendorPackageFormCitySlugFormatHelperText),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(l10n.vendorPackageFormCustomizableLabel, style: TyType.sans(14, color: ty.ink)),
            value: _isCustomizable,
            onChanged: (v) => setState(() => _isCustomizable = v),
          ),
          const SizedBox(height: 8),
          Text(l10n.vendorPackageFormOccasionsLabel, style: TyType.sans(13, color: ty.ink2, weight: FontWeight.w600)),
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
            const SizedBox(height: 16),
            Text(l10n.vendorPackageFormThemeHelperText, style: TyType.sans(12, color: ty.ink3)),
          ],
          const SizedBox(height: 32),
          ElevatedButton(
            onPressed: _isSaving ? null : _save,
            child: Text(_isSaving ? l10n.vendorAvailabilitySavingLabel : (isEdit ? l10n.vendorAvailabilitySaveChangesLabel : l10n.vendorPackageFormCreateButtonLabel)),
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

  Widget _textField(TyColors ty, String label, TextEditingController ctrl, {int maxLines = 1, TextInputType? keyboardType, String? helperText}) {
    return _labeled(
      ty,
      label,
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
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
          if (helperText != null) ...[
            const SizedBox(height: 4),
            Text(helperText, style: TyType.sans(11.5, color: ty.ink3)),
          ],
        ],
      ),
    );
  }
}
