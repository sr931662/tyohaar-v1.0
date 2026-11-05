import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../l10n/generated/app_localizations.dart';
import '../theme/responsive.dart';
import '../theme/theme.dart';
import '../theme/typography.dart';
import 'event_ui.dart';

/// The band behind the shell's floating header: the dark theme's page colour, so
/// the card sits straight on the page there. In the light theme it ends just
/// below the card, because the header's white text needs something dark behind it.
const Color _band = Color(0xFF2B0A14);
const Color _cardTop = Color(0xFF571326);
const Color _cardBottom = Color(0xFF320A17);

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
    final radius = BorderRadius.circular(resp.w(22));
    final features = [
      (Icons.send_outlined, l10n.evHeroFeatureSend),
      (Icons.groups_outlined, l10n.evHeroFeatureRsvp),
      (Icons.room_service_outlined, l10n.evHeroFeatureFood),
      (Icons.bar_chart_rounded, l10n.evHeroFeatureUpdates),
    ];

    final widestLabel = features.map((f) => f.$2).reduce((a, b) => a.length >= b.length ? a : b);

    // The status bar and floating header sit over the band, so the icons stay
    // white and the card starts below them.
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: tyOverlayOverImage,
      child: Container(
        padding: EdgeInsets.fromLTRB(resp.w(14), topInset + resp.h(76), resp.w(14), resp.h(14)),
        decoration: BoxDecoration(
          color: _band,
          borderRadius: BorderRadius.vertical(bottom: Radius.circular(resp.w(28))),
        ),
        // Generous, not unlimited: the tiles have little room to grow.
        child: MediaQuery.withClampedTextScaling(
          maxScaleFactor: 1.15,
          child: Container(
            clipBehavior: Clip.antiAlias,
            decoration: BoxDecoration(
              borderRadius: radius,
              border: Border.all(color: kInvitationGold.withValues(alpha: 0.5)),
              gradient: const LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [_cardTop, _cardBottom],
              ),
            ),
            // The text takes the left 60% and the artwork the rest, so neither
            // ever runs under the other, on any phone width.
            child: LayoutBuilder(builder: (context, box) {
              return Stack(children: [
                Positioned(
                  top: 0,
                  bottom: 0,
                  right: 0,
                  width: box.maxWidth * 0.41,
                  child: const ExcludeSemantics(child: CustomPaint(painter: _InvitationArtPainter())),
                ),
                Padding(
                  padding: EdgeInsets.fromLTRB(resp.w(14), resp.h(14), 0, resp.h(16)),
                  child: SizedBox(
                    width: box.maxWidth * 0.6 - resp.w(14),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                      _Eyebrow(label: l10n.evHeroEyebrow),
                      SizedBox(height: resp.h(10)),
                      Text(l10n.evHeroHeading, style: TyType.display(resp.sp(21), color: Colors.white, height: 1.14)),
                      SizedBox(height: resp.h(7)),
                      Text(l10n.evHeroBody,
                          style: TyType.sans(resp.sp(11.5), color: Colors.white.withValues(alpha: 0.86), height: 1.38)),
                      SizedBox(height: resp.h(11)),
                      IntrinsicHeight(
                        child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                          for (var i = 0; i < features.length; i++) ...[
                            if (i > 0) SizedBox(width: resp.w(4)),
                            Expanded(child: _FeatureTile(icon: features[i].$1, label: features[i].$2, sizedLike: widestLabel)),
                          ],
                        ]),
                      ),
                      SizedBox(height: resp.h(13)),
                      _ManageButton(label: l10n.evHeroCta, onTap: onExplore),
                    ]),
                  ),
                ),
              ]);
            }),
          ),
        ),
      ),
    );
  }
}

class _Eyebrow extends StatelessWidget {
  final String label;
  const _Eyebrow({required this.label});

  @override
  Widget build(BuildContext context) {
    final resp = context.resp;
    return Container(
      padding: EdgeInsets.symmetric(horizontal: resp.w(9), vertical: resp.h(4)),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(99),
        border: Border.all(color: kInvitationGold.withValues(alpha: 0.6)),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(Icons.mail_outline_rounded, size: resp.sp(12), color: kInvitationGold),
        SizedBox(width: resp.w(5)),
        Flexible(
          child: FittedBox(
            fit: BoxFit.scaleDown,
            child: Text(label, maxLines: 1, style: TyType.eyebrow(resp.sp(8.5), color: kInvitationGold)),
          ),
        ),
      ]),
    );
  }
}

class _FeatureTile extends StatelessWidget {
  final IconData icon;
  final String label;

  /// The longest label in the row. Every tile fits this rather than its own
  /// text, so all four shrink by the same amount and stay the same size.
  final String sizedLike;
  const _FeatureTile({required this.icon, required this.label, required this.sizedLike});

  @override
  Widget build(BuildContext context) {
    final resp = context.resp;
    final style = TyType.sans(resp.sp(9), color: Colors.white, weight: FontWeight.w600, height: 1.2);
    return Container(
      padding: EdgeInsets.symmetric(horizontal: resp.w(2), vertical: resp.h(7)),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.07),
        borderRadius: BorderRadius.circular(resp.w(10)),
        border: Border.all(color: kInvitationGold.withValues(alpha: 0.22)),
      ),
      child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
        Icon(icon, size: resp.sp(17), color: kInvitationGold),
        SizedBox(height: resp.h(4)),
        FittedBox(
          fit: BoxFit.scaleDown,
          child: Stack(alignment: Alignment.center, children: [
            Visibility(
              visible: false,
              maintainSize: true,
              maintainAnimation: true,
              maintainState: true,
              child: Text(sizedLike, textAlign: TextAlign.center, maxLines: 2, style: style),
            ),
            Text(label, textAlign: TextAlign.center, maxLines: 2, style: style),
          ]),
        ),
      ]),
    );
  }
}

class _ManageButton extends StatelessWidget {
  final String label;
  final VoidCallback onTap;
  const _ManageButton({required this.label, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final resp = context.resp;
    final radius = BorderRadius.circular(14);
    return Semantics(
      button: true,
      child: DecoratedBox(
        decoration: BoxDecoration(
          borderRadius: radius,
          gradient: const LinearGradient(colors: [Color(0xFFEFCB84), Color(0xFFD3A24E)]),
        ),
        // Its own Material: ink on the card's would be painted behind the gradient.
        child: Material(
          type: MaterialType.transparency,
          child: InkWell(
            borderRadius: radius,
            onTap: onTap,
            child: Container(
              constraints: const BoxConstraints(minHeight: 46),
              padding: EdgeInsets.symmetric(horizontal: resp.w(13)),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                Flexible(
                  child: Text(label,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TyType.sans(resp.sp(13), color: const Color(0xFF3A0C1A), weight: FontWeight.w800)),
                ),
                SizedBox(width: resp.w(6)),
                Icon(Icons.arrow_forward_rounded, size: resp.sp(16), color: const Color(0xFF3A0C1A)),
              ]),
            ),
          ),
        ),
      ),
    );
  }
}

/// An envelope, a cream card with a gold floral and a wax seal, ribbon and
/// flowers. Painted rather than a bitmap so it is sharp at any size and adds
/// nothing to the app's download.
class _InvitationArtPainter extends CustomPainter {
  const _InvitationArtPainter();

  static const _cream = Color(0xFFF6EAD4);
  static const _creamShade = Color(0xFFE6D2AE);
  static const _gold = Color(0xFFC89A4B);
  static const _goldLight = Color(0xFFEBCB8C);
  static const _wine = Color(0xFF7C1830);
  static const _wineDeep = Color(0xFF5A0F22);
  static const _petal = Color(0xFFFBF3E2);
  static const _leaf = Color(0xFF8C7A45);

  @override
  void paint(Canvas canvas, Size size) {
    // Drawn on a 180 x 250 sheet, anchored to the card's right edge and centred
    // vertically, so a taller card just gets more background around it.
    final scale = math.min(size.width / 180, size.height / 250);
    canvas.translate(size.width - 180 * scale, (size.height - 250 * scale) / 2);
    canvas.scale(scale);
    _envelope(canvas);
    _sprig(canvas, const Offset(150, 34), flip: false);
    _card(canvas);
    _ribbon(canvas);
    _flower(canvas, const Offset(148, 214), 21);
    _flower(canvas, const Offset(120, 233), 14);
    _flower(canvas, const Offset(172, 186), 13);
    _leafAt(canvas, const Offset(100, 226), 2.9, 18);
    _leafAt(canvas, const Offset(168, 232), 0.5, 18);
    _flower(canvas, const Offset(161, 28), 12);
    _flower(canvas, const Offset(174, 54), 9);
  }

  void _envelope(Canvas canvas) {
    canvas.save();
    canvas.translate(102, 86);
    canvas.rotate(0.22);
    final body = RRect.fromRectAndRadius(const Rect.fromLTWH(-74, -52, 148, 104), const Radius.circular(5));
    canvas.drawRRect(
      body.shift(const Offset(-3, 5)),
      Paint()
        ..color = Colors.black.withValues(alpha: 0.35)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 7),
    );
    canvas.drawRRect(
      body,
      Paint()
        ..shader = const LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: [_wine, _wineDeep])
            .createShader(body.outerRect),
    );
    final flap = Path()
      ..moveTo(-74, -50)
      ..lineTo(0, 10)
      ..lineTo(74, -50)
      ..close();
    canvas.drawPath(flap, Paint()..color = const Color(0xFF8A1E38));
    canvas.drawPath(
      flap,
      Paint()
        ..color = Colors.black.withValues(alpha: 0.18)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1,
    );
    canvas.restore();
  }

  void _card(Canvas canvas) {
    canvas.save();
    canvas.translate(92, 132);
    canvas.rotate(-0.13);
    final rect = RRect.fromRectAndRadius(const Rect.fromLTWH(-56, -76, 112, 152), const Radius.circular(4));
    canvas.drawRRect(
      rect.shift(const Offset(-3, 5)),
      Paint()
        ..color = Colors.black.withValues(alpha: 0.4)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 8),
    );
    canvas.drawRRect(
      rect,
      Paint()
        ..shader = const LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: [_cream, _creamShade])
            .createShader(rect.outerRect),
    );
    canvas.drawRRect(
      rect.deflate(5),
      Paint()
        ..color = _gold.withValues(alpha: 0.75)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 0.7,
    );
    // A mirrored gold floral, above and below the seal.
    for (final side in [-1.0, 1.0]) {
      canvas.save();
      canvas.scale(side, 1);
      _vine(canvas, top: true);
      _vine(canvas, top: false);
      canvas.restore();
    }
    _bloom(canvas, const Offset(0, -46), 8);
    _bloom(canvas, const Offset(0, 50), 7);
    _seal(canvas);
    canvas.restore();
  }

  void _vine(Canvas canvas, {required bool top}) {
    final y = top ? -1.0 : 1.0;
    final stroke = Paint()
      ..color = _gold
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1
      ..strokeCap = StrokeCap.round;
    final stem = Path()
      ..moveTo(3, 48 * y)
      ..cubicTo(14, 58 * y, 30, 52 * y, 38, 34 * y);
    canvas.drawPath(stem, stroke);
    final curl = Path()
      ..moveTo(14, 54 * y)
      ..cubicTo(24, 44 * y, 16, 34 * y, 8, 36 * y);
    canvas.drawPath(curl, stroke);
    for (final (o, a) in [(Offset(24, 53 * y), 0.5), (Offset(34, 42 * y), 1.1), (Offset(39, 31 * y), 1.6), (Offset(9, 36 * y), 3.0)]) {
      _goldLeaf(canvas, o, a * y);
    }
  }

  void _goldLeaf(Canvas canvas, Offset at, double angle) {
    canvas.save();
    canvas.translate(at.dx, at.dy);
    canvas.rotate(angle);
    canvas.drawOval(const Rect.fromLTWH(-1.8, -4.5, 3.6, 9), Paint()..color = _gold);
    canvas.restore();
  }

  void _bloom(Canvas canvas, Offset at, double r) {
    final petal = Paint()..color = _gold;
    for (var i = 0; i < 6; i++) {
      canvas.save();
      canvas.translate(at.dx, at.dy);
      canvas.rotate(i * math.pi / 3);
      canvas.drawOval(Rect.fromCenter(center: Offset(0, -r * 0.62), width: r * 0.62, height: r * 0.95), petal);
      canvas.restore();
    }
    canvas.drawCircle(at, r * 0.3, Paint()..color = _cream);
  }

  void _seal(Canvas canvas) {
    const r = 18.0;
    final blob = Path();
    for (var i = 0; i <= 28; i++) {
      final angle = i / 28 * 2 * math.pi;
      final wobble = r + 1.7 * math.sin(angle * 5) + 1.0 * math.cos(angle * 3);
      final p = Offset(math.cos(angle) * wobble, math.sin(angle) * wobble);
      i == 0 ? blob.moveTo(p.dx, p.dy) : blob.lineTo(p.dx, p.dy);
    }
    blob.close();
    canvas.drawPath(
      blob.shift(const Offset(-1, 2)),
      Paint()
        ..color = Colors.black.withValues(alpha: 0.4)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 3),
    );
    canvas.drawPath(
      blob,
      Paint()
        ..shader = const RadialGradient(center: Alignment(-0.3, -0.4), colors: [Color(0xFFA72D49), _wineDeep])
            .createShader(Rect.fromCircle(center: Offset.zero, radius: r + 3)),
    );
    canvas.drawCircle(
      Offset.zero,
      r - 4.5,
      Paint()
        ..color = const Color(0xFF4F0C1D).withValues(alpha: 0.75)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1,
    );
    final letter = TextPainter(
      text: TextSpan(
        text: 'T',
        style: TextStyle(
          color: _goldLight,
          fontSize: 17,
          fontFamily: TyType.display(17).fontFamily,
          fontWeight: FontWeight.w400,
        ),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    letter.paint(canvas, Offset(-letter.width / 2, -letter.height / 2));
  }

  void _ribbon(Canvas canvas) {
    final band = Path()
      ..moveTo(26, 214)
      ..cubicTo(52, 190, 84, 226, 112, 208)
      ..cubicTo(128, 198, 146, 200, 160, 210)
      ..cubicTo(146, 208, 130, 208, 116, 217)
      ..cubicTo(86, 236, 56, 202, 32, 222)
      ..close();
    canvas.drawPath(
      band,
      Paint()
        ..shader = const LinearGradient(colors: [_gold, _goldLight, _gold]).createShader(const Rect.fromLTWH(26, 190, 134, 46)),
    );
    final tail = Path()
      ..moveTo(70, 214)
      ..cubicTo(62, 232, 74, 238, 92, 243)
      ..lineTo(86, 248)
      ..cubicTo(62, 244, 50, 232, 62, 210)
      ..close();
    canvas.drawPath(tail, Paint()..color = _gold);
  }

  void _flower(Canvas canvas, Offset at, double r) {
    canvas.drawCircle(
      at.translate(-1, 3),
      r,
      Paint()
        ..color = Colors.black.withValues(alpha: 0.28)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 5),
    );
    // Rings of overlapping petals, darkening inward like a garden rose.
    for (final (ring, count, reach, tone) in [
      (0, 7, 0.62, _petal),
      (1, 6, 0.4, const Color(0xFFF3E3C6)),
      (2, 5, 0.22, const Color(0xFFE5CD9F)),
    ]) {
      for (var i = 0; i < count; i++) {
        canvas.save();
        canvas.translate(at.dx, at.dy);
        canvas.rotate(i * 2 * math.pi / count + ring * 0.5);
        final oval = Rect.fromCenter(center: Offset(0, -r * reach), width: r * (0.95 - ring * 0.15), height: r * (0.85 - ring * 0.1));
        canvas.drawOval(oval, Paint()..color = tone);
        canvas.drawOval(
          oval,
          Paint()
            ..color = const Color(0xFFB9975E).withValues(alpha: 0.5)
            ..style = PaintingStyle.stroke
            ..strokeWidth = 0.5,
        );
        canvas.restore();
      }
    }
    canvas.drawCircle(at, r * 0.13, Paint()..color = _gold);
  }

  void _leafAt(Canvas canvas, Offset at, double angle, double length) {
    canvas.save();
    canvas.translate(at.dx, at.dy);
    canvas.rotate(angle);
    final leaf = Path()
      ..moveTo(0, 0)
      ..quadraticBezierTo(length * 0.5, -length * 0.32, length, 0)
      ..quadraticBezierTo(length * 0.5, length * 0.32, 0, 0);
    canvas.drawPath(leaf, Paint()..color = _leaf);
    canvas.restore();
  }

  void _sprig(Canvas canvas, Offset at, {required bool flip}) {
    final stem = Paint()
      ..color = _leaf
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;
    canvas.drawLine(at.translate(-26, -22), at.translate(16, 28), stem);
    for (var i = 0; i < 4; i++) {
      final along = at.translate(-20.0 + i * 11, -15.0 + i * 13);
      _leafAt(canvas, along, -0.6, 10);
      _leafAt(canvas, along, 2.2, 9);
    }
  }

  @override
  bool shouldRepaint(_InvitationArtPainter oldDelegate) => false;
}
