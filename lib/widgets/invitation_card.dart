import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:intl/intl.dart';

import '../theme/colors.dart';
import '../theme/mood_styles.dart';
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

  /// Parses a hex color string like "#FF5733" or "FF5733" into a [Color].
  /// Returns null for anything that isn't a valid 6/8-digit hex color.
  static Color? _parseHexColor(String? hex) {
    if (hex == null || hex.isEmpty) return null;
    var value = hex.replaceFirst('#', '');
    if (value.length == 6) value = 'FF$value';
    if (value.length != 8) return null;
    final parsed = int.tryParse(value, radix: 16);
    return parsed != null ? Color(parsed) : null;
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final date = celebration.celebrationDate;
    final dateStr = date != null ? DateFormat('EEEE, d MMMM yyyy').format(date) : '';
    final venue = celebration.venueName ?? celebration.venueAddress ?? '';

    // Occasion-based layout, theme-dependent: prefer the customer's chosen
    // theme colors/cover image over the mood-driven gradient and the
    // occasion's generic hero image, so the card actually reflects the
    // plan's customization rather than a one-size-fits-all look. When no
    // explicit theme was picked, fall back to the celebration's mood
    // (elegant/grand/fun/romantic) instead of a flat hardcoded saffron.
    final themeColors = celebration.themeColors;
    final moodStyle = moodStyleFor(celebration.mood?.slug);
    final primary = _parseHexColor(themeColors?['primary']) ?? moodStyle.primary(ty);
    final secondary = _parseHexColor(themeColors?['secondary']) ?? moodStyle.secondary(ty);
    final coverImageUrl = (celebration.themeCoverImageUrl?.isNotEmpty ?? false)
        ? celebration.themeCoverImageUrl
        : celebration.heroImageUrl;

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
            colors: [primary, secondary],
          ),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ClipRRect(
              borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
              child: coverImageUrl != null && coverImageUrl.isNotEmpty
                  ? CachedNetworkImage(
                      imageUrl: coverImageUrl,
                      height: 200,
                      width: double.infinity,
                      fit: BoxFit.cover,
                      errorWidget: (_, __, ___) => _logoPlaceholder(),
                    )
                  : _logoPlaceholder(),
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
                  if (celebration.mood != null) ...[
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.15),
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(moodStyle.icon, size: 13, color: Colors.white.withOpacity(0.9)),
                          const SizedBox(width: 5),
                          Text(
                            celebration.mood!.name,
                            style: TyType.sans(11, color: Colors.white.withOpacity(0.9), weight: FontWeight.w600),
                          ),
                        ],
                      ),
                    ),
                  ],
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

  Widget _logoPlaceholder() {
    return Container(
      height: 200,
      width: double.infinity,
      color: Colors.white.withOpacity(0.15),
      alignment: Alignment.center,
      child: Image.asset(
        'assets/images/tyohaar-mark.png',
        width: 84,
        height: 84,
      ),
    );
  }
}
