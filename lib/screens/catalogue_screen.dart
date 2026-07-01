import 'package:flutter/material.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/models.dart';
import 'product_detail_screen.dart';
import '../widgets/photo_placeholder.dart';
import '../widgets/common.dart';

class CatalogueScreen extends StatelessWidget {
  final String category;
  final String? selectedItemId;
  final List<PackageItem> items;

  const CatalogueScreen({
    super.key,
    required this.category,
    this.selectedItemId,
    required this.items,
  });

  static String tintFor(String itemType) {
    switch (itemType.toLowerCase()) {
      case 'decoration': return 'rose';
      case 'cake': return 'saffron';
      case 'bouquet': return 'leaf';
      case 'photography': return 'gold';
      default: return 'saffron';
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;

    if (items.isEmpty) {
      return Scaffold(
        appBar: tyAppBar(context, title: '$category Catalogue'),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.inventory_2_outlined, size: 64, color: ty.ink3),
              const SizedBox(height: 16),
              Text('No items available', style: TyType.sans(16, color: ty.ink2)),
            ],
          ),
        ),
      );
    }

    return Scaffold(
      appBar: tyAppBar(context, title: '$category Catalogue'),
      body: GridView.builder(
        padding: const EdgeInsets.all(18),
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 2,
          childAspectRatio: 0.72,
          crossAxisSpacing: 16,
          mainAxisSpacing: 16,
        ),
        itemCount: items.length,
        itemBuilder: (context, i) {
          final item = items[i];
          final isSelected = item.id == selectedItemId;
          return GestureDetector(
            onTap: () async {
              final PackageItem? result = await Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => ProductDetailScreen(item: item)),
              );
              if (result != null && context.mounted) Navigator.pop(context, result);
            },
            child: Container(
              decoration: BoxDecoration(
                color: ty.surface,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: isSelected ? ty.saffron : ty.line,
                  width: isSelected ? 2 : 1,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Stack(
                      children: [
                        PhotoPlaceholder(
                          tint: tintFor(item.unit ?? 'service'),
                          arch: false,
                          radius: const BorderRadius.vertical(top: Radius.circular(15)),
                        ),
                        if (isSelected)
                          Positioned(
                            top: 8, right: 8,
                            child: Icon(Icons.check_circle, color: ty.saffron, size: 20),
                          ),
                      ],
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.all(10),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          item.name,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TyType.sans(13.5, color: ty.ink, weight: FontWeight.w700),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          item.unit ?? 'service'.replaceAll('_', ' ').toUpperCase(),
                          style: TyType.sans(10, color: ty.ink3, weight: FontWeight.w600),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          '₹${item.unitPrice.toInt()}',
                          style: TyType.sans(15, color: ty.ink, weight: FontWeight.w800),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}
