import 'dart:io' show Platform;
import 'dart:math' as math;

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';

/// Animated hand-off from the (static) iOS launch screen into the app.
///
/// iOS can't animate its native launch screen, so the first Flutter frame
/// reproduces it exactly (white background, flower logo centred at the same
/// size) and then plays: petals fold in and bloom back out one by one -> the
/// centre pops -> the flower spins while the brand gradient floods the screen
/// and the logo turns white -> the overlay fades out to reveal the app.
/// On other platforms this widget is a no-op and returns [child] untouched.
class IosLaunchAnimation extends StatefulWidget {
  const IosLaunchAnimation({super.key, required this.child});

  final Widget child;

  @override
  State<IosLaunchAnimation> createState() => _IosLaunchAnimationState();
}

class _IosLaunchAnimationState extends State<IosLaunchAnimation>
    with SingleTickerProviderStateMixin {
  // Must match the 192pt image in ios/Runner/Base.lproj/LaunchScreen.storyboard.
  static const _logoBox = 192.0;

  late final AnimationController _c;
  bool _done = false;

  bool get _enabled => !kIsWeb && Platform.isIOS;

  @override
  void initState() {
    super.initState();
    _c = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 3000),
    );
    if (_enabled) {
      _c.forward().whenComplete(() {
        if (mounted) setState(() => _done = true);
      });
    }
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_enabled) {
      for (var i = 0; i < 6; i++) {
        precacheImage(AssetImage('assets/images/logo_anim/petal_$i.png'), context);
      }
      precacheImage(const AssetImage('assets/images/logo_anim/center.png'), context);
    }
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  static double _seg(double t, double a, double b, [Curve curve = Curves.linear]) =>
      curve.transform(((t - a) / (b - a)).clamp(0.0, 1.0));

  @override
  Widget build(BuildContext context) {
    if (!_enabled || _done) return widget.child;
    return Stack(
      textDirection: TextDirection.ltr,
      fit: StackFit.expand,
      children: [
        widget.child,
        IgnorePointer(
          child: AnimatedBuilder(
            animation: _c,
            builder: (context, _) => _buildOverlay(context, _c.value),
          ),
        ),
      ],
    );
  }

  Widget _buildOverlay(BuildContext context, double t) {
    final size = MediaQuery.sizeOf(context);
    final center = Offset(size.width / 2, size.height / 2);
    final maxRadius = math.sqrt(size.width * size.width + size.height * size.height) / 2 + 40;

    // Petals: the first beat is a full-size hold (matches the native image),
    // then each petal folds toward the centre and blooms back, staggered.
    // 0.00-0.08 hold | 0.08-0.50 staggered bloom | 0.50-0.60 centre pop
    // 0.52-0.82 gradient flood + spin, logo whitens | 0.86-1.00 fade out
    final flood = _seg(t, 0.52, 0.82, Curves.easeInOutCubic);
    final whiten = _seg(t, 0.60, 0.76, Curves.easeIn);
    final spin = _seg(t, 0.30, 0.90, Curves.easeInOutCubic);
    final grow = _seg(t, 0.60, 0.90, Curves.easeInOut);
    final fade = 1.0 - _seg(t, 0.86, 1.0, Curves.easeIn);
    final centerPop = _seg(t, 0.46, 0.60, Curves.easeOutBack);

    final layers = <Widget>[];
    for (var i = 0; i < 6; i++) {
      final start = 0.08 + i * 0.05;
      final p = _seg(t, start, start + 0.20, Curves.easeOutBack);
      final dip = _seg(t, start - 0.08, start, Curves.easeIn);
      // 1 -> 0.15 (fold in) -> 1 (bloom back)
      final scale = t < start ? 1.0 - 0.85 * dip : 0.15 + 0.85 * p;
      layers.add(Transform.scale(
        scale: scale,
        child: Opacity(
          opacity: (t < start ? 1.0 - 0.8 * dip : 0.2 + 0.8 * p).clamp(0.0, 1.0),
          child: Image.asset('assets/images/logo_anim/petal_$i.png', gaplessPlayback: true),
        ),
      ));
    }
    final centerScale = t < 0.46 ? 1.0 : 1.0 + 0.35 * math.sin(centerPop * math.pi);
    layers.add(Transform.scale(
      scale: centerScale,
      child: Image.asset('assets/images/logo_anim/center.png', gaplessPlayback: true),
    ));

    return Opacity(
      opacity: fade,
      child: Stack(
        fit: StackFit.expand,
        children: [
          const ColoredBox(color: Colors.white),
          CustomPaint(
            painter: _FloodPainter(
              center: center,
              radius: maxRadius * flood,
              ripple: _seg(t, 0.55, 0.90),
              maxRadius: maxRadius,
            ),
          ),
          Center(
            child: Transform.rotate(
              angle: spin * math.pi / 3,
              child: Transform.scale(
                scale: 1.0 + 0.2 * grow,
                child: ColorFiltered(
                  colorFilter: ColorFilter.mode(
                    Colors.white.withValues(alpha: whiten),
                    BlendMode.srcATop,
                  ),
                  child: SizedBox(
                    width: _logoBox,
                    height: _logoBox,
                    child: Stack(fit: StackFit.expand, children: layers),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _FloodPainter extends CustomPainter {
  _FloodPainter({
    required this.center,
    required this.radius,
    required this.ripple,
    required this.maxRadius,
  });

  final Offset center;
  final double radius;
  final double ripple;
  final double maxRadius;

  @override
  void paint(Canvas canvas, Size size) {
    if (radius <= 0) return;
    final rect = Rect.fromCircle(center: center, radius: math.max(radius, 1));
    final paint = Paint()
      ..shader = const LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [Color(0xFFFFA62B), Color(0xFFFF6B4A), Color(0xFFF2557A)],
      ).createShader(Rect.fromCircle(center: center, radius: maxRadius));
    canvas.drawCircle(rect.center, rect.width / 2, paint);

    // Soft expanding rings that trail the flood edge.
    for (var i = 1; i <= 3; i++) {
      final r = radius * (1 - 0.14 * i);
      if (r <= 0) continue;
      canvas.drawCircle(
        center,
        r,
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 3
          ..color = Colors.white.withValues(alpha: 0.18 * (1 - ripple) / i),
      );
    }
  }

  @override
  bool shouldRepaint(_FloodPainter old) =>
      old.radius != radius || old.ripple != ripple || old.center != center;
}
