import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:intl/intl.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/models.dart';

/// A themed, shareable invitation card for a celebration. Wrap in a
/// [RepaintBoundary] (already done here) and capture via [captureCard]
/// to get PNG bytes for sharing/downloading.
class InvitationCard extends StatelessWidget {
  final Celebration celebration;
  final GlobalKey boundaryKey;

  const InvitationCard({super.key, required this.celebration, required this.boundaryKey});

  static Future<Uint8List?> captureCard(GlobalKey boundaryKey) async {
    final boundary = boundaryKey.currentContext?.findRenderObject() as RenderRepaintBoundary?;
    if (boundary == null) return null;
    final image = await boundary.toImage(pixelRatio: 3.0);
    final byteData = await image.toByteData(format: ui.ImageByteFormat.png);
    return byteData?.buffer.asUint8List();
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final date = celebration.celebrationDate;
    final dateStr = date != null ? DateFormat('EEEE, d MMMM yyyy').format(date) : '';
    final venue = celebration.venueName ?? celebration.venueAddress ?? '';

    return RepaintBoundary(
      key: boundaryKey,
      child: Container(
        width: 360,
        padding: const EdgeInsets.all(0),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(28),
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [ty.saffron, ty.saffronDeep],
          ),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ClipRRect(
              borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
              child: celebration.heroImageUrl != null && celebration.heroImageUrl!.isNotEmpty
                  ? CachedNetworkImage(
                      imageUrl: celebration.heroImageUrl!,
                      height: 200,
                      width: double.infinity,
                      fit: BoxFit.cover,
                      errorWidget: (_, __, ___) => Container(height: 200, color: Colors.white24),
                    )
                  : Container(
                      height: 200,
                      width: double.infinity,
                      color: Colors.white.withOpacity(0.15),
                      child: const Icon(Icons.celebration_rounded, color: Colors.white, size: 64),
                    ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 24, 24, 28),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  Text(
                    (celebration.occasionName ?? 'CELEBRATION').toUpperCase(),
                    style: TyType.eyebrow(12, color: Colors.white.withOpacity(0.85)),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    "You're Invited to",
                    textAlign: TextAlign.center,
                    style: TyType.sans(14, color: Colors.white.withOpacity(0.9)),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    celebration.title,
                    textAlign: TextAlign.center,
                    style: TyType.display(26, color: Colors.white),
                  ),
                  const SizedBox(height: 16),
                  if (dateStr.isNotEmpty) ...[
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.event_rounded, size: 15, color: Colors.white70),
                        const SizedBox(width: 6),
                        Text(dateStr, style: TyType.sans(13.5, color: Colors.white70)),
                      ],
                    ),
                    const SizedBox(height: 6),
                  ],
                  if (venue.isNotEmpty)
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.place_outlined, size: 15, color: Colors.white70),
                        const SizedBox(width: 6),
                        Flexible(child: Text(venue, style: TyType.sans(13.5, color: Colors.white70), textAlign: TextAlign.center)),
                      ],
                    ),
                  const SizedBox(height: 20),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text('Presented by Tyohaar', style: TyType.sans(11, color: Colors.white.withOpacity(0.85), weight: FontWeight.w700)),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
