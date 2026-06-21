import 'package:flutter/material.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/sample_data.dart';
import '../data/models.dart';
import '../widgets/photo_placeholder.dart';
import '../widgets/common.dart';

/// Memories — a living gallery of past celebrations, year by year.
class MemoriesScreen extends StatelessWidget {
  const MemoriesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return ListView(
      padding: const EdgeInsets.fromLTRB(18, 12, 18, 28),
      children: [
        Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Memories', style: TyType.display(26, color: ty.ink)),
                  const SizedBox(height: 1),
                  Text('Your family’s story, year by year',
                      style: TyType.sans(13, color: ty.ink2)),
                ],
              ),
            ),
            const ChromeIconButton(icon: Icons.search_rounded),
          ],
        ),
        const SizedBox(height: 20),
        _grid(context),
      ],
    );
  }

  Widget _grid(BuildContext context) {
    // A simple two-column masonry: items with span 2 take the full width.
    final rows = <Widget>[];
    final items = TyData.memories;
    int i = 0;
    while (i < items.length) {
      final m = items[i];
      if (m.span == 2) {
        rows.add(_tile(context, m, fullWidth: true));
        i += 1;
      } else {
        final left = items[i];
        final hasRight = i + 1 < items.length && items[i + 1].span == 1;
        rows.add(Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(child: _tile(context, left)),
            const SizedBox(width: 12),
            if (hasRight)
              Expanded(child: _tile(context, items[i + 1]))
            else
              const Expanded(child: SizedBox()),
          ],
        ));
        i += hasRight ? 2 : 1;
      }
      rows.add(const SizedBox(height: 12));
    }
    return Column(children: rows);
  }

  Widget _tile(BuildContext context, Memory m, {bool fullWidth = false}) {
    final h = fullWidth ? 150.0 : 170.0;
    return GestureDetector(
      onTap: () {},
      child: ClipRRect(
        borderRadius: BorderRadius.circular(20),
        child: Stack(
          children: [
            PhotoPlaceholder(tint: m.tint, height: h, arch: false),
            Positioned.fill(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.bottomCenter,
                    end: Alignment.topCenter,
                    colors: [Colors.black.withOpacity(0.6), Colors.transparent],
                    stops: const [0, 0.6],
                  ),
                ),
              ),
            ),
            Positioned(
              top: 10,
              right: 10,
              child: TyPill('📷 ${m.photos}'),
            ),
            Positioned(
              left: 13,
              bottom: 11,
              right: 13,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(m.title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TyType.display(fullWidth ? 22 : 18, color: Colors.white)),
                  const SizedBox(height: 2),
                  Text(m.date,
                      style: TextStyle(
                          fontSize: 11.5, color: Colors.white.withOpacity(0.85))),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
