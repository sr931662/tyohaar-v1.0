import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/test/test_flutter_secure_storage_platform.dart';
import 'package:flutter_secure_storage_platform_interface/flutter_secure_storage_platform_interface.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tyohaar/data/api_client.dart';
import 'package:tyohaar/data/auth_manager.dart';
import 'package:tyohaar/data/models.dart';
import 'package:tyohaar/l10n/generated/app_localizations.dart';
import 'package:tyohaar/screens/payment_screen.dart';
import 'package:tyohaar/screens/plan_flow/plan_flow_screen.dart';
import 'package:tyohaar/theme/theme.dart';

/// A small fake of the Tyohaar API: just enough state to walk a customer
/// through choosing add-ons, picking an address and booking.
class _FakeApi implements HttpClientAdapter {
  final List<RequestOptions> log = [];
  Map<String, dynamic>? bookingBody;
  int bookingCalls = 0;

  /// What the server says the booking costs. Deliberately independent of what
  /// the client computed, so the test proves the payment screen shows the
  /// server's figure and the summary shows the client's preview.
  double serverTotal = 1350;
  bool noAddresses = false;
  bool failBooking = false;

  @override
  void close({bool force = false}) {}

  ResponseBody _ok(Object data) => ResponseBody.fromString(
        jsonEncode({'data': data}),
        200,
        headers: {Headers.contentTypeHeader: [Headers.jsonContentType]},
      );

  @override
  Future<ResponseBody> fetch(RequestOptions o, Stream<Uint8List>? s, Future<void>? c) async {
    log.add(o);
    final p = o.path;
    final m = o.method;
    if (m == 'GET' && p == 'occasions') {
      return _ok([
        {'id': 'occ1', 'name': 'Birthday', 'allow_balloon_theme': true},
      ]);
    }
    if (m == 'GET' && p == 'users/me/addresses') {
      return _ok(noAddresses
          ? []
          : [
              {
                'id': 'ad1',
                'label': 'Home',
                'address_line_1': 'Tower A, 12th floor',
                'city': 'Noida',
                'state': 'Uttar Pradesh',
                'postal_code': '201304',
              }
            ]);
    }
    if (m == 'GET' && p == 'common/finance-settings') return _ok({'gst_enabled': false});
    if (m == 'GET' && p == 'packages/p1/items') {
      return _ok([
        {'id': 'i1', 'name': 'Backdrop', 'base_price': '100', 'quantity': 1, 'is_mandatory': true},
        {'id': 'i2', 'name': 'Cake', 'base_price': '250', 'quantity': 1, 'is_mandatory': false},
      ]);
    }
    if (m == 'GET' && p == 'packages/p1/services') return _ok([]);
    if (m == 'POST' && p == 'payments/coupons/preview') {
      final sub = (o.data as Map)['subtotal'] as num;
      return _ok({
        'original_amount': sub,
        'applied_discounts': [],
        'total_discount': 0,
        'final_amount': sub,
      });
    }
    if (m == 'POST' && p == 'bookings') {
      bookingCalls++;
      bookingBody = Map<String, dynamic>.from(o.data as Map);
      if (failBooking) {
        return ResponseBody.fromString(
          jsonEncode({'error': {'code': 'X', 'message': 'nope'}}),
          500,
          headers: {Headers.contentTypeHeader: [Headers.jsonContentType]},
        );
      }
      return _ok({
        'id': 'b0000000-aaaa-bbbb-cccc-dddddddddddd',
        'booking_number': 'TY-1',
        'celebration_id': 'c1',
        'booking_status': 'pending',
        'payment_status': 'pending',
        'total_amount': serverTotal.toString(),
      });
    }
    // Anything else the screens ask for (palette, finishes, …): empty.
    return _ok([]);
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  FlutterSecureStoragePlatform.instance = TestFlutterSecureStoragePlatform({});

  late _FakeApi api;

  const package = Package(
    id: 'p1',
    name: 'Birthday Luxe',
    price: 1000,
    tint: 'saffron',
    occasionIds: ['occ1'],
  );

  setUp(() async {
    api = _FakeApi();
    ApiClient().dio.httpClientAdapter = api;
    ApiClient().clearCache();
    await AuthManager.instance.login(
      'access',
      'refresh',
      User(id: 'u1', fullName: 'Asha', role: 'customer', status: 'active', emailVerified: true),
    );
  });

  tearDown(() => AuthManager.instance.logout());

  Future<void> start(WidgetTester tester, {Size size = const Size(390, 844)}) async {
    tester.view.devicePixelRatio = 1.0;
    tester.view.physicalSize = size;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(MaterialApp(
      theme: buildTyTheme(Brightness.light),
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: const PlanFlowScreen(initialPackage: package),
    ));
    await tester.pumpAndSettle();
  }

  Future<void> tapText(WidgetTester tester, String text) async {
    await tester.tap(find.text(text).last);
    await tester.pumpAndSettle();
  }

  testWidgets('customer opens a package, adds a cake, books, and is charged what the server says', (tester) async {
    await start(tester);

    // Opens straight on add-ons: the package is already chosen.
    expect(find.text('Step 1 of 3'), findsOneWidget);
    expect(find.text('Backdrop'), findsOneWidget);
    expect(find.text('Cake'), findsOneWidget);

    // Switch the optional cake on.
    await tester.tap(find.byType(Switch).last);
    await tester.pumpAndSettle();

    await tapText(tester, 'Continue'); // → details
    await tapText(tester, 'Continue'); // → summary

    expect(find.text('Step 3 of 3'), findsOneWidget);
    // 1000 package + 100 included backdrop + 250 cake.
    expect(find.text('₹1,350'), findsWidgets);
    expect(find.textContaining('Tower A, 12th floor'), findsWidgets);

    await tapText(tester, 'Proceed To Payment');

    // The booking carried the choices (and a saved address), once.
    expect(api.bookingCalls, 1);
    expect(api.bookingBody!['package_id'], 'p1');
    expect(api.bookingBody!['item_ids'], ['i2']);
    expect(api.bookingBody!['address_id'], 'ad1');
    expect(api.bookingBody!['occasion_id'], 'occ1');

    // And the customer lands on payment with the server's total, grouped.
    expect(find.byType(PaymentScreen), findsOneWidget);
    expect(find.text('₹1,350'), findsOneWidget);
    expect(find.text('Pay ₹1,350'), findsOneWidget);
    expect(find.text('Birthday Luxe'), findsOneWidget);
  });

  testWidgets('a large amount reads with Indian digit grouping and keeps its paise', (tester) async {
    api.serverTotal = 201098.5;
    await start(tester);
    await tapText(tester, 'Continue');
    await tapText(tester, 'Continue');
    await tapText(tester, 'Proceed To Payment');
    expect(find.text('₹2,01,098.50'), findsOneWidget);
    expect(find.text('Pay ₹2,01,098.50'), findsOneWidget);
  });

  testWidgets('without an address the customer is stopped and asked, nothing is booked', (tester) async {
    api.noAddresses = true;
    await start(tester);
    await tapText(tester, 'Continue');
    await tapText(tester, 'Continue');
    await tapText(tester, 'Proceed To Payment');

    expect(api.bookingCalls, 0);
    // The "current location?" sheet is what opens.
    expect(find.text('Do you want this order at your current location?'), findsOneWidget);
    expect(find.text('No, at some other location'), findsOneWidget);
  });

  testWidgets('a double-tap on Proceed To Payment books once', (tester) async {
    await start(tester);
    await tapText(tester, 'Continue');
    await tapText(tester, 'Continue');
    final button = find.text('Proceed To Payment').last;
    await tester.tap(button);
    await tester.tap(button, warnIfMissed: false);
    await tester.pumpAndSettle();
    expect(api.bookingCalls, 1);
  });

  testWidgets('a failed booking keeps the customer on the summary with a message and can retry', (tester) async {
    api.failBooking = true;
    await start(tester);
    await tapText(tester, 'Continue');
    await tapText(tester, 'Continue');
    await tapText(tester, 'Proceed To Payment');

    expect(find.byType(PaymentScreen), findsNothing);
    expect(find.text('Proceed To Payment'), findsWidgets); // still there, enabled again
    expect(find.byType(SnackBar), findsOneWidget);

    api.failBooking = false;
    await tester.pump(const Duration(seconds: 5));
    await tapText(tester, 'Proceed To Payment');
    expect(find.byType(PaymentScreen), findsOneWidget);
  });

  for (final w in [320.0, 360.0, 412.0]) {
    testWidgets('the whole flow lays out without overflow at ${w.toInt()}dp', (tester) async {
      await start(tester, size: Size(w, 700));
      await tapText(tester, 'Continue');
      await tapText(tester, 'Continue');
      expect(tester.takeException(), isNull);
    });
  }
}
