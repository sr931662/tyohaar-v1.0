import 'package:flutter/material.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/models.dart';
import 'product_detail_screen.dart';
import '../widgets/photo_placeholder.dart';
import '../widgets/common.dart';

class CatalogueScreen extends StatelessWidget {
  final String category;
  final String selectedProductId;

  const CatalogueScreen({
    super.key,
    required this.category,
    required this.selectedProductId,
  });

  static final Map<String, List<Product>> _products = {
    'Decoration': [
      Product(
        id: 'd1', name: 'Pink and Silver Bliss', price: 2199, tint: 'rose', rating: 4.8, reviews: 398, category: 'Decoration',
        description: 'A stunning combination of rose pink and metallic silver balloons, perfect for birthdays and anniversaries.',
        themes: ['Pink & Silver', 'Blue & Gold', 'Red & White', 'Black & Gold'],
      ),
      Product(
        id: 'd2', name: 'Fairy Lights Surprise', price: 2299, tint: 'gold', rating: 4.5, reviews: 991, category: 'Decoration',
        description: 'Warm fairy lights paired with elegant drapes to create a magical atmosphere.',
        themes: ['Warm Gold', 'Cool White', 'Multi-color'],
      ),
    ],
    'Cake': [
      Product(
        id: 'c1', name: 'Premium Custom Cake', price: 1499, tint: 'saffron', rating: 4.9, reviews: 120, category: 'Cake',
        description: 'Design your perfect celebration cake. Freshly baked with premium ingredients.',
        customizationOptions: {
          'Flavor': ['Vanilla', 'Chocolate', 'Red Velvet', 'Butterscotch'],
          'Weight': ['0.5 KG', '1.0 KG', '1.5 KG', '2.0 KG'],
          'Shape': ['Round', 'Heart', 'Square'],
          'Eggless': ['Yes', 'No'],
        },
      ),
    ],
    'Bouquet': [
      Product(
        id: 'b1', 
        name: 'Red Rose Bunch', 
        price: 599, 
        tint: 'rose', 
        rating: 4.9, 
        reviews: 210, 
        category: 'Bouquet',
        description: 'Hand-picked long-stemmed roses wrapped in premium craft paper.',
        themes: ['Deep Red', 'Sunshine Yellow', 'Snow White'],
      ),
      Product(
        id: 'b2', 
        name: 'Mixed Lilies Vase', 
        price: 899, 
        tint: 'leaf', 
        rating: 4.8, 
        reviews: 150, 
        category: 'Bouquet',
        description: 'A fragrant arrangement of lilies and seasonal greenery in a glass vase.',
      ),
      Product(
        id: 'b3', 
        name: 'Exotic Orchids', 
        price: 1299, 
        tint: 'gold', 
        rating: 4.7, 
        reviews: 90, 
        category: 'Bouquet',
        description: 'Premium purple orchids that last long and symbolize elegance.',
      ),
    ],
  };

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final items = _products[category] ?? [];

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
          final p = items[i];
          final isSelected = p.id == selectedProductId;
          return GestureDetector(
            onTap: () async {
              final Product? result = await Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => ProductDetailScreen(product: p)),
              );
              if (result != null && context.mounted) Navigator.pop(context, result);
            },
            child: Container(
              decoration: BoxDecoration(
                color: ty.surface,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: isSelected ? ty.saffron : ty.line, width: isSelected ? 2 : 1),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Stack(
                      children: [
                        PhotoPlaceholder(tint: p.tint, arch: false, radius: const BorderRadius.vertical(top: Radius.circular(15))),
                        if (isSelected)
                          Positioned(top: 8, right: 8, child: Icon(Icons.check_circle, color: ty.saffron, size: 20)),
                      ],
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.all(10),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(p.name, maxLines: 1, style: TyType.sans(13.5, color: ty.ink, weight: FontWeight.w700)),
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            const Icon(Icons.star, color: Colors.amber, size: 12),
                            const SizedBox(width: 4),
                            Text('${p.rating} · ${p.reviews}', style: TyType.sans(11, color: ty.ink3)),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Text('₹${p.price}', style: TyType.sans(15, color: ty.ink, weight: FontWeight.w800)),
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
