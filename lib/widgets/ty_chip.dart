import 'package:flutter/material.dart';
import '../theme/colors.dart';
import '../theme/responsive.dart';

/// A pill choice-chip used across filters and the mood picker.
class TyChip extends StatelessWidget {
  final String label;
  final bool active;
  final VoidCallback? onTap;
  const TyChip({super.key, required this.label, this.active = false, this.onTap});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final resp = context.resp;
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: EdgeInsets.symmetric(horizontal: resp.w(16), vertical: 10),
        decoration: BoxDecoration(
          color: active ? ty.saffronSoft : Colors.transparent,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(
            color: active ? ty.saffron : ty.line,
            width: 1.5,
          ),
        ),
        child: Text(
          label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(
            fontSize: resp.sp(14),
            fontWeight: FontWeight.w600,
            color: active ? ty.saffronDeep : ty.ink2,
          ),
        ),
      ),
    );
  }
}
