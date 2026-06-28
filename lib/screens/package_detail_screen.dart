import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:provider/provider.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/models.dart';
import '../data/services/package_service.dart';
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
  late Package _fullPackage;
  List<PackageItem> _allItems = [];

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
    super.dispose();
  }

  void _updateGuestCount(int value) {
    setState(() {
      _guestCount = value.clamp(1, 1000);
      _guestController.text = _guestCount.toString();
    });
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

    return Scaffold(
      backgroundColor: ty.paper,
      body: _isLoading 
        ? const Center(child: CircularProgressIndicator())
        : CustomScrollView(
            slivers: [
              SliverAppBar(
                expandedHeight: 300,
                pinned: true,
                leading: Padding(
                  padding: const EdgeInsets.all(8.0),
                  child: _glassIcon(context, Icons.chevron_left_rounded, () => Navigator.pop(context)),
                ),
                actions: [
                  Padding(
                    padding: const EdgeInsets.all(8.0),
                    child: _verifiedBadge(context),
                  ),
                ],
                flexibleSpace: FlexibleSpaceBar(
                  background: Stack(
                    fit: StackFit.expand,
                    children: [
                      CachedNetworkImage(
                        imageUrl: _fullPackage.coverImageUrl ?? '',
                        fit: BoxFit.cover,
                        placeholder: (context, url) => PhotoPlaceholder(tint: _fullPackage.tint, height: 300, arch: false, radius: BorderRadius.zero),
                        errorWidget: (context, url, error) => PhotoPlaceholder(tint: _fullPackage.tint, height: 300, arch: false, radius: BorderRadius.zero),
                      ),
                      DecoratedBox(
                        decoration: BoxDecoration(
                          gradient: LinearGradient(
                            begin: Alignment.bottomCenter,
                            end: Alignment.topCenter,
                            colors: [ty.paper, Colors.transparent],
                            stops: const [0.0, 0.4],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              SliverList(
                delegate: SliverChildListDelegate([
                  Padding(
                    padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            TyPill(_fullPackage.theme, background: ty.tint(_fullPackage.tint).withOpacity(0.15), foreground: ty.tint(_fullPackage.tint)),
                            const Spacer(),
                            Text('Base: ₹${(_fullPackage.price / 1000).toStringAsFixed(0)}K', 
                                style: TyType.sans(14, color: ty.ink2, weight: FontWeight.w600)),
                          ],
                        ),
                        const SizedBox(height: 16),
                        Text(_fullPackage.name, style: TyType.display(32, color: ty.ink)),
                        const SizedBox(height: 12),
                        Text(_fullPackage.description ?? '', style: TyType.sans(15, color: ty.ink2, height: 1.5)),
                        
                        const SizedBox(height: 32),
                        Text('Core Inclusions', style: TyType.eyebrow(12, color: ty.ink3)),
                        const SizedBox(height: 16),
                        ..._fullPackage.inclusions.map((item) => _inclusionRow(context, item)),

                        const SizedBox(height: 32),
                        Text('Guest Count', style: TyType.eyebrow(12, color: ty.ink3)),
                        const SizedBox(height: 12),
                        _guestStepper(context),

                        if (_optionalItems.isNotEmpty) ...[
                          const SizedBox(height: 32),
                          Text('Optional Add-ons', style: TyType.eyebrow(12, color: ty.ink3)),
                          const SizedBox(height: 16),
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
        padding: EdgeInsets.fromLTRB(20, 16, 20, MediaQuery.of(context).padding.bottom + 16),
        decoration: BoxDecoration(
          color: ty.paper,
          border: Border(top: BorderSide(color: ty.line2)),
          boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 10, offset: const Offset(0, -5))],
        ),
        child: Row(
          children: [
            Expanded(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Estimated Total', style: TyType.sans(12, color: ty.ink3, weight: FontWeight.w600)),
                  Text('₹${(_totalPrice / 1000).toStringAsFixed(1)}K', style: TyType.display(24, color: ty.ink)),
                ],
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              flex: 2,
              child: TyButton('Select & Continue', full: true, onTap: () => Navigator.pop(context, _fullPackage)),
            ),
          ],
        ),
      ),
    );
  }

  Widget _glassIcon(BuildContext context, IconData icon, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 40,
        height: 40,
        alignment: Alignment.center,
        decoration: BoxDecoration(color: Colors.black.withOpacity(0.2), shape: BoxShape.circle),
        child: Icon(icon, color: Colors.white),
      ),
    );
  }

  Widget _inclusionRow(BuildContext context, String text) {
    final ty = context.ty;
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(color: ty.leaf.withOpacity(0.1), shape: BoxShape.circle),
            child: Icon(Icons.check_rounded, color: ty.leaf, size: 16),
          ),
          const SizedBox(width: 12),
          Text(text, style: TyType.sans(14.5, color: ty.ink, weight: FontWeight.w600)),
        ],
      ),
    );
  }

  Widget _guestStepper(BuildContext context) {
    final ty = context.ty;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: ty.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: ty.line),
      ),
      child: Row(
        children: [
          IconButton(
            onPressed: () => _updateGuestCount(_guestCount - 1),
            icon: Icon(Icons.remove_circle_outline_rounded, color: ty.ink2),
          ),
          Expanded(
            child: TextField(
              controller: _guestController,
              keyboardType: TextInputType.number,
              textAlign: TextAlign.center,
              style: TyType.sans(18, color: ty.ink, weight: FontWeight.w700),
              decoration: const InputDecoration(
                border: InputBorder.none,
                isDense: true,
                suffixText: ' Guests',
                suffixStyle: TextStyle(fontSize: 14, fontWeight: FontWeight.w500),
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
            icon: Icon(Icons.add_circle_outline_rounded, color: ty.saffron),
          ),
        ],
      ),
    );
  }

  Widget _packageItemRow(BuildContext context, PackageItem item) {
    final ty = context.ty;
    final isSelected = _selectedOptionalItemIds.contains(item.id);
    return GestureDetector(
      onTap: () {
        setState(() {
          if (isSelected) _selectedOptionalItemIds.remove(item.id);
          else _selectedOptionalItemIds.add(item.id);
        });
      },
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: isSelected ? ty.saffron.withOpacity(0.05) : ty.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: isSelected ? ty.saffron : ty.line, width: isSelected ? 1.5 : 1),
        ),
        child: Row(
          children: [
            Icon(Icons.add_circle_outline_rounded, color: isSelected ? ty.saffron : ty.ink3, size: 20),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(item.name, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w600)),
                  if (item.description != null && item.description!.isNotEmpty)
                    Text(item.description!, style: TyType.sans(12, color: ty.ink3)),
                ],
              ),
            ),
            Text('+₹${(item.unitPrice / 1000).toStringAsFixed(1)}K',
                style: TyType.sans(13, color: ty.ink2, weight: FontWeight.w700)),
            const SizedBox(width: 12),
            Icon(isSelected ? Icons.check_box_rounded : Icons.add_box_outlined,
                color: isSelected ? ty.saffron : ty.ink3),
          ],
        ),
      ),
    );
  }

  Widget _verifiedBadge(BuildContext context) {
    final ty = context.ty;
    return GestureDetector(
      onTap: () => _showVerifiedInfo(context),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: Colors.black.withOpacity(0.3),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: Colors.white.withOpacity(0.2)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.verified_user_rounded, color: Colors.white, size: 14),
            const SizedBox(width: 6),
            Text(
              'Tyohaar Verified',
              style: TyType.sans(11, color: Colors.white, weight: FontWeight.w700),
            ),
          ],
        ),
      ),
    );
  }

  void _showVerifiedInfo(BuildContext context) {
    final ty = context.ty;
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: ty.surface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
        title: Row(
          children: [
            Icon(Icons.verified_user_rounded, color: ty.saffron, size: 24),
            const SizedBox(width: 12),
            Text('Tyohaar Verified', style: TyType.display(20, color: ty.ink)),
          ],
        ),
        content: Text(
          'Every vendor in this package is hand-picked and vetted for quality, ensuring your celebration is handled by true professionals.',
          style: TyType.sans(14.5, color: ty.ink2, height: 1.5),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('Got it', style: TyType.sans(14, color: ty.saffron, weight: FontWeight.w700)),
          ),
        ],
      ),
    );
  }
}
