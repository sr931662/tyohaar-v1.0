import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/test/test_flutter_secure_storage_platform.dart';
import 'package:flutter_secure_storage_platform_interface/flutter_secure_storage_platform_interface.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tyohaar/data/api_client.dart';
import 'package:tyohaar/data/models.dart';
import 'package:tyohaar/data/services/place_search_service.dart';
import 'package:tyohaar/l10n/generated/app_localizations.dart';
import 'package:tyohaar/screens/address/address_flow.dart';
import 'package:tyohaar/theme/theme.dart';

/// Photon stand-in whose answers the test releases by hand, so a slow answer
/// to an old keystroke can be made to arrive after a newer one.
class _Photon implements HttpClientAdapter {
  final Map<String, Completer<ResponseBody>> pending = {};
  final List<String> queries = [];
  bool offline = false;

  static ResponseBody feature(String name, String city, {String? pin}) => ResponseBody.fromString(
        jsonEncode({
          'features': [
            {
              'geometry': {'coordinates': [77.4, 28.5]},
              'properties': {
                'name': name,
                'city': city,
                'state': 'Uttar Pradesh',
                'countrycode': 'IN',
                if (pin != null) 'postcode': pin,
              },
            },
            // Outside India: must never be offered.
            {
              'geometry': {'coordinates': [-0.1, 51.5]},
              'properties': {'name': '$name (London)', 'city': 'London', 'countrycode': 'GB'},
            },
          ],
        }),
        200,
        headers: {Headers.contentTypeHeader: [Headers.jsonContentType]},
      );

  @override
  void close({bool force = false}) {}

  @override
  Future<ResponseBody> fetch(RequestOptions o, Stream<Uint8List>? s, Future<void>? cancel) {
    final q = o.queryParameters['q'] as String;
    queries.add(q);
    if (offline) {
      throw DioException(requestOptions: o, type: DioExceptionType.connectionError);
    }
    final c = pending[q] = Completer<ResponseBody>();
    cancel?.then((_) {
      if (!c.isCompleted) c.completeError(DioException(requestOptions: o, type: DioExceptionType.cancel));
    });
    return c.future;
  }
}

/// Answers the app's own API (city list etc.) with empty data.
class _EmptyApi implements HttpClientAdapter {
  @override
  void close({bool force = false}) {}
  @override
  Future<ResponseBody> fetch(RequestOptions o, Stream<Uint8List>? s, Future<void>? c) async =>
      ResponseBody.fromString(jsonEncode({'data': []}), 200,
          headers: {Headers.contentTypeHeader: [Headers.jsonContentType]});
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  FlutterSecureStoragePlatform.instance = TestFlutterSecureStoragePlatform({});

  late _Photon photon;
  late List<Map<String, dynamic>> saved;

  cityOverlapTests();

  setUp(() {
    photon = _Photon();
    PlaceSearchService.instance.debugReset(dio: Dio()..httpClientAdapter = photon);
    ApiClient().dio.httpClientAdapter = _EmptyApi();
    ApiClient().clearCache();
    saved = [];
  });

  /// The details screen exactly as it opens after "No, at some other location".
  Future<void> openOtherLocation(WidgetTester tester) async {
    tester.view.devicePixelRatio = 1.0;
    tester.view.physicalSize = const Size(390, 844);
    addTearDown(tester.view.reset);
    await tester.pumpWidget(MaterialApp(
      theme: buildTyTheme(Brightness.light),
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: AddressDetailsScreen(
        save: (d) async {
          saved.add(d);
          return Address(
              id: 'a', label: 'Home', addressLine1: d['address_line_1'] as String, city: d['city'] as String,
              state: d['state'] as String, postalCode: d['postal_code'] as String);
        },
      ),
    ));
    await tester.pumpAndSettle();
  }

  Finder searchBox() => find.byWidgetPredicate((w) => w is TextField && w.decoration?.hintText == 'Search area, street or landmark');

  testWidgets('"some other location" opens the area search by itself, with a helpful prompt', (tester) async {
    await openOtherLocation(tester);
    expect(searchBox(), findsOneWidget);
    expect(find.text('Type at least 2 letters to search.'), findsOneWidget);
    expect(find.text('Use my current location'), findsOneWidget);
  });

  testWidgets('typing shows suggestions; picking one fills the form and closes the search', (tester) async {
    await openOtherLocation(tester);
    await tester.enterText(searchBox(), 'sector 93');
    await tester.pump(const Duration(milliseconds: 400)); // debounce
    expect(photon.queries, ['sector 93']);
    photon.pending['sector 93']!.complete(_Photon.feature('Sector 93B', 'Noida', pin: '201304'));
    await tester.pumpAndSettle();

    expect(find.text('Sector 93B'), findsOneWidget);
    expect(find.textContaining('London'), findsNothing, reason: 'results outside India are filtered out');

    await tester.tap(find.text('Sector 93B'));
    await tester.pumpAndSettle();

    expect(searchBox(), findsNothing);
    expect(find.text('Noida'), findsWidgets); // city tile now filled
    await tester.enterText(
        find.byWidgetPredicate((w) => w is TextField && w.decoration?.hintText == 'House no. / Tower / Floor'), 'Tower A');
    await tester.tap(find.text('Save address'));
    await tester.pumpAndSettle();
    expect(saved.single['city'], 'Noida');
    expect(saved.single['postal_code'], '201304');
  });

  testWidgets('fast typing sends one request, not one per keystroke', (tester) async {
    await openOtherLocation(tester);
    for (final t in ['se', 'sec', 'sect', 'secto', 'sector']) {
      await tester.enterText(searchBox(), t);
      await tester.pump(const Duration(milliseconds: 60));
    }
    await tester.pump(const Duration(milliseconds: 400));
    expect(photon.queries, ['sector']);
  });

  testWidgets('a slow answer to an OLD query never overwrites the newer results', (tester) async {
    await openOtherLocation(tester);
    await tester.enterText(searchBox(), 'sector 1');
    await tester.pump(const Duration(milliseconds: 400));
    await tester.enterText(searchBox(), 'sector 93');
    await tester.pump(const Duration(milliseconds: 400));
    expect(photon.queries, ['sector 1', 'sector 93']);

    photon.pending['sector 93']!.complete(_Photon.feature('Sector 93B', 'Noida'));
    await tester.pumpAndSettle();
    // The stale request now answers late.
    if (!photon.pending['sector 1']!.isCompleted) {
      photon.pending['sector 1']!.complete(_Photon.feature('Sector 1 Old Result', 'Noida'));
    }
    await tester.pumpAndSettle();

    expect(find.text('Sector 93B'), findsOneWidget);
    expect(find.text('Sector 1 Old Result'), findsNothing);
  });

  testWidgets('with no network the search says so instead of looking empty', (tester) async {
    photon.offline = true;
    await openOtherLocation(tester);
    await tester.enterText(searchBox(), 'sector 93');
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pumpAndSettle();
    expect(find.textContaining('Check your connection'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('clearing the box returns to the prompt', (tester) async {
    await openOtherLocation(tester);
    await tester.enterText(searchBox(), 'sector 93');
    await tester.pump(const Duration(milliseconds: 400));
    photon.pending['sector 93']!.complete(_Photon.feature('Sector 93B', 'Noida'));
    await tester.pumpAndSettle();
    await tester.tap(find.byIcon(Icons.close_rounded).last);
    await tester.pumpAndSettle();
    expect(find.text('Type at least 2 letters to search.'), findsOneWidget);
    expect(find.text('Sector 93B'), findsNothing);
  });
}

void cityOverlapTests() {
  testWidgets('picking "Sector 93B (Greater Noida)" while on Noida keeps the customer\'s city', (tester) async {
    tester.view.devicePixelRatio = 1.0;
    tester.view.physicalSize = const Size(390, 844);
    addTearDown(tester.view.reset);
    final photon = _Photon();
    PlaceSearchService.instance.debugReset(dio: Dio()..httpClientAdapter = photon);
    ApiClient().dio.httpClientAdapter = _EmptyApi();
    final saved = <Map<String, dynamic>>[];
    await tester.pumpWidget(MaterialApp(
      theme: buildTyTheme(Brightness.light),
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: AddressDetailsScreen(
        initialPlace: const PlaceSuggestion(
            title: 'Sector 62', subtitle: 'Noida', city: 'Noida', state: 'Uttar Pradesh', postalCode: '201301'),
        save: (d) async {
          saved.add(d);
          return Address(id: 'a', label: 'Home', addressLine1: 'x', city: 'Noida', state: 'u', postalCode: '1');
        },
      ),
    ));
    await tester.pumpAndSettle();

    // Change the area; the map returns it labelled "Greater Noida".
    await tester.tap(find.text('Change').last);
    await tester.pumpAndSettle();
    await tester.enterText(
        find.byWidgetPredicate((w) => w is TextField && w.decoration?.hintText == 'Search area, street or landmark'),
        'sector 93');
    await tester.pump(const Duration(milliseconds: 400));
    photon.pending['sector 93, Noida']!.complete(_Photon.feature('Sector 93B', 'Greater Noida'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Sector 93B'));
    await tester.pumpAndSettle();

    await tester.enterText(
        find.byWidgetPredicate((w) => w is TextField && w.decoration?.hintText == 'House no. / Tower / Floor'), 'Tower A');
    await tester.tap(find.text('Save address'));
    await tester.pumpAndSettle();
    expect(saved.single['city'], 'Noida');
    expect(saved.single['state'], 'Uttar Pradesh');
    expect(saved.single['postal_code'], '201301', reason: 'the PIN must not be wiped by a spurious city change');
  });
}
