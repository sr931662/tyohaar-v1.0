import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tyohaar/data/models.dart';
import 'package:tyohaar/data/services/place_search_service.dart';
import 'package:tyohaar/l10n/generated/app_localizations.dart';
import 'package:tyohaar/screens/address/address_flow.dart';
import 'package:tyohaar/theme/theme.dart';

const _place = PlaceSuggestion(
  title: 'Sector 93B',
  subtitle: 'Noida, Uttar Pradesh',
  area: 'Noida',
  city: 'Noida',
  state: 'Uttar Pradesh',
  postalCode: '201304',
  latitude: 28.5,
  longitude: 77.4,
);

void main() {
  accessibilityMain();
  late List<Map<String, dynamic>> saved;

  Future<void> open(WidgetTester tester, {PlaceSuggestion? place = _place}) async {
    tester.view.physicalSize = const Size(900, 2600);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    saved = [];
    await tester.pumpWidget(MaterialApp(
      theme: buildTyTheme(Brightness.light),
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: AddressDetailsScreen(
        initialPlace: place,
        save: (data) async {
          saved.add(data);
          return Address(
            id: 'a1',
            label: 'Home',
            addressLine1: data['address_line_1'] as String,
            city: data['city'] as String,
            state: data['state'] as String,
            postalCode: data['postal_code'] as String,
          );
        },
      ),
    ));
    await tester.pump();
  }

  Finder field(String hint) =>
      find.byWidgetPredicate((w) => w is TextField && w.decoration?.hintText == hint);

  Future<void> save(WidgetTester tester) async {
    await tester.tap(find.text('Save address'));
    await tester.pumpAndSettle();
  }

  testWidgets('the picked place fills city and area; only house/tower/floor is typed', (tester) async {
    await open(tester);
    expect(find.text('Noida'), findsWidgets);
    expect(find.textContaining('Sector 93B'), findsWidgets);

    await tester.enterText(field('House no. / Tower / Floor'), 'Tower A, 12th floor');
    await save(tester);

    final data = saved.single;
    expect(data['address_line_1'], 'Tower A, 12th floor');
    expect(data['address_line_2'], 'Sector 93B, Noida');
    expect(data['locality'], 'Sector 93B');
    expect(data['city'], 'Noida');
    expect(data['state'], 'Uttar Pradesh');
    expect(data['postal_code'], '201304');
    expect(data['latitude'], 28.5);
    expect(data['longitude'], 77.4);
    expect(data['address_type'], 'home');
    expect(data['country'], 'India');
  });

  testWidgets('a missing house number blocks saving and says why', (tester) async {
    await open(tester);
    await save(tester);
    expect(saved, isEmpty);
    expect(find.text('Enter your house number, tower or floor.'), findsOneWidget);
  });

  testWidgets('a bare "12" still satisfies the API minimum length', (tester) async {
    await open(tester);
    await tester.enterText(field('House no. / Tower / Floor'), '12');
    await save(tester);
    expect(saved.single['address_line_1'], '12, Sector 93B');
  });

  testWidgets('"Someone else" needs a name and a valid 10-digit number', (tester) async {
    await open(tester);
    await tester.enterText(field('House no. / Tower / Floor'), 'Flat 4B');
    await tester.tap(find.text('Someone else'));
    await tester.pumpAndSettle();

    await save(tester);
    expect(saved, isEmpty);
    expect(find.text("Enter the receiver's name."), findsOneWidget);
    expect(find.text('Enter a valid 10-digit phone number.'), findsOneWidget);

    await tester.enterText(field("Receiver's name"), 'Asha');
    await tester.enterText(field("Receiver's phone number"), '9876543210');
    await save(tester);
    expect(saved.single['recipient_name'], 'Asha');
    expect(saved.single['recipient_phone'], '+919876543210');
  });

  testWidgets('a pasted Google Maps link is kept, and its coordinates win over the search result', (tester) async {
    await open(tester);
    await tester.enterText(field('House no. / Tower / Floor'), 'Flat 4B');
    await tester.enterText(field('Add Google Maps link (optional)'), 'maps.google.com/maps/@28.5355,77.3910,15z');
    await save(tester);
    final data = saved.single;
    expect(data['delivery_instructions'], 'Google Maps: https://maps.google.com/maps/@28.5355,77.3910,15z');
    expect(data['latitude'], 28.5355);
    expect(data['longitude'], 77.391);
  });

  testWidgets('something that is not a link is refused', (tester) async {
    await open(tester);
    await tester.enterText(field('House no. / Tower / Floor'), 'Flat 4B');
    await tester.enterText(field('Add Google Maps link (optional)'), 'near the big park');
    await save(tester);
    expect(saved, isEmpty);
    expect(find.textContaining("doesn't look like a link"), findsOneWidget);
  });

  testWidgets('a PIN code that is not 6 digits is refused', (tester) async {
    await open(tester);
    await tester.enterText(field('House no. / Tower / Floor'), 'Flat 4B');
    await tester.enterText(field('PIN code'), '2013');
    await save(tester);
    expect(saved, isEmpty);
    expect(find.text('Enter a valid 6-digit PIN code.'), findsOneWidget);
  });
}

void accessibilityMain() {
  group('small phone + largest text size', () {
    for (final scale in [1.0, 1.3]) {
      testWidgets('details screen has no overflow at 320dp, text x$scale', (tester) async {
        tester.view.devicePixelRatio = 1.0;
        tester.view.physicalSize = const Size(320, 640);
        addTearDown(tester.view.reset);
        await tester.pumpWidget(MaterialApp(
          theme: buildTyTheme(Brightness.light),
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          builder: (c, child) => MediaQuery(
              data: MediaQuery.of(c).copyWith(textScaler: TextScaler.linear(scale)), child: child!),
          home: AddressDetailsScreen(initialPlace: _place, save: (d) async => throw UnimplementedError()),
        ));
        await tester.pumpAndSettle();
        // A real person scrolls down to the contact section.
        await tester.scrollUntilVisible(find.text('Someone else'), 200, scrollable: find.byType(Scrollable).first);
        await tester.tap(find.text('Someone else'));
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
      });
    }
  });
}
