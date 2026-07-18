import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import '../theme/colors.dart';

/// The celebration symbol system.
/// Uses IconData by default, or a network image (e.g. an admin-uploaded
/// occasion icon) via [imageUrl] when present — falls back to [icon] on
/// null/error so every existing call site is unaffected.
class Emblem extends StatelessWidget {
  final IconData icon;
  final String tint;
  final double size;
  final String? imageUrl;
  final Color? tintColor;
  const Emblem({super.key, required this.icon, this.tint = 'saffron', this.size = 44, this.imageUrl, this.tintColor});

  @override
  Widget build(BuildContext context) {
    final c = tintColor ?? (tint == 'white' ? Colors.white : context.ty.tint(tint));
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: c.withOpacity(0.12),
        shape: BoxShape.circle,
      ),
      clipBehavior: Clip.antiAlias,
      child: Center(
        child: (imageUrl != null && imageUrl!.isNotEmpty)
            ? CachedNetworkImage(
                imageUrl: imageUrl!,
                width: size,
                height: size,
                fit: BoxFit.cover,
                errorWidget: (_, __, ___) => Icon(icon, color: c, size: size * 0.6),
                placeholder: (_, __) => Icon(icon, color: c, size: size * 0.6),
              )
            : Icon(
                icon,
                color: c,
                size: size * 0.6,
              ),
      ),
    );
  }
}
