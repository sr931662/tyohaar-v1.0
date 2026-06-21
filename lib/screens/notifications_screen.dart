import 'package:flutter/material.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/sample_data.dart';
import '../data/models.dart';
import '../widgets/common.dart';

class NotificationsScreen extends StatelessWidget {
  const NotificationsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final today = TyData.notifs.take(3).toList();
    final earlier = TyData.notifs.skip(3).toList();

    return Scaffold(
      appBar: tyAppBar(context, title: 'Activity', actions: [
        Padding(
          padding: const EdgeInsets.only(right: 18),
          child: Center(
            child: GestureDetector(
              onTap: () {},
              child: Text('Mark read',
                  style: TyType.sans(12.5, color: ty.saffron, weight: FontWeight.w700)),
            ),
          ),
        ),
      ]),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(18, 4, 18, 28),
        children: [
          _group(context, 'Today', today),
          const SizedBox(height: 22),
          _group(context, 'Earlier', earlier),
        ],
      ),
    );
  }

  Widget _group(BuildContext context, String label, List<NotifItem> items) {
    final ty = context.ty;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label.toUpperCase(), style: TyType.eyebrow(11.5, color: ty.ink3)),
        const SizedBox(height: 8),
        ...items.map((n) => _row(context, n)),
      ],
    );
  }

  Widget _row(BuildContext context, NotifItem n) {
    final ty = context.ty;
    final c = ty.tint(n.tint);
    return Container(
      margin: const EdgeInsets.only(bottom: 6),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
      decoration: BoxDecoration(
        color: n.unread ? ty.surface : Colors.transparent,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: n.unread ? ty.line : Colors.transparent),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: Color.alphaBlend(c.withOpacity(0.15), ty.surface2),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(tyIcon(n.icon), color: c, size: 20),
          ),
          const SizedBox(width: 13),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                RichText(
                  text: TextSpan(
                    style: TyType.sans(14, color: ty.ink2),
                    children: [
                      TextSpan(
                          text: '${n.who} ',
                          style: TyType.sans(14, color: ty.ink, weight: FontWeight.w700)),
                      TextSpan(text: n.text),
                    ],
                  ),
                ),
                const SizedBox(height: 3),
                Text('${n.time} ago', style: TyType.sans(11.5, color: ty.ink3)),
              ],
            ),
          ),
          if (n.unread)
            Container(
              margin: const EdgeInsets.only(top: 6, left: 6),
              width: 8,
              height: 8,
              decoration: BoxDecoration(color: ty.saffron, shape: BoxShape.circle),
            ),
        ],
      ),
    );
  }
}
