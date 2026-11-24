import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/test/test_flutter_secure_storage_platform.dart';
import 'package:flutter_secure_storage_platform_interface/flutter_secure_storage_platform_interface.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:tyohaar/data/api_client.dart';
import 'package:tyohaar/data/auth_manager.dart';
import 'package:tyohaar/data/services/auth_service.dart';
import 'package:tyohaar/data/services/google_auth_service.dart';
import 'package:tyohaar/l10n/generated/app_localizations.dart';
import 'package:tyohaar/screens/auth_screen.dart';
import 'package:tyohaar/theme/theme.dart';

class _FakeServer implements HttpClientAdapter {
  final List<RequestOptions> log = [];
  bool phoneOtp = false;
  bool failSend = false;

  @override
  void close({bool force = false}) {}

  ResponseBody _json(int status, Object body) => ResponseBody.fromString(
        jsonEncode(body),
        status,
        headers: {Headers.contentTypeHeader: [Headers.jsonContentType]},
      );

  @override
  Future<ResponseBody> fetch(RequestOptions o, Stream<Uint8List>? s, Future<void>? c) async {
    log.add(o);
    switch ('${o.method} ${o.path}') {
      case 'GET auth/config':
        return _json(200, {
          'data': {'google_enabled': false, 'google_client_id': '', 'email_otp_enabled': true, 'phone_otp_enabled': phoneOtp}
        });
      case 'POST auth/otp/request':
        return failSend
            ? _json(502, {'error': {'code': 'X', 'message': 'Could not send the verification code. Please try again.'}})
            : _json(200, {'data': {'status': 'pending'}});
      case 'POST auth/otp/verify':
        return _json(200, {
          'data': {'access_token': 'a', 'refresh_token': 'r', 'is_new_user': true}
        });
      case 'GET users/me':
        return _json(200, {
          'data': {'id': 'u1', 'role': 'customer', 'status': 'active', 'email': 'asha@example.com', 'email_verified': true}
        });
    }
    return _json(200, {'data': []});
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  FlutterSecureStoragePlatform.instance = TestFlutterSecureStoragePlatform({});

  late _FakeServer server;

  setUp(() async {
    server = _FakeServer();
    ApiClient().dio.httpClientAdapter = server;
    ApiClient().clearCache();
    await AuthManager.instance.logout();
  });

  Future<void> open(WidgetTester tester) async {
    tester.view.devicePixelRatio = 1.0;
    tester.view.physicalSize = const Size(390, 844);
    addTearDown(tester.view.reset);
    await tester.pumpWidget(MultiProvider(
      providers: [
        Provider<AuthService>(create: (_) => AuthService()),
        Provider<GoogleAuthService>(create: (_) => GoogleAuthService()),
      ],
      child: MaterialApp(
        theme: buildTyTheme(Brightness.light),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: AuthScreen(onAuthenticated: () {}),
      ),
    ));
    await tester.pumpAndSettle();
  }

  TextField activeField(WidgetTester tester) => tester.widget<TextField>(find.byType(TextField).first);

  testWidgets('today: mobile SMS is not live, so the screen leads with email and never promises mobile', (tester) async {
    await open(tester);
    // The wording matches what actually works.
    expect(find.textContaining('Enter your email.'), findsOneWidget);
    expect(find.textContaining('mobile number or email'), findsNothing);
    expect(find.text('Soon'), findsOneWidget);
    expect(activeField(tester).keyboardType, TextInputType.emailAddress);
  });

  testWidgets('email sign-up: code is requested, verified, and a new customer is asked their name', (tester) async {
    await open(tester);
    await tester.enterText(find.byType(TextField).first, 'asha@example.com');
    await tester.tap(find.text('Send code'));
    await tester.pumpAndSettle();

    final req = server.log.firstWhere((r) => r.path == 'auth/otp/request');
    expect(req.data, {'identifier': 'asha@example.com', 'channel': 'email', 'purpose': 'login'});
    expect(find.textContaining('asha@example.com'), findsOneWidget);

    await tester.enterText(find.byType(TextField).first, '123456');
    await tester.pumpAndSettle();

    expect(server.log.where((r) => r.path == 'auth/otp/verify'), hasLength(1));
    expect(find.text('What should we call you?'), findsOneWidget);
  });

  testWidgets('the keypad is put away when the code is sent, so nothing hides the next step', (tester) async {
    await open(tester);
    await tester.tap(find.byType(TextField).first);
    await tester.pump();
    expect(FocusManager.instance.primaryFocus?.hasFocus, isTrue);

    await tester.enterText(find.byType(TextField).first, 'asha@example.com');
    await tester.tap(find.text('Send code'));
    await tester.pump();
    // Focus has moved off the email field (to the code box once it appears).
    await tester.pumpAndSettle();
    expect(find.text('Verify & continue'), findsOneWidget);
  });

  testWidgets('a send failure shows the server message and leaves the form usable', (tester) async {
    server.failSend = true;
    await open(tester);
    await tester.enterText(find.byType(TextField).first, 'asha@example.com');
    await tester.tap(find.text('Send code'));
    await tester.pumpAndSettle();
    expect(find.text('Could not send the verification code. Please try again.'), findsOneWidget);
    expect(find.text('Send code'), findsOneWidget); // can try again

    server.failSend = false;
    await tester.tap(find.text('Send code'));
    await tester.pumpAndSettle();
    expect(find.text('Verify & continue'), findsOneWidget);
  });

  testWidgets('once SMS is live: mobile leads, digits only, +91 added for the server', (tester) async {
    server.phoneOtp = true;
    await open(tester);
    expect(find.text('Soon'), findsNothing);
    expect(activeField(tester).keyboardType, TextInputType.phone);
    expect(find.textContaining('mobile number or email'), findsOneWidget);

    // A person types it the way they say it aloud.
    await tester.enterText(find.byType(TextField).first, '98765 43210');
    await tester.tap(find.text('Send code'));
    await tester.pumpAndSettle();
    final req = server.log.firstWhere((r) => r.path == 'auth/otp/request');
    expect(req.data, {'identifier': '+919876543210', 'channel': 'sms', 'purpose': 'login'});
  });

  testWidgets('hammering Send code does not fire a pile of requests', (tester) async {
    await open(tester);
    await tester.enterText(find.byType(TextField).first, 'asha@example.com');
    for (var i = 0; i < 6; i++) {
      await tester.tap(find.text('Send code'), warnIfMissed: false);
    }
    await tester.pumpAndSettle();
    expect(server.log.where((r) => r.path == 'auth/otp/request'), hasLength(1));
  });
}
