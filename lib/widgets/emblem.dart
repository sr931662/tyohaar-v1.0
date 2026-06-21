import 'package:flutter/material.dart';
import '../theme/colors.dart';

/// The celebration symbol system.
/// Now uses IconData for maximum flexibility.
class Emblem extends StatelessWidget {
  final IconData icon;
  final String tint;
  final double size;
  const Emblem({super.key, required this.icon, this.tint = 'saffron', this.size = 44});

  @override
  Widget build(BuildContext context) {
    final c = context.ty.tint(tint);
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: c.withOpacity(0.12),
        shape: BoxShape.circle,
      ),
      child: Center(
        child: Icon(
          icon,
          color: c,
          size: size * 0.6,
        ),
      ),
    );
  }
}
