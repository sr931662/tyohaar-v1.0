import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../l10n/generated/app_localizations.dart';
import '../../theme/colors.dart';

/// One place that turns API status codes into words and colours, so the
/// list, detail, scanner and gate-access screens always agree.
class InvitationLabels {
  final AppLocalizations l10n;
  final TyColors ty;
  InvitationLabels(BuildContext context)
      : l10n = AppLocalizations.of(context)!,
        ty = context.ty;

  String passState(String state) => switch (state) {
        'valid' => l10n.invPassValid,
        'not_yet_valid' => l10n.invPassReady,
        'checked_in' => l10n.invPassInside,
        'checked_out' => l10n.invPassCheckedOut,
        'used' => l10n.invPassUsed,
        'expired' => l10n.invPassExpired,
        'revoked' => l10n.invPassRevoked,
        'event_cancelled' => l10n.invPassEventCancelled,
        'postponed' => l10n.invPassPostponed,
        _ => state,
      };

  Color passColor(String state) => switch (state) {
        'valid' || 'checked_in' => ty.leaf,
        'not_yet_valid' || 'checked_out' => ty.saffron,
        'revoked' || 'event_cancelled' => ty.rose,
        _ => ty.ink3,
      };

  String rsvp(String status) => switch (status) {
        'attending' => l10n.invRsvpAttending,
        'maybe' => l10n.invRsvpMaybe,
        'declined' => l10n.invRsvpDeclined,
        _ => l10n.invRsvpPending,
      };

  Color rsvpColor(String status) => switch (status) {
        'attending' => ty.leaf,
        'maybe' => ty.gold,
        'declined' => ty.rose,
        _ => ty.ink3,
      };

  String gateResult(String result) => switch (result) {
        'valid' => l10n.invGateValid,
        'checked_in' => l10n.invGateCheckedIn,
        'checked_out' => l10n.invGateCheckedOut,
        'already_checked_in' => l10n.invGateAlreadyIn,
        'already_used' => l10n.invGateAlreadyUsed,
        'not_checked_in' => l10n.invGateNotCheckedIn,
        'not_yet_valid' => l10n.invGateNotYetValid,
        'expired' => l10n.invGateExpired,
        'revoked' => l10n.invGateRevoked,
        'event_cancelled' => l10n.invGateEventCancelled,
        'denied' => l10n.invGateDenied,
        'party_size_exceeded' => l10n.invGatePartyExceeded,
        _ => l10n.invGateInvalid,
      };

  /// Green: admitted / recorded. Amber: needs a human look. Red: refuse.
  Color gateColor(String result) => switch (result) {
        'valid' || 'checked_in' || 'checked_out' => ty.leaf,
        'already_checked_in' || 'already_used' || 'not_checked_in' || 'not_yet_valid' || 'party_size_exceeded' =>
          ty.gold,
        _ => ty.rose,
      };

  String channel(String? channel) => switch (channel) {
        'whatsapp' => l10n.invChannelWhatsapp,
        'copy_link' => l10n.invChannelCopy,
        'email' => l10n.invChannelEmail,
        _ => l10n.invChannelShareSheet,
      };

  String warning(String w) => switch (w) {
        'rsvp_declined' => l10n.invWarnDeclined,
        'reentry' => l10n.invWarnReentry,
        _ => w,
      };

  String historyEvent(String type, {String? newStatus, Map<String, dynamic>? details}) => switch (type) {
        'invited' => l10n.invHistInvited,
        'invitation_opened' => l10n.invHistOpened,
        'rsvp_changed' => l10n.invHistRsvp(rsvp(newStatus ?? 'pending')),
        'checked_in' => l10n.invHistCheckedIn,
        'checked_out' => l10n.invHistCheckedOut,
        'details_updated' => l10n.invHistEdited,
        'shared' => l10n.invHistShared(channel(details?['channel'] as String?)),
        'email_sent' => l10n.invHistEmailed,
        'email_failed' => l10n.invHistEmailFailed,
        'link_rotated' => l10n.invHistRotated,
        'revoked' => l10n.invHistRevoked,
        _ => type,
      };

  String allowance(int plusOnes) => plusOnes == 0 ? l10n.invAllowanceSolo : l10n.invAllowancePlus(plusOnes);

  String? window(String? start, String? end) {
    String? fmt(String? hhmm) {
      if (hhmm == null || hhmm.length < 5) return null;
      final parts = hhmm.split(':');
      final t = DateTime(2000, 1, 1, int.parse(parts[0]), int.parse(parts[1]));
      return DateFormat.jm().format(t);
    }

    final a = fmt(start), b = fmt(end);
    return a == null || b == null ? null : '$a – $b';
  }

  String when(DateTime t) => DateFormat('d MMM, h:mm a').format(t);
}
