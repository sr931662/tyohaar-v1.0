import 'package:flutter/material.dart';
import '../theme/colors.dart';
import '../theme/responsive.dart';

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
    final resp = context.resp;
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
              blurRadius: resp.w(18),
              offset: Offset(0, resp.h(6)),
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
              EdgeInsets.symmetric(horizontal: resp.w(24), vertical: resp.h(15)),
          decoration: BoxDecoration(
            color: bg,
            border: border,
            borderRadius: BorderRadius.circular(resp.w(16)),
            boxShadow: shadow,
          ),
          child: Row(
            mainAxisSize: widget.full ? MainAxisSize.max : MainAxisSize.min,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              if (widget.leadingIcon != null) ...[
                Icon(widget.leadingIcon, size: resp.w(18), color: fg),
                SizedBox(width: resp.w(9)),
              ],
              Flexible(
                child: Text(
                  widget.label,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: fg,
                    fontWeight: FontWeight.w700,
                    fontSize: resp.sp(15.5),
                    letterSpacing: -0.1,
                  ),
                ),
              ),
              if (widget.icon != null) ...[
                SizedBox(width: resp.w(9)),
                Icon(widget.icon, size: resp.w(18), color: fg),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
