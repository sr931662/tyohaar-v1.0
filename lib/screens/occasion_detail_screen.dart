import 'package:flutter/material.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/models.dart';
import '../widgets/common.dart';
import '../widgets/photo_placeholder.dart';
import '../widgets/ty_button.dart';

class OccasionDetailScreen extends StatelessWidget {
  final Occasion occasion;
  const OccasionDetailScreen({super.key, required this.occasion});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final color = ty.tint(occasion.tint);

    return Scaffold(
      backgroundColor: ty.paper,
      body: CustomScrollView(
        slivers: [
          SliverAppBar(
            expandedHeight: 240,
            pinned: true,
            leading: Padding(
              padding: const EdgeInsets.all(8.0),
              child: ChromeIconButton(
                icon: Icons.chevron_left_rounded,
                onTap: () => Navigator.pop(context),
              ),
            ),
            flexibleSpace: FlexibleSpaceBar(
              background: Stack(
                fit: StackFit.expand,
                children: [
                  // Background: Image or Placeholder
                  occasion.heroImage != null
                      ? Image.asset(
                          occasion.heroImage!,
                          fit: BoxFit.cover,
                        )
                      : PhotoPlaceholder(tint: occasion.tint, arch: false),

                  // Overlay Gradients for Readability
                  DecoratedBox(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.bottomCenter,
                        end: Alignment.topCenter,
                        colors: [
                          ty.paper,
                          ty.paper.withOpacity(0.0),
                          Colors.black.withOpacity(0.4),
                        ],
                        stops: const [0.0, 0.5, 1.0],
                      ),
                    ),
                  ),

                  // Optional: Icon as a watermark if no hero image is present
                  if (occasion.heroImage == null)
                    Center(
                      child: Icon(
                        occasion.icon,
                        color: color.withOpacity(0.4),
                        size: 100,
                      ),
                    ),
                ],
              ),
            ),
          ),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  TyPill(occasion.category.replaceAll('_', ' ').toUpperCase(), 
                    background: color.withOpacity(0.12), 
                    foreground: color),
                  const SizedBox(height: 12),
                  Text(occasion.en, style: TyType.display(32, color: ty.ink)),
                  const SizedBox(height: 8),
                  Text(occasion.blurb,
                    style: TyType.sans(16, color: ty.ink2, height: 1.5)),
                  const SizedBox(height: 32),
                  const SectionHeader('Curated Packages'),
                  _mockPackage(context, 'Essential ${occasion.en}', 'Standard decoration & setup', '₹15K', occasion.tint, 
                      image: occasion.id == 'birthday' ? 'assets/images/birthday banner.png' : null),
                  _mockPackage(context, 'Premium ${occasion.en}', 'Full floral & light experience', '₹35K', occasion.tint),
                  const SizedBox(height: 32),
                  const SectionHeader('Traditions'),
                  _traditionRow(context, Icons.auto_awesome, 'Vibrant Decor', 'Traditional motifs and bright colors.'),
                  _traditionRow(context, Icons.restaurant_menu, 'Special Feast', 'Authentic delicacies and sweets.'),
                  const SizedBox(height: 40),
                  TyButton('Plan this celebration', full: true, onTap: () {}),
                  const SizedBox(height: 40),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _mockPackage(BuildContext context, String name, String sub, String price, String tint, {String? image}) {
    final ty = context.ty;
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: ty.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: ty.line),
      ),
      child: Row(
        children: [
          SizedBox(
            width: 60, 
            height: 60, 
            child: image != null && image.startsWith('assets/')
              ? ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: Image.asset(image, fit: BoxFit.cover),
                )
              : PhotoPlaceholder(tint: tint, arch: false),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(name, style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
                Text(sub, style: TyType.sans(12, color: ty.ink3)),
              ],
            ),
          ),
          Text(price, style: TyType.sans(16, color: ty.ink, weight: FontWeight.w800)),
        ],
      ),
    );
  }

  Widget _traditionRow(BuildContext context, IconData icon, String title, String desc) {
    final ty = context.ty;
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: ty.saffron, size: 20),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w700)),
                Text(desc, style: TyType.sans(13, color: ty.ink2)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
