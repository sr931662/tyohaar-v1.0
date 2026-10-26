import 'dart:math' as math;
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../theme/colors.dart';

/// Which visual language the bottom navigation speaks.
///
/// The shells (customer [RootNav], vendor [VendorRootNav]) own the selected
/// index, auth gating and routing; this only decides how the dock *looks*.
enum TyNavStyle {
  /// Floating, frosted-glass capsule — Apple platforms.
  glass,

  /// Solid, edge-attached Material 3 bar — Android and everything else.
  material,
}

/// Resolves the nav style from the theme's platform, which defaults to the
/// device's [defaultTargetPlatform] and can be overridden in tests.
TyNavStyle tyNavStyleOf(BuildContext context) {
  switch (Theme.of(context).platform) {
    case TargetPlatform.iOS:
    case TargetPlatform.macOS:
      return TyNavStyle.glass;
    default:
      return TyNavStyle.material;
  }
}

/// One slot in the dock. Each platform gets its own icon family — SF-style
/// glyphs on iOS, Material Symbols on Android — so neither looks borrowed.
@immutable
class TyNavDestination {
  final String label;
  final IconData icon;
  final IconData activeIcon;
  final IconData? cupertinoIcon;
  final IconData? cupertinoActiveIcon;

  const TyNavDestination({
    required this.label,
    required this.icon,
    required this.activeIcon,
    this.cupertinoIcon,
    this.cupertinoActiveIcon,
  });
}

/// The app's bottom navigation, rendered natively per platform.
///
/// [selectedIndex] is a dock position, not a page index: a slot that opens a
/// pushed screen (e.g. Invitations) is never selected, and `null` means no
/// slot is active (a drawer-only destination is showing).
///
/// Use it as a [Scaffold.bottomNavigationBar]. With `extendBody: true` the
/// Scaffold adds the bar's full height to the body's
/// `MediaQuery.padding.bottom`, which every tab already pads its scroll view
/// by — so content scrolls behind the glass but never ends up hidden under it.
class TyAdaptiveNavBar extends StatelessWidget {
  final List<TyNavDestination> destinations;
  final int? selectedIndex;
  final ValueChanged<int> onDestinationSelected;

  /// Forces a style; resolved from the platform when null.
  final TyNavStyle? style;

  const TyAdaptiveNavBar({
    super.key,
    required this.destinations,
    required this.selectedIndex,
    required this.onDestinationSelected,
    this.style,
  });

  @override
  Widget build(BuildContext context) {
    switch (style ?? tyNavStyleOf(context)) {
      case TyNavStyle.glass:
        return _GlassNavBar(
          destinations: destinations,
          selectedIndex: selectedIndex,
          onSelected: onDestinationSelected,
        );
      case TyNavStyle.material:
        return _MaterialNavBar(
          destinations: destinations,
          selectedIndex: selectedIndex,
          onSelected: onDestinationSelected,
        );
    }
  }
}

// ─── iOS: glass capsule ─────────────────────────────────────────────────────

class _GlassNavBar extends StatelessWidget {
  final List<TyNavDestination> destinations;
  final int? selectedIndex;
  final ValueChanged<int> onSelected;

  const _GlassNavBar({
    required this.destinations,
    required this.selectedIndex,
    required this.onSelected,
  });

  static const double _height = 66;
  static const double _lensInset = 6;

  /// Blur then lift saturation: the content behind a Liquid Glass surface
  /// looks richer, not just softened.
  static final ImageFilter _backdrop = ImageFilter.compose(
    outer: const ColorFilter.matrix(<double>[
      1.18, -0.09, -0.09, 0, 0, //
      -0.09, 1.18, -0.09, 0, 0, //
      -0.09, -0.09, 1.18, 0, 0, //
      0, 0, 0, 1, 0,
    ]),
    inner: ImageFilter.blur(sigmaX: 18, sigmaY: 18, tileMode: TileMode.mirror),
  );

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    // viewPadding (not padding) so the capsule keeps its seat while the
    // keyboard is up. It floats just above the home indicator.
    final homeIndicator = MediaQuery.viewPaddingOf(context).bottom;
    final bottomGap = homeIndicator > 0 ? math.max(homeIndicator - 10, 10.0) : 14.0;
    final radius = BorderRadius.circular(_height / 2);

    // Liquid Glass is far more transparent than frosted glass: a thin tint
    // only, so the page shows through and the rim does the defining.
    final tint =
        ty.isDark ? Colors.white.withValues(alpha: 0.07) : Colors.white.withValues(alpha: 0.34);

    return Padding(
      padding: EdgeInsets.fromLTRB(16, 0, 16, bottomGap),
      child: Align(
        alignment: Alignment.bottomCenter,
        heightFactor: 1,
        child: ConstrainedBox(
          // Stays a compact capsule on iPad instead of stretching edge to edge.
          constraints: const BoxConstraints(maxWidth: 480),
          child: DecoratedBox(
            decoration: BoxDecoration(
              borderRadius: radius,
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: ty.isDark ? 0.34 : 0.14),
                  blurRadius: 28,
                  spreadRadius: -4,
                  offset: const Offset(0, 12),
                ),
              ],
            ),
            child: ClipRRect(
              borderRadius: radius,
              child: BackdropFilter(
                filter: _backdrop,
                child: CustomPaint(
                  foregroundPainter: _GlassRimPainter(radius: _height / 2, dark: ty.isDark),
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      color: tint,
                      borderRadius: radius,
                      // Light pooling at the top, falling away: the glass's
                      // curvature catching an overhead light.
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: [
                          Colors.white.withValues(alpha: ty.isDark ? 0.14 : 0.42),
                          Colors.white.withValues(alpha: 0.0),
                          Colors.white.withValues(alpha: ty.isDark ? 0.05 : 0.12),
                        ],
                        stops: const [0, 0.55, 1],
                      ),
                    ),
                    child: SizedBox(
                      height: _height,
                      child: LayoutBuilder(
                        builder: (context, constraints) {
                          final slot = constraints.maxWidth / destinations.length;
                          final selected = selectedIndex;
                          return Stack(
                            children: [
                              // The selected tab sits in a lens of its own
                              // glass that glides (and slightly overshoots)
                              // between slots.
                              AnimatedPositioned(
                                duration: const Duration(milliseconds: 460),
                                curve: Curves.easeOutBack,
                                left: (selected ?? 0) * slot + _lensInset,
                                width: slot - _lensInset * 2,
                                top: _lensInset,
                                bottom: _lensInset,
                                child: AnimatedOpacity(
                                  opacity: selected == null ? 0 : 1,
                                  duration: const Duration(milliseconds: 220),
                                  child: _GlassLens(dark: ty.isDark, accent: ty.saffron),
                                ),
                              ),
                              Row(
                                children: [
                                  for (var i = 0; i < destinations.length; i++)
                                    Expanded(
                                      child: _GlassNavItem(
                                        destination: destinations[i],
                                        selected: i == selected,
                                        onTap: () {
                                          if (i != selected) HapticFeedback.selectionClick();
                                          onSelected(i);
                                        },
                                      ),
                                    ),
                                ],
                              ),
                            ],
                          );
                        },
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// The sliding highlight under the active tab: a small piece of brighter
/// glass with its own rim, not a flat coloured pill.
class _GlassLens extends StatelessWidget {
  final bool dark;
  final Color accent;
  const _GlassLens({required this.dark, required this.accent});

  @override
  Widget build(BuildContext context) {
    final r = (_GlassNavBar._height - _GlassNavBar._lensInset * 2) / 2;
    return CustomPaint(
      foregroundPainter: _GlassRimPainter(radius: r, dark: dark, strength: 0.8),
      child: DecoratedBox(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(r),
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              Colors.white.withValues(alpha: dark ? 0.22 : 0.62),
              Color.alphaBlend(
                accent.withValues(alpha: dark ? 0.10 : 0.07),
                Colors.white.withValues(alpha: dark ? 0.08 : 0.26),
              ),
            ],
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: dark ? 0.22 : 0.07),
              blurRadius: 10,
              offset: const Offset(0, 3),
            ),
          ],
        ),
      ),
    );
  }
}

/// Specular edge: bright where the glass catches light (top-left,
/// bottom-right), nearly clear elsewhere. This rim is what reads as "liquid".
class _GlassRimPainter extends CustomPainter {
  final double radius;
  final bool dark;
  final double strength;
  const _GlassRimPainter({required this.radius, required this.dark, this.strength = 1});

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Offset.zero & size;
    final rrect = RRect.fromRectAndRadius(rect.deflate(0.6), Radius.circular(radius));
    final hi = (dark ? 0.55 : 0.95) * strength;
    final lo = (dark ? 0.04 : 0.12) * strength;
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.2
      ..shader = LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [
          Colors.white.withValues(alpha: hi),
          Colors.white.withValues(alpha: lo),
          Colors.white.withValues(alpha: lo),
          Colors.white.withValues(alpha: hi * 0.65),
        ],
        stops: const [0, 0.38, 0.62, 1],
      ).createShader(rect);
    canvas.drawRRect(rrect, paint);

    // Soft inner glow just inside the rim.
    final glow = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 4
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 3)
      ..color = Colors.white.withValues(alpha: (dark ? 0.06 : 0.20) * strength);
    canvas.save();
    canvas.clipRRect(RRect.fromRectAndRadius(rect, Radius.circular(radius)));
    canvas.drawRRect(rrect.deflate(2), glow);
    canvas.restore();
  }

  @override
  bool shouldRepaint(_GlassRimPainter old) =>
      old.radius != radius || old.dark != dark || old.strength != strength;
}

/// Icon over label with an iOS-style press dim instead of a ripple.
class _GlassNavItem extends StatefulWidget {
  final TyNavDestination destination;
  final bool selected;
  final VoidCallback onTap;

  const _GlassNavItem({
    required this.destination,
    required this.selected,
    required this.onTap,
  });

  @override
  State<_GlassNavItem> createState() => _GlassNavItemState();
}

class _GlassNavItemState extends State<_GlassNavItem> {
  bool _pressed = false;

  void _setPressed(bool v) {
    if (_pressed != v) setState(() => _pressed = v);
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final d = widget.destination;
    final selected = widget.selected;
    final color = selected
        ? (ty.isDark ? ty.saffron : ty.saffronDeep)
        : ty.ink2.withValues(alpha: ty.isDark ? 0.85 : 0.9);
    final icon = selected ? (d.cupertinoActiveIcon ?? d.activeIcon) : (d.cupertinoIcon ?? d.icon);

    return Semantics(
      button: true,
      selected: selected,
      label: d.label,
      // Children's semantics (including the detector's tap) are excluded so
      // the slot reads as one button; the action is re-exposed here.
      onTap: widget.onTap,
      excludeSemantics: true,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTapDown: (_) => _setPressed(true),
        onTapUp: (_) => _setPressed(false),
        onTapCancel: () => _setPressed(false),
        onTap: widget.onTap,
        child: AnimatedOpacity(
          opacity: _pressed ? 0.55 : 1,
          duration: const Duration(milliseconds: 120),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              AnimatedScale(
                scale: selected ? 1.06 : 1.0,
                duration: const Duration(milliseconds: 260),
                curve: Curves.easeOutCubic,
                child: Icon(icon, size: 23, color: color),
              ),
              const SizedBox(height: 3),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 4),
                child: Text(
                  d.label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 10.5,
                    height: 1.1,
                    letterSpacing: 0.1,
                    fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                    color: color,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ─── Android: Material 3 bar ────────────────────────────────────────────────

/// Burgundy accent for the light theme's active state; the dark theme is
/// already burgundy, so there the indicator lifts a shade off the bar instead.
const Color _burgundy = Color(0xFF7A1E33);
const Color _burgundyRaised = Color(0xFF5A1C2C);

class _MaterialNavBar extends StatelessWidget {
  final List<TyNavDestination> destinations;
  final int? selectedIndex;
  final ValueChanged<int> onSelected;

  const _MaterialNavBar({
    required this.destinations,
    required this.selectedIndex,
    required this.onSelected,
  });

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final background = ty.isDark ? ty.paper2 : ty.surface;

    return AnnotatedRegion<SystemUiOverlayStyle>(
      // Blend the system navigation bar into this one on devices that still
      // paint it (pre edge-to-edge); ignored where it is transparent.
      value: SystemUiOverlayStyle(
        systemNavigationBarColor: background,
        systemNavigationBarDividerColor: background,
        systemNavigationBarIconBrightness: ty.isDark ? Brightness.light : Brightness.dark,
      ),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: background,
          border: Border(top: BorderSide(color: ty.line2)),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: ty.isDark ? 0.22 : 0.05),
              blurRadius: 8,
              offset: const Offset(0, -2),
            ),
          ],
        ),
        child: SafeArea(
          top: false,
          // Gesture pill or 3-button bar: viewPadding keeps the bar clear of
          // either, even while the keyboard reports a different inset.
          minimum: EdgeInsets.only(bottom: MediaQuery.viewPaddingOf(context).bottom),
          child: SizedBox(
            height: 72,
            child: Row(
              children: [
                for (var i = 0; i < destinations.length; i++)
                  Expanded(
                    child: _MaterialNavItem(
                      destination: destinations[i],
                      selected: i == selectedIndex,
                      onTap: () => onSelected(i),
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _MaterialNavItem extends StatelessWidget {
  final TyNavDestination destination;
  final bool selected;
  final VoidCallback onTap;

  const _MaterialNavItem({
    required this.destination,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final accent = ty.isDark ? ty.saffron : _burgundy;
    final indicator = ty.isDark ? _burgundyRaised : _burgundy.withValues(alpha: 0.10);
    final labelColor = selected ? (ty.isDark ? ty.ink : _burgundy) : ty.ink2;

    return Semantics(
      button: true,
      selected: selected,
      label: destination.label,
      onTap: onTap,
      excludeSemantics: true,
      child: Material(
        type: MaterialType.transparency,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(18),
          overlayColor: WidgetStatePropertyAll(accent.withValues(alpha: 0.08)),
          splashColor: accent.withValues(alpha: 0.12),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // M3 active indicator: a pill that widens out from the icon.
              AnimatedContainer(
                duration: const Duration(milliseconds: 220),
                curve: Curves.easeOutCubic,
                width: selected ? 60 : 32,
                height: 32,
                decoration: BoxDecoration(
                  color: selected ? indicator : indicator.withValues(alpha: 0),
                  borderRadius: BorderRadius.circular(16),
                ),
                alignment: Alignment.center,
                child: Icon(
                  selected ? destination.activeIcon : destination.icon,
                  size: 24,
                  color: selected ? accent : ty.ink2,
                ),
              ),
              const SizedBox(height: 4),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 4),
                child: Text(
                  destination.label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 12,
                    height: 1.2,
                    letterSpacing: 0.2,
                    fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                    color: labelColor,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
