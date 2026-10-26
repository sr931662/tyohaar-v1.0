import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tyohaar/theme/theme.dart';
import 'package:tyohaar/widgets/adaptive_nav_bar.dart';

const _destinations = [
  TyNavDestination(label: 'Home', icon: Icons.home_outlined, activeIcon: Icons.home_rounded),
  TyNavDestination(label: 'Plans', icon: Icons.event_note_outlined, activeIcon: Icons.event_note),
  TyNavDestination(label: 'Invitations', icon: Icons.mail_outline, activeIcon: Icons.mail),
  TyNavDestination(label: 'Account', icon: Icons.person_outline, activeIcon: Icons.person),
];

Widget _shell({
  required TargetPlatform platform,
  int? selected = 0,
  ValueChanged<int>? onSelected,
  Brightness brightness = Brightness.dark,
  double textScale = 1.0,
  EdgeInsets viewPadding = EdgeInsets.zero,
  ValueChanged<double>? onBodyBottomPadding,
}) {
  return MaterialApp(
    theme: buildTyTheme(brightness).copyWith(platform: platform),
    home: Builder(
      builder: (context) => MediaQuery(
        data: MediaQuery.of(context).copyWith(
          textScaler: TextScaler.linear(textScale),
          padding: viewPadding,
          viewPadding: viewPadding,
        ),
        child: Scaffold(
          extendBody: true,
          body: Builder(builder: (context) {
            onBodyBottomPadding?.call(MediaQuery.paddingOf(context).bottom);
            return ListView(children: [for (var i = 0; i < 40; i++) Text('row $i')]);
          }),
          bottomNavigationBar: TyAdaptiveNavBar(
            destinations: _destinations,
            selectedIndex: selected,
            onDestinationSelected: onSelected ?? (_) {},
          ),
        ),
      ),
    ),
  );
}

void main() {
  testWidgets('iOS renders the frosted glass dock', (tester) async {
    await tester.pumpWidget(_shell(platform: TargetPlatform.iOS));
    expect(find.byType(BackdropFilter), findsOneWidget);
    expect(find.byType(InkWell), findsNothing);
  });

  testWidgets('Android renders a solid bar with no blur', (tester) async {
    await tester.pumpWidget(_shell(platform: TargetPlatform.android));
    expect(find.byType(BackdropFilter), findsNothing);
    expect(find.byType(InkWell), findsNWidgets(_destinations.length));
  });

  for (final platform in [TargetPlatform.iOS, TargetPlatform.android]) {
    testWidgets('${platform.name}: taps report the dock slot', (tester) async {
      final taps = <int>[];
      await tester.pumpWidget(_shell(platform: platform, onSelected: taps.add));
      await tester.tap(find.text('Invitations'));
      await tester.tap(find.text('Account'));
      await tester.pumpAndSettle();
      expect(taps, [2, 3]);
    });

    testWidgets('${platform.name}: selection is exposed to accessibility', (tester) async {
      final handle = tester.ensureSemantics();
      await tester.pumpWidget(_shell(platform: platform, selected: 1));
      expect(
        tester.getSemantics(find.bySemanticsLabel('Plans')),
        isSemantics(
          isButton: true,
          isSelected: true,
          hasSelectedState: true,
          hasTapAction: true,
        ),
      );
      handle.dispose();
    });

    testWidgets('${platform.name}: no slot selected is allowed', (tester) async {
      await tester.pumpWidget(_shell(platform: platform, selected: null));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    });

    for (final brightness in Brightness.values) {
      testWidgets('${platform.name}/${brightness.name}: fits a 320pt screen at max text scale',
          (tester) async {
        tester.view.physicalSize = const Size(320, 568);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.reset);
        await tester.pumpWidget(_shell(
          platform: platform,
          brightness: brightness,
          textScale: 1.3,
          viewPadding: const EdgeInsets.only(bottom: 34),
        ));
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
      });
    }

    testWidgets('${platform.name}: body padding clears the whole bar', (tester) async {
      var bodyBottom = 0.0;
      await tester.pumpWidget(_shell(
        platform: platform,
        viewPadding: const EdgeInsets.only(bottom: 34),
        onBodyBottomPadding: (v) => bodyBottom = v,
      ));
      await tester.pumpAndSettle();
      final bar = tester.getRect(find.byType(TyAdaptiveNavBar));
      final screenHeight = tester.view.physicalSize.height / tester.view.devicePixelRatio;
      // Scroll views pad by this, so their last item rests above the dock.
      expect(bodyBottom, greaterThanOrEqualTo(screenHeight - bar.top));
    });
  }
}
