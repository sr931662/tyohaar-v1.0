import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../l10n/generated/app_localizations.dart';
import '../theme/responsive.dart';
import '../theme/theme.dart';
import '../theme/typography.dart';
import 'event_ui.dart';

/// The Home screen's opening: what Invitation Management is, and the way in.
/// Burgundy and gold in both themes, like a card from an invitation box.
class InvitationHero extends StatelessWidget {
  final VoidCallback onExplore;
  const InvitationHero({super.key, required this.onExplore});

  @override
  Widget build(BuildContext context) {
    final resp = context.resp;
    final l10n = AppLocalizations.of(context)!;
    final topInset = MediaQuery.of(context).padding.top;
    final features = [
      (Icons.style_outlined, l10n.evHeroFeatureCreate),
      (Icons.send_outlined, l10n.evHeroFeatureShare),
      (Icons.how_to_reg_outlined, l10n.evHeroFeatureRsvp),
      (Icons.restaurant_outlined, l10n.evHeroFeatureFood),
      (Icons.campaign_outlined, l10n.evHeroFeatureUpdates),
    ];
    // The status bar and the shell's floating header sit over this, so the
    // icons stay white and the content starts below them.
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: tyOverlayOverImage,
      child: Container(
        padding: EdgeInsets.fromLTRB(resp.w(22), topInset + resp.h(92), resp.w(22), resp.h(26)),
        decoration: BoxDecoration(
          color: kInvitationBurgundy,
          borderRadius: BorderRadius.vertical(bottom: Radius.circular(resp.w(32))),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(l10n.evHeroEyebrow, style: TyType.eyebrow(resp.sp(11), color: kInvitationGold)),
          SizedBox(height: resp.h(10)),
          Text(l10n.evHeroHeading, style: TyType.display(resp.sp(31), color: Colors.white)),
          SizedBox(height: resp.h(8)),
          Text(l10n.evHeroBody,
              style: TyType.sans(resp.sp(14), color: Colors.white.withValues(alpha: 0.86), height: 1.45)),
          SizedBox(height: resp.h(16)),
          Wrap(
            spacing: resp.w(8),
            runSpacing: resp.h(8),
            children: [
              for (final (icon, label) in features)
                Container(
                  padding: EdgeInsets.symmetric(horizontal: resp.w(10), vertical: resp.h(6)),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(99),
                    border: Border.all(color: kInvitationGold.withValues(alpha: 0.45)),
                  ),
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    Icon(icon, size: resp.sp(13), color: kInvitationGold),
                    SizedBox(width: resp.w(5)),
                    Flexible(child: Text(label, maxLines: 1, overflow: TextOverflow.ellipsis, style: TyType.sans(resp.sp(12), color: Colors.white, weight: FontWeight.w600))),
                  ]),
                ),
            ],
          ),
          SizedBox(height: resp.h(18)),
          Semantics(
            button: true,
            child: Material(
              color: kInvitationGold,
              borderRadius: BorderRadius.circular(14),
              child: InkWell(
                borderRadius: BorderRadius.circular(14),
                onTap: onExplore,
                child: Container(
                  constraints: const BoxConstraints(minHeight: 50),
                  width: double.infinity,
                  alignment: Alignment.center,
                  child: Text(l10n.evHeroCta,
                      style: TyType.sans(resp.sp(15), color: kInvitationBurgundy, weight: FontWeight.w800)),
                ),
              ),
            ),
          ),
          SizedBox(height: resp.h(10)),
          Text(l10n.evHeroNote,
              textAlign: TextAlign.center,
              style: TyType.sans(resp.sp(12), color: Colors.white.withValues(alpha: 0.72), height: 1.35)),
        ]),
      ),
    );
  }
}
