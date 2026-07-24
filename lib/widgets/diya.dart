import 'package:flutter/material.dart';
import '../theme/colors.dart';

/// The brand's living spark — a glowing dot of light (diya).
/// Breathes gently when [pulse] is true.
class Diya extends StatefulWidget {
  final double size;
  final bool pulse;
  const Diya({super.key, this.size = 12, this.pulse = true});

  @override
  State<Diya> createState() => _DiyaState();
}

class _DiyaState extends State<Diya> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 3400),
  );

  @override
  void initState() {
    super.initState();
    if (widget.pulse) _c.repeat(reverse: true);
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final glow = ty.saffron;
    return AnimatedBuilder(
      animation: _c,
      builder: (context, child) {
        final t = Curves.easeInOut.transform(_c.value);
        final scale = widget.pulse ? 1.0 + 0.12 * t : 1.0;
        final opacity = widget.pulse ? 0.85 + 0.15 * t : 1.0;
        return Transform.scale(
          scale: scale,
          child: Opacity(opacity: opacity, child: child),
        );
      },
      child: Container(
        width: widget.size,
        height: widget.size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: RadialGradient(
            center: const Alignment(0, -0.2),
            colors: [const Color(0xFFFFE6BF), glow, ty.saffronDeep],
            stops: const [0.0, 0.55, 1.0],
          ),
          boxShadow: [
            BoxShadow(
              color: glow.withValues(alpha: 0.7),
              blurRadius: widget.size * 1.6,
              spreadRadius: widget.size * 0.18,
            ),
          ],
        ),
      ),
    );
  }
}
