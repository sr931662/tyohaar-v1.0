import 'package:flutter/material.dart';
import '../theme/colors.dart';

enum TyButtonKind { primary, ghost, soft }

/// The Tyohaar button — three weights, with a soft press-scale.
class TyButton extends StatefulWidget {
  final String label;
  final VoidCallback? onTap;
  final TyButtonKind kind;
  final bool full;
  final IconData? icon;
  final IconData? leadingIcon;
  final EdgeInsets? padding;
  final bool enabled;
  const TyButton(
    this.label, {
    super.key,
    this.onTap,
    this.kind = TyButtonKind.primary,
    this.full = false,
    this.icon,
    this.leadingIcon,
    this.padding,
    this.enabled = true,
  });

  @override
  State<TyButton> createState() => _TyButtonState();
}

class _TyButtonState extends State<TyButton> {
  double _scale = 1;

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    Color bg;
    Color fg;
    BoxBorder? border;
    List<BoxShadow>? shadow;

    switch (widget.kind) {
      case TyButtonKind.ghost:
        bg = Colors.transparent;
        fg = widget.enabled ? ty.ink : ty.ink3;
        border = Border.all(color: widget.enabled ? ty.line : ty.line2, width: 1.5);
        break;
      case TyButtonKind.soft:
        bg = ty.surface;
        fg = widget.enabled ? ty.ink : ty.ink3;
        border = Border.all(color: ty.line);
        break;
      case TyButtonKind.primary:
      default:
        bg = widget.enabled ? ty.saffron : ty.surface2;
        fg = widget.enabled ? ty.onPrimary : ty.ink3;
        if (widget.enabled) {
          shadow = [
            BoxShadow(
              color: ty.saffron.withOpacity(0.38),
              blurRadius: 18,
              offset: const Offset(0, 6),
            )
          ];
        }
    }

    return GestureDetector(
      onTapDown: (widget.onTap == null || !widget.enabled) ? null : (_) => setState(() => _scale = 0.97),
      onTapUp: (widget.onTap == null || !widget.enabled) ? null : (_) => setState(() => _scale = 1),
      onTapCancel: () => setState(() => _scale = 1),
      onTap: widget.enabled ? widget.onTap : null,
      child: AnimatedScale(
        scale: _scale,
        duration: const Duration(milliseconds: 120),
        child: Container(
          width: widget.full ? double.infinity : null,
          padding: widget.padding ??
              const EdgeInsets.symmetric(horizontal: 24, vertical: 15),
          decoration: BoxDecoration(
            color: bg,
            border: border,
            borderRadius: BorderRadius.circular(16),
            boxShadow: shadow,
          ),
          child: Row(
            mainAxisSize: widget.full ? MainAxisSize.max : MainAxisSize.min,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              if (widget.leadingIcon != null) ...[
                Icon(widget.leadingIcon, size: 18, color: fg),
                const SizedBox(width: 9),
              ],
              Flexible(
                child: Text(
                  widget.label,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: fg,
                    fontWeight: FontWeight.w700,
                    fontSize: 15.5,
                    letterSpacing: -0.1,
                  ),
                ),
              ),
              if (widget.icon != null) ...[
                const SizedBox(width: 9),
                Icon(widget.icon, size: 18, color: fg),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
