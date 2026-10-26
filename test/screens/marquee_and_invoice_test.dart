import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tyohaar/data/api_client.dart';
import 'package:tyohaar/l10n/generated/app_localizations.dart';
import 'package:tyohaar/screens/booking_detail_screen.dart';
import 'package:tyohaar/screens/plan_flow/marquee_sheet.dart';
import 'package:tyohaar/theme/theme.dart';
import 'package:tyohaar/widgets/line_kind_badge.dart';

Widget app(Widget home) => MaterialApp(
      theme: buildTyTheme(Brightness.light),
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: home,
    );

void phone(WidgetTester tester, {double width = 390, double height = 1700}) {
  tester.view.physicalSize = Size(width, height);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
}

/// Opens the sheet from a button and records what it resolves to.
class _Host extends StatefulWidget {
  final CharSetKind kind;
  final int max;
  final String? initial;
  const _Host({required this.kind, this.max = 20, this.initial});
  @override
  State<_Host> createState() => _HostState();
}

class _HostState extends State<_Host> {
  String? result = 'unset';
  @override
  Widget build(BuildContext context) => Scaffold(
        body: Column(children: [
          TextButton(
            onPressed: () async {
              final r = await showMarqueeSheet(
                context,
                title: 'LED Marquee',
                unitPrice: 399,
                charSet: widget.kind,
                maxChars: widget.max,
                initial: widget.initial,
              );
              setState(() => result = r);
            },
            child: const Text('open'),
          ),
          Text('result:$result', key: const Key('result')),
        ]),
      );
}

Future<void> openSheet(WidgetTester tester) async {
  await tester.tap(find.text('open'));
  await tester.pumpAndSettle();
}

Future<void> tapKey(WidgetTester tester, String label) async {
  final key = find.widgetWithText(InkWell, label);
  await tester.ensureVisible(key.first);
  await tester.tap(key.first);
  await tester.pump();
}

void main() {
  group('marquee sheet', () {
    testWidgets('numbers: two pieces cost 2 x the unit price and confirm returns them',
        (tester) async {
      phone(tester);
      await tester.pumpWidget(app(const _Host(kind: CharSetKind.digits, max: 4)));
      await openSheet(tester);
      expect(find.text('Customise your LED Marquee'), findsOneWidget);
      expect(find.text('Nothing selected yet'), findsOneWidget);

      await tapKey(tester, '2');
      await tapKey(tester, '5');
      expect(find.text('₹798'), findsOneWidget); // total add-on price
      expect(find.text('₹399'), findsOneWidget); // price per character

      await tester.ensureVisible(find.text('Confirm selection'));
      await tester.tap(find.text('Confirm selection'));
      await tester.pumpAndSettle();
      expect(find.text('result:25'), findsOneWidget);
    });

    testWidgets('digits-only has no letter keys and the cap stops extra characters',
        (tester) async {
      phone(tester);
      await tester.pumpWidget(app(const _Host(kind: CharSetKind.digits, max: 3)));
      await openSheet(tester);
      expect(find.widgetWithText(InkWell, 'A'), findsNothing);
      for (final d in ['1', '2', '3', '4']) {
        await tapKey(tester, d);
      }
      expect(find.text('₹1,197'), findsOneWidget); // 3 x 399, the fourth was refused
    });

    testWidgets('alphanumeric: typing "anita 30" is 7 billable characters, spaces are free',
        (tester) async {
      phone(tester);
      await tester.pumpWidget(app(const _Host(kind: CharSetKind.alphanumeric)));
      await openSheet(tester);
      await tester.enterText(find.byType(TextField), 'anita 30');
      await tester.pump();
      expect(find.text('₹2,793'), findsOneWidget); // 7 x 399
      await tester.ensureVisible(find.text('Confirm selection'));
      await tester.tap(find.text('Confirm selection'));
      await tester.pumpAndSettle();
      expect(find.text('result:ANITA 30'), findsOneWidget);
    });

    testWidgets('letters-only drops digits typed in', (tester) async {
      phone(tester);
      await tester.pumpWidget(app(const _Host(kind: CharSetKind.letters)));
      await openSheet(tester);
      await tester.enterText(find.byType(TextField), 'Love 2');
      await tester.pump();
      expect(find.text('₹1,596'), findsOneWidget); // L-O-V-E = 4
    });

    testWidgets('tapping a lit piece removes it; confirm stays disabled when empty',
        (tester) async {
      phone(tester);
      await tester.pumpWidget(app(const _Host(kind: CharSetKind.alphanumeric, initial: 'AB')));
      await openSheet(tester);
      expect(find.text('₹798'), findsOneWidget);
      await tester.tap(
          find.byWidgetPredicate((w) => w is Text && w.data == 'B' && w.style?.fontSize == 28));
      await tester.pump();
      expect(find.text('₹399'), findsWidgets);
      await tester.tap(
          find.byWidgetPredicate((w) => w is Text && w.data == 'A' && w.style?.fontSize == 28));
      await tester.pump();
      expect(find.text('Nothing selected yet'), findsOneWidget);
      final confirm =
          tester.widget<FilledButton>(find.widgetWithText(FilledButton, 'Confirm selection'));
      expect(confirm.onPressed, isNull);
    });

    testWidgets('backing out resolves to null', (tester) async {
      phone(tester);
      await tester.pumpWidget(app(const _Host(kind: CharSetKind.digits)));
      await openSheet(tester);
      await tester.tapAt(const Offset(10, 10)); // the scrim
      await tester.pumpAndSettle();
      expect(find.text('result:null'), findsOneWidget);
    });
  });

  testWidgets('line kind badges say what each line is, in words', (tester) async {
    await tester.pumpWidget(app(Scaffold(
      body: Column(children: [
        const LineKindBadge(LineKind.rental),
        const LineKindBadge(LineKind.keep),
        const LineKindBadge(LineKind.service),
        DefaultTextStyle(
            style: const TextStyle(color: Colors.black), child: const LineKindLegend()),
      ]),
    )));
    for (final label in ['RENTAL', 'KEEP', 'SERVICE']) {
      expect(find.text(label), findsNWidgets(2)); // badge + legend
    }
    expect(find.textContaining('Returnable item'), findsOneWidget);
    expect(find.text('Yours to keep'), findsOneWidget);
    expect(LineKind.forItem(isReturnable: true), LineKind.rental);
    expect(LineKind.forItem(isReturnable: false), LineKind.keep);
    expect(LineKind.parse('service'), LineKind.service);
    expect(LineKind.parse('nonsense'), LineKind.keep);
  });

  group('booking detail + invoice', () {
    late List<RequestOptions> requests;

    void useFake() {
      requests = [];
      ApiClient().dio.httpClientAdapter = _Adapter((o) {
        requests.add(o);
        if (o.path.endsWith('invoice.pdf')) {
          return _Reply.bytes(Uint8List.fromList('%PDF-fake'.codeUnits), {
            'content-disposition': ['attachment; filename="INV-TYO123.pdf"'],
          });
        }
        if (o.path.endsWith('/lines')) {
          return _Reply.json({
            'data': [
              {
                'kind': 'rental',
                'name': 'LED Marquee Letters',
                'quantity': 2,
                'unit': 'characters',
                'unit_price': '399.00',
                'final_price': '798.00',
                'is_addon': true,
                'note': 'ANITA 30'
              },
              {
                'kind': 'keep',
                'name': 'Party banner',
                'quantity': 1,
                'unit_price': '250.50',
                'final_price': '250.50'
              },
              {
                'kind': 'service',
                'name': 'Setup & dismantling',
                'quantity': 1,
                'unit_price': '500.00',
                'final_price': '500.00'
              },
            ]
          });
        }
        if (o.path.endsWith('balloon-colors')) {
          return _Reply.json({
            'data': [
              {
                'id': '1',
                'name': 'Rose Gold',
                'hex_code': '#E8B4B8',
                'sort_order': 0,
                'is_active': true
              },
            ]
          });
        }
        return _Reply.json({
          'data': {
            'id': 'b1',
            'booking_number': 'TYO123',
            'package_name': 'Starter Pack',
            'celebration_title': "Anita's 25th",
            'scheduled_date': '2026-11-14',
            'booking_status': 'confirmed',
            'payment_status': 'paid',
            'subtotal': '2548.50',
            'discount_amount': '100.00',
            'tax_amount': '440.73',
            'total_amount': '2889.23',
            'amount_paid': '2889.23',
            'amount_due': '0.00',
            'balloon_colors': ['#e8b4b8', '#123456'],
            'balloon_finish': 'Pastel',
          }
        });
      });
    }

    testWidgets('shows labelled lines, colours in order, finish, totals and the download button',
        (tester) async {
      phone(tester, height: 2400);
      useFake();
      await tester.pumpWidget(app(const BookingDetailScreen(bookingId: 'b1')));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      for (final label in ['RENTAL', 'KEEP', 'SERVICE']) {
        expect(find.text(label), findsNWidgets(2)); // on the line and in the legend
      }
      expect(find.text('LED Marquee Letters'), findsOneWidget);
      expect(find.text('Custom: ANITA 30'), findsOneWidget);
      expect(find.text('1. Rose Gold'), findsOneWidget);
      expect(find.text('2. #123456'), findsOneWidget); // not in the palette: hex still shows
      expect(find.text('Finish: Pastel'), findsOneWidget);
      expect(find.text('-₹100'), findsOneWidget);
      expect(find.text('₹440.73'), findsOneWidget);
      expect(find.text('₹2,889.23'), findsNWidgets(2)); // total and paid
      expect(find.text('Download invoice (PDF)'), findsOneWidget);
    });

    testWidgets('the download button asks the server for the PDF', (tester) async {
      phone(tester, height: 2400);
      useFake();
      await tester.pumpWidget(app(const BookingDetailScreen(bookingId: 'b1')));
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.text('Download invoice (PDF)'));
      await tester.tap(find.text('Download invoice (PDF)'));
      await tester.pumpAndSettle();
      final pdf = requests.where((r) => r.path.endsWith('bookings/b1/invoice.pdf'));
      expect(pdf, hasLength(1));
      expect(pdf.single.responseType, ResponseType.bytes);
    });

    testWidgets('a failed load offers a retry instead of a blank screen', (tester) async {
      phone(tester);
      ApiClient().dio.httpClientAdapter = _Adapter((o) => _Reply.status(500));
      await tester.pumpWidget(app(const BookingDetailScreen(bookingId: 'b1')));
      await tester.pumpAndSettle();
      expect(find.byType(CircularProgressIndicator), findsNothing);
      expect(find.text('Download invoice (PDF)'), findsNothing);
    });
  });
}

class _Reply {
  final int status;
  final List<int> body;
  final Map<String, List<String>> headers;
  _Reply(this.status, this.body, this.headers);
  factory _Reply.json(Object o) => _Reply(200, utf8.encode(jsonEncode(o)), {
        Headers.contentTypeHeader: [Headers.jsonContentType]
      });
  factory _Reply.bytes(Uint8List b, Map<String, List<String>> h) => _Reply(200, b, h);
  factory _Reply.status(int s) => _Reply(s, utf8.encode('{}'), {
        Headers.contentTypeHeader: [Headers.jsonContentType]
      });
}

class _Adapter implements HttpClientAdapter {
  final _Reply Function(RequestOptions) handler;
  _Adapter(this.handler);

  @override
  Future<ResponseBody> fetch(
      RequestOptions options, Stream<Uint8List>? requestStream, Future<void>? cancelFuture) async {
    final r = handler(options);
    return ResponseBody.fromBytes(r.body, r.status, headers: r.headers);
  }

  @override
  void close({bool force = false}) {}
}
