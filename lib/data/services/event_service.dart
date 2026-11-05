import 'dart:io';

import 'package:dio/dio.dart';

import '../api_client.dart';
import '../models.dart' show asUrl;

/// The client for `/events`: the customer's celebrations seen through
/// invitation management, for booked and independent events alike. Guests,
/// links and passes stay in InvitationService.
class EventService {
  final ApiClient _api = ApiClient();

  String _base(String id) => 'events/$id';

  Future<EventLists> list() async {
    final res = await _api.dio.get('events');
    return EventLists.fromJson(res.data['data'] as Map<String, dynamic>);
  }

  Future<EventDetail> get(String id) async {
    final res = await _api.dio.get(_base(id));
    return EventDetail.fromJson(res.data['data'] as Map<String, dynamic>);
  }

  /// [clientRequestId] stays the same across retries so a lost response can't
  /// create the event twice.
  Future<EventDetail> create(EventDraft draft, {required String clientRequestId}) async {
    final res = await _api.dio.post('events', data: {...draft.toJson(), 'client_request_id': clientRequestId});
    return EventDetail.fromJson(res.data['data'] as Map<String, dynamic>);
  }

  Future<EventDetail> update(String id, Map<String, dynamic> changes) async {
    final res = await _api.dio.patch(_base(id), data: changes);
    return EventDetail.fromJson(res.data['data'] as Map<String, dynamic>);
  }

  Future<EventDetail> saveSettings(String id, Map<String, dynamic> settings) async {
    final res = await _api.dio.put('${_base(id)}/invitation', data: settings);
    return EventDetail.fromJson(res.data['data'] as Map<String, dynamic>);
  }

  Future<EventDetail> publish(String id) async {
    final res = await _api.dio.post('${_base(id)}/invitation/publish');
    return EventDetail.fromJson(res.data['data'] as Map<String, dynamic>);
  }

  Future<EventDetail> unpublish(String id) async {
    final res = await _api.dio.post('${_base(id)}/invitation/unpublish');
    return EventDetail.fromJson(res.data['data'] as Map<String, dynamic>);
  }

  Future<EventDetail> setGeneralLink(String id, {required bool enabled, int? plusOnes, bool rotate = false}) async {
    final res = await _api.dio.put('${_base(id)}/invitation/general-link', data: {
      'enabled': enabled,
      if (plusOnes != null) 'plus_ones_allowed': plusOnes,
      'rotate': rotate,
    });
    return EventDetail.fromJson(res.data['data'] as Map<String, dynamic>);
  }

  Future<String> previewLink(String id) async {
    final res = await _api.dio.post('${_base(id)}/invitation/preview-link');
    return res.data['data']['url'] as String;
  }

  // ── Functions ──────────────────────────────────────────────────────────────

  Future<EventFunction> addFunction(String id, FunctionDraft draft) async {
    final res = await _api.dio.post('${_base(id)}/functions', data: draft.toJson());
    return EventFunction.fromJson(res.data['data'] as Map<String, dynamic>);
  }

  Future<EventFunction> updateFunction(String id, String functionId, Map<String, dynamic> changes) async {
    final res = await _api.dio.patch('${_base(id)}/functions/$functionId', data: changes);
    return EventFunction.fromJson(res.data['data'] as Map<String, dynamic>);
  }

  Future<void> deleteFunction(String id, String functionId) =>
      _api.dio.delete('${_base(id)}/functions/$functionId');

  Future<void> reorderFunctions(String id, List<String> functionIds) =>
      _api.dio.put('${_base(id)}/functions/reorder', data: {'function_ids': functionIds});

  Future<void> setGuestFunctions(String id, {required List<String> guestIds, required List<String> functionIds}) =>
      _api.dio.put('${_base(id)}/functions/guests', data: {'guest_ids': guestIds, 'function_ids': functionIds});

  // ── Households, import ─────────────────────────────────────────────────────

  Future<List<GuestHousehold>> createGroup(String id, Map<String, dynamic> body) async {
    final res = await _api.dio.post('${_base(id)}/groups', data: body);
    return _households(res.data['data']);
  }

  Future<List<GuestHousehold>> updateGroup(String id, String groupId, Map<String, dynamic> body) async {
    final res = await _api.dio.patch('${_base(id)}/groups/$groupId', data: body);
    return _households(res.data['data']);
  }

  Future<void> deleteGroup(String id, String groupId) => _api.dio.delete('${_base(id)}/groups/$groupId');

  List<GuestHousehold> _households(dynamic data) =>
      ((data ?? []) as List).map((e) => GuestHousehold.fromJson(e as Map<String, dynamic>)).toList();

  Future<ImportOutcome> importGuests(String id, String filePath, String fileName) async {
    final form = FormData.fromMap({'file': await MultipartFile.fromFile(filePath, filename: fileName)});
    final res = await _api.dio.post('${_base(id)}/guests/import', data: form);
    return ImportOutcome.fromJson(res.data['data'] as Map<String, dynamic>);
  }

  // ── Insight ────────────────────────────────────────────────────────────────

  Future<EventAnalytics> analytics(String id) async {
    final res = await _api.dio.get('${_base(id)}/analytics');
    return EventAnalytics.fromJson(res.data['data'] as Map<String, dynamic>);
  }

  Future<RsvpPage> rsvps(String id, {String? functionId, String? status, int page = 1, int pageSize = 50}) async {
    final res = await _api.dio.get('${_base(id)}/rsvps', queryParameters: {
      if (functionId != null) 'function_id': functionId,
      if (status != null) 'status': status,
      'page': page,
      'page_size': pageSize,
    });
    final meta = (res.data['meta'] ?? {}) as Map<String, dynamic>;
    return RsvpPage(
      items: ((res.data['data'] ?? []) as List).map((e) => RsvpRow.fromJson(e as Map<String, dynamic>)).toList(),
      total: meta['total'] as int? ?? 0,
      hasNext: meta['has_next'] as bool? ?? false,
    );
  }

  Future<FoodReport> food(String id) async {
    final res = await _api.dio.get('${_base(id)}/food');
    return FoodReport.fromJson(res.data['data'] as Map<String, dynamic>);
  }

  /// The CSV saved to [directory], ready to hand to the share sheet.
  Future<File> downloadFoodReport(String id, String directory) async {
    final path = '$directory/food-report-$id.csv';
    await _api.dio.download('${_base(id)}/food/report.csv', path);
    return File(path);
  }

  Future<ActivityPage> activity(String id, {int page = 1, int pageSize = 50}) async {
    final res = await _api.dio.get('${_base(id)}/activity', queryParameters: {'page': page, 'page_size': pageSize});
    final meta = (res.data['meta'] ?? {}) as Map<String, dynamic>;
    return ActivityPage(
      items: ((res.data['data'] ?? []) as List).map((e) => ActivityEntry.fromJson(e as Map<String, dynamic>)).toList(),
      hasNext: meta['has_next'] as bool? ?? false,
    );
  }

  Future<ReminderList> reminders(String id) async {
    final res = await _api.dio.get('${_base(id)}/reminders');
    return ReminderList.fromJson(res.data['data'] as Map<String, dynamic>);
  }

  /// Call only once the device confirmed it sent; recorded as sent, never delivered.
  Future<void> recordReminder(String id, List<String> guestIds, String channel) =>
      _api.dio.post('${_base(id)}/reminders/record', data: {'guest_ids': guestIds, 'channel': channel});

  Future<void> approveOperationsSummary(String id, {int? finalGuestCount, String? note}) =>
      _api.dio.post('${_base(id)}/operations-summary', data: {
        if (finalGuestCount != null) 'final_guest_count': finalGuestCount,
        if (note != null && note.trim().isNotEmpty) 'note': note.trim(),
      });

  /// For a vendor on this booking: aggregates the host approved. Null until then.
  Future<VendorGuestSummary?> vendorGuestSummary(String bookingId) async {
    final res = await _api.dio.get('bookings/vendor/$bookingId/guest-summary');
    final data = res.data['data'];
    return data == null ? null : VendorGuestSummary.fromJson(data as Map<String, dynamic>);
  }
}

DateTime? _dt(dynamic v) => v is String ? DateTime.tryParse(v)?.toLocal() : null;
DateTime? _day(dynamic v) => v is String ? DateTime.tryParse(v) : null;
String _ymd(DateTime d) =>
    '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

/// The nine categories an independent event can be. `custom` needs its own name.
const List<String> kEventTypes = [
  'wedding', 'birthday', 'anniversary', 'engagement', 'baby_shower',
  'housewarming', 'religious', 'corporate', 'custom',
];

class EventCounts {
  final int invited, confirmed, maybe, declined, pending;
  const EventCounts({this.invited = 0, this.confirmed = 0, this.maybe = 0, this.declined = 0, this.pending = 0});

  factory EventCounts.fromJson(Map<String, dynamic>? j) => EventCounts(
        invited: j?['invited'] as int? ?? 0,
        confirmed: j?['confirmed'] as int? ?? 0,
        maybe: j?['maybe'] as int? ?? 0,
        declined: j?['declined'] as int? ?? 0,
        pending: j?['pending'] as int? ?? 0,
      );
}

class EventSummaryCard {
  final String id;
  final String title;
  final String? eventType;
  final String eventTypeLabel;
  final String? coverImageUrl;
  final DateTime? date;
  final DateTime? endDate;
  final String? startTime;
  final String? venueName;
  final String? venueAddress;
  final String status;
  final String segment; // upcoming | ongoing | completed
  final int? daysRemaining;
  final String source; // tyohaar_booking | standalone
  final String? bookingId;
  final String? bookingStatus;
  final int functionCount;
  final String invitationStatus; // draft | published
  final bool invitationsConfigured;
  final EventCounts counts;

  EventSummaryCard({
    required this.id,
    required this.title,
    this.eventType,
    required this.eventTypeLabel,
    this.coverImageUrl,
    this.date,
    this.endDate,
    this.startTime,
    this.venueName,
    this.venueAddress,
    required this.status,
    required this.segment,
    this.daysRemaining,
    required this.source,
    this.bookingId,
    this.bookingStatus,
    this.functionCount = 0,
    required this.invitationStatus,
    this.invitationsConfigured = false,
    this.counts = const EventCounts(),
  });

  bool get isBooked => source == 'tyohaar_booking';
  bool get isDraft => invitationStatus == 'draft';
  String get location => [venueName, venueAddress].where((s) => s != null && s.trim().isNotEmpty).join(', ');

  factory EventSummaryCard.fromJson(Map<String, dynamic> j) => EventSummaryCard(
        id: j['id'] as String,
        title: j['title'] as String? ?? '',
        eventType: j['event_type'] as String?,
        eventTypeLabel: j['event_type_label'] as String? ?? '',
        coverImageUrl: asUrl(j['cover_image_url']),
        date: _day(j['celebration_date']),
        endDate: _day(j['end_date']),
        startTime: j['start_time'] as String?,
        venueName: j['venue_name'] as String?,
        venueAddress: j['venue_address'] as String?,
        status: j['status'] as String? ?? 'planning',
        segment: j['segment'] as String? ?? 'upcoming',
        daysRemaining: j['days_remaining'] as int?,
        source: j['event_source'] as String? ?? 'standalone',
        bookingId: j['booking_id'] as String?,
        bookingStatus: j['booking_status'] as String?,
        functionCount: j['function_count'] as int? ?? 0,
        invitationStatus: j['invitation_status'] as String? ?? 'published',
        invitationsConfigured: j['invitations_configured'] as bool? ?? false,
        counts: EventCounts.fromJson(j['counts'] as Map<String, dynamic>?),
      );
}

class EventLists {
  final List<EventSummaryCard> upcoming, ongoing, completed;
  EventLists({required this.upcoming, required this.ongoing, required this.completed});

  List<EventSummaryCard> get all => [...ongoing, ...upcoming, ...completed];

  factory EventLists.fromJson(Map<String, dynamic> j) {
    List<EventSummaryCard> read(String k) =>
        ((j[k] ?? []) as List).map((e) => EventSummaryCard.fromJson(e as Map<String, dynamic>)).toList();
    return EventLists(upcoming: read('upcoming'), ongoing: read('ongoing'), completed: read('completed'));
  }
}

class EventFunction {
  final String id;
  final String name;
  final DateTime? date;
  final String? startTime;
  final String? endTime;
  final String? venueName;
  final String? venueAddress;
  final String? description;
  final String? dressCode;
  final bool isCancelled;

  EventFunction({
    required this.id,
    required this.name,
    this.date,
    this.startTime,
    this.endTime,
    this.venueName,
    this.venueAddress,
    this.description,
    this.dressCode,
    this.isCancelled = false,
  });

  factory EventFunction.fromJson(Map<String, dynamic> j) => EventFunction(
        id: j['id'] as String,
        name: j['name'] as String? ?? '',
        date: _day(j['function_date']),
        startTime: j['start_time'] as String?,
        endTime: j['end_time'] as String?,
        venueName: j['venue_name'] as String?,
        venueAddress: j['venue_address'] as String?,
        description: j['description'] as String?,
        dressCode: j['dress_code'] as String?,
        isCancelled: j['is_cancelled'] as bool? ?? false,
      );
}

class FunctionDraft {
  final String name;
  final DateTime date;
  final String? startTime; // "HH:MM"
  final String? venueName;
  final String? venueAddress;
  final String? description;
  final String? dressCode;
  final bool inviteAllGuests;

  FunctionDraft({
    required this.name,
    required this.date,
    this.startTime,
    this.venueName,
    this.venueAddress,
    this.description,
    this.dressCode,
    this.inviteAllGuests = true,
  });

  Map<String, dynamic> toJson() => {
        'name': name.trim(),
        'function_date': _ymd(date),
        'start_time': startTime,
        'venue_name': venueName,
        'venue_address': venueAddress,
        'description': description,
        'dress_code': dressCode,
        'invite_all_guests': inviteAllGuests,
      };
}

class EventDraft {
  final String title;
  final String eventType;
  final String? customEventType;
  final String? hostName;
  final DateTime date;
  final String? startTime;
  final String? venueName;
  final String? venueAddress;
  final String? description;
  final String? coverImageUrl;
  final String? contactName;
  final String? contactPhone;

  EventDraft({
    required this.title,
    required this.eventType,
    this.customEventType,
    this.hostName,
    required this.date,
    this.startTime,
    this.venueName,
    this.venueAddress,
    this.description,
    this.coverImageUrl,
    this.contactName,
    this.contactPhone,
  });

  Map<String, dynamic> toJson() {
    final map = <String, dynamic>{
      'title': title.trim(),
      'event_type': eventType,
      'custom_event_type': customEventType,
      'host_name': hostName,
      'celebration_date': _ymd(date),
      'start_time': startTime,
      'venue_name': venueName,
      'venue_address': venueAddress,
      'description': description,
      'cover_image_url': coverImageUrl,
      'contact_name': contactName,
      'contact_phone': contactPhone,
    };
    map.removeWhere((_, v) => v == null || (v is String && v.trim().isEmpty));
    return map;
  }
}

class GuestHouseholdMember {
  final String id;
  final String name;
  final int plusOnesAllowed;
  GuestHouseholdMember({required this.id, required this.name, required this.plusOnesAllowed});
}

class GuestHousehold {
  final String id;
  final String name;
  final String? category;
  final int? capacity;
  final String responseMode; // group | individual
  final String? primaryGuestId;
  final List<GuestHouseholdMember> members;
  final String? inviteUrl;

  GuestHousehold({
    required this.id,
    required this.name,
    this.category,
    this.capacity,
    required this.responseMode,
    this.primaryGuestId,
    this.members = const [],
    this.inviteUrl,
  });

  factory GuestHousehold.fromJson(Map<String, dynamic> j) => GuestHousehold(
        id: j['id'] as String,
        name: j['name'] as String? ?? '',
        category: j['category'] as String?,
        capacity: j['invitation_capacity'] as int?,
        responseMode: j['response_mode'] as String? ?? 'group',
        primaryGuestId: j['primary_guest_id'] as String?,
        inviteUrl: j['invite_url'] as String?,
        members: ((j['members'] ?? []) as List).map((e) {
          final m = e as Map<String, dynamic>;
          return GuestHouseholdMember(
            id: m['id'] as String,
            name: m['name'] as String? ?? '',
            plusOnesAllowed: m['plus_ones_allowed'] as int? ?? 0,
          );
        }).toList(),
      );
}

class EventEntitlements {
  final bool customTemplates, advancedRsvp, foodPreferences, qrCheckIn, automatedReminders, vendorReports, advancedAnalytics;

  const EventEntitlements({
    this.customTemplates = true,
    this.advancedRsvp = true,
    this.foodPreferences = true,
    this.qrCheckIn = true,
    this.automatedReminders = false,
    this.vendorReports = false,
    this.advancedAnalytics = true,
  });

  factory EventEntitlements.fromJson(Map<String, dynamic>? j) => EventEntitlements(
        customTemplates: j?['custom_templates'] as bool? ?? true,
        advancedRsvp: j?['advanced_rsvp'] as bool? ?? true,
        foodPreferences: j?['food_preferences'] as bool? ?? true,
        qrCheckIn: j?['qr_check_in'] as bool? ?? true,
        automatedReminders: j?['automated_reminders'] as bool? ?? false,
        vendorReports: j?['vendor_reports'] as bool? ?? false,
        advancedAnalytics: j?['advanced_analytics'] as bool? ?? true,
      );
}

class EventBookingInfo {
  final String bookingId;
  final String? bookingNumber;
  final String status;
  final String? packageName;
  final String? packageCoverUrl;

  EventBookingInfo({required this.bookingId, this.bookingNumber, required this.status, this.packageName, this.packageCoverUrl});

  factory EventBookingInfo.fromJson(Map<String, dynamic> j) => EventBookingInfo(
        bookingId: j['booking_id'] as String,
        bookingNumber: j['booking_number'] as String?,
        status: j['status'] as String? ?? '',
        packageName: j['package_name'] as String?,
        packageCoverUrl: asUrl(j['package_cover_url']),
      );
}

/// Editable invitation settings. Kept as maps of plain values so the screens
/// send back exactly what they show, and unknown server fields aren't lost.
class EventInvitationSettings {
  Map<String, dynamic> design;
  Map<String, dynamic> rsvp;
  Map<String, dynamic> display;
  Map<String, dynamic> reminders;
  Map<String, dynamic> generalLink;
  String invitationType;

  EventInvitationSettings({
    required this.design,
    required this.rsvp,
    required this.display,
    required this.reminders,
    required this.generalLink,
    required this.invitationType,
  });

  factory EventInvitationSettings.fromJson(Map<String, dynamic>? j) {
    Map<String, dynamic> read(String k) => Map<String, dynamic>.from((j?[k] ?? const {}) as Map);
    return EventInvitationSettings(
      design: read('design'),
      rsvp: read('rsvp'),
      display: read('display'),
      reminders: read('reminders'),
      generalLink: read('general_link'),
      invitationType: j?['invitation_type'] as String? ?? 'web',
    );
  }
}

class EventDetail extends EventSummaryCard {
  final String? description;
  final String? hostName;
  final String? customEventType;
  final String? contactName;
  final String? contactPhone;
  final EventInvitationSettings settings;
  final List<EventFunction> functions;
  final List<GuestHousehold> groups;
  final EventEntitlements entitlements;
  final EventBookingInfo? booking;
  final String? generalLinkUrl;
  final List<String> lockedFields;
  final bool operationsApproved;

  EventDetail._(
    EventSummaryCard c, {
    this.description,
    this.hostName,
    this.customEventType,
    this.contactName,
    this.contactPhone,
    required this.settings,
    this.functions = const [],
    this.groups = const [],
    required this.entitlements,
    this.booking,
    this.generalLinkUrl,
    this.lockedFields = const [],
    this.operationsApproved = false,
  }) : super(
          id: c.id,
          title: c.title,
          eventType: c.eventType,
          eventTypeLabel: c.eventTypeLabel,
          coverImageUrl: c.coverImageUrl,
          date: c.date,
          endDate: c.endDate,
          startTime: c.startTime,
          venueName: c.venueName,
          venueAddress: c.venueAddress,
          status: c.status,
          segment: c.segment,
          daysRemaining: c.daysRemaining,
          source: c.source,
          bookingId: c.bookingId,
          bookingStatus: c.bookingStatus,
          functionCount: c.functionCount,
          invitationStatus: c.invitationStatus,
          invitationsConfigured: c.invitationsConfigured,
          counts: c.counts,
        );

  factory EventDetail.fromJson(Map<String, dynamic> j) => EventDetail._(
        EventSummaryCard.fromJson(j),
        description: j['description'] as String?,
        hostName: j['host_name'] as String?,
        customEventType: j['custom_event_type'] as String?,
        contactName: j['contact_name'] as String?,
        contactPhone: j['contact_phone'] as String?,
        settings: EventInvitationSettings.fromJson(j['settings'] as Map<String, dynamic>?),
        functions: ((j['functions'] ?? []) as List).map((e) => EventFunction.fromJson(e as Map<String, dynamic>)).toList(),
        groups: ((j['groups'] ?? []) as List).map((e) => GuestHousehold.fromJson(e as Map<String, dynamic>)).toList(),
        entitlements: EventEntitlements.fromJson(j['entitlements'] as Map<String, dynamic>?),
        booking: j['booking'] == null ? null : EventBookingInfo.fromJson(j['booking'] as Map<String, dynamic>),
        generalLinkUrl: j['general_link_url'] as String?,
        lockedFields: ((j['locked_fields'] ?? []) as List).cast<String>(),
        operationsApproved: j['operations_summary'] != null,
      );
}

class FunctionNumbers {
  final String? functionId;
  final String name;
  final DateTime? date;
  final bool isCancelled;
  final int invited, confirmed, maybe, declined, pending, confirmedPeople;

  FunctionNumbers({
    this.functionId,
    required this.name,
    this.date,
    this.isCancelled = false,
    this.invited = 0,
    this.confirmed = 0,
    this.maybe = 0,
    this.declined = 0,
    this.pending = 0,
    this.confirmedPeople = 0,
  });

  factory FunctionNumbers.fromJson(Map<String, dynamic> j) => FunctionNumbers(
        functionId: j['function_id'] as String?,
        name: j['name'] as String? ?? '',
        date: _day(j['function_date']),
        isCancelled: j['is_cancelled'] as bool? ?? false,
        invited: j['invited'] as int? ?? 0,
        confirmed: j['confirmed'] as int? ?? 0,
        maybe: j['maybe'] as int? ?? 0,
        declined: j['declined'] as int? ?? 0,
        pending: j['pending'] as int? ?? 0,
        confirmedPeople: j['confirmed_people'] as int? ?? 0,
      );
}

class EventAnalytics {
  final int generated, shared, linkAccessed, qualifiedVisits, rsvpStarted, responded, pending, confirmed, declined, maybe;
  final int expectedPeople, arrivedGuests, generalLinkVisits;
  final double responseRate, confirmationRate;
  final List<FunctionNumbers> functions;

  EventAnalytics({
    required this.generated,
    required this.shared,
    required this.linkAccessed,
    required this.qualifiedVisits,
    required this.rsvpStarted,
    required this.responded,
    required this.pending,
    required this.confirmed,
    required this.declined,
    required this.maybe,
    required this.expectedPeople,
    required this.arrivedGuests,
    required this.generalLinkVisits,
    required this.responseRate,
    required this.confirmationRate,
    required this.functions,
  });

  factory EventAnalytics.fromJson(Map<String, dynamic> j) {
    int n(String k) => j[k] as int? ?? 0;
    final summary = Map<String, dynamic>.from((j['summary'] ?? const {}) as Map);
    return EventAnalytics(
      generated: n('invitations_generated'),
      shared: n('shared'),
      linkAccessed: n('link_accessed'),
      qualifiedVisits: n('qualified_visits'),
      rsvpStarted: n('rsvp_started'),
      responded: n('responded'),
      pending: n('pending'),
      confirmed: n('confirmed'),
      declined: n('declined'),
      maybe: n('maybe'),
      expectedPeople: summary['expected_people'] as int? ?? 0,
      arrivedGuests: summary['arrived_guests'] as int? ?? 0,
      generalLinkVisits: n('general_link_visits'),
      responseRate: (j['response_rate'] as num? ?? 0).toDouble(),
      confirmationRate: (j['confirmation_rate'] as num? ?? 0).toDouble(),
      functions: ((j['functions'] ?? []) as List).map((e) => FunctionNumbers.fromJson(e as Map<String, dynamic>)).toList(),
    );
  }
}

class RsvpRow {
  final String guestId;
  final String guestName;
  final String? groupName;
  final String? functionId;
  final String? functionName;
  final String status;
  final int? attendeeCount;
  final String? dietaryType;
  final String? mealSelection;
  final String? allergies;
  final String? specialRequirements;
  final DateTime? respondedAt;

  RsvpRow({
    required this.guestId,
    required this.guestName,
    this.groupName,
    this.functionId,
    this.functionName,
    required this.status,
    this.attendeeCount,
    this.dietaryType,
    this.mealSelection,
    this.allergies,
    this.specialRequirements,
    this.respondedAt,
  });

  factory RsvpRow.fromJson(Map<String, dynamic> j) => RsvpRow(
        guestId: j['guest_id'] as String,
        guestName: j['guest_name'] as String? ?? '',
        groupName: j['group_name'] as String?,
        functionId: j['function_id'] as String?,
        functionName: j['function_name'] as String?,
        status: j['status'] as String? ?? 'pending',
        attendeeCount: j['attendee_count'] as int?,
        dietaryType: j['dietary_type'] as String?,
        mealSelection: j['meal_selection'] as String?,
        allergies: j['allergies'] as String?,
        specialRequirements: j['special_requirements'] as String?,
        respondedAt: _dt(j['responded_at']),
      );
}

class RsvpPage {
  final List<RsvpRow> items;
  final int total;
  final bool hasNext;
  RsvpPage({required this.items, required this.total, required this.hasNext});
}

class FoodFunction {
  final String name;
  final int people, notSpecified, withAllergies;
  final Map<String, int> dietary, meals;

  FoodFunction({
    required this.name,
    required this.people,
    required this.notSpecified,
    required this.withAllergies,
    required this.dietary,
    required this.meals,
  });

  factory FoodFunction.fromJson(Map<String, dynamic> j) {
    Map<String, int> read(String k) => ((j[k] ?? const {}) as Map).map((a, b) => MapEntry(a.toString(), (b as num).toInt()));
    return FoodFunction(
      name: j['name'] as String? ?? '',
      people: j['people'] as int? ?? 0,
      notSpecified: j['not_specified'] as int? ?? 0,
      withAllergies: j['with_allergies'] as int? ?? 0,
      dietary: read('dietary'),
      meals: read('meals'),
    );
  }
}

class FoodReport {
  final bool enabled;
  final List<FoodFunction> functions;
  FoodReport({required this.enabled, required this.functions});

  factory FoodReport.fromJson(Map<String, dynamic> j) => FoodReport(
        enabled: j['enabled'] as bool? ?? false,
        functions: ((j['functions'] ?? []) as List).map((e) => FoodFunction.fromJson(e as Map<String, dynamic>)).toList(),
      );
}

class VendorGuestSummary {
  final DateTime? approvedAt;
  final int? finalGuestCount;
  final String? note;
  final List<FoodFunction> functions;

  VendorGuestSummary({this.approvedAt, this.finalGuestCount, this.note, required this.functions});

  factory VendorGuestSummary.fromJson(Map<String, dynamic> j) => VendorGuestSummary(
        approvedAt: _dt(j['approved_at']),
        finalGuestCount: j['final_guest_count'] as int?,
        note: j['note'] as String?,
        functions: ((j['functions'] ?? []) as List).map((e) => FoodFunction.fromJson(e as Map<String, dynamic>)).toList(),
      );
}

class ActivityEntry {
  final String id;
  final String guestId;
  final String guestName;
  final String eventType;
  final String? newStatus;
  final String? functionName;
  final String? channel;
  final bool isUpdate;
  final DateTime occurredAt;

  ActivityEntry({
    required this.id,
    required this.guestId,
    required this.guestName,
    required this.eventType,
    this.newStatus,
    this.functionName,
    this.channel,
    this.isUpdate = false,
    required this.occurredAt,
  });

  factory ActivityEntry.fromJson(Map<String, dynamic> j) => ActivityEntry(
        id: j['id'] as String,
        guestId: j['guest_id'] as String,
        guestName: j['guest_name'] as String? ?? '',
        eventType: j['event_type'] as String? ?? '',
        newStatus: j['new_status'] as String?,
        functionName: j['function_name'] as String?,
        channel: j['channel'] as String?,
        isUpdate: j['is_update'] as bool? ?? false,
        occurredAt: _dt(j['occurred_at']) ?? DateTime.now(),
      );
}

class ActivityPage {
  final List<ActivityEntry> items;
  final bool hasNext;
  ActivityPage({required this.items, required this.hasNext});
}

class ReminderCandidate {
  final String guestId;
  final String guestName;
  final String? phone;
  final String? inviteUrl;
  final List<String> reasons;
  final int reminderCount;
  final DateTime? lastRemindedAt;

  ReminderCandidate({
    required this.guestId,
    required this.guestName,
    this.phone,
    this.inviteUrl,
    this.reasons = const [],
    this.reminderCount = 0,
    this.lastRemindedAt,
  });

  factory ReminderCandidate.fromJson(Map<String, dynamic> j) => ReminderCandidate(
        guestId: j['guest_id'] as String,
        guestName: j['guest_name'] as String? ?? '',
        phone: j['phone'] as String?,
        inviteUrl: j['invite_url'] as String?,
        reasons: ((j['reasons'] ?? []) as List).cast<String>(),
        reminderCount: j['reminder_count'] as int? ?? 0,
        lastRemindedAt: _dt(j['last_reminded_at']),
      );
}

class ReminderList {
  final bool automatedAvailable;
  final Map<String, dynamic> rules;
  final List<ReminderCandidate> candidates;

  ReminderList({required this.automatedAvailable, required this.rules, required this.candidates});

  factory ReminderList.fromJson(Map<String, dynamic> j) => ReminderList(
        automatedAvailable: j['automated_available'] as bool? ?? false,
        rules: Map<String, dynamic>.from((j['rules'] ?? const {}) as Map),
        candidates: ((j['candidates'] ?? []) as List).map((e) => ReminderCandidate.fromJson(e as Map<String, dynamic>)).toList(),
      );
}

class ImportOutcome {
  final int created, skipped, groupsCreated;
  final List<ImportRow> rows;
  ImportOutcome({required this.created, required this.skipped, required this.groupsCreated, required this.rows});

  factory ImportOutcome.fromJson(Map<String, dynamic> j) => ImportOutcome(
        created: j['created'] as int? ?? 0,
        skipped: j['skipped'] as int? ?? 0,
        groupsCreated: j['groups_created'] as int? ?? 0,
        rows: ((j['rows'] ?? []) as List).map((e) {
          final m = e as Map<String, dynamic>;
          return ImportRow(
            row: m['row'] as int? ?? 0,
            status: m['status'] as String? ?? 'error',
            name: m['name'] as String?,
            message: m['message'] as String?,
          );
        }).toList(),
      );
}

class ImportRow {
  final int row;
  final String status;
  final String? name;
  final String? message;
  ImportRow({required this.row, required this.status, this.name, this.message});
}
