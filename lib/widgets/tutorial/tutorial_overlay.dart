import 'package:flutter/material.dart';

import '../../data/tutorial_manager.dart';
import '../../theme/colors.dart';
import '../../theme/typography.dart';

/// One step in a per-screen tutorial: a widget to spotlight plus copy
/// explaining it. [targetKey] must belong to a widget already in the tree
/// by the time [TutorialOverlay.show] runs (a post-frame callback).
class TutorialStep {
  final GlobalKey targetKey;
  final String title;
  final String description;

  const TutorialStep({
    required this.targetKey,
    required this.title,
    required this.description,
  });
}

class TutorialOverlay {
  /// Shows a sequential coachmark walkthrough for [screenKey] if this
  /// account hasn't seen it before. Safe to call from every visit to the
  /// screen — it's a no-op once TutorialManager has recorded it as seen.
  static Future<void> show(
    BuildContext context, {
    required String screenKey,
    required List<TutorialStep> steps,
  }) async {
    if (steps.isEmpty) return;
    final shouldShow = await TutorialManager.instance.shouldShow(screenKey);
    if (!shouldShow || !context.mounted) return;

    late OverlayEntry entry;
    entry = OverlayEntry(
      builder: (overlayContext) => _TutorialOverlayWidget(
        steps: steps,
        onFinished: () {
          entry.remove();
          TutorialManager.instance.markSeen(screenKey);
        },
      ),
    );
    Overlay.of(context, rootOverlay: true).insert(entry);
  }
}

class _TutorialOverlayWidget extends StatefulWidget {
  final List<TutorialStep> steps;
  final VoidCallback onFinished;

  const _TutorialOverlayWidget({required this.steps, required this.onFinished});

  @override
  State<_TutorialOverlayWidget> createState() => _TutorialOverlayWidgetState();
}

class _TutorialOverlayWidgetState extends State<_TutorialOverlayWidget> {
  int _index = 0;

  Rect? _targetRect() {
    final key = widget.steps[_index].targetKey;
    final renderObject = key.currentContext?.findRenderObject();
    if (renderObject is! RenderBox || !renderObject.attached) return null;
    final topLeft = renderObject.localToGlobal(Offset.zero);
    return topLeft & renderObject.size;
  }

  void _next() {
    if (_index >= widget.steps.length - 1) {
      widget.onFinished();
    } else {
      setState(() => _index++);
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final step = widget.steps[_index];
    final rect = _targetRect();
    final screenSize = MediaQuery.of(context).size;

    return Positioned.fill(
      child: Material(
        color: Colors.transparent,
        child: Stack(
          children: [
            GestureDetector(
              onTap: _next,
              child: CustomPaint(
                size: screenSize,
                painter: _SpotlightPainter(rect: rect),
              ),
            ),
            if (rect != null) _buildTooltip(context, ty, rect, screenSize, step),
            Positioned(
              top: MediaQuery.of(context).padding.top + 12,
              right: 16,
              child: TextButton(
                onPressed: widget.onFinished,
                style: TextButton.styleFrom(
                  backgroundColor: Colors.black.withValues(alpha: 0.35),
                  foregroundColor: Colors.white,
                ),
                child: const Text('Skip'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTooltip(BuildContext context, TyColors ty, Rect rect, Size screenSize, TutorialStep step) {
    final belowSpace = screenSize.height - rect.bottom;
    final showBelow = belowSpace > 180 || rect.top < 180;
    final top = showBelow ? rect.bottom + 16 : null;
    final bottom = showBelow ? null : (screenSize.height - rect.top + 16);

    return Positioned(
      left: 20,
      right: 20,
      top: top,
      bottom: bottom,
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: ty.surface,
          borderRadius: BorderRadius.circular(20),
          boxShadow: const [BoxShadow(color: Colors.black26, blurRadius: 20, offset: Offset(0, 8))],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(step.title, style: TyType.display(17, color: ty.ink)),
            const SizedBox(height: 8),
            Text(step.description, style: TyType.sans(13.5, color: ty.ink2, height: 1.5)),
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  '${_index + 1} / ${widget.steps.length}',
                  style: TyType.sans(12, color: ty.ink3, weight: FontWeight.w600),
                ),
                TextButton(
                  onPressed: _next,
                  child: Text(
                    _index >= widget.steps.length - 1 ? 'Got it' : 'Next',
                    style: TyType.sans(14, color: ty.saffron, weight: FontWeight.w700),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _SpotlightPainter extends CustomPainter {
  final Rect? rect;

  _SpotlightPainter({required this.rect});

  @override
  void paint(Canvas canvas, Size size) {
    final scrimPaint = Paint()..color = Colors.black.withValues(alpha: 0.65);
    final fullPath = Path()..addRect(Rect.fromLTWH(0, 0, size.width, size.height));

    if (rect == null) {
      canvas.drawPath(fullPath, scrimPaint);
      return;
    }

    final spotlightRect = rect!.inflate(8);
    final holePath = Path()
      ..addRRect(RRect.fromRectAndRadius(spotlightRect, const Radius.circular(16)));
    final combined = Path.combine(PathOperation.difference, fullPath, holePath);
    canvas.drawPath(combined, scrimPaint);

    final borderPaint = Paint()
      ..color = Colors.white
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2;
    canvas.drawRRect(
      RRect.fromRectAndRadius(spotlightRect, const Radius.circular(16)),
      borderPaint,
    );
  }

  @override
  bool shouldRepaint(covariant _SpotlightPainter oldDelegate) => oldDelegate.rect != rect;
}
