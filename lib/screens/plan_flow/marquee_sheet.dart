import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../l10n/generated/app_localizations.dart';
import '../../theme/colors.dart';
import '../../theme/typography.dart';
import '../../utils/currency.dart';
import '../../data/models.dart' show countBillableCharacters;
import 'plan_logic.dart';

/// What a character line accepts. Mirrors the API's character_set.
enum CharSetKind {
  digits,
  letters,
  alphanumeric;

  static CharSetKind parse(String? raw) => switch (raw) {
        'letters' => CharSetKind.letters,
        'alphanumeric' => CharSetKind.alphanumeric,
        _ => CharSetKind.digits,
      };

  bool get allowsLetters => this != CharSetKind.digits;
  bool get allowsDigits => this != CharSetKind.letters;
  bool get allowsSpaces => this != CharSetKind.digits;
}

/// Opens the "Customise your marquee" sheet and resolves to the confirmed
/// text, or null if the customer backed out.
///
/// The customer builds the text from a keypad (or types it), sees each
/// character as a lit marquee piece, and watches the price add up before
/// confirming: [unitPrice] per non-space character, so "25" is two pieces and
/// "ANITA 30" is seven. The server counts and caps the same way.
Future<String?> showMarqueeSheet(
  BuildContext context, {
  required String title,
  String? prompt,
  required double unitPrice,
  required CharSetKind charSet,
  required int maxChars,
  String? initial,
}) {
  return showModalBottomSheet<String>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    showDragHandle: true,
    backgroundColor: context.ty.paper,
    builder: (_) => MarqueeSheet(
      title: title,
      prompt: prompt,
      unitPrice: unitPrice,
      charSet: charSet,
      maxChars: maxChars,
      initial: initial,
    ),
  );
}

class MarqueeSheet extends StatefulWidget {
  final String title;
  final String? prompt;
  final double unitPrice;
  final CharSetKind charSet;
  final int maxChars;
  final String? initial;

  const MarqueeSheet({
    super.key,
    required this.title,
    this.prompt,
    required this.unitPrice,
    required this.charSet,
    required this.maxChars,
    this.initial,
  });

  @override
  State<MarqueeSheet> createState() => _MarqueeSheetState();
}

class _MarqueeSheetState extends State<MarqueeSheet> {
  late final TextEditingController _typed = TextEditingController();
  late final CharacterFormatter _formatter = CharacterFormatter(
    allowLetters: widget.charSet.allowsLetters,
    allowDigits: widget.charSet.allowsDigits,
    allowSpaces: widget.charSet.allowsSpaces,
    maxChars: widget.maxChars,
  );
  String _value = '';

  @override
  void initState() {
    super.initState();
    _set(widget.initial ?? '');
  }

  @override
  void dispose() {
    _typed.dispose();
    super.dispose();
  }

  /// One path for every edit: normalise through the same rules the server
  /// applies, then mirror into the text field.
  void _set(String raw) {
    final cleaned =
        _formatter.formatEditUpdate(TextEditingValue.empty, TextEditingValue(text: raw)).text;
    setState(() => _value = cleaned);
    if (_typed.text != cleaned) {
      _typed.value = TextEditingValue(
          text: cleaned, selection: TextSelection.collapsed(offset: cleaned.length));
    }
  }

  int get _count => countBillableCharacters(_value);
  bool get _atLimit => _count >= widget.maxChars;

  void _append(String ch) {
    if (ch != ' ' && _atLimit) {
      HapticFeedback.lightImpact();
      return;
    }
    _set('$_value$ch');
    HapticFeedback.selectionClick();
  }

  void _removeAt(int index) {
    final chars = _value.split('');
    if (index < 0 || index >= chars.length) return;
    chars.removeAt(index);
    _set(chars.join());
  }

  void _backspace() => _value.isEmpty ? null : _removeAt(_value.length - 1);

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final trimmed = _value.trim();
    final total = widget.unitPrice * _count;

    final subtitle = widget.prompt?.trim().isNotEmpty == true
        ? widget.prompt!.trim()
        : switch (widget.charSet) {
            CharSetKind.digits => l10n.marqueeSubtitleDigits,
            CharSetKind.letters => l10n.marqueeSubtitleLetters,
            CharSetKind.alphanumeric => l10n.marqueeSubtitleAlphanumeric,
          };
    final allowed = switch (widget.charSet) {
      CharSetKind.digits => l10n.marqueeAllowedDigits,
      CharSetKind.letters => l10n.marqueeAllowedLetters,
      CharSetKind.alphanumeric => l10n.marqueeAllowedAlphanumeric,
    };
    final placeholder = switch (widget.charSet) {
      CharSetKind.digits => l10n.marqueePlaceholderDigits,
      CharSetKind.letters => l10n.marqueePlaceholderLetters,
      CharSetKind.alphanumeric => l10n.marqueePlaceholderAlphanumeric,
    };

    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(l10n.marqueeTitle(widget.title), style: TyType.display(22, color: ty.ink)),
            const SizedBox(height: 4),
            Text(subtitle, style: TyType.sans(13.5, color: ty.ink2)),
            const SizedBox(height: 14),

            // ── Preview: each character is one lit piece ─────────────────────
            Text(l10n.marqueePreviewLabel, style: TyType.eyebrow(10.5, color: ty.ink3)),
            const SizedBox(height: 8),
            Container(
              width: double.infinity,
              constraints: const BoxConstraints(minHeight: 84),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFF1C1411),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: ty.line),
              ),
              child: trimmed.isEmpty
                  ? Center(
                      child: Text(l10n.marqueeEmptyPreview,
                          style: TyType.sans(13, color: Colors.white54)))
                  : Wrap(
                      spacing: 6,
                      runSpacing: 8,
                      alignment: WrapAlignment.center,
                      children: [
                        for (var i = 0; i < _value.length; i++)
                          _value[i] == ' '
                              ? const SizedBox(width: 18, height: 54)
                              : _Piece(char: _value[i], onTap: () => _removeAt(i)),
                      ],
                    ),
            ),
            const SizedBox(height: 6),
            Text(
              trimmed.isEmpty ? l10n.marqueeLimit(widget.maxChars) : l10n.marqueeTapToRemove,
              style: TyType.sans(11.5, color: ty.ink3),
            ),

            const SizedBox(height: 16),
            Text(l10n.marqueeSelectHeading,
                style: TyType.sans(15, color: ty.ink, weight: FontWeight.w800)),
            const SizedBox(height: 2),
            Text(allowed, style: TyType.sans(13, color: ty.ink)),
            Text(l10n.marqueeRepeatsHint, style: TyType.sans(12, color: ty.ink3)),
            const SizedBox(height: 10),

            // ── Keypad ───────────────────────────────────────────────────────
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                if (widget.charSet.allowsDigits)
                  for (final d in '0123456789'.split('')) _Key(label: d, onTap: () => _append(d)),
                if (widget.charSet.allowsLetters)
                  for (final c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split(''))
                    _Key(label: c, onTap: () => _append(c)),
                if (widget.charSet.allowsSpaces)
                  _Key(label: l10n.marqueeSpace, wide: true, onTap: () => _append(' ')),
                _Key(
                  icon: Icons.backspace_outlined,
                  semantics: l10n.marqueeBackspace,
                  wide: true,
                  onTap: _value.isEmpty ? null : _backspace,
                ),
              ],
            ),
            const SizedBox(height: 12),

            // ── Or type it ───────────────────────────────────────────────────
            TextField(
              controller: _typed,
              inputFormatters: [_formatter],
              textCapitalization: TextCapitalization.characters,
              autocorrect: false,
              enableSuggestions: false,
              keyboardType: widget.charSet == CharSetKind.digits
                  ? TextInputType.number
                  : TextInputType.visiblePassword,
              style: TyType.sans(16, color: ty.ink, weight: FontWeight.w700),
              decoration: InputDecoration(
                isDense: true,
                filled: true,
                fillColor: ty.surface,
                labelText: l10n.marqueeTypeLabel,
                hintText: placeholder,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
              ),
              onChanged: (v) => setState(() => _value = v),
            ),

            // ── Live price ───────────────────────────────────────────────────
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.fromLTRB(14, 10, 14, 12),
              decoration: BoxDecoration(
                color: ty.surface,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: ty.line),
              ),
              child: Column(children: [
                _line(ty, l10n.marqueeSelectedCount, '$_count', bold: true),
                _line(ty, l10n.marqueePricePerChar, formatRupees(widget.unitPrice)),
                Divider(height: 18, color: ty.line),
                _line(ty, l10n.marqueeTotal, formatRupees(total), accent: true),
              ]),
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              height: 52,
              child: FilledButton(
                style: FilledButton.styleFrom(
                    backgroundColor: ty.saffronDeep, foregroundColor: Colors.white),
                onPressed: _count == 0 ? null : () => Navigator.of(context).pop(_value.trim()),
                child: Text(l10n.marqueeConfirm,
                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
              ),
            ),
            if (_value.isNotEmpty)
              Align(
                alignment: Alignment.center,
                child: TextButton(onPressed: () => _set(''), child: Text(l10n.marqueeClear)),
              ),
          ],
        ),
      ),
    );
  }

  Widget _line(TyColors ty, String label, String value, {bool bold = false, bool accent = false}) =>
      Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          Flexible(
            child: Text(label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TyType.sans(14,
                    color: ty.ink, weight: accent ? FontWeight.w800 : FontWeight.w500)),
          ),
          const SizedBox(width: 8),
          Text(
            value,
            style: TyType.sans(accent ? 20 : 14.5,
                color: accent ? ty.saffronDeep : ty.ink,
                weight: bold || accent ? FontWeight.w800 : FontWeight.w600),
          ),
        ]),
      );
}

/// One lit marquee piece in the preview. Tap to remove it.
class _Piece extends StatelessWidget {
  final String char;
  final VoidCallback onTap;
  const _Piece({required this.char, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: char,
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          width: 38,
          height: 54,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: const Color(0xFF2A1E18),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: const Color(0xFF5A4636)),
          ),
          child: Text(
            char,
            style: const TextStyle(
              fontSize: 28,
              fontWeight: FontWeight.w800,
              color: Color(0xFFFFF4D6),
              shadows: [
                Shadow(color: Color(0xFFFFC857), blurRadius: 14),
                Shadow(color: Color(0xFFFFE9A8), blurRadius: 4)
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _Key extends StatelessWidget {
  final String? label;
  final IconData? icon;
  final String? semantics;
  final bool wide;
  final VoidCallback? onTap;
  const _Key({this.label, this.icon, this.semantics, this.wide = false, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final enabled = onTap != null;
    return Semantics(
      button: true,
      enabled: enabled,
      label: semantics ?? label,
      excludeSemantics: true,
      child: Material(
        color: ty.surface2,
        borderRadius: BorderRadius.circular(10),
        child: InkWell(
          borderRadius: BorderRadius.circular(10),
          onTap: onTap,
          child: Container(
            width: wide ? 78 : 40,
            height: 44,
            alignment: Alignment.center,
            decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(10), border: Border.all(color: ty.line)),
            child: icon != null
                ? Icon(icon, size: 20, color: enabled ? ty.ink : ty.ink3)
                : Text(label!,
                    style: TyType.sans(wide ? 13 : 16, color: ty.ink, weight: FontWeight.w700)),
          ),
        ),
      ),
    );
  }
}
