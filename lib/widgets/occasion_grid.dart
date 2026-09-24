import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/models.dart';
import '../l10n/generated/app_localizations.dart';

/// Groups occasions into Milestones / Memories / Growth / Other buckets by
/// name heuristics and renders them as a vertically-stacked, 2-column card
/// grid. Shared by the plan flow's occasion step and the home screen's
/// browse-by-occasion section so both present occasions identically.
///
/// Built from plain Rows (not GridView) — a shrink-wrapped GridView.count
/// reserves noticeably more height than its rows actually need, leaving a
/// large dead gap below the last row; Rows size to exactly their content.
class OccasionGrid extends StatelessWidget {
  final List<Occasion> occasions;
  final String? selectedId;
  final ValueChanged<Occasion> onSelect;

  const OccasionGrid({
    super.key,
    required this.occasions,
    this.selectedId,
    required this.onSelect,
  });

  @override
  Widget build(BuildContext context) {
    final milestones = occasions.where((o) {
      final n = o.name.toLowerCase();
      return n.contains('birth') || n.contains('anniv') || n.contains('grad') || n.contains('baby') || n.contains('shower');
    }).toList();

    final memories = occasions.where((o) {
      final n = o.name.toLowerCase();
      return n.contains('wedding') || n.contains('mehndi') || n.contains('haldi') || n.contains('sangeet') || n.contains('marriage') || n.contains('engagement') || n.contains('roka');
    }).toList();

    final growth = occasions.where((o) {
      final n = o.name.toLowerCase();
      return n.contains('corporate') || n.contains('annual') || n.contains('office') || n.contains('growth') || n.contains('seminar') || n.contains('workshop');
    }).toList();

    final others = occasions.where((o) {
      return !milestones.contains(o) && !memories.contains(o) && !growth.contains(o);
    }).toList();

    final l10n = AppLocalizations.of(context)!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (milestones.isNotEmpty) ...[
          _group(context, l10n.planFlowMilestonesGroupLabel, milestones),
          const SizedBox(height: 20),
        ],
        if (memories.isNotEmpty) ...[
          _group(context, l10n.planFlowMemoriesGroupLabel, memories),
          const SizedBox(height: 20),
        ],
        if (growth.isNotEmpty) ...[
          _group(context, l10n.planFlowGrowthGroupLabel, growth),
          const SizedBox(height: 20),
        ],
        if (others.isNotEmpty) _group(context, l10n.planFlowOtherMomentsGroupLabel, others),
      ],
    );
  }

  Widget _group(BuildContext context, String label, List<Occasion> list) {
    final ty = context.ty;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label.toUpperCase(), style: TyType.eyebrow(11, color: ty.ink3)),
        const SizedBox(height: 12),
        for (int i = 0; i < list.length; i += 2)
          Padding(
            padding: EdgeInsets.only(bottom: i + 2 < list.length ? 10 : 0),
            child: Row(
              children: [
                Expanded(child: _card(context, list[i])),
                const SizedBox(width: 10),
                Expanded(child: i + 1 < list.length ? _card(context, list[i + 1]) : const SizedBox()),
              ],
            ),
          ),
      ],
    );
  }

  Widget _card(BuildContext context, Occasion o) {
    final ty = context.ty;
    final on = selectedId == o.id;
    final c = o.themeColor ?? ty.tint(o.tint);
    final String? iconUrl = o.iconUrl;
    final bool hasIcon = iconUrl != null && iconUrl.isNotEmpty;

    return GestureDetector(
      onTap: () => onSelect(o),
      child: AspectRatio(
        aspectRatio: 1.3,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          decoration: BoxDecoration(
            // No photography here by design — occasion cards are a flat
            // tint plus the vendor/admin-supplied 3D icon, never an
            // AI-generated background image.
            color: Color.alphaBlend(c.withValues(alpha: on ? 0.16 : 0.08), ty.surface),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: on ? Colors.transparent : ty.line, width: 1),
          ),
          foregroundDecoration: BoxDecoration(
            borderRadius: BorderRadius.circular(18),
            border: on ? Border.all(color: c, width: 2.5) : null,
          ),
          clipBehavior: Clip.antiAlias,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(10, 10, 10, 8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Expanded(
                  child: Center(
                    child: hasIcon
                        ? CachedNetworkImage(
                            imageUrl: iconUrl,
                            fit: BoxFit.contain,
                            // Drawn at 44dp; the grid shows a dozen of these
                            // at once, so decoding each at source size is
                            // pure waste on the home screen's first paint.
                            memCacheWidth: 132,
                            errorWidget: (_, __, ___) => Icon(o.icon, size: 44, color: c),
                            placeholder: (_, __) => Icon(o.icon, size: 44, color: c.withValues(alpha: 0.4)),
                          )
                        : Icon(o.icon, size: 44, color: c),
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  o.name,
                  textAlign: TextAlign.center,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TyType.sans(13.5, color: ty.ink, weight: FontWeight.w700),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
