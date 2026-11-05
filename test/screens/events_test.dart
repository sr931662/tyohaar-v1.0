import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tyohaar/data/api_client.dart';
import 'package:tyohaar/data/services/event_service.dart';
import 'package:tyohaar/l10n/generated/app_localizations.dart';
import 'package:tyohaar/screens/events/create_event_wizard.dart';
import 'package:tyohaar/screens/events/event_dashboard_screen.dart';
import 'package:tyohaar/screens/events/invitation_entry_screen.dart';
import 'package:tyohaar/screens/events/invitation_setup_screen.dart';
import 'package:tyohaar/screens/events/my_events_screen.dart';
import 'package:tyohaar/theme/theme.dart';
import 'package:tyohaar/widgets/invitation_hero.dart';

/// Answers from a table instead of the network, keeping every request so tests
/// can assert what was really sent.
class FakeAdapter implements HttpClientAdapter {
  final List<RequestOptions> requests = [];
  final Object? Function(RequestOptions) handler;
  FakeAdapter(this.handler);

  @override
  Future<ResponseBody> fetch(RequestOptions o, Stream<Uint8List>? s, Future<void>? c) async {
    requests.add(o);
    final out = handler(o);
    if (out is DioException) throw out;
    final (status, body) = out is (int, Object) ? out : (200, out!);
    return ResponseBody.fromString(jsonEncode(body), status, headers: {
      Headers.contentTypeHeader: [Headers.jsonContentType],
    });
  }

  @override
  void close({bool force = false}) {}
}

Map<String, dynamic> eventJson({
  String id = 'e1',
  String title = 'Sharma Wedding',
  String source = 'tyohaar_booking',
  String segment = 'upcoming',
  int? days = 39,
  String invitation = 'published',
  bool configured = true,
  int invited = 184,
  int confirmed = 96,
  int pending = 38,
  int functions = 4,
  bool vendorReports = true,
}) =>
    {
      'id': id,
      'title': title,
      'event_type': source == 'standalone' ? 'wedding' : null,
      'event_type_label': 'Wedding',
      'celebration_date': '2026-12-14',
      'venue_name': 'Taj Mahal Hotel',
      'venue_address': 'Lucknow, Uttar Pradesh',
      'status': 'confirmed',
      'segment': segment,
      'days_remaining': days,
      'event_source': source,
      'booking_id': source == 'tyohaar_booking' ? 'b1' : null,
      'booking_status': source == 'tyohaar_booking' ? 'confirmed' : null,
      'function_count': functions,
      'invitation_status': invitation,
      'invitations_configured': configured,
      'counts': {'invited': invited, 'confirmed': confirmed, 'maybe': 0, 'declined': invited - confirmed - pending, 'pending': pending},
      'settings': {
        'invitation_type': 'web',
        'design': {'template': 'classic', 'font': 'serif', 'primary_color': '#5B1226', 'accent_color': '#B8892F', 'background_color': '#FBF6EC'},
        'rsvp': {'allow_maybe': true, 'allow_edit': true, 'ask_attendee_count': true, 'ask_food': false},
        'display': <String, dynamic>{},
        'reminders': <String, dynamic>{},
        'general_link': {'enabled': false, 'plus_ones_allowed': 0},
      },
      'functions': [
        if (functions > 0)
          {'id': 'f1', 'celebration_id': id, 'name': 'Haldi', 'function_date': '2026-12-14', 'display_order': 0, 'is_cancelled': false},
      ],
      'groups': <Object>[],
      'entitlements': {'qr_check_in': true, 'food_preferences': true, 'vendor_reports': vendorReports, 'custom_templates': true, 'advanced_rsvp': true},
      'booking': source == 'tyohaar_booking'
          ? {'booking_id': 'b1', 'status': 'confirmed', 'package_name': 'Grand Wedding'}
          : null,
      'locked_fields': source == 'tyohaar_booking' ? ['celebration_date', 'venue_name', 'venue_address'] : <String>[],
    };

Map<String, dynamic> analyticsJson() => {
      'summary': {'expected_people': 210, 'arrived_guests': 0},
      'invitations_generated': 184,
      'shared': 150,
      'link_accessed': 130,
      'qualified_visits': 120,
      'rsvp_started': 110,
      'responded': 146,
      'pending': 38,
      'confirmed': 96,
      'declined': 50,
      'maybe': 0,
      'response_rate': 0.7935,
      'confirmation_rate': 0.5217,
      'general_link_visits': 0,
      'functions': [
        {'function_id': 'f1', 'name': 'Haldi', 'function_date': '2026-12-14', 'invited': 72, 'confirmed': 48, 'pending': 20, 'declined': 4, 'confirmed_people': 48},
        {'function_id': 'f2', 'name': 'Wedding', 'function_date': '2026-12-16', 'invited': 184, 'confirmed': 96, 'pending': 38, 'declined': 50, 'confirmed_people': 120},
      ],
    };

Widget app(Widget home, {Brightness brightness = Brightness.light, double width = 390, double height = 844}) => MediaQuery(
      data: MediaQueryData(size: Size(width, height), devicePixelRatio: 1),
      child: MaterialApp(
        theme: buildTyTheme(brightness),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: home,
      ),
    );

Widget scaffolded(Widget child, {Brightness brightness = Brightness.light}) =>
    app(Scaffold(body: child), brightness: brightness);

void useAdapter(WidgetTester tester, FakeAdapter adapter) {
  final original = ApiClient().dio.httpClientAdapter;
  ApiClient().dio.httpClientAdapter = adapter;
  addTearDown(() => ApiClient().dio.httpClientAdapter = original);
}

void phone(WidgetTester tester, {double width = 390, double height = 844}) {
  tester.view.physicalSize = Size(width, height);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
}

Future<void> settle(WidgetTester tester) async {
  for (var i = 0; i < 12; i++) {
    await tester.pump(const Duration(milliseconds: 50));
  }
}

Map<String, dynamic> lists({List<Map<String, dynamic>> upcoming = const [], List<Map<String, dynamic>> ongoing = const [], List<Map<String, dynamic>> completed = const []}) =>
    {'data': {'upcoming': upcoming, 'ongoing': ongoing, 'completed': completed}};

void main() {
  group('My Events', () {
    testWidgets('shows real counts, status and source for each segment', (tester) async {
      phone(tester);
      useAdapter(tester, FakeAdapter((o) => lists(
            upcoming: [eventJson()],
            completed: [eventJson(id: 'e2', title: "Dad's 60th", source: 'standalone', segment: 'completed', days: null, invited: 12, confirmed: 10, pending: 0, functions: 0)],
          )));
      await tester.pumpWidget(scaffolded(MyEventsScreen(service: EventService())));
      await settle(tester);

      expect(find.text('My Events'), findsOneWidget);
      expect(find.text('Your celebrations, all in one place.'), findsOneWidget);
      expect(find.text('Sharma Wedding'), findsOneWidget);
      expect(find.text('Upcoming · 39 days remaining'), findsOneWidget);
      expect(find.text('184 invited · 96 confirmed · 38 pending'), findsOneWidget);
      expect(find.text('Tyohaar Booking'), findsOneWidget);
      expect(find.text('Manage Event'), findsOneWidget);
      expect(find.text("Dad's 60th"), findsNothing); // a different tab

      await tester.tap(find.text('Completed (1)'));
      await tester.pump();
      expect(find.text("Dad's 60th"), findsOneWidget);
      expect(find.text('Independent Event'), findsOneWidget);
      expect(find.text('Sharma Wedding'), findsNothing);
    });

    testWidgets('empty account is invited to create an event, with no fake numbers', (tester) async {
      phone(tester);
      useAdapter(tester, FakeAdapter((o) => lists()));
      await tester.pumpWidget(scaffolded(MyEventsScreen(service: EventService())));
      await settle(tester);
      expect(find.text('Nothing on the calendar yet'), findsOneWidget);
      expect(find.text('Create an event'), findsOneWidget);
      expect(find.textContaining('invited'), findsNothing);
    });

    testWidgets('a failed load offers a retry instead of an empty page', (tester) async {
      phone(tester);
      useAdapter(tester, FakeAdapter((o) => (500, {'error': {'message': 'boom'}})));
      await tester.pumpWidget(scaffolded(MyEventsScreen(service: EventService())));
      await settle(tester);
      expect(find.text('Nothing on the calendar yet'), findsNothing);
      expect(find.text('Sharma Wedding'), findsNothing);
      expect(find.byType(TextButton), findsWidgets);
    });

    testWidgets('fits a small phone with long names in dark mode', (tester) async {
      phone(tester, width: 320, height: 568);
      useAdapter(tester, FakeAdapter((o) => lists(upcoming: [
            eventJson(title: 'A very long celebration name that goes on and on for the whole family ' * 2),
          ])));
      await tester.pumpWidget(scaffolded(MyEventsScreen(service: EventService()), brightness: Brightness.dark));
      await settle(tester);
      expect(tester.takeException(), isNull);
    });
  });

  group('Invitation entry', () {
    testWidgets('booked customer sees their events and can still start their own', (tester) async {
      phone(tester, height: 1100);
      useAdapter(tester, FakeAdapter((o) => lists(upcoming: [
            eventJson(),
            eventJson(id: 'e2', title: "Aarav's Birthday", source: 'standalone', configured: false, invited: 0, confirmed: 0, pending: 0),
          ])));
      await tester.pumpWidget(app(InvitationEntryScreen(service: EventService())));
      await settle(tester);

      expect(find.text('How would you like to manage your invitations?'), findsOneWidget);
      expect(find.text('Your Tyohaar Events'), findsOneWidget);
      expect(find.text('Sharma Wedding'), findsOneWidget);
      expect(find.text('Manage Invitations'), findsOneWidget);
      expect(find.text('Hosting Your Own Event?'), findsOneWidget);
      expect(find.text("Aarav's Birthday"), findsOneWidget);
      expect(find.text('Set up invitations for this event.'), findsOneWidget);
      expect(find.text('Create My Event'), findsOneWidget);
      expect(find.text('No Tyohaar bookings found.'), findsNothing);
    });

    testWidgets('no bookings: a friendly note, and creating an event stays open', (tester) async {
      phone(tester, height: 1000);
      useAdapter(tester, FakeAdapter((o) => lists()));
      await tester.pumpWidget(app(InvitationEntryScreen(service: EventService())));
      await settle(tester);
      expect(find.text('No Tyohaar bookings found.'), findsOneWidget);
      expect(find.text('Explore event packages'), findsOneWidget);
      expect(find.text('Create My Event'), findsOneWidget);
    });

    testWidgets('an error in the booked section never blocks the independent path', (tester) async {
      phone(tester, height: 1000);
      useAdapter(tester, FakeAdapter((o) => (500, {'error': {'message': 'x'}})));
      await tester.pumpWidget(app(InvitationEntryScreen(service: EventService())));
      await settle(tester);
      expect(find.text('Create My Event'), findsOneWidget);
    });
  });

  group('Create event wizard', () {
    testWidgets('refuses to continue without name, category and date, and never asks for a booking', (tester) async {
      phone(tester, height: 2400);
      final adapter = FakeAdapter((o) => {'data': eventJson(source: 'standalone')});
      useAdapter(tester, adapter);
      await tester.pumpWidget(app(CreateEventWizard(service: EventService())));
      await tester.pump();
      expect(find.textContaining('ooking'), findsNothing);

      await tester.tap(find.text('Continue'));
      await tester.pump();
      expect(find.text('Choose what kind of event this is.'), findsOneWidget);
      expect(adapter.requests, isEmpty);

      await tester.tap(find.text('Custom Event'));
      await tester.pump();
      expect(find.text('What kind of event?'), findsOneWidget); // custom type asks for its name
    });
  });

  group('Setup', () {
    testWidgets('booked event arrives filled in, and the note says the booking is safe', (tester) async {
      phone(tester, height: 1200);
      useAdapter(tester, FakeAdapter((o) => {'data': eventJson()}));
      await tester.pumpWidget(app(InvitationSetupScreen(eventId: 'e1', service: EventService())));
      await settle(tester);
      final title = tester.widget<EditableText>(find.byType(EditableText).first);
      expect(title.controller.text, 'Sharma Wedding');
      expect(find.textContaining('From your booking'), findsOneWidget);
      expect(find.textContaining('not your booking'), findsOneWidget);
    });

    testWidgets('sends display changes as overrides, never as event edits', (tester) async {
      phone(tester, height: 1200);
      final adapter = FakeAdapter((o) => {'data': eventJson()});
      useAdapter(tester, adapter);
      await tester.pumpWidget(app(InvitationSetupScreen(eventId: 'e1', service: EventService())));
      await settle(tester);
      await tester.enterText(find.byType(TextFormField).first, 'Ananya weds Rohan');
      await tester.tap(find.text('Next'));
      await settle(tester);

      final put = adapter.requests.singleWhere((r) => r.method == 'PUT');
      expect(put.path, 'events/e1/invitation');
      final display = (put.data as Map)['display'] as Map;
      expect(display['title'], 'Ananya weds Rohan');
      expect(display['venue_name'], isNull); // unchanged, so not overridden
      expect(adapter.requests.where((r) => r.method == 'PATCH'), isEmpty);
    });
  });

  group('Dashboard', () {
    FakeAdapter dashboardAdapter({bool qr = true, String source = 'tyohaar_booking'}) => FakeAdapter((o) {
          if (o.path.endsWith('/analytics')) return {'data': analyticsJson()};
          if (o.path.startsWith('events/')) {
            final e = eventJson(source: source);
            (e['entitlements'] as Map)['qr_check_in'] = qr;
            return {'data': e};
          }
          if (o.path.startsWith('celebrations/e1/invitations')) {
            return o.path.endsWith('summary')
                ? {'data': <String, dynamic>{}}
                : {'data': <Object>[], 'meta': {'total': 0, 'has_next': false}};
          }
          if (o.path.startsWith('celebrations/')) return {'data': {'id': 'e1', 'title': 'Sharma Wedding'}};
          return {'data': <Object>[]};
        });

    testWidgets('numbers come from the server and say what they mean', (tester) async {
      phone(tester, height: 1600);
      useAdapter(tester, dashboardAdapter());
      await tester.pumpWidget(app(EventDashboardScreen(eventId: 'e1', service: EventService())));
      await settle(tester);

      expect(find.text('184'), findsWidgets);
      expect(find.text('96'), findsWidgets);
      expect(find.text('79%'), findsOneWidget);
      expect(find.textContaining('146 of 184 invitations have answered'), findsOneWidget);
      expect(find.text('72 invited · 48 confirmed · 20 pending · 4 declined'), findsOneWidget);
      expect(find.textContaining("doesn't mean the invitation was read"), findsOneWidget);
      for (final tab in ['Overview', 'Guests', 'Invitations', 'RSVPs', 'Food & Preferences', 'Activity']) {
        expect(find.text(tab), findsOneWidget);
      }
    });

    testWidgets('QR check-in only appears when the event has it', (tester) async {
      phone(tester, height: 1600);
      useAdapter(tester, dashboardAdapter(qr: false));
      await tester.pumpWidget(app(EventDashboardScreen(eventId: 'e1', service: EventService())));
      await settle(tester);
      expect(find.text('QR Check-in'), findsNothing);
      expect(find.text('Send Reminder'), findsOneWidget);
    });

    testWidgets("someone else's event shows no access, and nothing about it", (tester) async {
      phone(tester);
      useAdapter(tester, FakeAdapter((o) => (404, {'error': {'message': 'Not found'}})));
      await tester.pumpWidget(app(EventDashboardScreen(eventId: 'e9', service: EventService())));
      await settle(tester);
      expect(find.text("You can't open this event"), findsOneWidget);
    });
  });

  testWidgets('home hero says what it is and its button works, on a small phone', (tester) async {
    phone(tester, width: 320, height: 720);
    var taps = 0;
    await tester.pumpWidget(scaffolded(SingleChildScrollView(child: InvitationHero(onExplore: () => taps++))));
    await tester.pump();
    expect(find.text('INVITATION MANAGEMENT'), findsOneWidget);
    expect(find.text('Every invitation. Every guest. One place.'), findsOneWidget);
    for (final f in ['Create Invitations', 'Share with Guests', 'Track RSVPs', 'Manage Food Preferences', 'Guest Updates']) {
      expect(find.text(f), findsOneWidget);
    }
    await tester.ensureVisible(find.text('Explore Invitations'));
    await tester.tap(find.text('Explore Invitations'));
    expect(taps, 1);
    expect(tester.takeException(), isNull);
    expect(find.textContaining('Your Next Celebration', findRichText: true), findsNothing);
  });

  test('every screen-facing model tolerates a sparse response', () {
    final detail = EventDetail.fromJson({'id': 'x', 'title': 'T'});
    expect(detail.isBooked, isFalse);
    expect(detail.functions, isEmpty);
    expect(EventAnalytics.fromJson(const {}).functions, isEmpty);
    expect(File('lib/screens/events/my_events_screen.dart').existsSync(), isTrue);
  });
}
