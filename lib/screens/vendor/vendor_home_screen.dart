import 'package:flutter/material.dart';
import '../../theme/colors.dart';
import '../../theme/typography.dart';
import '../../widgets/common.dart';
import '../../widgets/ty_button.dart';

class VendorHomeScreen extends StatelessWidget {
  final VoidCallback? onOpenDrawer;
  const VendorHomeScreen({super.key, this.onOpenDrawer});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;

    return Scaffold(
      backgroundColor: ty.paper,
      body: CustomScrollView(
        slivers: [
          _buildAppBar(context),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 24, 20, 100),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildBusinessStats(context),
                  const SizedBox(height: 32),
                  SectionHeader('New Requests', action: 'View All', onAction: () {}),
                  _buildRequestsRail(context),
                  const SizedBox(height: 32),
                  SectionHeader('Upcoming Schedule', action: 'Calendar', onAction: () {}),
                  _buildScheduleList(context),
                  const SizedBox(height: 32),
                  SectionHeader('Recent Performance'),
                  _buildPerformanceCard(context),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAppBar(BuildContext context) {
    final ty = context.ty;
    return SliverAppBar(
      pinned: true,
      expandedHeight: 140,
      backgroundColor: ty.paper,
      elevation: 0,
      leading: Padding(
        padding: const EdgeInsets.only(left: 12, top: 8),
        child: ChromeIconButton(icon: Icons.menu_rounded, onTap: onOpenDrawer),
      ),
      surfaceTintColor: Colors.transparent,
      flexibleSpace: FlexibleSpaceBar(
        centerTitle: false,
        titlePadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        title: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Namaste, Frame Stories', style: TyType.display(24, color: ty.ink)),
            Text('Ready for today\'s celebrations?', style: TyType.sans(12, color: ty.ink3, weight: FontWeight.w600)),
          ],
        ),
      ),
      actions: [
        Padding(
          padding: const EdgeInsets.only(right: 12),
          child: ChromeIconButton(icon: Icons.notifications_none_rounded, onTap: () {}),
        ),
      ],
    );
  }

  Widget _buildBusinessStats(BuildContext context) {
    final ty = context.ty;
    // We want a high-contrast dark card that feels premium and "business".
    // On Dark Theme, ty.paper is dark. On Light Theme, it's light.
    // Let's use a fixed dark background for the business card for better impact.
    final Color cardBg = ty.isDark ? const Color(0xFF2D1F35) : ty.ink;
    final Color textColor = Colors.white;

    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(28),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.25),
            blurRadius: 20,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('MONTHLY EARNINGS', 
                      style: TyType.eyebrow(10, color: textColor.withValues(alpha: 0.6))),
                  const SizedBox(height: 6),
                  Text('₹2,48,500', 
                      style: TyType.display(34, color: textColor)),
                ],
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: ty.leaf.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: ty.leaf.withValues(alpha: 0.3)),
                ),
                child: Row(
                  children: [
                    Icon(Icons.trending_up_rounded, color: ty.leaf, size: 14),
                    const SizedBox(width: 4),
                    Text('+12%', 
                        style: TyType.sans(11, color: ty.leaf, weight: FontWeight.w700)),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),
          Container(
            height: 1,
            color: textColor.withValues(alpha: 0.1),
          ),
          const SizedBox(height: 24),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _miniStat('Active Jobs', '04', ty.saffron, textColor),
              _miniStat('Rating', '4.9 ★', ty.gold, textColor),
              _miniStat('Completed', '128', ty.leaf, textColor),
            ],
          ),
        ],
      ),
    );
  }

  Widget _miniStat(String label, String value, Color accent, Color textColor) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label.toUpperCase(), 
            style: TyType.eyebrow(9, color: textColor.withValues(alpha: 0.5))),
        const SizedBox(height: 6),
        Row(
          children: [
            Container(
              width: 3,
              height: 12,
              decoration: BoxDecoration(
                color: accent,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            const SizedBox(width: 8),
            Text(value, 
                style: TyType.sans(18, color: textColor, weight: FontWeight.w700)),
          ],
        ),
      ],
    );
  }

  Widget _buildRequestsRail(BuildContext context) {
    final ty = context.ty;
    return SizedBox(
      height: 180,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: 3,
        separatorBuilder: (_, __) => const SizedBox(width: 16),
        itemBuilder: (context, i) {
          return Container(
            width: 300,
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: ty.surface,
              borderRadius: BorderRadius.circular(24),
              border: Border.all(color: ty.line),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const TyPill('Birthday', background: Colors.orange, foreground: Colors.white),
                    const Spacer(),
                    Text('Ends in 2h', style: TyType.sans(11, color: ty.rose, weight: FontWeight.w700)),
                  ],
                ),
                const SizedBox(height: 16),
                Text('Diya\'s 1st Birthday', style: TyType.sans(18, color: ty.ink, weight: FontWeight.w700)),
                const SizedBox(height: 4),
                Text('Sat, 14 June · Malviya Nagar, Jaipur', style: TyType.sans(13, color: ty.ink2)),
                const Spacer(),
                Row(
                  children: [
                    Text('₹45,000', style: TyType.display(20, color: ty.ink)),
                    const Spacer(),
                    TyButton('Review', kind: TyButtonKind.soft, padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8), onTap: () {}),
                  ],
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildScheduleList(BuildContext context) {
    final ty = context.ty;
    return Column(
      children: [
        _scheduleRow(context, 'Tomorrow, 10:00 AM', 'Haldi Ceremony', 'Ravi & Sneha', 'Vashali Nagar', 'rose'),
        _scheduleRow(context, 'Sun, 15 June, 6:00 PM', 'Anniversary Dinner', 'Kapoor Family', 'Civil Lines', 'leaf'),
      ],
    );
  }

  Widget _scheduleRow(BuildContext context, String time, String title, String client, String loc, String tint) {
    final ty = context.ty;
    final color = ty.tint(tint);
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: ty.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: ty.line),
      ),
      child: Row(
        children: [
          Container(
            width: 50,
            height: 50,
            decoration: BoxDecoration(
              color: color.withOpacity(0.1),
              borderRadius: BorderRadius.circular(15),
            ),
            child: Icon(Icons.event_available_rounded, color: color, size: 24),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(time, style: TyType.sans(11, color: ty.saffron, weight: FontWeight.w700)),
                const SizedBox(height: 2),
                Text(title, style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
                Text('$client · $loc', style: TyType.sans(13, color: ty.ink2)),
              ],
            ),
          ),
          Icon(Icons.chevron_right_rounded, color: ty.ink3),
        ],
      ),
    );
  }

  Widget _buildPerformanceCard(BuildContext context) {
    final ty = context.ty;
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: ty.surface,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: ty.line),
      ),
      child: Column(
        children: [
          _performanceRow(context, 'Profile Views', '1,284', '+18%'),
          const Divider(height: 32),
          _performanceRow(context, 'Customer Lead Rate', '24%', '+5%'),
          const Divider(height: 32),
          _performanceRow(context, 'Avg Response Time', '14m', '-2m'),
        ],
      ),
    );
  }

  Widget _performanceRow(BuildContext context, String label, String val, String trend) {
    final ty = context.ty;
    final isPos = trend.startsWith('+');
    return Row(
      children: [
        Text(label, style: TyType.sans(14, color: ty.ink2, weight: FontWeight.w600)),
        const Spacer(),
        Text(val, style: TyType.sans(16, color: ty.ink, weight: FontWeight.w800)),
        const SizedBox(width: 12),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: (isPos ? ty.leaf : ty.rose).withOpacity(0.1),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text(trend, style: TyType.sans(11, color: isPos ? ty.leaf : ty.rose, weight: FontWeight.w700)),
        ),
      ],
    );
  }
}
