import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../theme/colors.dart';
import '../../theme/typography.dart';
import 'plan_logic.dart';

/// One colour in the mix, as shown by [BalloonProportionMeter].
class BalloonShare {
  final String label;
  final Color color;
  const BalloonShare(this.label, this.color);
}

/// The whole mix at a glance: one rounded strip, each colour taking its share.
class BalloonMixPreview extends StatelessWidget {
  final List<BalloonShare> colours;
  final List<int> ratios;
  final double height;
  const BalloonMixPreview({super.key, required this.colours, required this.ratios, this.height = 14});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    if (colours.isEmpty || ratios.length != colours.length) return const SizedBox.shrink();
    return ExcludeSemantics(
      child: Container(
        height: height,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(height),
          border: Border.all(color: ty.line),
        ),
        clipBehavior: Clip.antiAlias,
        child: Row(children: [
          for (var i = 0; i < colours.length; i++)
            Expanded(flex: ratios[i].clamp(1, 100), child: ColoredBox(color: colours[i].color)),
        ]),
      ),
    );
  }
}

/// A horizontal, rounded "volume bar" for one colour's share of the mix.
///
/// Drag along it or tap anywhere on it to set the percentage; it fills with
/// the balloon colour up to that point. [onChanged] null means the bar is the
/// automatic remainder (the last colour): it shows its share but can't be moved.
class BalloonProportionMeter extends StatelessWidget {
  final BalloonShare colour;
  final int percent;
  final int max;
  final ValueChanged<int>? onChanged;
  final String autoLabel;

  const BalloonProportionMeter({
    super.key,
    required this.colour,
    required this.percent,
    required this.max,
    required this.onChanged,
    this.autoLabel = 'auto',
  });

  bool get _adjustable => onChanged != null;

  void _setFromDx(double dx, double width) {
    if (!_adjustable || width <= 0) return;
    final value = (dx / width * 100).round();
    if (value != percent) {
      onChanged!(value);
    }
  }

  void _nudge(int delta) {
    if (!_adjustable) return;
    HapticFeedback.selectionClick();
    onChanged!(percent + delta);
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    // Pale balloons (white, silver, pastel) would vanish into the track, so
    // their fill gets an outline.
    final pale = colour.color.computeLuminance() > 0.75;

    return Semantics(
      label: colour.label,
      value: '$percent%',
      slider: _adjustable,
      readOnly: !_adjustable,
      increasedValue: _adjustable ? '${(percent + kBalloonRatioStep).clamp(kBalloonRatioMin, max)}%' : null,
      decreasedValue: _adjustable ? '${(percent - kBalloonRatioStep).clamp(kBalloonRatioMin, max)}%' : null,
      onIncrease: _adjustable ? () => _nudge(kBalloonRatioStep) : null,
      onDecrease: _adjustable ? () => _nudge(-kBalloonRatioStep) : null,
      excludeSemantics: true,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Container(
                width: 14,
                height: 14,
                decoration: BoxDecoration(
                  color: colour.color,
                  shape: BoxShape.circle,
                  border: Border.all(color: ty.line),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(colour.label,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TyType.sans(13.5, color: ty.ink, weight: FontWeight.w600)),
              ),
              if (!_adjustable)
                Container(
                  margin: const EdgeInsets.only(right: 8),
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(color: ty.surface2, borderRadius: BorderRadius.circular(999)),
                  child: Text(autoLabel, style: TyType.sans(11, color: ty.ink3, weight: FontWeight.w600)),
                ),
              Text('$percent%', style: TyType.sans(15, color: ty.ink, weight: FontWeight.w800)),
            ]),
            const SizedBox(height: 8),
            LayoutBuilder(builder: (context, box) {
              final width = box.maxWidth;
              const height = 30.0;
              final fill = (width * percent / 100).clamp(height, width);
              return GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTapDown: _adjustable ? (d) => _setFromDx(d.localPosition.dx, width) : null,
                onHorizontalDragUpdate: _adjustable ? (d) => _setFromDx(d.localPosition.dx, width) : null,
                child: SizedBox(
                  height: height,
                  child: Stack(children: [
                    // Track.
                    Container(
                      decoration: BoxDecoration(
                        color: ty.surface2,
                        borderRadius: BorderRadius.circular(height),
                        border: Border.all(color: ty.line),
                      ),
                    ),
                    // Fill, in the balloon colour.
                    AnimatedContainer(
                      duration: const Duration(milliseconds: 120),
                      curve: Curves.easeOut,
                      width: fill,
                      decoration: BoxDecoration(
                        color: colour.color.withValues(alpha: _adjustable ? 1 : 0.75),
                        borderRadius: BorderRadius.circular(height),
                        border: pale ? Border.all(color: ty.ink3.withValues(alpha: 0.5)) : null,
                      ),
                    ),
                    // Thumb at the end of the fill.
                    if (_adjustable)
                      AnimatedPositioned(
                        duration: const Duration(milliseconds: 120),
                        curve: Curves.easeOut,
                        left: fill - height + 3,
                        top: 3,
                        child: Container(
                          width: height - 6,
                          height: height - 6,
                          decoration: BoxDecoration(
                            color: Colors.white,
                            shape: BoxShape.circle,
                            boxShadow: const [BoxShadow(color: Color(0x40000000), blurRadius: 4, offset: Offset(0, 1))],
                            border: Border.all(color: ty.line),
                          ),
                        ),
                      ),
                  ]),
                ),
              );
            }),
          ],
        ),
      ),
    );
  }
}
