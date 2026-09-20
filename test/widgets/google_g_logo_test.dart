import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tyohaar/widgets/google_g_logo.dart';

/// The logo is drawn by a hand-rolled SVG path reader, so these tests render
/// it and sample pixels at known points of the mark — a parser slip would
/// silently produce a wrong shape that a "does it build" test would pass.
void main() {
  const size = 48.0; // 1:1 with the logo's own viewBox, so the path
  // coordinates below double as pixel coordinates.

  late ByteData pixels;

  Future<ByteData> render(WidgetTester tester) async {
    final key = GlobalKey();
    await tester.pumpWidget(
      MaterialApp(
        home: Center(
          child: RepaintBoundary(
            key: key,
            child: const GoogleGLogo(size: size),
          ),
        ),
      ),
    );
    late ByteData data;
    await tester.runAsync(() async {
      final boundary =
          key.currentContext!.findRenderObject()! as RenderRepaintBoundary;
      final image = await boundary.toImage(pixelRatio: 1);
      data = (await image.toByteData(format: ui.ImageByteFormat.rawRgba))!;
    });
    return data;
  }

  Color at(ByteData data, int x, int y) {
    final i = (y * size.toInt() + x) * 4;
    return Color.fromARGB(
      data.getUint8(i + 3),
      data.getUint8(i),
      data.getUint8(i + 1),
      data.getUint8(i + 2),
    );
  }

  /// Compares only the dominant hue, so antialiasing can't flake the test.
  void expectRoughly(Color actual, Color expected, String where) {
    expect(actual.a, greaterThan(0.5), reason: '$where should be opaque');
    for (final (name, a, e) in [
      ('red', actual.r, expected.r),
      ('green', actual.g, expected.g),
      ('blue', actual.b, expected.b),
    ]) {
      expect((a - e).abs(), lessThan(0.2), reason: '$where: $name channel');
    }
  }

  testWidgets('renders the four brand colours in the right quadrants',
      (tester) async {
    pixels = await render(tester);

    // Blue: the horizontal crossbar, which spans x 24→35.8 at y≈20→28.5.
    expectRoughly(at(pixels, 30, 24), const Color(0xFF4285F4), 'crossbar');
    // Red: the top arc.
    expectRoughly(at(pixels, 24, 6), const Color(0xFFEA4335), 'top arc');
    // Yellow: the left arc.
    expectRoughly(at(pixels, 6, 24), const Color(0xFFFBBC05), 'left arc');
    // Green: the bottom arc.
    expectRoughly(at(pixels, 24, 43), const Color(0xFF34A853), 'bottom arc');
  });

  testWidgets('leaves the centre of the G hollow', (tester) async {
    pixels = await render(tester);

    // Between the ring's inner edge (x≈11.7) and the crossbar (x=24) the
    // mark is empty. If the parser mis-closed a subpath this fills in.
    expect(at(pixels, 17, 24).a, lessThan(0.1), reason: 'centre must be clear');
    // Outside the ring entirely.
    expect(at(pixels, 1, 1).a, lessThan(0.1), reason: 'corner must be clear');
  });

  testWidgets('scales without error', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: Center(child: GoogleGLogo(size: 20))),
    );
    expect(tester.getSize(find.byType(GoogleGLogo)), const Size(20, 20));
    expect(tester.takeException(), isNull);
  });
}
