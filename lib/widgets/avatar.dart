import 'package:flutter/material.dart';
import '../theme/colors.dart';

/// An initial-letter avatar, tinted by index for cheerful variety.
class TyAvatar extends StatelessWidget {
  final String name;
  final double size;
  final int index;
  const TyAvatar({super.key, required this.name, this.size = 34, this.index = 0});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    const tints = ['saffron', 'rose', 'leaf', 'gold'];
    final c = ty.tint(tints[index % 4]);
    final letter = name.trim().isEmpty ? '?' : name.trim()[0].toUpperCase();
    return Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: Color.alphaBlend(c.withValues(alpha: 0.20), ty.surface),
        border: Border.all(color: ty.surface, width: 2),
      ),
      child: Text(
        letter,
        style: TextStyle(
          color: c,
          fontWeight: FontWeight.w800,
          fontSize: size * 0.4,
        ),
      ),
    );
  }
}
