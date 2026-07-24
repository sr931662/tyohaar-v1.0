import 'package:flutter/material.dart';
import '../theme/colors.dart';

/// Star rating widget with two modes:
/// - Display mode (default): shows `rating` as filled/empty stars, read-only.
/// - Input mode: pass `onChanged` to make stars tappable (1-5), used in the
///   submit-review form.
class TyRatingStars extends StatelessWidget {
  final double rating;
  final int? value;
  final ValueChanged<int>? onChanged;
  final double size;

  const TyRatingStars({
    super.key,
    this.rating = 0,
    this.value,
    this.onChanged,
    this.size = 18,
  });

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final filled = onChanged != null ? (value ?? 0) : rating.round();
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: List.generate(5, (i) {
        final starIndex = i + 1;
        final icon = Icon(
          starIndex <= filled ? Icons.star_rounded : Icons.star_outline_rounded,
          size: size,
          color: starIndex <= filled ? ty.saffron : ty.ink3,
        );
        if (onChanged == null) return icon;
        return GestureDetector(
          onTap: () => onChanged!(starIndex),
          child: Padding(padding: const EdgeInsets.only(right: 2), child: icon),
        );
      }),
    );
  }
}
