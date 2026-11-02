import 'package:flutter/material.dart';

import '../data/auth_manager.dart';
import '../screens/booking_detail_screen.dart';
import 'log.dart';

/// The app's single navigator, so a tap on a push notification can open a
/// screen from outside the widget tree.
final GlobalKey<NavigatorState> rootNavigatorKey = GlobalKey<NavigatorState>();

final RegExp _bookingLink = RegExp(r'^/bookings/([A-Za-z0-9-]+)$');

/// Opens the screen a push notification points at (its `action_url`).
///
/// Only links this build can show are handled; anything else (including vendor
/// links, which belong to the vendor portal) is ignored rather than guessed at.
/// A signed-out user is never routed into account screens.
void openFromPush(String? actionUrl, {int attempt = 0}) {
  if (actionUrl == null || actionUrl.isEmpty) return;
  final match = _bookingLink.firstMatch(actionUrl);
  if (match == null) {
    logDebug('Push: no screen for "$actionUrl"');
    return;
  }
  if (!AuthManager.instance.isAuthenticated) return;

  final navigator = rootNavigatorKey.currentState;
  if (navigator == null) {
    // Launched from a notification: the first frame hasn't built the
    // navigator yet. Try again after it, a few times at most.
    if (attempt < 5) {
      WidgetsBinding.instance
          .addPostFrameCallback((_) => openFromPush(actionUrl, attempt: attempt + 1));
    }
    return;
  }
  navigator.push(MaterialPageRoute(builder: (_) => BookingDetailScreen(bookingId: match.group(1)!)));
}
