import 'dart:math';

import 'package:dio/dio.dart';

import '../api_client.dart';

/// Guest invitations, passes and gate entry — the client for
/// `/celebrations/{id}/invitations`, `/gate` and `/gate-access`.
///
/// Every rule (who may see what, whether a pass admits someone, duplicate
/// prevention) is enforced by the server; this layer only carries requests
/// and keeps retries safe by reusing idempotency keys.
class InvitationService {
  final ApiClient _api = ApiClient();

  String _base(String celebrationId) => 'celebrations/$celebrationId';

  Future<InvitationPage> list(
    String celebrationId, {
    String status = 'all',
    String? query,
    String sort = 'created_at',
    String order = 'desc',
    int page = 1,
    int pageSize = 20,
  }) async {
    final res = await _api.dio.get('${_base(celebrationId)}/invitations', queryParameters: {
      'status': status,
      if (query != null && query.trim().isNotEmpty) 'q': query.trim(),
      'sort': sort,
      'order': order,
      'page': page,
      'page_size': pageSize,
    });
    final items = ((res.data['data'] ?? []) as List)
        .map((e) => GuestInvitation.fromJson(e as Map<String, dynamic>))
        .toList();
    final meta = (res.data['meta'] ?? {}) as Map<String, dynamic>;
    return InvitationPage(
      items: items,
      total: meta['total'] as int? ?? items.length,
      hasNext: meta['has_next'] as bool? ?? false,
    );
  }

  Future<InvitationSummary> summary(String celebrationId) async {
    final res = await _api.dio.get('${_base(celebrationId)}/invitations/summary');
    return InvitationSummary.fromJson(res.data['data'] as Map<String, dynamic>);
  }

  Future<DeliveryCapabilities> capabilities() async {
    final res = await _api.dio.get('invitations/capabilities');
    return DeliveryCapabilities.fromJson(res.data['data'] as Map<String, dynamic>);
  }

  /// [clientRequestId] must stay the same across retries of one submission
  /// so a lost response can't turn into a second invitation.
  Future<GuestInvitation> create(String celebrationId, InvitationDraft draft, {required String clientRequestId}) async {
    final res = await _api.dio.post('${_base(celebrationId)}/invitations', data: {
      ...draft.toJson(),
      'client_request_id': clientRequestId,
    });
    return GuestInvitation.fromJson(res.data['data'] as Map<String, dynamic>);
  }

  Future<BulkInviteResult> bulkCreate(String celebrationId, List<InvitationDraft> drafts, {required String clientRequestId}) async {
    final res = await _api.dio.post('${_base(celebrationId)}/invitations/bulk', data: {
      'client_request_id': clientRequestId,
      'guests': drafts.map((d) => d.toJson()).toList(),
    });
    return BulkInviteResult.fromJson(res.data['data'] as Map<String, dynamic>);
  }

  Future<InvitationDetail> detail(String celebrationId, String guestId) async {
    final res = await _api.dio.get('${_base(celebrationId)}/invitations/$guestId');
    return InvitationDetail.fromJson(res.data['data'] as Map<String, dynamic>);
  }

  Future<GuestInvitation> update(String celebrationId, String guestId, InvitationDraft draft) async {
    final res = await _api.dio.patch('${_base(celebrationId)}/invitations/$guestId', data: draft.toJson(forUpdate: true));
    return GuestInvitation.fromJson(res.data['data'] as Map<String, dynamic>);
  }

  Future<GuestInvitation> revoke(String celebrationId, String guestId, {String? reason}) async {
    final res = await _api.dio.post('${_base(celebrationId)}/invitations/$guestId/revoke',
        data: {if (reason != null && reason.trim().isNotEmpty) 'reason': reason.trim()});
    return GuestInvitation.fromJson(res.data['data'] as Map<String, dynamic>);
  }

  Future<GuestInvitation> rotate(String celebrationId, String guestId) async {
    final res = await _api.dio.post('${_base(celebrationId)}/invitations/$guestId/rotate');
    return GuestInvitation.fromJson(res.data['data'] as Map<String, dynamic>);
  }

  /// Call only after the device confirmed the share (share sheet completed,
  /// WhatsApp opened, link copied) — it is recorded as such, never as
  /// "delivered".
  Future<GuestInvitation> markShared(String celebrationId, String guestId, String channel) async {
    final res = await _api.dio.post('${_base(celebrationId)}/invitations/$guestId/shared', data: {'channel': channel});
    return GuestInvitation.fromJson(res.data['data'] as Map<String, dynamic>);
  }

  Future<EmailResult> sendEmail(String celebrationId, String guestId) async {
    final res = await _api.dio.post('${_base(celebrationId)}/invitations/$guestId/email');
    final data = res.data['data'] as Map<String, dynamic>;
    return EmailResult(sent: data['sent'] as bool? ?? false, message: data['message'] as String? ?? '');
  }

  // ── Gate (the host's own scanner) ──────────────────────────────────────────

  Future<GateSessionInfo> gateSession(String celebrationId) async {
    final res = await _api.dio.get('${_base(celebrationId)}/gate/session');
    return GateSessionInfo.fromJson(res.data['data'] as Map<String, dynamic>);
  }

  Future<GateResult> gateVerify(String celebrationId, GatePassRef ref) =>
      _gate(celebrationId, 'verify', ref.toJson());

  Future<GateResult> gateCheckIn(String celebrationId, GatePassRef ref, {required int partySize}) =>
      _gate(celebrationId, 'check-in', {...ref.toJson(), 'party_size': partySize});

  Future<GateResult> gateCheckOut(String celebrationId, GatePassRef ref) =>
      _gate(celebrationId, 'check-out', ref.toJson());

  Future<GateResult> _gate(String celebrationId, String action, Map<String, dynamic> body) async {
    final res = await _api.dio.post('${_base(celebrationId)}/gate/$action', data: body);
    return GateResult.fromJson(res.data['data'] as Map<String, dynamic>);
  }

  Future<List<GateGuest>> gateSearch(String celebrationId, String query) async {
    final res = await _api.dio.get('${_base(celebrationId)}/gate/search', queryParameters: {'q': query});
    return ((res.data['data'] ?? []) as List).map((e) => GateGuest.fromJson(e as Map<String, dynamic>)).toList();
  }

  // ── Gate access (delegated entry staff) ────────────────────────────────────

  Future<List<GateAccess>> gateAccesses(String celebrationId) async {
    final res = await _api.dio.get('${_base(celebrationId)}/gate-access');
    return ((res.data['data'] ?? []) as List).map((e) => GateAccess.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<GateAccess> createGateAccess(String celebrationId, String label, {int? validHours}) async {
    final res = await _api.dio.post('${_base(celebrationId)}/gate-access', data: {
      'label': label,
      if (validHours != null) 'valid_hours': validHours,
    });
    return GateAccess.fromJson(res.data['data'] as Map<String, dynamic>);
  }

  Future<GateAccess> revokeGateAccess(String celebrationId, String accessId) async {
    final res = await _api.dio.post('${_base(celebrationId)}/gate-access/$accessId/revoke');
    return GateAccess.fromJson(res.data['data'] as Map<String, dynamic>);
  }
}

/// Random id for idempotency keys and scan ids (not a credential).
String newRequestId([String prefix = 'r']) {
  final rnd = Random.secure();
  final hex = List.generate(16, (_) => rnd.nextInt(256).toRadixString(16).padLeft(2, '0')).join();
  return '$prefix-$hex';
}

/// The server's own message for business errors (409/422/429 are written
/// for people), otherwise the generic network description.
String invitationErrorMessage(Object error) {
  if (error is DioException) {
    final status = error.response?.statusCode;
    final data = error.response?.data;
    if (status != null && status >= 400 && status < 500 && status != 401 && data is Map) {
      final err = data['error'];
      if (err is Map && err['message'] is String && err['code'] != 'VALIDATION_ERROR') {
        return err['message'] as String;
      }
    }
  }
  return describeApiError(error);
}

/// True when the request never got a server answer — the action may or may
/// not have happened, so the UI must not claim either.
bool isNoResponse(Object error) =>
    error is DioException &&
    error.response == null &&
    error.type != DioExceptionType.cancel;

DateTime? _dt(dynamic v) => v is String ? DateTime.tryParse(v)?.toLocal() : null;

// ── Models ────────────────────────────────────────────────────────────────────

class InvitationPage {
  final List<GuestInvitation> items;
  final int total;
  final bool hasNext;
  InvitationPage({required this.items, required this.total, required this.hasNext});
}

/// "HH:MM[:SS]" from the API.
class TimeOfDayText {
  static String? display(String? hhmm) {
    if (hhmm == null || hhmm.length < 5) return null;
    final h = int.tryParse(hhmm.substring(0, 2)) ?? 0;
    final m = hhmm.substring(3, 5);
    final suffix = h < 12 ? 'AM' : 'PM';
    return '${h % 12 == 0 ? 12 : h % 12}:$m $suffix';
  }
}

class GuestInvitation {
  final String id;
  final String celebrationId;
  final String name;
  final String? phone;
  final String? email;
  final String? groupTag;
  final String? notes;
  final int plusOnesAllowed;
  final String? arrivalWindowStart;
  final String? arrivalWindowEnd;
  final String? vehicleNumber;
  final String passStatus;
  final String passState;
  final String rsvpStatus;
  final int? rsvpPartySize;
  final DateTime? rsvpRespondedAt;
  final String? guestNote;
  final String entryStatus;
  final DateTime? checkedInAt;
  final DateTime? checkedOutAt;
  final int? checkedInPartySize;
  final DateTime? invitationOpenedAt;
  final DateTime? lastSharedAt;
  final String? lastSharedChannel;
  final int shareCount;
  final DateTime? revokedAt;
  final String? revokedReason;
  final DateTime? createdAt;
  final String? inviteUrl;
  final String? entryCode;
  final String? qrPayload;

  GuestInvitation({
    required this.id,
    required this.celebrationId,
    required this.name,
    this.phone,
    this.email,
    this.groupTag,
    this.notes,
    required this.plusOnesAllowed,
    this.arrivalWindowStart,
    this.arrivalWindowEnd,
    this.vehicleNumber,
    required this.passStatus,
    required this.passState,
    required this.rsvpStatus,
    this.rsvpPartySize,
    this.rsvpRespondedAt,
    this.guestNote,
    required this.entryStatus,
    this.checkedInAt,
    this.checkedOutAt,
    this.checkedInPartySize,
    this.invitationOpenedAt,
    this.lastSharedAt,
    this.lastSharedChannel,
    this.shareCount = 0,
    this.revokedAt,
    this.revokedReason,
    this.createdAt,
    this.inviteUrl,
    this.entryCode,
    this.qrPayload,
  });

  bool get isRevoked => passStatus == 'revoked';
  bool get isInside => entryStatus == 'checked_in';
  bool get hasArrived => entryStatus != 'not_arrived';

  factory GuestInvitation.fromJson(Map<String, dynamic> j) => GuestInvitation(
        id: j['id'] as String,
        celebrationId: j['celebration_id'] as String,
        name: j['name'] as String? ?? '',
        phone: j['phone'] as String?,
        email: j['email'] as String?,
        groupTag: j['group_tag'] as String?,
        notes: j['notes'] as String?,
        plusOnesAllowed: j['plus_ones_allowed'] as int? ?? 0,
        arrivalWindowStart: j['arrival_window_start'] as String?,
        arrivalWindowEnd: j['arrival_window_end'] as String?,
        vehicleNumber: j['vehicle_number'] as String?,
        passStatus: j['pass_status'] as String? ?? 'active',
        passState: j['pass_state'] as String? ?? 'valid',
        rsvpStatus: j['rsvp_status'] as String? ?? 'pending',
        rsvpPartySize: j['rsvp_party_size'] as int?,
        rsvpRespondedAt: _dt(j['rsvp_responded_at']),
        guestNote: j['guest_note'] as String?,
        entryStatus: j['entry_status'] as String? ?? 'not_arrived',
        checkedInAt: _dt(j['checked_in_at']),
        checkedOutAt: _dt(j['checked_out_at']),
        checkedInPartySize: j['checked_in_party_size'] as int?,
        invitationOpenedAt: _dt(j['invitation_opened_at']),
        lastSharedAt: _dt(j['last_shared_at']),
        lastSharedChannel: j['last_shared_channel'] as String?,
        shareCount: j['share_count'] as int? ?? 0,
        revokedAt: _dt(j['revoked_at']),
        revokedReason: j['revoked_reason'] as String?,
        createdAt: _dt(j['created_at']),
        inviteUrl: j['invite_url'] as String?,
        entryCode: j['entry_code'] as String?,
        qrPayload: j['qr_payload'] as String?,
      );
}

/// Form values for create (all fields) and edit (sent fields only).
class InvitationDraft {
  final String name;
  final String? phone;
  final String? email;
  final int plusOnesAllowed;
  final String? arrivalWindowStart; // "HH:MM"
  final String? arrivalWindowEnd;
  final String? vehicleNumber;
  final String? groupTag;
  final String? notes;

  InvitationDraft({
    required this.name,
    this.phone,
    this.email,
    this.plusOnesAllowed = 0,
    this.arrivalWindowStart,
    this.arrivalWindowEnd,
    this.vehicleNumber,
    this.groupTag,
    this.notes,
  });

  Map<String, dynamic> toJson({bool forUpdate = false}) {
    String? clean(String? v) => (v == null || v.trim().isEmpty) ? null : v.trim();
    final map = <String, dynamic>{
      'name': name.trim(),
      'phone': clean(phone),
      'email': clean(email),
      'plus_ones_allowed': plusOnesAllowed,
      'arrival_window_start': arrivalWindowStart,
      'arrival_window_end': arrivalWindowEnd,
      'vehicle_number': clean(vehicleNumber),
      'group_tag': clean(groupTag),
      'notes': clean(notes),
    };
    // On create, omit empties; on edit, send nulls so a cleared field clears.
    if (!forUpdate) map.removeWhere((_, v) => v == null);
    return map;
  }
}

class InvitationSummary {
  final int total, active, revoked, attending, maybe, declined, pending, opened;
  final int expectedPeople, arrivedGuests, arrivedPeople, insideNow, checkedOut, stillExpected;

  InvitationSummary({
    required this.total,
    required this.active,
    required this.revoked,
    required this.attending,
    required this.maybe,
    required this.declined,
    required this.pending,
    required this.opened,
    required this.expectedPeople,
    required this.arrivedGuests,
    required this.arrivedPeople,
    required this.insideNow,
    required this.checkedOut,
    required this.stillExpected,
  });

  factory InvitationSummary.fromJson(Map<String, dynamic> j) {
    int n(String k) => j[k] as int? ?? 0;
    return InvitationSummary(
      total: n('total'),
      active: n('active'),
      revoked: n('revoked'),
      attending: n('rsvp_attending'),
      maybe: n('rsvp_maybe'),
      declined: n('rsvp_declined'),
      pending: n('rsvp_pending'),
      opened: n('opened'),
      expectedPeople: n('expected_people'),
      arrivedGuests: n('arrived_guests'),
      arrivedPeople: n('arrived_people'),
      insideNow: n('inside_now'),
      checkedOut: n('checked_out'),
      stillExpected: n('still_expected'),
    );
  }
}

class InvitationHistoryItem {
  final String eventType;
  final String? previousStatus;
  final String? newStatus;
  final String? actorType;
  final String? actorLabel;
  final Map<String, dynamic>? details;
  final DateTime occurredAt;

  InvitationHistoryItem({
    required this.eventType,
    this.previousStatus,
    this.newStatus,
    this.actorType,
    this.actorLabel,
    this.details,
    required this.occurredAt,
  });

  factory InvitationHistoryItem.fromJson(Map<String, dynamic> j) => InvitationHistoryItem(
        eventType: j['event_type'] as String? ?? '',
        previousStatus: j['previous_status'] as String?,
        newStatus: j['new_status'] as String?,
        actorType: j['actor_type'] as String?,
        actorLabel: j['actor_label'] as String?,
        details: j['details'] as Map<String, dynamic>?,
        occurredAt: _dt(j['occurred_at']) ?? DateTime.now(),
      );
}

class EntryLogItem {
  final String action;
  final String result;
  final String method;
  final int? partySize;
  final String operatorType;
  final String? operatorLabel;
  final DateTime occurredAt;

  EntryLogItem({
    required this.action,
    required this.result,
    required this.method,
    this.partySize,
    required this.operatorType,
    this.operatorLabel,
    required this.occurredAt,
  });

  factory EntryLogItem.fromJson(Map<String, dynamic> j) => EntryLogItem(
        action: j['action'] as String? ?? '',
        result: j['result'] as String? ?? '',
        method: j['method'] as String? ?? '',
        partySize: j['party_size'] as int?,
        operatorType: j['operator_type'] as String? ?? '',
        operatorLabel: j['operator_label'] as String?,
        occurredAt: _dt(j['occurred_at']) ?? DateTime.now(),
      );
}

class InvitationDetail {
  final GuestInvitation invitation;
  final List<InvitationHistoryItem> history;
  final List<EntryLogItem> entries;

  InvitationDetail({required this.invitation, required this.history, required this.entries});

  factory InvitationDetail.fromJson(Map<String, dynamic> j) => InvitationDetail(
        invitation: GuestInvitation.fromJson(j['invitation'] as Map<String, dynamic>),
        history: ((j['history'] ?? []) as List)
            .map((e) => InvitationHistoryItem.fromJson(e as Map<String, dynamic>))
            .toList(),
        entries: ((j['entries'] ?? []) as List).map((e) => EntryLogItem.fromJson(e as Map<String, dynamic>)).toList(),
      );
}

class BulkInviteRow {
  final int index;
  final String status; // created | existing | duplicate | error
  final String? message;
  final GuestInvitation? invitation;
  BulkInviteRow({required this.index, required this.status, this.message, this.invitation});
}

class BulkInviteResult {
  final int created;
  final int skipped;
  final List<BulkInviteRow> results;
  BulkInviteResult({required this.created, required this.skipped, required this.results});

  factory BulkInviteResult.fromJson(Map<String, dynamic> j) => BulkInviteResult(
        created: j['created'] as int? ?? 0,
        skipped: j['skipped'] as int? ?? 0,
        results: ((j['results'] ?? []) as List).map((e) {
          final m = e as Map<String, dynamic>;
          return BulkInviteRow(
            index: m['index'] as int? ?? 0,
            status: m['status'] as String? ?? 'error',
            message: m['message'] as String?,
            invitation: m['invitation'] == null ? null : GuestInvitation.fromJson(m['invitation'] as Map<String, dynamic>),
          );
        }).toList(),
      );
}

class DeliveryCapabilities {
  final bool email;
  DeliveryCapabilities({required this.email});
  factory DeliveryCapabilities.fromJson(Map<String, dynamic> j) => DeliveryCapabilities(email: j['email'] as bool? ?? false);
}

class EmailResult {
  final bool sent;
  final String message;
  EmailResult({required this.sent, required this.message});
}

/// Identifies a pass at the gate. The [clientScanId] is created once per
/// scan and reused for every retry of the resulting check-in/out.
class GatePassRef {
  final String? code;
  final String? guestId;
  final String method; // qr | manual | search
  final String clientScanId;

  GatePassRef({this.code, this.guestId, required this.method, String? clientScanId})
      : clientScanId = clientScanId ?? newRequestId('scan');

  GatePassRef withNewScanId() => GatePassRef(code: code, guestId: guestId, method: method);

  Map<String, dynamic> toJson() => {
        if (code != null) 'code': code,
        if (guestId != null) 'guest_id': guestId,
        'method': method,
        'client_scan_id': clientScanId,
      };
}

class GateGuest {
  final String id;
  final String name;
  final String? phoneMasked;
  final int plusOnesAllowed;
  final String rsvpStatus;
  final int? rsvpPartySize;
  final String entryStatus;
  final DateTime? checkedInAt;
  final int? checkedInPartySize;
  final String? arrivalWindowStart;
  final String? arrivalWindowEnd;
  final String? vehicleNumber;

  GateGuest({
    required this.id,
    required this.name,
    this.phoneMasked,
    required this.plusOnesAllowed,
    required this.rsvpStatus,
    this.rsvpPartySize,
    required this.entryStatus,
    this.checkedInAt,
    this.checkedInPartySize,
    this.arrivalWindowStart,
    this.arrivalWindowEnd,
    this.vehicleNumber,
  });

  factory GateGuest.fromJson(Map<String, dynamic> j) => GateGuest(
        id: j['id'] as String,
        name: j['name'] as String? ?? '',
        phoneMasked: j['phone_masked'] as String?,
        plusOnesAllowed: j['plus_ones_allowed'] as int? ?? 0,
        rsvpStatus: j['rsvp_status'] as String? ?? 'pending',
        rsvpPartySize: j['rsvp_party_size'] as int?,
        entryStatus: j['entry_status'] as String? ?? 'not_arrived',
        checkedInAt: _dt(j['checked_in_at']),
        checkedInPartySize: j['checked_in_party_size'] as int?,
        arrivalWindowStart: j['arrival_window_start'] as String?,
        arrivalWindowEnd: j['arrival_window_end'] as String?,
        vehicleNumber: j['vehicle_number'] as String?,
      );
}

class GateResult {
  final String result;
  final String message;
  final bool recorded;
  final bool replayed;
  final List<String> warnings;
  final GateGuest? guest;

  GateResult({
    required this.result,
    required this.message,
    required this.recorded,
    required this.replayed,
    required this.warnings,
    this.guest,
  });

  factory GateResult.fromJson(Map<String, dynamic> j) => GateResult(
        result: j['result'] as String? ?? 'invalid',
        message: j['message'] as String? ?? '',
        recorded: j['recorded'] as bool? ?? false,
        replayed: j['replayed'] as bool? ?? false,
        warnings: ((j['warnings'] ?? []) as List).cast<String>(),
        guest: j['guest'] == null ? null : GateGuest.fromJson(j['guest'] as Map<String, dynamic>),
      );
}

class GateSessionInfo {
  final String celebrationTitle;
  final int arrivedGuests;
  final int arrivedPeople;
  final int stillExpected;

  GateSessionInfo({
    required this.celebrationTitle,
    required this.arrivedGuests,
    required this.arrivedPeople,
    required this.stillExpected,
  });

  factory GateSessionInfo.fromJson(Map<String, dynamic> j) => GateSessionInfo(
        celebrationTitle: j['celebration_title'] as String? ?? '',
        arrivedGuests: j['arrived_guests'] as int? ?? 0,
        arrivedPeople: j['arrived_people'] as int? ?? 0,
        stillExpected: j['still_expected'] as int? ?? 0,
      );
}

class GateAccess {
  final String id;
  final String label;
  final DateTime? expiresAt;
  final DateTime? revokedAt;
  final DateTime? lastUsedAt;
  final bool isActive;
  final String? consoleUrl;

  GateAccess({
    required this.id,
    required this.label,
    this.expiresAt,
    this.revokedAt,
    this.lastUsedAt,
    required this.isActive,
    this.consoleUrl,
  });

  factory GateAccess.fromJson(Map<String, dynamic> j) => GateAccess(
        id: j['id'] as String,
        label: j['label'] as String? ?? '',
        expiresAt: _dt(j['expires_at']),
        revokedAt: _dt(j['revoked_at']),
        lastUsedAt: _dt(j['last_used_at']),
        isActive: j['is_active'] as bool? ?? false,
        consoleUrl: j['console_url'] as String?,
      );
}
