import 'package:flutter/material.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/models.dart';
import '../data/services/package_service.dart';
import '../widgets/photo_placeholder.dart';
import '../widgets/ty_button.dart';
import '../widgets/ty_rating_stars.dart';
import 'catalogue_screen.dart';
import 'review/submit_review_sheet.dart';

class ProductDetailScreen extends StatefulWidget {
  final PackageItem item;
  // Needed to build the like/review API paths (packages/{packageId}/items/{item.id}/...).
  // Nullable because not every caller currently has the parent package in
  // scope — like/review actions are disabled (no-op) when this is null.
  final String? packageId;
  const ProductDetailScreen({super.key, required this.item, this.packageId});

  @override
  State<ProductDetailScreen> createState() => _ProductDetailScreenState();
}

class _ProductDetailScreenState extends State<ProductDetailScreen> {
  final PackageService _packageService = PackageService();
  late bool _isLiked = widget.item.isLiked;
  late int _likeCount = widget.item.likeCount;

  Future<void> _toggleLike() async {
    final packageId = widget.packageId;
    if (packageId == null) {
      setState(() => _isLiked = !_isLiked);
      return;
    }
    final wasLiked = _isLiked;
    setState(() {
      _isLiked = !wasLiked;
      _likeCount += wasLiked ? -1 : 1;
    });
    try {
      final result = wasLiked
          ? await _packageService.unlikePackageItem(packageId, widget.item.id)
          : await _packageService.likePackageItem(packageId, widget.item.id);
      if (!mounted) return;
      setState(() {
        _isLiked = result['is_liked'] as bool;
        _likeCount = result['like_count'] as int;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isLiked = wasLiked;
        _likeCount = widget.item.likeCount;
      });
    }
  }

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
                  _toggleLike,
                  color: _isLiked ? ty.rose : Colors.white,
                ),
              ),
              const SizedBox(width: 8),
            ],
            flexibleSpace: FlexibleSpaceBar(
              background: PhotoPlaceholder(
                tint: CatalogueScreen.tintFor(item.unit ?? 'service'),
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
                      item.unit ?? 'service'.replaceAll('_', ' ').toUpperCase(),
                      style: TyType.eyebrow(10, color: ty.saffron),
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(item.name, style: TyType.display(30, color: ty.ink)),
                  if ((item.averageRating ?? 0) > 0 || item.reviewCount > 0) ...[
                    const SizedBox(height: 6),
                    Row(
                      children: [
                        TyRatingStars(rating: item.averageRating ?? 0, size: 15),
                        const SizedBox(width: 6),
                        Text('(${item.reviewCount} reviews)', style: TyType.sans(12.5, color: ty.ink3)),
                        const SizedBox(width: 10),
                        Icon(Icons.favorite_rounded, size: 13, color: ty.ink3),
                        const SizedBox(width: 3),
                        Text('$_likeCount', style: TyType.sans(12.5, color: ty.ink3)),
                      ],
                    ),
                  ],
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
                  if (widget.packageId != null) ...[
                    const SizedBox(height: 16),
                    GestureDetector(
                      onTap: () => showSubmitReviewSheet(
                        context,
                        title: 'Review ${item.name}',
                        onSubmit: (rating, title, body) => _packageService.addPackageItemReview(
                          widget.packageId!,
                          item.id,
                          rating: rating,
                          title: title,
                          body: body,
                        ),
                      ),
                      child: Row(
                        children: [
                          Icon(Icons.rate_review_outlined, size: 16, color: ty.saffron),
                          const SizedBox(width: 6),
                          Text('Write a review', style: TyType.sans(13.5, color: ty.saffron, weight: FontWeight.w700)),
                        ],
                      ),
                    ),
                  ],
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
