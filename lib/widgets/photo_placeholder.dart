import 'package:flutter/material.dart';
import '../theme/colors.dart';

/// An arch-topped, tinted image stand-in with an optional monospace label.
/// Replace with real photography for the biggest visual upgrade.
class PhotoPlaceholder extends StatelessWidget {
  final String tint;
  final double? height;
  final double? width;
  final bool arch;
  final String label;
  final BorderRadius? radius;
  const PhotoPlaceholder({
    super.key,
    this.tint = 'saffron',
    this.height,
    this.width,
    this.arch = true,
    this.label = '',
    this.radius,
  });

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final c = ty.tint(tint);
    final br = radius ??
        BorderRadius.vertical(
          top: Radius.circular(arch ? 200 : 18),
          bottom: const Radius.circular(18),
        );

    return ClipRRect(
      borderRadius: br,
      child: SizedBox(
        height: height,
        width: width,
        child: Stack(
          fit: StackFit.expand,
          children: [
            DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    Color.alphaBlend(c.withOpacity(0.26), ty.surface),
                    Color.alphaBlend(c.withOpacity(0.09), ty.surface),
                  ],
                ),
              ),
            ),
            Center(
              child: FractionallySizedBox(
                widthFactor: 0.34,
                child: AspectRatio(
                  aspectRatio: 1,
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: c.withOpacity(0.30),
                    ),
                  ),
                ),
              ),
            ),
            if (label.isNotEmpty)
              Positioned(
                left: 12,
                bottom: 12,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                  decoration: BoxDecoration(
                    color: ty.surface.withOpacity(0.72),
                    borderRadius: BorderRadius.circular(7),
                  ),
                  child: Text(
                    label,
                    style: TextStyle(
                      fontFamily: 'monospace',
                      fontSize: 10.5,
                      letterSpacing: 0.4,
                      color: ty.ink2,
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
