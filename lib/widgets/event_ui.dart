import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../data/services/event_service.dart';
import '../l10n/generated/app_localizations.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import 'photo_placeholder.dart';
import 'ty_button.dart';

/// Tyohaar's burgundy and gold, the invitation family's signature in both
/// themes. Everything else on these screens uses the regular theme tokens.
const Color kInvitationBurgundy = Color(0xFF5B1226);
const Color kInvitationGold = Color(0xFFD9B266);

String eventDateRange(BuildContext context, DateTime? start, DateTime? end) {
  if (start == null) return '';
  if (end != null && end != start) {
    final sameYear = start.year == end.year;
    return '${DateFormat(sameYear ? 'd MMM' : 'd MMM yyyy').format(start)} – ${DateFormat('d MMM yyyy').format(end)}';
  }
  return DateFormat('d MMMM yyyy').format(start);
}

String? eventTimeText(String? hhmm) {
  if (hhmm == null || hhmm.length < 5) return null;
  final parts = hhmm.split(':');
  return DateFormat.jm().format(DateTime(2000, 1, 1, int.parse(parts[0]), int.parse(parts[1])));
}

/// "Tyohaar Booking" or "Independent Event". Same weight on purpose: neither
/// kind of customer is the lesser one.
class EventSourceBadge extends StatelessWidget {
  final bool booked;
  const EventSourceBadge({super.key, required this.booked});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final color = booked ? ty.saffronDeep : ty.leaf;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
      decoration: BoxDecoration(color: color.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(99)),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(booked ? Icons.verified_outlined : Icons.edit_calendar_outlined, size: 12, color: color),
        const SizedBox(width: 4),
        Flexible(
          child: Text(booked ? l10n.evBadgeBooked : l10n.evBadgeIndependent,
              maxLines: 1, overflow: TextOverflow.ellipsis, style: TyType.sans(11, color: color, weight: FontWeight.w700)),
        ),
      ]),
    );
  }
}

String eventStatusLine(AppLocalizations l10n, EventSummaryCard e) {
  if (e.status == 'cancelled') return l10n.evStatusCancelled;
  if (e.status == 'postponed') return l10n.evStatusPostponed;
  return switch (e.segment) {
    'ongoing' => l10n.evStatusOngoing,
    'completed' => l10n.evStatusCompleted,
    _ => switch (e.daysRemaining) {
        null => l10n.evStatusUpcoming,
        0 => l10n.evStatusToday,
        1 => l10n.evStatusTomorrow,
        final d => l10n.evStatusDaysLeft(d),
      },
  };
}

/// One celebration. Every number on it comes from the server; an event with no
/// guests says so rather than showing zeros that read like a result.
class EventCard extends StatelessWidget {
  final EventSummaryCard event;
  final String actionLabel;
  final VoidCallback onTap;
  final bool compact;

  const EventCard({super.key, required this.event, required this.actionLabel, required this.onTap, this.compact = false});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final e = event;
    final time = eventTimeText(e.startTime);
    final when = [eventDateRange(context, e.date, e.endDate), if (time != null && e.endDate == null) time].join(' · ');
    final meta = [
      e.eventTypeLabel,
      if (e.functionCount > 1) l10n.evFunctionCount(e.functionCount),
    ].join(' · ');
    final muted = e.segment == 'completed' || e.status == 'cancelled';
    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(20), border: Border.all(color: ty.line)),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            if (!compact)
              SizedBox(
                height: 132,
                child: Stack(fit: StackFit.expand, children: [
                  _Cover(url: e.coverImageUrl, muted: muted),
                  Positioned(left: 12, top: 12, child: _OnImage(child: EventSourceBadge(booked: e.isBooked))),
                  if (e.isDraft) Positioned(right: 12, top: 12, child: _OnImage(child: _Draft(label: l10n.evDraftBadge))),
                ]),
              ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                if (compact) ...[EventSourceBadge(booked: e.isBooked), const SizedBox(height: 8)],
                Text(e.title, maxLines: 2, overflow: TextOverflow.ellipsis, style: TyType.display(21, color: ty.ink)),
                const SizedBox(height: 2),
                Text(meta, maxLines: 1, overflow: TextOverflow.ellipsis, style: TyType.sans(12.5, color: ty.ink3)),
                const SizedBox(height: 8),
                if (when.isNotEmpty) _line(ty, Icons.event_rounded, when),
                if (e.location.isNotEmpty) _line(ty, Icons.place_outlined, e.location),
                const SizedBox(height: 6),
                Text(eventStatusLine(l10n, e),
                    style: TyType.sans(13, color: muted ? ty.ink3 : ty.saffronDeep, weight: FontWeight.w700)),
                if (e.counts.invited > 0) ...[
                  const SizedBox(height: 4),
                  Text(l10n.evCountsLine(e.counts.invited, e.counts.confirmed, e.counts.pending),
                      maxLines: 2, overflow: TextOverflow.ellipsis, style: TyType.sans(12.5, color: ty.ink2)),
                ],
                const SizedBox(height: 12),
                TyButton(actionLabel, kind: TyButtonKind.soft, full: true, onTap: onTap),
              ]),
            ),
          ]),
        ),
      ),
    );
  }

  Widget _line(TyColors ty, IconData icon, String text) => Padding(
        padding: const EdgeInsets.only(bottom: 3),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(icon, size: 14, color: ty.ink3),
          const SizedBox(width: 6),
          Expanded(child: Text(text, maxLines: 1, overflow: TextOverflow.ellipsis, style: TyType.sans(13, color: ty.ink2))),
        ]),
      );
}

class _Cover extends StatelessWidget {
  final String? url;
  final bool muted;
  const _Cover({this.url, this.muted = false});

  @override
  Widget build(BuildContext context) {
    const placeholder = PhotoPlaceholder(tint: 'saffron', arch: false, radius: BorderRadius.zero);
    final image = url == null
        ? placeholder
        : CachedNetworkImage(
            imageUrl: url!,
            fit: BoxFit.cover,
            memCacheWidth: 900,
            placeholder: (_, __) => placeholder,
            errorWidget: (_, __, ___) => placeholder,
          );
    if (!muted) return image;
    return ColorFiltered(colorFilter: const ColorFilter.mode(Colors.grey, BlendMode.saturation), child: image);
  }
}

class _OnImage extends StatelessWidget {
  final Widget child;
  const _OnImage({required this.child});

  @override
  Widget build(BuildContext context) => DecoratedBox(
        decoration: BoxDecoration(color: context.ty.surface, borderRadius: BorderRadius.circular(99)),
        child: child,
      );
}

class _Draft extends StatelessWidget {
  final String label;
  const _Draft({required this.label});

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
        child: Text(label, style: TyType.sans(11, color: context.ty.ink2, weight: FontWeight.w700)),
      );
}

/// A small titled block used across the invitation screens.
class EventSection extends StatelessWidget {
  final String title;
  final String? subtitle;
  final Widget? trailing;
  final List<Widget> children;
  const EventSection({super.key, required this.title, this.subtitle, this.trailing, required this.children});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Row(children: [
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(title, style: TyType.display(19, color: ty.ink)),
            if (subtitle != null) ...[
              const SizedBox(height: 2),
              Text(subtitle!, style: TyType.sans(13, color: ty.ink3, height: 1.35)),
            ],
          ]),
        ),
        if (trailing != null) trailing!,
      ]),
      const SizedBox(height: 10),
      ...children,
    ]);
  }
}

BoxDecoration eventCardDecoration(TyColors ty) => BoxDecoration(
      color: ty.surface,
      borderRadius: BorderRadius.circular(16),
      border: Border.all(color: ty.line),
    );

/// A bordered card for a ListTile. Being a Material itself, the tile's own ink
/// shows; a decorated Container would paint over it.
class EventTileCard extends StatelessWidget {
  final EdgeInsetsGeometry? margin;
  final Widget child;
  const EventTileCard({super.key, this.margin, required this.child});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return Padding(
      padding: margin ?? EdgeInsets.zero,
      child: Material(
        color: ty.surface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16), side: BorderSide(color: ty.line)),
        clipBehavior: Clip.antiAlias,
        child: child,
      ),
    );
  }
}

/// Friendly "nothing here yet" for lists, with an optional next step.
class EventEmpty extends StatelessWidget {
  final IconData icon;
  final String title;
  final String? message;
  final String? action;
  final VoidCallback? onAction;
  const EventEmpty({super.key, required this.icon, required this.title, this.message, this.action, this.onAction});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 30, horizontal: 12),
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        Icon(icon, size: 38, color: ty.ink3),
        const SizedBox(height: 10),
        Text(title, textAlign: TextAlign.center, style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
        if (message != null) ...[
          const SizedBox(height: 4),
          Text(message!, textAlign: TextAlign.center, style: TyType.sans(13, color: ty.ink3, height: 1.4)),
        ],
        if (action != null) ...[
          const SizedBox(height: 14),
          TyButton(action!, kind: TyButtonKind.soft, onTap: onAction),
        ],
      ]),
    );
  }
}
