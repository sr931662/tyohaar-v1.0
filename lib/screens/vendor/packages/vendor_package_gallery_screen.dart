import 'dart:io';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';

import '../../../theme/colors.dart';
import '../../../theme/typography.dart';
import '../../../theme/responsive.dart';
import '../../../data/vendor_models.dart';
import '../../../data/services/vendor_service.dart';

class VendorPackageGalleryScreen extends StatefulWidget {
  final VendorPackage package;
  const VendorPackageGalleryScreen({super.key, required this.package});

  @override
  State<VendorPackageGalleryScreen> createState() => _VendorPackageGalleryScreenState();
}

class _VendorPackageGalleryScreenState extends State<VendorPackageGalleryScreen> {
  final _vendorService = VendorService();
  List<VendorGalleryItem> _items = [];
  bool _isLoading = true;
  bool _isUploading = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _isLoading = true);
    try {
      final items = await _vendorService.listPackageGallery(widget.package.id);
      if (mounted) setState(() { _items = items; _isLoading = false; });
    } catch (_) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _addPhoto() async {
    try {
      final image = await ImagePicker().pickImage(source: ImageSource.gallery, imageQuality: 85);
      if (image == null) return;

      setState(() => _isUploading = true);
      final url = await _vendorService.uploadImage(File(image.path), 'package_gallery');
      await _vendorService.addPackageGalleryItem(widget.package.id, url);
      _load();
    } on PlatformException {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Permission needed — enable photo access in Settings.')),
        );
      }
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Upload failed.')));
    } finally {
      if (mounted) setState(() => _isUploading = false);
    }
  }

  Future<void> _delete(VendorGalleryItem item) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Delete photo?'),
        content: const Text('This photo will be permanently removed from the package gallery.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(context, true), child: const Text('Delete')),
        ],
      ),
    );
    if (confirmed != true) return;

    try {
      await _vendorService.deletePackageGalleryItem(widget.package.id, item.id);
      _load();
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Could not delete photo.')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final resp = context.resp;

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: AppBar(
        title: Text('${widget.package.name} Gallery', style: TyType.display(18, color: ty.ink)),
        centerTitle: true,
        backgroundColor: ty.paper,
        elevation: 0,
        iconTheme: IconThemeData(color: ty.ink),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _isUploading ? null : _addPhoto,
        backgroundColor: ty.saffron,
        foregroundColor: ty.onPrimary,
        icon: _isUploading 
          ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
          : const Icon(Icons.add_a_photo_outlined),
        label: Text(_isUploading ? 'Uploading...' : 'Add Photo'),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _items.isEmpty
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.photo_library_outlined, size: 64, color: ty.ink3.withOpacity(0.5)),
                      const SizedBox(height: 16),
                      Text('No gallery photos yet', style: TyType.sans(15, color: ty.ink2)),
                      const SizedBox(height: 8),
                      Text('Add photos to showcase this package.', style: TyType.sans(13, color: ty.ink3)),
                    ],
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _load,
                  child: GridView.builder(
                    padding: const EdgeInsets.all(20),
                    gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 2,
                      mainAxisSpacing: 16,
                      crossAxisSpacing: 16,
                      childAspectRatio: 1,
                    ),
                    itemCount: _items.length,
                    itemBuilder: (context, i) {
                      final item = _items[i];
                      return Container(
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: ty.line),
                          boxShadow: [
                            BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 8, offset: const Offset(0, 2)),
                          ],
                        ),
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(16),
                          child: Stack(
                            children: [
                              Positioned.fill(
                                child: CachedNetworkImage(
                                  imageUrl: item.mediaUrl,
                                  fit: BoxFit.cover,
                                  memCacheWidth: 400,
                                  placeholder: (context, url) => Container(color: Colors.black12),
                                  errorWidget: (context, url, error) => Container(color: Colors.black12, child: const Icon(Icons.broken_image_outlined, size: 24)),
                                ),
                              ),
                              Positioned(
                                top: 8,
                                right: 8,
                                child: GestureDetector(
                                  onTap: () => _delete(item),
                                  child: Container(
                                    padding: const EdgeInsets.all(6),
                                    decoration: BoxDecoration(
                                      color: Colors.black.withOpacity(0.5),
                                      shape: BoxShape.circle,
                                    ),
                                    child: const Icon(Icons.delete_outline, size: 18, color: Colors.white),
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ),
    );
  }
}
