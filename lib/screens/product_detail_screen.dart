import 'package:flutter/material.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/models.dart';
import '../widgets/photo_placeholder.dart';
import '../widgets/ty_button.dart';
import 'catalogue_screen.dart';

class ProductDetailScreen extends StatefulWidget {
  final PackageItem item;
  const ProductDetailScreen({super.key, required this.item});

  @override
  State<ProductDetailScreen> createState() => _ProductDetailScreenState();
}

class _ProductDetailScreenState extends State<ProductDetailScreen> {
  bool _isLiked = false;

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final item = widget.item;

    return Scaffold(
      backgroundColor: ty.paper,
      body: CustomScrollView(
        slivers: [
          SliverAppBar(
            expandedHeight: 320,
            pinned: true,
            leading: Padding(
              padding: const EdgeInsets.all(8.0),
              child: _glassIcon(context, Icons.chevron_left_rounded, () => Navigator.pop(context)),
            ),
            actions: [
              Padding(
                padding: const EdgeInsets.all(8.0),
                child: _glassIcon(
                  context,
                  _isLiked ? Icons.favorite_rounded : Icons.favorite_border_rounded,
                  () => setState(() => _isLiked = !_isLiked),
                  color: _isLiked ? ty.rose : Colors.white,
                ),
              ),
              const SizedBox(width: 8),
            ],
            flexibleSpace: FlexibleSpaceBar(
              background: PhotoPlaceholder(
                tint: CatalogueScreen.tintFor(item.itemType),
                arch: false,
                radius: BorderRadius.zero,
              ),
            ),
          ),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: ty.saffron.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      item.itemType.replaceAll('_', ' ').toUpperCase(),
                      style: TyType.eyebrow(10, color: ty.saffron),
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(item.name, style: TyType.display(30, color: ty.ink)),
                  const SizedBox(height: 8),
                  Text(
                    '₹${item.unitPrice.toInt()}',
                    style: TyType.sans(24, color: ty.saffron, weight: FontWeight.w800),
                  ),
                  const SizedBox(height: 20),
                  Text(
                    item.description?.isNotEmpty == true
                        ? item.description!
                        : 'A premium add-on for your celebration, crafted with attention to detail and quality.',
                    style: TyType.sans(15, color: ty.ink2, height: 1.6),
                  ),
                  if (item.quantity > 1) ...[
                    const SizedBox(height: 20),
                    Row(
                      children: [
                        Icon(Icons.inventory_2_outlined, size: 18, color: ty.ink3),
                        const SizedBox(width: 8),
                        Text(
                          'Quantity included: ${item.quantity}',
                          style: TyType.sans(14, color: ty.ink2, weight: FontWeight.w600),
                        ),
                      ],
                    ),
                  ],
                  const SizedBox(height: 100),
                ],
              ),
            ),
          ),
        ],
      ),
      bottomNavigationBar: Container(
        padding: EdgeInsets.fromLTRB(24, 16, 24, MediaQuery.of(context).padding.bottom + 16),
        decoration: BoxDecoration(
          color: ty.paper,
          border: Border(top: BorderSide(color: ty.line2)),
          boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 10, offset: const Offset(0, -5))],
        ),
        child: TyButton(
          'Add to Plan',
          full: true,
          onTap: () => Navigator.pop(context, item),
        ),
      ),
    );
  }

  Widget _glassIcon(BuildContext context, IconData icon, VoidCallback onTap, {Color color = Colors.white}) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 40, height: 40,
        alignment: Alignment.center,
        decoration: BoxDecoration(color: Colors.black.withOpacity(0.2), shape: BoxShape.circle),
        child: Icon(icon, color: color, size: 24),
      ),
    );
  }
}
