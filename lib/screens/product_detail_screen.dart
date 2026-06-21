import 'package:flutter/material.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/models.dart';
import '../widgets/photo_placeholder.dart';
import '../widgets/ty_button.dart';
import '../widgets/common.dart';

class ProductDetailScreen extends StatefulWidget {
  final Product product;
  const ProductDetailScreen({super.key, required this.product});

  @override
  State<ProductDetailScreen> createState() => _ProductDetailScreenState();
}

class _ProductDetailScreenState extends State<ProductDetailScreen> {
  String? _selectedTheme;
  final Map<String, String> _customSelections = {};
  bool _isLiked = false;

  final List<Review> _dummyReviews = const [
    Review(userName: 'Anjali M.', comment: 'Absolutely beautiful! The colors were exactly as shown.', rating: 5.0, date: '2 days ago', likes: 12),
    Review(userName: 'Vikram S.', comment: 'Great quality, but setup took a bit longer than 2 hours.', rating: 4.0, date: '1 week ago', likes: 5),
  ];

  @override
  void initState() {
    super.initState();
    if (widget.product.themes != null && widget.product.themes!.isNotEmpty) {
      _selectedTheme = widget.product.themes!.first;
    }
    if (widget.product.customizationOptions != null) {
      widget.product.customizationOptions!.forEach((key, value) {
        if (value.isNotEmpty) _customSelections[key] = value.first;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final p = widget.product;

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
                tint: p.tint,
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
                  Row(
                    children: [
                      _starRating(p.rating),
                      const SizedBox(width: 8),
                      Text('${p.rating} (${p.reviews} Reviews)', 
                          style: TyType.sans(14, color: ty.ink2, weight: FontWeight.w600)),
                    ],
                  ),
                  const SizedBox(height: 16),
                  Text(p.name, style: TyType.display(30, color: ty.ink)),
                  const SizedBox(height: 8),
                  Text('₹${p.price}', 
                      style: TyType.sans(24, color: ty.saffron, weight: FontWeight.w800)),
                  const SizedBox(height: 20),
                  Text(
                    p.description ?? 'A premium choice for your celebration, crafted with attention to detail and quality materials.',
                    style: TyType.sans(15, color: ty.ink2, height: 1.6),
                  ),
                  
                  // --- Theme Selection (For Decorations) ---
                  if (p.category == 'Decoration' && p.themes != null && p.themes!.isNotEmpty) ...[
                    const SizedBox(height: 32),
                    Text('Select Theme', style: TyType.eyebrow(12, color: ty.ink3)),
                    const SizedBox(height: 16),
                    _themePicker(p.themes!),
                  ],

                  // --- In-depth Customization (For Cakes) ---
                  if (p.category == 'Cake' && p.customizationOptions != null) ...[
                    const SizedBox(height: 32),
                    Text('Customize Your Cake', style: TyType.eyebrow(12, color: ty.ink3)),
                    const SizedBox(height: 16),
                    ...p.customizationOptions!.keys.map((key) => _customizationRow(key, p.customizationOptions![key]!)),
                  ],

                  const SizedBox(height: 40),
                  const Divider(),
                  const SizedBox(height: 32),
                  
                  // --- Feedback & Reviews ---
                  Row(
                    children: [
                      Text('Reviews & Feedback', style: TyType.display(22, color: ty.ink)),
                      const Spacer(),
                      TextButton(onPressed: () {}, child: Text('Rate & Review', style: TextStyle(color: ty.saffron))),
                    ],
                  ),
                  const SizedBox(height: 20),
                  ..._dummyReviews.map((r) => _reviewItem(r)),
                  
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
          'Confirm Selection',
          full: true,
          onTap: () => Navigator.pop(context, p),
        ),
      ),
    );
  }

  Widget _starRating(double rating) {
    return Row(
      children: List.generate(5, (index) {
        return Icon(
          index < rating.floor() ? Icons.star_rounded : Icons.star_outline_rounded,
          color: Colors.amber,
          size: 20,
        );
      }),
    );
  }

  Widget _themePicker(List<String> themes) {
    final ty = context.ty;
    return Wrap(
      spacing: 12,
      runSpacing: 12,
      children: themes.map((theme) {
        final isSelected = _selectedTheme == theme;
        return GestureDetector(
          onTap: () => setState(() => _selectedTheme = theme),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
            decoration: BoxDecoration(
              color: isSelected ? ty.saffron.withOpacity(0.1) : ty.surface,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: isSelected ? ty.saffron : ty.line, width: isSelected ? 1.5 : 1),
            ),
            child: Text(theme, style: TyType.sans(14, color: isSelected ? ty.ink : ty.ink2, weight: isSelected ? FontWeight.w700 : FontWeight.w500)),
          ),
        );
      }).toList(),
    );
  }

  Widget _customizationRow(String title, List<String> options) {
    final ty = context.ty;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w700)),
        const SizedBox(height: 12),
        SizedBox(
          height: 44,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: options.length,
            separatorBuilder: (_, __) => const SizedBox(width: 10),
            itemBuilder: (context, i) {
              final opt = options[i];
              final isSelected = _customSelections[title] == opt;
              return GestureDetector(
                onTap: () => setState(() => _customSelections[title] = opt),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: isSelected ? ty.ink : ty.surface,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: isSelected ? ty.ink : ty.line),
                  ),
                  child: Text(opt, style: TyType.sans(13, color: isSelected ? ty.paper : ty.ink2, weight: isSelected ? FontWeight.w600 : FontWeight.w500)),
                ),
              );
            },
          ),
        ),
        const SizedBox(height: 24),
      ],
    );
  }

  Widget _reviewItem(Review r) {
    final ty = context.ty;
    return Container(
      margin: const EdgeInsets.only(bottom: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              CircleAvatar(radius: 16, backgroundColor: ty.saffronSoft, child: Text(r.userName[0], style: TextStyle(color: ty.saffronDeep, fontSize: 12))),
              const SizedBox(width: 12),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(r.userName, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w700)),
                  Text(r.date, style: TyType.sans(11, color: ty.ink3)),
                ],
              ),
              const Spacer(),
              _starRating(r.rating),
            ],
          ),
          const SizedBox(height: 12),
          Text(r.comment, style: TyType.sans(14, color: ty.ink2, height: 1.5)),
          const SizedBox(height: 12),
          Row(
            children: [
              Icon(Icons.thumb_up_alt_outlined, size: 16, color: ty.ink3),
              const SizedBox(width: 6),
              Text('${r.likes} Helpful', style: TyType.sans(12, color: ty.ink3)),
              const SizedBox(width: 20),
              Icon(Icons.reply_rounded, size: 16, color: ty.ink3),
              const SizedBox(width: 6),
              Text('Reply', style: TyType.sans(12, color: ty.ink3)),
            ],
          ),
          const SizedBox(height: 16),
          const Divider(height: 1),
        ],
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
