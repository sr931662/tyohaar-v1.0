import 'package:flutter/material.dart';

/// The official four-colour Google "G", drawn from the logo's own SVG path
/// data so the mark stays exact at any size without shipping a raster asset
/// or pulling in an SVG package.
class GoogleGLogo extends StatelessWidget {
  final double size;

  const GoogleGLogo({super.key, this.size = 20});

  @override
  Widget build(BuildContext context) {
    return SizedBox.square(
      dimension: size,
      child: CustomPaint(painter: _GoogleGPainter()),
    );
  }
}

// Paths are authored against the logo's 48×48 viewBox and scaled to fit.
const double _kViewBox = 48;

const _kSegments = <(String, Color)>[
  (
    'M45.12 24.5c0-1.56-.14-3.06-.4-4.5H24v8.51h11.84c-.51 2.75-2.06 5.08-4.39 '
        '6.64v5.52h7.11c4.16-3.83 6.56-9.47 6.56-16.17z',
    Color(0xFF4285F4),
  ),
  (
    'M24 46c5.94 0 10.92-1.97 14.56-5.33l-7.11-5.52c-1.97 1.32-4.49 2.1-7.45 '
        '2.1-5.73 0-10.58-3.87-12.31-9.07H4.34v5.7C7.96 41.07 15.4 46 24 46z',
    Color(0xFF34A853),
  ),
  (
    'M11.69 28.18C11.25 26.86 11 25.45 11 24s.25-2.86.69-4.18v-5.7H4.34C2.85 '
        '17.09 2 20.45 2 24s.85 6.91 2.34 9.88l7.35-5.7z',
    Color(0xFFFBBC05),
  ),
  (
    'M24 10.75c3.23 0 6.13 1.11 8.41 3.29l6.31-6.31C34.91 4.18 29.93 2 24 2 '
        '15.4 2 7.96 6.93 4.34 14.12l7.35 5.7c1.73-5.2 6.58-9.07 12.31-9.07z',
    Color(0xFFEA4335),
  ),
];

class _GoogleGPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    canvas.save();
    canvas.scale(size.width / _kViewBox, size.height / _kViewBox);
    final paint = Paint()..isAntiAlias = true;
    for (final (d, color) in _kSegments) {
      canvas.drawPath(_parseSvgPath(d), paint..color = color);
    }
    canvas.restore();
  }

  @override
  bool shouldRepaint(covariant _GoogleGPainter oldDelegate) => false;
}

final _tokenPattern = RegExp(r'[MmLlHhVvCcSsZz]|-?\d*\.?\d+(?:[eE][-+]?\d+)?');
final _commandPattern = RegExp(r'^[A-Za-z]$');

/// Minimal SVG path reader covering the command set these four paths use
/// (move, line, horizontal/vertical line, cubic, smooth cubic, close).
/// Deliberately not a general parser — arcs and quadratics are not supported.
Path _parseSvgPath(String d) {
  final path = Path();
  final tokens = _tokenPattern.allMatches(d).map((m) => m.group(0)!).toList();

  var i = 0;
  double next() => double.parse(tokens[i++]);

  var cx = 0.0, cy = 0.0; // current point
  var startX = 0.0, startY = 0.0; // current subpath start, for close()
  double? prevC2x, prevC2y; // previous cubic's 2nd control point, for S/s
  var cmd = '';

  while (i < tokens.length) {
    if (_commandPattern.hasMatch(tokens[i])) {
      cmd = tokens[i];
      i++;
      if (cmd == 'Z' || cmd == 'z') {
        path.close();
        cx = startX;
        cy = startY;
        prevC2x = prevC2y = null;
        continue;
      }
    }

    // Offsets in relative commands are all measured from the point the
    // command started at, so snapshot it before consuming any numbers.
    final ox = cx, oy = cy;
    final relative = cmd == cmd.toLowerCase();
    double dx(double v) => relative ? ox + v : v;
    double dy(double v) => relative ? oy + v : v;

    switch (cmd.toUpperCase()) {
      case 'M':
        cx = dx(next());
        cy = dy(next());
        path.moveTo(cx, cy);
        startX = cx;
        startY = cy;
        // Extra coordinate pairs after a moveto are implicit linetos.
        cmd = relative ? 'l' : 'L';
        prevC2x = prevC2y = null;
      case 'L':
        cx = dx(next());
        cy = dy(next());
        path.lineTo(cx, cy);
        prevC2x = prevC2y = null;
      case 'H':
        cx = dx(next());
        path.lineTo(cx, cy);
        prevC2x = prevC2y = null;
      case 'V':
        cy = dy(next());
        path.lineTo(cx, cy);
        prevC2x = prevC2y = null;
      case 'C':
        final x1 = dx(next()), y1 = dy(next());
        final x2 = dx(next()), y2 = dy(next());
        cx = dx(next());
        cy = dy(next());
        path.cubicTo(x1, y1, x2, y2, cx, cy);
        prevC2x = x2;
        prevC2y = y2;
      case 'S':
        // The first control point mirrors the previous cubic's second one;
        // with no preceding cubic it coincides with the current point.
        final x1 = prevC2x == null ? cx : 2 * cx - prevC2x;
        final y1 = prevC2y == null ? cy : 2 * cy - prevC2y;
        final x2 = dx(next()), y2 = dy(next());
        cx = dx(next());
        cy = dy(next());
        path.cubicTo(x1, y1, x2, y2, cx, cy);
        prevC2x = x2;
        prevC2y = y2;
    }
  }
  return path;
}
