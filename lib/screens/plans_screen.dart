import 'package:flutter/material.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../widgets/photo_placeholder.dart';
import '../widgets/common.dart';
import 'event_hub_screen.dart';
import 'plan_flow/plan_flow_screen.dart';

/// "Your plans" — every celebration, in progress and dreamed-of.
class PlansScreen extends StatelessWidget {
  const PlansScreen({super.key});

  static const _events = [
    ['Diya turns One', 'Birthday', 'saffron', '14 Jun', 35, 'Planning'],
    ['Griha Pravesh', 'Housewarming', 'leaf', '2 Aug', 12, 'Planning'],
    ['Anniversary Dinner', 'Anniversary', 'rose', '19 Sep', 0, 'Idea'],
  ];

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final topPadding = MediaQuery.of(context).padding.top + 70; // Header height approx

    return ListView(
      padding: EdgeInsets.fromLTRB(18, topPadding, 18, 28),
      children: [
        Row(
          children: [
            Expanded(child: Text('Your plans', style: TyType.display(26, color: ty.ink))),
            ChromeIconButton(
              icon: Icons.add_rounded,
              onTap: () => Navigator.of(context)
                  .push(MaterialPageRoute(builder: (_) => const PlanFlowScreen())),
            ),
          ],
        ),
        const SizedBox(height: 22),
        const SectionHeader('In progress'),
        ..._events.map((e) => _eventCard(context, e)),
        const SizedBox(height: 12),
        GestureDetector(
          onTap: () => Navigator.of(context)
              .push(MaterialPageRoute(builder: (_) => const PlanFlowScreen())),
          child: Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: ty.line, width: 1.5),
            ),
            child: Row(
              children: [
                Container(
                  width: 46,
                  height: 46,
                  decoration: BoxDecoration(
                    color: ty.saffronSoft,
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Icon(Icons.add_rounded, color: ty.saffronDeep, size: 22),
                ),
                const SizedBox(width: 13),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Plan a new celebration',
                          style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
                      const SizedBox(height: 2),
                      Text('Start from any occasion',
                          style: TyType.sans(12.5, color: ty.ink2)),
                    ],
                  ),
                ),
                Icon(Icons.chevron_right_rounded, color: ty.ink3),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _eventCard(BuildContext context, List e) {
    final ty = context.ty;
    final tint = e[2] as String;
    final pct = e[4] as int;
    return GestureDetector(
      onTap: () => Navigator.of(context)
          .push(MaterialPageRoute(builder: (_) => const EventHubScreen())),
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(13),
        decoration: BoxDecoration(
          color: ty.surface,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: ty.line),
        ),
        child: Row(
          children: [
            SizedBox(
              width: 58,
              height: 58,
              child: PhotoPlaceholder(tint: tint, arch: false),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('${e[1]} · ${e[3]}'.toUpperCase(),
                      style: TyType.eyebrow(11, color: ty.tint(tint))),
                  const SizedBox(height: 3),
                  Text(e[0] as String,
                      style: TyType.sans(16, color: ty.ink, weight: FontWeight.w700)),
                  const SizedBox(height: 9),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(3),
                    child: LinearProgressIndicator(
                      value: pct / 100,
                      minHeight: 5,
                      backgroundColor: ty.surface2,
                      color: ty.saffron,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            Column(
              children: [
                Text('$pct%',
                    style: TyType.sans(15, color: ty.ink, weight: FontWeight.w800)),
                Text(e[5] as String, style: TyType.sans(10.5, color: ty.ink3)),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
