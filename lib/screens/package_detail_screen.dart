import 'package:flutter/material.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/models.dart';
import '../widgets/photo_placeholder.dart';
import '../widgets/ty_button.dart';
import '../widgets/common.dart';
import 'catalogue_screen.dart';

class PackageDetailScreen extends StatefulWidget {
  final Package package;
  const PackageDetailScreen({super.key, required this.package});

  @override
  State<PackageDetailScreen> createState() => _PackageDetailScreenState();
}

class _PackageDetailScreenState extends State<PackageDetailScreen> {
  int _guestCount = 20;
  late TextEditingController _guestController;
  final Set<String> _selectedAddons = {};
  
  // Explicitly typed Map to avoid any inference issues
  final Map<String, Product> _selections = {
    'Decoration': const Product(id: 'd1', name: 'Pink and Silver Bliss', price: 2199, tint: 'rose', rating: 4.8, reviews: 398, category: 'Decoration'),
    'Cake': const Product(id: 'c1', name: '1-Tier Vanilla Bliss', price: 899, tint: 'saffron', rating: 4.9, reviews: 120, category: 'Cake'),
    'Bouquet': const Product(id: 'b1', name: 'Red Rose Bunch', price: 599, tint: 'rose', rating: 4.9, reviews: 210, category: 'Bouquet'),
  };

  @override
  void initState() {
    super.initState();
    _guestController = TextEditingController(text: _guestCount.toString());
  }

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

  final List<Map<String, dynamic>> _addons = [
    {'id': 'a1', 'name': 'Drone Photography', 'price': 5000, 'icon': Icons.videocam_rounded},
    {'id': 'a2', 'name': 'Live Food Counters', 'price': 8000, 'icon': Icons.restaurant_rounded},
    {'id': 'a3', 'name': 'Valet Parking', 'price': 3000, 'icon': Icons.local_parking_rounded},
    {'id': 'a4', 'name': 'Fireworks Show', 'price': 12000, 'icon': Icons.auto_awesome_rounded},
  ];

  int get _totalPrice {
    int base = widget.package.price;
    int selectionTotal = _selections.values.fold(0, (sum, p) => sum + p.price);
    int addonTotal = _addons
        .where((a) => _selectedAddons.contains(a['id']))
        .fold(0, (sum, item) => sum + (item['price'] as int));
    int guestSurcharge = (_guestCount > 20) ? (_guestCount - 20) * 500 : 0;
    return base + selectionTotal + addonTotal + guestSurcharge;
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final package = widget.package;

    return Scaffold(
      backgroundColor: ty.paper,
      body: CustomScrollView(
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
                  package.coverImage.startsWith('assets/')
                      ? Image.asset(package.coverImage, fit: BoxFit.cover)
                      : PhotoPlaceholder(tint: package.tint, height: 300, arch: false, radius: BorderRadius.zero),
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
                        TyPill(package.theme, background: ty.tint(package.tint).withOpacity(0.15), foreground: ty.tint(package.tint)),
                        const Spacer(),
                        Text('Base: ₹${(package.price / 1000).toStringAsFixed(0)}K', 
                            style: TyType.sans(14, color: ty.ink2, weight: FontWeight.w600)),
                      ],
                    ),
                    const SizedBox(height: 16),
                    Text(package.name, style: TyType.display(32, color: ty.ink)),
                    const SizedBox(height: 12),
                    Text(package.description, style: TyType.sans(15, color: ty.ink2, height: 1.5)),
                    
                    const SizedBox(height: 32),
                    Text('Core Inclusions', style: TyType.eyebrow(12, color: ty.ink3)),
                    const SizedBox(height: 16),
                    ...package.inclusions.map((item) => _inclusionRow(context, item)),

                    const SizedBox(height: 32),
                    Text('Customization Catalogue', style: TyType.eyebrow(12, color: ty.ink3)),
                    const SizedBox(height: 16),
                    ..._selections.keys.map((cat) => _catalogueRow(context, cat)),
                    
                    const SizedBox(height: 32),
                    Text('Guest Count', style: TyType.eyebrow(12, color: ty.ink3)),
                    const SizedBox(height: 12),
                    _guestStepper(context),
                    
                    const SizedBox(height: 32),
                    Text('Popular Add-ons', style: TyType.eyebrow(12, color: ty.ink3)),
                    const SizedBox(height: 16),
                    ..._addons.map((addon) => _addonRow(context, addon)),
                    
                    const SizedBox(height: 32),
                    // Removed large _infoCard here as it's now a badge in the AppBar
                  ],
                ),
              ),
            ]),
          ),
        ],
      ),
      bottomSheet: Container(
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
              child: TyButton('Select & Continue', full: true, onTap: () => Navigator.pop(context, package)),
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

  Widget _addonRow(BuildContext context, Map<String, dynamic> addon) {
    final ty = context.ty;
    final isSelected = _selectedAddons.contains(addon['id']);
    return GestureDetector(
      onTap: () {
        setState(() {
          if (isSelected) _selectedAddons.remove(addon['id']);
          else _selectedAddons.add(addon['id']);
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
            Icon(addon['icon'] as IconData, color: isSelected ? ty.saffron : ty.ink3, size: 20),
            const SizedBox(width: 16),
            Expanded(child: Text(addon['name'] as String, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w600))),
            Text('+₹${((addon['price'] as int) / 1000).toStringAsFixed(0)}K', style: TyType.sans(13, color: ty.ink2, weight: FontWeight.w700)),
            const SizedBox(width: 12),
            Icon(isSelected ? Icons.check_box_rounded : Icons.add_box_outlined, color: isSelected ? ty.saffron : ty.ink3),
          ],
        ),
      ),
    );
  }

  Widget _catalogueRow(BuildContext context, String category) {
    final ty = context.ty;
    final product = _selections[category]!;
    return GestureDetector(
      onTap: () async {
        final Product? result = await Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => CatalogueScreen(
              category: category,
              selectedProductId: product.id,
            ),
          ),
        );
        if (result != null) {
          setState(() => _selections[category] = result);
        }
      },
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: ty.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: ty.line),
        ),
        child: Row(
          children: [
            SizedBox(
              width: 54,
              height: 54,
              child: PhotoPlaceholder(tint: product.tint, arch: false),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(category, style: TyType.sans(11, color: ty.ink3, weight: FontWeight.w700)),
                  const SizedBox(height: 2),
                  Text(product.name, style: TyType.sans(14.5, color: ty.ink, weight: FontWeight.w600)),
                  Text('₹${product.price}', style: TyType.sans(13, color: ty.saffron, weight: FontWeight.w700)),
                ],
              ),
            ),
            Icon(Icons.keyboard_arrow_right_rounded, color: ty.ink3),
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

  Widget _infoCard(BuildContext context, IconData icon, String title, String sub) {
    final ty = context.ty;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: ty.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: ty.line),
      ),
      child: Row(
        children: [
          Icon(icon, color: ty.saffron, size: 24),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w700)),
                Text(sub, style: TyType.sans(12, color: ty.ink2)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
