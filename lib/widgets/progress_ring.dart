import 'package:flutter/material.dart';
import '../theme/colors.dart';

/// A circular progress ring with a centred label — the planning gauge.
class ProgressRing extends StatelessWidget {
  final double percent; // 0..100
  final double size;
  final double stroke;
  final Widget? center;
  final Color? color;
  const ProgressRing({
    super.key,
    required this.percent,
    this.size = 56,
    this.stroke = 5,
    this.center,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          CustomPaint(
            size: Size(size, size),
            painter: _RingPainter(
              percent: percent.clamp(0, 100).toDouble(),
              track: ty.line,
              color: color ?? ty.saffron,
              stroke: stroke,
            ),
          ),
          if (center != null) center!,
        ],
      ),
    );
  }
}

class _RingPainter extends CustomPainter {
  final double percent;
  final Color track;
  final Color color;
  final double stroke;
  _RingPainter({
    required this.percent,
    required this.track,
    required this.color,
    required this.stroke,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = (size.width - stroke) / 2;
    final trackPaint = Paint()
      ..color = track
      ..style = PaintingStyle.stroke
      ..strokeWidth = stroke;
    final arcPaint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = stroke
      ..strokeCap = StrokeCap.round;

    canvas.drawCircle(center, radius, trackPaint);
    final sweep = 6.2831853 * (percent / 100);
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      -1.5707963, // -90°
      sweep,
      false,
      arcPaint,
    );
  }

  @override
  bool shouldRepaint(covariant _RingPainter old) =>
      old.percent != percent || old.color != color;
}
