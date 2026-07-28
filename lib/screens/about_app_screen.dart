import 'package:flutter/material.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../widgets/common.dart';
import '../l10n/generated/app_localizations.dart';

class AboutAppScreen extends StatelessWidget {
  const AboutAppScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: l10n.aboutAppTitle),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
        children: [
          Center(
            child: Column(
              children: [
                const SizedBox(height: 24),
                Image.asset('assets/images/tyohaar-mark.png', width: 100, height: 100),
                const SizedBox(height: 16),
                Text(l10n.aboutAppBrandName, style: TyType.display(32, color: ty.ink)),
                Text(l10n.aboutAppVersionLabel, style: TyType.sans(12, color: ty.ink3)),
              ],
            ),
          ),
          const SizedBox(height: 48),
          Text(l10n.aboutAppMissionHeading, style: TyType.eyebrow(11, color: ty.ink3)),
          const SizedBox(height: 12),
          Text(
            l10n.aboutAppMissionBody,
            style: TyType.sans(15, color: ty.ink2, height: 1.6),
          ),
          const SizedBox(height: 32),
          _item(context, l10n.aboutAppWebsiteLabel, l10n.aboutAppWebsiteValue),
          _item(context, l10n.aboutAppContactEmailLabel, l10n.aboutAppContactEmailValue),
          const SizedBox(height: 48),
          Center(
            child: Text(l10n.aboutAppDesignedByLabel, style: TyType.sans(13, color: ty.ink3)),
          ),
        ],
      ),
    );
  }

  Widget _item(BuildContext context, String label, String value) {
    final ty = context.ty;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w600)),
          Text(value, style: TyType.sans(14, color: ty.saffronDeep, weight: FontWeight.w700)),
        ],
      ),
    );
  }
}
