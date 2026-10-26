import 'package:flutter/material.dart';

import '../l10n/generated/app_localizations.dart';
import '../theme/typography.dart';

/// What a priced line is, in the one word the customer needs:
///
///  * [rental]  — a returnable item; it goes back after the event
///  * [keep]    — the customer keeps it
///  * [service] — a service, not a product
///
/// The same three labels print on the invoice, so what the customer saw while
/// planning is what the bill says.
enum LineKind {
  rental,
  keep,
  service;

  /// API value ("rental" | "keep" | "service"); anything else reads as keep.
  static LineKind parse(String? raw) => switch (raw) {
        'rental' => LineKind.rental,
        'service' => LineKind.service,
        _ => LineKind.keep,
      };

  static LineKind forItem({required bool isReturnable}) => isReturnable ? rental : keep;

  /// Fixed hues, not theme colours: the meaning has to survive light and dark
  /// mode and every theme tint.
  Color get color => switch (this) {
        LineKind.rental => const Color(0xFF2F7A4B),
        LineKind.keep => const Color(0xFF9A6A00),
        LineKind.service => const Color(0xFF2F4F9A),
      };

  String label(AppLocalizations l10n) => switch (this) {
        LineKind.rental => l10n.lineKindRental,
        LineKind.keep => l10n.lineKindKeep,
        LineKind.service => l10n.lineKindService,
      };

  String meaning(AppLocalizations l10n) => switch (this) {
        LineKind.rental => l10n.lineKindRentalMeaning,
        LineKind.keep => l10n.lineKindKeepMeaning,
        LineKind.service => l10n.lineKindServiceMeaning,
      };
}

/// A bold, outlined tag — deliberately loud so nobody has to wonder.
class LineKindBadge extends StatelessWidget {
  final LineKind kind;
  const LineKindBadge(this.kind, {super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final color = kind.color;
    return Semantics(
      label: '${kind.label(l10n)}: ${kind.meaning(l10n)}',
      excludeSemantics: true,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.14),
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: color, width: 1.2),
        ),
        child: Text(
          kind.label(l10n),
          style:
              TyType.sans(10.5, color: color, weight: FontWeight.w800).copyWith(letterSpacing: 0.6),
        ),
      ),
    );
  }
}

/// One line per label in [kinds], each with its meaning in words.
class LineKindLegend extends StatelessWidget {
  final Iterable<LineKind> kinds;
  const LineKindLegend({super.key, this.kinds = LineKind.values});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final ink = DefaultTextStyle.of(context).style.color;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (final k in kinds)
          Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Row(children: [
              SizedBox(
                  width: 74,
                  child: Align(alignment: Alignment.centerLeft, child: LineKindBadge(k))),
              const SizedBox(width: 8),
              Expanded(
                  child: Text(k.meaning(l10n),
                      style: TyType.sans(12, color: ink?.withValues(alpha: 0.75)))),
            ]),
          ),
      ],
    );
  }
}
