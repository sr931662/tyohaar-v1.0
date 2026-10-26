import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tyohaar/data/api_client.dart';
import 'package:tyohaar/data/services/invitation_service.dart';
import 'package:tyohaar/l10n/generated/app_localizations.dart';
import 'package:tyohaar/screens/invitation_management_screen.dart';
import 'package:tyohaar/screens/invitations/gate_scan_screen.dart';
import 'package:tyohaar/screens/invitations/invitation_form_screen.dart';
import 'package:tyohaar/theme/theme.dart';
import 'package:tyohaar/widgets/ty_chip.dart';

/// Answers requests from a handler table instead of the network, and keeps
/// every request so tests can assert what was actually sent.
class FakeAdapter implements HttpClientAdapter {
  final List<RequestOptions> requests = [];
  final Object? Function(RequestOptions) handler;
  FakeAdapter(this.handler);

  @override
  Future<ResponseBody> fetch(RequestOptions options, Stream<Uint8List>? requestStream, Future<void>? cancelFuture) async {
    requests.add(options);
    final out = handler(options);
    if (out is DioException) throw out;
    final (status, body) = out is (int, Object) ? out : (200, out!);
    return ResponseBody.fromString(jsonEncode(body), status, headers: {
      Headers.contentTypeHeader: [Headers.jsonContentType],
    });
  }

  @override
  void close({bool force = false}) {}
}

DioException offline(RequestOptions o) =>
    DioException(requestOptions: o, type: DioExceptionType.connectionError, error: 'offline');

Map<String, dynamic> body(RequestOptions o) =>
    o.data is String ? jsonDecode(o.data as String) as Map<String, dynamic> : Map<String, dynamic>.from(o.data as Map);

Map<String, dynamic> guest({String id = 'g1', String name = 'Asha Rao', String state = 'valid', String entry = 'not_arrived'}) => {
      'id': id,
      'celebration_id': 'c1',
      'name': name,
      'phone': '+919876543210',
      'plus_ones_allowed': 2,
      'pass_status': 'active',
      'pass_state': state,
      'rsvp_status': 'attending',
      'entry_status': entry,
      'share_count': 0,
      'created_at': '2026-10-18T10:00:00Z',
      'invite_url': 'https://api.test/api/v1/public/invite/page#tok',
      'entry_code': 'K7QM-3XPD',
      'qr_payload': 'TYH1:K7QM3XPD',
    };

Map<String, dynamic> gateGuest({String entry = 'not_arrived'}) => {
      'id': 'g1',
      'name': 'Asha Rao',
      'phone_masked': '••••3210',
      'plus_ones_allowed': 2,
      'rsvp_status': 'attending',
      'rsvp_party_size': 2,
      'entry_status': entry,
    };

Widget app(Widget home) => MaterialApp(
      theme: buildTyTheme(Brightness.light),
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: home,
    );

late FakeAdapter adapter;

/// Scrolls the main list until [text] is built and visible, then taps it.
Future<void> tapText(WidgetTester tester, String text) async {
  final target = find.text(text);
  await tester.scrollUntilVisible(target, 200, scrollable: find.byType(Scrollable).first);
  await tester.ensureVisible(target);
  await tester.pumpAndSettle();
  await tester.tap(target);
  await tester.pumpAndSettle();
}

/// A phone-shaped surface: lists lay out as they would on a device.
void phone(WidgetTester tester, {double width = 390, double height = 1400}) {
  tester.view.physicalSize = Size(width, height);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
}

void useFake(Object? Function(RequestOptions) handler) {
  adapter = FakeAdapter(handler);
  ApiClient().dio.httpClientAdapter = adapter;
}

void main() {
  group('InvitationService', () {
    test('parses a page and surfaces server business messages', () async {
      useFake((o) {
        if (o.method == 'POST') {
          return (409, {'error': {'code': 'CONFLICT', 'message': 'This guest already has an active invitation for this celebration.'}});
        }
        return {
          'data': [guest()],
          'meta': {'page': 1, 'page_size': 20, 'total': 1, 'total_pages': 1, 'has_next': false, 'has_prev': false},
        };
      });
      final page = await InvitationService().list('c1', status: 'arrived', query: 'asha');
      expect(page.items.single.entryCode, 'K7QM-3XPD');
      expect(adapter.requests.last.queryParameters, containsPair('status', 'arrived'));
      expect(adapter.requests.last.queryParameters, containsPair('q', 'asha'));

      try {
        await InvitationService().create('c1', InvitationDraft(name: 'Asha'), clientRequestId: 'inv-1');
        fail('expected an error');
      } catch (e) {
        expect(invitationErrorMessage(e), contains('already has an active invitation'));
        expect(isNoResponse(e), isFalse);
      }
    });

    test('scan ids are stable per pass reference and new for a new action', () {
      final ref = GatePassRef(code: 'K7QM-3XPD', method: 'manual');
      expect(ref.toJson()['client_scan_id'], ref.clientScanId);
      expect(ref.withNewScanId().clientScanId, isNot(ref.clientScanId));
    });
  });

  testWidgets('create form: a lost response is retried with the same idempotency key', (tester) async {
    var calls = 0;
    useFake((o) {
      calls++;
      return calls == 1 ? offline(o) : {'data': guest()};
    });
    phone(tester);
    await tester.pumpWidget(app(const InvitationFormScreen(celebrationId: 'c1')));
    await tester.enterText(find.byType(TextFormField).first, 'Asha Rao');
    await tapText(tester, 'Create invitation');
    expect(find.textContaining("can't confirm it was saved"), findsOneWidget);

    await tapText(tester, 'Create invitation');
    final keys = adapter.requests.map((r) => body(r)['client_request_id']).toSet();
    expect(adapter.requests, hasLength(2));
    expect(keys, hasLength(1), reason: 'a retry must reuse the key so the server can dedupe');
  });

  testWidgets('create form validates before sending anything', (tester) async {
    useFake((o) => {'data': guest()});
    phone(tester);
    await tester.pumpWidget(app(const InvitationFormScreen(celebrationId: 'c1')));
    await tapText(tester, 'Create invitation');
    expect(find.text('Required', skipOffstage: false), findsOneWidget);
    expect(adapter.requests, isEmpty);
  });

  testWidgets('gate: entry is never shown as recorded without the server, and retries reuse the scan id', (tester) async {
    var checkIns = 0;
    useFake((o) {
      if (o.path.endsWith('gate/session')) {
        return {'data': {'celebration_title': 'Diwali', 'arrived_guests': 0, 'arrived_people': 0, 'still_expected': 1}};
      }
      if (o.path.endsWith('gate/verify')) {
        return {'data': {'result': 'valid', 'message': 'Pass is valid.', 'recorded': false, 'replayed': false, 'warnings': [], 'guest': gateGuest()}};
      }
      if (o.path.endsWith('gate/check-in')) {
        checkIns++;
        if (checkIns == 1) return offline(o);
        return {'data': {'result': 'checked_in', 'message': 'Entry recorded.', 'recorded': true, 'replayed': false, 'warnings': [], 'guest': gateGuest(entry: 'checked_in')}};
      }
      return {'data': []};
    });
    phone(tester);
    await tester.pumpWidget(app(const GateScanScreen(celebrationId: 'c1', celebrationTitle: 'Diwali', startCamera: false)));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField).first, 'k7qm 3xpd');
    await tapText(tester, 'Check');
    expect(find.text('Valid pass'), findsOneWidget);
    expect(find.text('Asha Rao'), findsOneWidget);

    await tapText(tester, 'Check in');
    expect(find.textContaining('NOT recorded'), findsOneWidget);
    expect(find.text('Checked in'), findsNothing);

    await tapText(tester, 'Check in');
    expect(find.text('Checked in'), findsOneWidget);
    final scans = adapter.requests.where((r) => r.path.endsWith('check-in')).map((r) => body(r)['client_scan_id']).toSet();
    expect(scans, hasLength(1));
    final sent = body(adapter.requests.firstWhere((r) => r.path.endsWith('check-in')));
    expect(sent['party_size'], 2, reason: 'defaults to the RSVP party size within the allowance');
  });

  testWidgets('gate: a refused pass is red and offers no check-in', (tester) async {
    useFake((o) {
      if (o.path.endsWith('gate/verify')) {
        return {'data': {'result': 'revoked', 'message': 'This invitation was cancelled by the host.', 'recorded': false, 'replayed': false, 'warnings': [], 'guest': gateGuest()}};
      }
      return {'data': {'celebration_title': 'Diwali', 'arrived_guests': 0, 'arrived_people': 0, 'still_expected': 1}};
    });
    phone(tester);
    await tester.pumpWidget(app(const GateScanScreen(celebrationId: 'c1', celebrationTitle: 'Diwali', startCamera: false)));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField).first, 'K7QM3XPD');
    await tapText(tester, 'Check');
    expect(find.text('Invitation cancelled'), findsOneWidget);
    expect(find.text('Check in'), findsNothing);
  });

  for (final width in [320.0, 412.0]) {
    testWidgets('hub renders server counts, filters by status and fits ${width.toInt()}dp', (tester) async {
      phone(tester, width: width, height: 900);
      useFake((o) {
        if (o.path == 'celebrations') {
          return {'data': [{'id': 'c1', 'title': 'Diwali at home', 'celebration_date': '2030-11-01', 'guest_count': 20}]};
        }
        if (o.path.endsWith('invitations/summary')) {
          return {'data': {'total': 12, 'active': 11, 'rsvp_attending': 7, 'arrived_guests': 3, 'still_expected': 5,
              'arrived_people': 6, 'expected_people': 14, 'inside_now': 3}};
        }
        return {
          'data': [guest(), guest(id: 'g2', name: 'Bimal Sen', state: 'checked_in', entry: 'checked_in')],
          'meta': {'page': 1, 'page_size': 20, 'total': 2, 'total_pages': 1, 'has_next': false, 'has_prev': false},
        };
      });
      await tester.pumpWidget(app(const InvitationManagementScreen()));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      expect(find.text('11'), findsOneWidget); // invited (active) from the server summary
      expect(find.text('7'), findsOneWidget);
      expect(find.text('Asha Rao'), findsOneWidget);
      expect(find.text('Inside'), findsOneWidget);

      final chip = find.byWidgetPredicate((w) => w is TyChip && w.label == 'Arrived', skipOffstage: false);
      expect(chip, findsOneWidget);
      tester.widget<TyChip>(chip).onTap!();
      await tester.pumpAndSettle();
      expect(adapter.requests.last.queryParameters['status'], 'arrived');
    });
  }
}
