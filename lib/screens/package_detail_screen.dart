import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:provider/provider.dart';
import 'package:dio/dio.dart';
import 'package:gal/gal.dart';
import 'package:permission_handler/permission_handler.dart';

import 'package:tyohaar/screens/booking_flow_screen.dart';
import 'package:tyohaar/theme/assets.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../theme/responsive.dart';
import '../data/models.dart';
import '../data/services/package_service.dart';
import '../utils/currency.dart';
import '../widgets/photo_placeholder.dart';
import '../widgets/ty_button.dart';
import '../widgets/common.dart';

class PackageDetailScreen extends StatefulWidget {
  final Package package;
  const PackageDetailScreen({super.key, required this.package});

  @override
  State<PackageDetailScreen> createState() => _PackageDetailScreenState();
}

class _PackageDetailScreenState extends State<PackageDetailScreen> {
  int _guestCount = 20;
  late TextEditingController _guestController;
  final Set<String> _selectedOptionalItemIds = {};
  bool _isLoading = true;
  bool _isDownloading = false;
  late Package _fullPackage;
  List<PackageItem> _allItems = [];
  final PageController _imagePageController = PageController();
  int _currentImageIndex = 0;

  List<String> get _allImageUrls {
    final urls = <String>[];
    final cover = _fullPackage.coverImageUrl;
    if (cover != null && cover.isNotEmpty) urls.add(cover);
    urls.addAll(_fullPackage.galleryImageUrls.where((u) => u.isNotEmpty && u != cover));
    return urls;
  }

  @override
  void initState() {
    super.initState();
    _guestController = TextEditingController(text: _guestCount.toString());
    _fullPackage = widget.package;
    _loadPackageDetails();
  }

  Future<void> _loadPackageDetails() async {
    try {
      final svc = context.read<PackageService>();
      final results = await Future.wait([
        svc.getPackageDetails(widget.package.id),
        svc.listPackageItems(widget.package.id),
      ]);
      if (mounted) {
        setState(() {
          _fullPackage = results[0] as Package;
          _allItems = results[1] as List<PackageItem>;
          _isLoading = false;
        });
      }
    } catch (e) {
      debugPrint('Error loading package details: $e');
      if (mounted) setState(() => _isLoading = false);
    }
  }

  List<PackageItem> get _coreItems => _allItems.where((i) => !i.isOptional).toList();
  List<PackageItem> get _optionalItems => _allItems.where((i) => i.isOptional).toList();

  @override
  void dispose() {
    _guestController.dispose();
    _imagePageController.dispose();
    super.dispose();
  }

  void _updateGuestCount(int value) {
    setState(() {
      _guestCount = value.clamp(1, 1000);
      _guestController.text = _guestCount.toString();
    });
  }

  // The served image URL already has the Tyohaar watermark baked in
  // server-side (see cloudinary_client.py) — saving it is enough, no
  // client-side watermarking needed. Downloads whichever image is
  // currently visible in the slider, not always the cover.
  Future<void> _downloadCurrentImage() async {
    final urls = _allImageUrls;
    if (urls.isEmpty || _currentImageIndex >= urls.length) return;
    final url = urls[_currentImageIndex];

    setState(() => _isDownloading = true);
    try {
      final hasAccess = await Gal.hasAccess();
      if (!hasAccess) {
        final granted = await Gal.requestAccess();
        if (!granted) {
          if (await Permission.photos.request().isDenied && mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Photo library access is needed to save images.')),
            );
            return;
          }
        }
      }
      final response = await Dio().get<List<int>>(
        url,
        options: Options(responseType: ResponseType.bytes),
      );
      final bytes = response.data;
      if (bytes == null) throw Exception('Empty image response');
      await Gal.putImageBytes(
        Uint8List.fromList(bytes),
        name: '${_fullPackage.name}_tyohaar_${_currentImageIndex + 1}',
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Image saved to your gallery.')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not save the image. Please try again.')),
        );
      }
    } finally {
      if (mounted) setState(() => _isDownloading = false);
    }
  }

  int get _totalPrice {
    double base = _fullPackage.price;
    double optionalTotal = _allItems
        .where((i) => i.isOptional && _selectedOptionalItemIds.contains(i.id))
        .fold(0.0, (sum, item) => sum + item.unitPrice);
    int guestSurcharge = (_guestCount > 20) ? (_guestCount - 20) * 500 : 0;
    return (base + optionalTotal + guestSurcharge).toInt();
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final resp = context.resp;

    return Scaffold(
      backgroundColor: ty.paper,
      body: _isLoading 
        ? const Center(child: CircularProgressIndicator())
        : CustomScrollView(
            slivers: [
              SliverAppBar(
                expandedHeight: resp.h(300),
                pinned: true,
                leading: Padding(
                  padding: EdgeInsets.all(resp.w(8)),
                  child: _glassIcon(context, Icons.chevron_left_rounded, () => Navigator.pop(context)),
                ),
                actions: [
                  Padding(
                    padding: EdgeInsets.all(resp.w(8)),
                    child: _verifiedBadge(context),
                  ),
                ],
                flexibleSpace: FlexibleSpaceBar(
                  background: _imageSlider(context),
                ),
              ),
              SliverList(
                delegate: SliverChildListDelegate([
                  Padding(
                    padding: EdgeInsets.fromLTRB(resp.w(20), resp.h(12), resp.w(20), resp.h(120)),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            TyPill(_fullPackage.slug ?? _fullPackage.name, background: ty.tint(_fullPackage.tint).withOpacity(0.15), foreground: ty.tint(_fullPackage.tint)),
                            const Spacer(),
                            Text('Base: ${formatPrice(_fullPackage.price)}',
                                style: TyType.sans(resp.sp(14), color: ty.ink2, weight: FontWeight.w600)),
                          ],
                        ),
                        SizedBox(height: resp.h(16)),
                        Text(_fullPackage.name, style: TyType.display(resp.sp(32), color: ty.ink)),
                        SizedBox(height: resp.h(12)),
                        Text(_fullPackage.description ?? '', style: TyType.sans(resp.sp(15), color: ty.ink2, height: 1.5)),
                        
                        SizedBox(height: resp.h(32)),
                        Text('Core Inclusions', style: TyType.eyebrow(resp.sp(12), color: ty.ink3)),
                        SizedBox(height: resp.h(16)),
                        ..._fullPackage.inclusions.map((item) => _inclusionRow(context, item)),

                        SizedBox(height: resp.h(32)),
                        Text('Guest Count', style: TyType.eyebrow(resp.sp(12), color: ty.ink3)),
                        SizedBox(height: resp.h(12)),
                        _guestStepper(context),

                        if (_optionalItems.isNotEmpty) ...[
                          SizedBox(height: resp.h(32)),
                          Text('Optional Add-ons', style: TyType.eyebrow(resp.sp(12), color: ty.ink3)),
                          SizedBox(height: resp.h(16)),
                          ..._optionalItems.map((item) => _packageItemRow(context, item)),
                        ],
                      ],
                    ),
                  ),
                ]),
              ),
            ],
          ),
      bottomSheet: _isLoading ? null : Container(
        padding: EdgeInsets.fromLTRB(resp.w(20), resp.h(16), resp.w(20), MediaQuery.of(context).padding.bottom + resp.h(16)),
        decoration: BoxDecoration(
          color: ty.paper,
          border: Border(top: BorderSide(color: ty.line2)),
          boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: resp.w(10), offset: Offset(0, resp.h(-5)))],
        ),
        child: Row(
          children: [
            Expanded(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Estimated Total', style: TyType.sans(resp.sp(12), color: ty.ink3, weight: FontWeight.w600)),
                  Text(formatPrice(_totalPrice), style: TyType.display(resp.sp(24), color: ty.ink)),
                ],
              ),
            ),
            SizedBox(width: resp.w(16)),
            Expanded(
              flex: 2,
              child: TyButton('Select & Continue', full: true, onTap: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => BookingFlowScreen(
                      package: _fullPackage,
                      initialGuestCount: _guestCount,
                    ),
                  ),
                );
              }),
            ),
          ],
        ),
      ),
    );
  }

  Widget _imageSlider(BuildContext context) {
    final ty = context.ty;
    final resp = context.resp;
    final urls = _allImageUrls;

    if (urls.isEmpty) {
      return PhotoPlaceholder(tint: _fullPackage.tint, height: resp.h(300), arch: false, radius: BorderRadius.zero);
    }

    return Stack(
      fit: StackFit.expand,
      children: [
        PageView.builder(
          controller: _imagePageController,
          itemCount: urls.length,
          onPageChanged: (i) => setState(() => _currentImageIndex = i),
          itemBuilder: (context, i) => CachedNetworkImage(
            imageUrl: urls[i],
            fit: BoxFit.cover,
            placeholder: (context, url) => PhotoPlaceholder(tint: _fullPackage.tint, height: resp.h(300), arch: false, radius: BorderRadius.zero),
            errorWidget: (context, url, error) => OccasionAssets.getFallback(_fullPackage.name, tint: _fullPackage.tint, arch: false),
          ),
        ),
        IgnorePointer(
          child: DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.bottomCenter,
                end: Alignment.topCenter,
                colors: [ty.paper, Colors.transparent],
                stops: const [0.0, 0.4],
              ),
            ),
          ),
        ),
        // Save/download button — clearly visible against any photo: solid
        // white pill with a label, bottom-right, above the page dots so it
        // never overlaps them regardless of image count.
        Positioned(
          right: resp.w(14),
          bottom: resp.h(36),
          child: GestureDetector(
            onTap: _isDownloading ? null : _downloadCurrentImage,
            child: Container(
              padding: EdgeInsets.symmetric(horizontal: resp.w(14), vertical: resp.h(9)),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(resp.w(20)),
                boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.25), blurRadius: 8, offset: const Offset(0, 2))],
              ),
              child: _isDownloading
                  ? SizedBox(width: resp.w(16), height: resp.w(16), child: const CircularProgressIndicator(strokeWidth: 2))
                  : Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.download_rounded, color: ty.ink, size: resp.sp(16)),
                        SizedBox(width: resp.w(6)),
                        Text('Save', style: TyType.sans(resp.sp(12.5), color: ty.ink, weight: FontWeight.w700)),
                      ],
                    ),
            ),
          ),
        ),
        if (urls.length > 1)
          Positioned(
            bottom: resp.h(14),
            left: 0,
            right: 0,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: List.generate(urls.length, (i) {
                final active = i == _currentImageIndex;
                return AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  margin: EdgeInsets.symmetric(horizontal: resp.w(3)),
                  width: active ? resp.w(18) : resp.w(6),
                  height: resp.w(6),
                  decoration: BoxDecoration(
                    color: active ? Colors.white : Colors.white.withOpacity(0.5),
                    borderRadius: BorderRadius.circular(resp.w(3)),
                  ),
                );
              }),
            ),
          ),
      ],
    );
  }

  Widget _glassIcon(BuildContext context, IconData icon, VoidCallback onTap) {
    final resp = context.resp;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: resp.w(40),
        height: resp.w(40),
        alignment: Alignment.center,
        decoration: BoxDecoration(color: Colors.black.withOpacity(0.2), shape: BoxShape.circle),
        child: Icon(icon, color: Colors.white, size: resp.sp(20)),
      ),
    );
  }

  Widget _inclusionRow(BuildContext context, String text) {
    final ty = context.ty;
    final resp = context.resp;
    return Padding(
      padding: EdgeInsets.only(bottom: resp.h(12)),
      child: Row(
        children: [
          Container(
            padding: EdgeInsets.all(resp.w(6)),
            decoration: BoxDecoration(color: ty.leaf.withOpacity(0.1), shape: BoxShape.circle),
            child: Icon(Icons.check_rounded, color: ty.leaf, size: resp.sp(16)),
          ),
          SizedBox(width: resp.w(12)),
          Text(text, style: TyType.sans(resp.sp(14.5), color: ty.ink, weight: FontWeight.w600)),
        ],
      ),
    );
  }

  Widget _guestStepper(BuildContext context) {
    final ty = context.ty;
    final resp = context.resp;
    return Container(
      padding: EdgeInsets.symmetric(horizontal: resp.w(16), vertical: resp.h(8)),
      decoration: BoxDecoration(
        color: ty.surface,
        borderRadius: BorderRadius.circular(resp.w(16)),
        border: Border.all(color: ty.line),
      ),
      child: Row(
        children: [
          IconButton(
            onPressed: () => _updateGuestCount(_guestCount - 1),
            icon: Icon(Icons.remove_circle_outline_rounded, color: ty.ink2, size: resp.sp(24)),
          ),
          Expanded(
            child: TextField(
              controller: _guestController,
              keyboardType: TextInputType.number,
              textAlign: TextAlign.center,
              style: TyType.sans(resp.sp(18), color: ty.ink, weight: FontWeight.w700),
              decoration: InputDecoration(
                border: InputBorder.none,
                isDense: true,
                suffixText: ' Guests',
                suffixStyle: TextStyle(fontSize: resp.sp(14), fontWeight: FontWeight.w500),
              ),
              onChanged: (v) {
                final n = int.tryParse(v);
                if (n != null) {
                  setState(() => _guestCount = n.clamp(1, 1000));
                }
              },
            ),
          ),
          IconButton(
            onPressed: () => _updateGuestCount(_guestCount + 1),
            icon: Icon(Icons.add_circle_outline_rounded, color: ty.saffron, size: resp.sp(24)),
          ),
        ],
      ),
    );
  }

  Widget _packageItemRow(BuildContext context, PackageItem item) {
    final ty = context.ty;
    final resp = context.resp;
    final isSelected = _selectedOptionalItemIds.contains(item.id);
    return GestureDetector(
      onTap: () {
        setState(() {
          if (isSelected) _selectedOptionalItemIds.remove(item.id);
          else _selectedOptionalItemIds.add(item.id);
        });
      },
      child: Container(
        margin: EdgeInsets.only(bottom: resp.h(12)),
        padding: EdgeInsets.all(resp.w(12)),
        decoration: BoxDecoration(
          color: isSelected ? ty.saffron.withOpacity(0.05) : ty.surface,
          borderRadius: BorderRadius.circular(resp.w(16)),
          border: Border.all(color: isSelected ? ty.saffron : ty.line, width: isSelected ? 1.5 : 1),
        ),
        child: Row(
          children: [
            Icon(Icons.add_circle_outline_rounded, color: isSelected ? ty.saffron : ty.ink3, size: resp.sp(20)),
            SizedBox(width: resp.w(16)),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(item.name, style: TyType.sans(resp.sp(14), color: ty.ink, weight: FontWeight.w600)),
                  if (item.description != null && item.description!.isNotEmpty)
                    Text(item.description!, style: TyType.sans(resp.sp(12), color: ty.ink3)),
                ],
              ),
            ),
            Text('+${formatPrice(item.unitPrice)}',
                style: TyType.sans(resp.sp(13), color: ty.ink2, weight: FontWeight.w700)),
            SizedBox(width: resp.w(12)),
            Icon(isSelected ? Icons.check_box_rounded : Icons.add_box_outlined,
                color: isSelected ? ty.saffron : ty.ink3, size: resp.sp(24)),
          ],
        ),
      ),
    );
  }

  Widget _verifiedBadge(BuildContext context) {
    final ty = context.ty;
    final resp = context.resp;
    return GestureDetector(
      onTap: () => _showVerifiedInfo(context),
      child: Container(
        padding: EdgeInsets.symmetric(horizontal: resp.w(10), vertical: resp.h(6)),
        decoration: BoxDecoration(
          color: Colors.black.withOpacity(0.3),
          borderRadius: BorderRadius.circular(resp.w(20)),
          border: Border.all(color: Colors.white.withOpacity(0.2)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.verified_user_rounded, color: Colors.white, size: resp.sp(14)),
            SizedBox(width: resp.w(6)),
            Text(
              'Tyohaar Verified',
              style: TyType.sans(resp.sp(11), color: Colors.white, weight: FontWeight.w700),
            ),
          ],
        ),
      ),
    );
  }

  void _showVerifiedInfo(BuildContext context) {
    final ty = context.ty;
    final resp = context.resp;
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: ty.surface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(resp.w(24))),
        title: Row(
          children: [
            Icon(Icons.verified_user_rounded, color: ty.saffron, size: resp.sp(24)),
            SizedBox(width: resp.w(12)),
            Text('Tyohaar Verified', style: TyType.display(resp.sp(20), color: ty.ink)),
          ],
        ),
        content: Text(
          'Every vendor in this package is hand-picked and vetted for quality, ensuring your celebration is handled by true professionals.',
          style: TyType.sans(resp.sp(14.5), color: ty.ink2, height: 1.5),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('Got it', style: TyType.sans(resp.sp(14), color: ty.saffron, weight: FontWeight.w700)),
          ),
        ],
      ),
    );
  }
}
