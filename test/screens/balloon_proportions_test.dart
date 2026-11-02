import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tyohaar/screens/plan_flow/balloon_proportions.dart';
import 'package:tyohaar/screens/plan_flow/plan_logic.dart';
import 'package:tyohaar/theme/theme.dart';

void _valid(List<int> r) {
  expect(r.fold<int>(0, (a, b) => a + b), 100, reason: '$r must add up to 100');
  for (final v in r) {
    expect(v >= kBalloonRatioMin, isTrue, reason: '$r has a share under the minimum');
    expect(v % kBalloonRatioStep, 0, reason: '$r is off the 5% grid');
  }
}

void main() {
  group('proportion maths', () {
    test('even starting mixes', () {
      expect(evenBalloonProportions(0), isEmpty);
      expect(evenBalloonProportions(1), isEmpty);
      expect(evenBalloonProportions(2), [50, 50]);
      expect(evenBalloonProportions(3), [30, 30, 40]);
      expect(evenBalloonProportions(4), [25, 25, 25, 25]);
    });

    test("the user's example: 30% red, 20% gold, the rest white", () {
      var r = evenBalloonProportions(3);
      r = setBalloonProportion(r, 0, 30);
      r = setBalloonProportion(r, 1, 20);
      expect(r, [30, 20, 50]);
    });

    test('values snap to 5% and clamp so the last colour keeps at least 5%', () {
      final r = evenBalloonProportions(3); // [30, 30, 40]
      expect(setBalloonProportion(r, 0, 32), [30, 30, 40]);
      expect(setBalloonProportion(r, 0, 33), [35, 30, 35]);
      expect(setBalloonProportion(r, 0, 99), [65, 30, 5]); // 100 - 30 - 5
      expect(setBalloonProportion(r, 0, 0), [5, 30, 65]);
    });

    test('the last colour cannot be set directly', () {
      final r = [30, 30, 40];
      expect(setBalloonProportion(r, 2, 10), same(r));
      expect(setBalloonProportion(r, 9, 10), same(r));
    });

    test('random dragging never breaks the rules', () {
      final rnd = Random(7);
      for (final n in [2, 3, 4]) {
        var r = evenBalloonProportions(n);
        for (var step = 0; step < 500; step++) {
          r = setBalloonProportion(r, rnd.nextInt(n - 1), rnd.nextInt(130) - 15);
          _valid(r);
        }
      }
    });
  });

  group('BalloonProportionMeter', () {
    Widget host(Widget child) => MaterialApp(
          theme: buildTyTheme(Brightness.light),
          home: Scaffold(body: Center(child: SizedBox(width: 400, child: child))),
        );

    testWidgets('tapping along the bar sets the share', (tester) async {
      int? got;
      await tester.pumpWidget(host(BalloonProportionMeter(
        colour: const BalloonShare('Red', Color(0xFFE63946)),
        percent: 30,
        max: 65,
        onChanged: (v) => got = v,
      )));
      final bar = tester.getRect(find.byType(GestureDetector).first);
      await tester.tapAt(Offset(bar.left + bar.width * 0.5, bar.center.dy));
      expect(got, 50);
    });

    testWidgets('dragging reports values as the finger moves', (tester) async {
      final seen = <int>[];
      await tester.pumpWidget(host(BalloonProportionMeter(
        colour: const BalloonShare('Gold', Color(0xFFD4AF37)),
        percent: 20,
        max: 65,
        onChanged: seen.add,
      )));
      final bar = tester.getRect(find.byType(GestureDetector).first);
      await tester.dragFrom(Offset(bar.left + bar.width * 0.2, bar.center.dy), Offset(bar.width * 0.3, 0));
      expect(seen, isNotEmpty);
      expect(seen.last, greaterThan(40));
    });

    testWidgets('the automatic last colour shows its share but cannot move', (tester) async {
      await tester.pumpWidget(host(const BalloonProportionMeter(
        colour: BalloonShare('White', Color(0xFFFFFFFF)),
        percent: 50,
        max: 50,
        onChanged: null,
        autoLabel: 'auto',
      )));
      expect(find.text('50%'), findsOneWidget);
      expect(find.text('auto'), findsOneWidget);
      final bar = tester.getRect(find.byType(GestureDetector).first);
      await tester.tapAt(Offset(bar.left + 10, bar.center.dy)); // nothing to call; must not throw
    });

    testWidgets('screen readers can step the share up and down', (tester) async {
      final handle = tester.ensureSemantics();
      int? got;
      await tester.pumpWidget(host(BalloonProportionMeter(
        colour: const BalloonShare('Red', Color(0xFFE63946)),
        percent: 30,
        max: 65,
        onChanged: (v) => got = v,
      )));
      final node = tester.getSemantics(find.byType(BalloonProportionMeter));
      expect(node.value, '30%');
      tester.semantics.performAction(find.semantics.byValue('30%'), SemanticsAction.increase);
      expect(got, 35);
      handle.dispose();
    });
  });

  testWidgets('the mix strip draws one segment per colour', (tester) async {
    await tester.pumpWidget(MaterialApp(
      theme: buildTyTheme(Brightness.light),
      home: const Scaffold(
        body: BalloonMixPreview(
          colours: [BalloonShare('Red', Colors.red), BalloonShare('Gold', Colors.amber), BalloonShare('White', Colors.white)],
          ratios: [30, 20, 50],
        ),
      ),
    ));
    final flexes = tester.widgetList<Expanded>(find.byType(Expanded)).map((e) => e.flex).toList();
    expect(flexes, [30, 20, 50]);
  });
}
