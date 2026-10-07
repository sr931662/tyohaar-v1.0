import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../theme/colors.dart';

/// Full-screen photo viewer shared by packages, package items and services.
///
/// Swipe between photos, pinch or double-tap to zoom, use the -/+ buttons for
/// stepped zoom, tap to hide/show the controls, jump via the thumbnail strip.
/// Paging is locked while a photo is zoomed so panning around it never flips
/// the page.
class ImageViewer extends StatefulWidget {
  final List<String> images;
  final int initialIndex;
  final String? title;

  const ImageViewer({
    super.key,
    required this.images,
    this.initialIndex = 0,
    this.title,
  });

  static Future<void> open(
    BuildContext context, {
    required List<String> images,
    int initialIndex = 0,
    String? title,
  }) {
    final urls = images.where((u) => u.isNotEmpty).toList();
    if (urls.isEmpty) return Future.value();
    return Navigator.of(context, rootNavigator: true).push(PageRouteBuilder(
      opaque: false,
      barrierColor: Colors.black,
      transitionDuration: const Duration(milliseconds: 220),
      reverseTransitionDuration: const Duration(milliseconds: 180),
      pageBuilder: (_, __, ___) => ImageViewer(
        images: urls,
        initialIndex: initialIndex.clamp(0, urls.length - 1),
        title: title,
      ),
      transitionsBuilder: (_, anim, __, child) =>
          FadeTransition(opacity: anim, child: child),
    ));
  }

  @override
  State<ImageViewer> createState() => _ImageViewerState();
}

class _ImageViewerState extends State<ImageViewer>
    with SingleTickerProviderStateMixin {
  static const _minScale = 1.0;
  static const _maxScale = 5.0;
  static const _step = 1.0;

  late final PageController _pages =
      PageController(initialPage: widget.initialIndex);
  late int _index = widget.initialIndex;
  late final List<TransformationController> _transforms =
      List.generate(widget.images.length, (_) => TransformationController());
  late final AnimationController _zoomAnim = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 220),
  );
  Animation<Matrix4>? _zoomTween;
  Offset? _doubleTapAt;
  bool _zoomed = false;
  bool _chromeVisible = true;

  @override
  void initState() {
    super.initState();
    _zoomAnim.addListener(() {
      final t = _zoomTween;
      if (t != null) _transforms[_index].value = t.value;
    });
    for (final t in _transforms) {
      t.addListener(_syncZoomed);
    }
  }

  @override
  void dispose() {
    _pages.dispose();
    _zoomAnim.dispose();
    for (final t in _transforms) {
      t.dispose();
    }
    super.dispose();
  }

  double get _scale => _transforms[_index].value.getMaxScaleOnAxis();

  // Rebuilds on every transform change so the zoom % readout tracks pinches
  // live, and flips paging lock once the photo leaves (or returns to) 1x.
  void _syncZoomed() {
    if (!mounted) return;
    setState(() => _zoomed = _scale > 1.01);
  }

  void _animateTo(Matrix4 target) {
    _zoomTween = Matrix4Tween(begin: _transforms[_index].value, end: target)
        .animate(
            CurvedAnimation(parent: _zoomAnim, curve: Curves.easeOutCubic));
    _zoomAnim.forward(from: 0);
  }

  /// Zooms to [scale] keeping [focal] (viewport coords) fixed on screen.
  void _zoomTo(double scale, Offset focal) {
    scale = scale.clamp(_minScale, _maxScale);
    if (scale <= 1.0) {
      _animateTo(Matrix4.identity());
      return;
    }
    final current = _transforms[_index].value;
    // Scene point currently under the focal point.
    final inv = Matrix4.inverted(current);
    final scene = MatrixUtils.transformPoint(inv, focal);
    _animateTo(
      Matrix4.translationValues(
              focal.dx - scene.dx * scale, focal.dy - scene.dy * scale, 0) *
          Matrix4.diagonal3Values(scale, scale, 1),
    );
  }

  Offset _viewportCenter() {
    final size = MediaQuery.sizeOf(context);
    return Offset(size.width / 2, size.height / 2);
  }

  void _onDoubleTap() {
    HapticFeedback.selectionClick();
    if (_zoomed) {
      _animateTo(Matrix4.identity());
    } else {
      _zoomTo(2.5, _doubleTapAt ?? _viewportCenter());
    }
  }

  void _onPageChanged(int i) {
    // Leaving a page resets its zoom so coming back starts clean.
    _transforms[_index].value = Matrix4.identity();
    setState(() {
      _index = i;
      _zoomed = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final padding = MediaQuery.paddingOf(context);
    final total = widget.images.length;

    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.light,
      child: Material(
        color: Colors.black,
        child: Stack(
          children: [
            GestureDetector(
              onTap: () => setState(() => _chromeVisible = !_chromeVisible),
              onDoubleTapDown: (d) => _doubleTapAt = d.localPosition,
              onDoubleTap: _onDoubleTap,
              child: PageView.builder(
                controller: _pages,
                physics: _zoomed
                    ? const NeverScrollableScrollPhysics()
                    : const PageScrollPhysics(),
                itemCount: total,
                onPageChanged: _onPageChanged,
                itemBuilder: (context, i) => InteractiveViewer(
                  transformationController: _transforms[i],
                  minScale: _minScale,
                  maxScale: _maxScale,
                  clipBehavior: Clip.none,
                  child: SizedBox.expand(
                    child: CachedNetworkImage(
                      imageUrl: widget.images[i],
                      fit: BoxFit.contain,
                      placeholder: (_, __) => const Center(
                        child: SizedBox(
                          width: 28,
                          height: 28,
                          child: CircularProgressIndicator(
                              strokeWidth: 2, color: Colors.white70),
                        ),
                      ),
                      errorWidget: (_, __, ___) => const Center(
                        child: Icon(Icons.broken_image_outlined,
                            color: Colors.white54, size: 48),
                      ),
                    ),
                  ),
                ),
              ),
            ),
            // Top bar: close, title, counter.
            _fadeChrome(
              Positioned(
                top: 0,
                left: 0,
                right: 0,
                child: Container(
                  padding: EdgeInsets.fromLTRB(8, padding.top + 4, 16, 12),
                  decoration: const BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [Color(0x99000000), Color(0x00000000)],
                    ),
                  ),
                  child: Row(
                    children: [
                      IconButton(
                        icon: const Icon(Icons.close_rounded,
                            color: Colors.white),
                        onPressed: () => Navigator.of(context).maybePop(),
                      ),
                      Expanded(
                        child: Text(
                          widget.title ?? '',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                              color: Colors.white,
                              fontSize: 16,
                              fontWeight: FontWeight.w600),
                        ),
                      ),
                      if (total > 1)
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 10, vertical: 4),
                          decoration: BoxDecoration(
                            color: Colors.white.withValues(alpha: 0.16),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Text(
                            '${_index + 1} / $total',
                            style: const TextStyle(
                                color: Colors.white,
                                fontSize: 12.5,
                                fontWeight: FontWeight.w700),
                          ),
                        ),
                    ],
                  ),
                ),
              ),
            ),
            // Bottom: zoom controls + thumbnail strip.
            _fadeChrome(
              Positioned(
                left: 0,
                right: 0,
                bottom: 0,
                child: Container(
                  padding: EdgeInsets.fromLTRB(0, 24, 0, padding.bottom + 12),
                  decoration: const BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.bottomCenter,
                      end: Alignment.topCenter,
                      colors: [Color(0x99000000), Color(0x00000000)],
                    ),
                  ),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      _zoomControls(),
                      if (total > 1) ...[
                        const SizedBox(height: 14),
                        SizedBox(
                          height: 54,
                          child: ListView.separated(
                            scrollDirection: Axis.horizontal,
                            padding: const EdgeInsets.symmetric(horizontal: 16),
                            itemCount: total,
                            separatorBuilder: (_, __) =>
                                const SizedBox(width: 8),
                            itemBuilder: (_, i) {
                              final active = i == _index;
                              return GestureDetector(
                                onTap: () => _pages.animateToPage(i,
                                    duration: const Duration(milliseconds: 280),
                                    curve: Curves.easeOutCubic),
                                child: AnimatedContainer(
                                  duration: const Duration(milliseconds: 200),
                                  width: 54,
                                  decoration: BoxDecoration(
                                    borderRadius: BorderRadius.circular(10),
                                    border: Border.all(
                                      color:
                                          active ? ty.saffron : Colors.white24,
                                      width: active ? 2 : 1,
                                    ),
                                  ),
                                  child: ClipRRect(
                                    borderRadius: BorderRadius.circular(8),
                                    child: Opacity(
                                      opacity: active ? 1 : 0.6,
                                      child: CachedNetworkImage(
                                        imageUrl: widget.images[i],
                                        fit: BoxFit.cover,
                                        memCacheWidth: 160,
                                        errorWidget: (_, __, ___) =>
                                            const ColoredBox(
                                                color: Colors.white10),
                                      ),
                                    ),
                                  ),
                                ),
                              );
                            },
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _fadeChrome(Positioned child) => Positioned(
        top: child.top,
        left: child.left,
        right: child.right,
        bottom: child.bottom,
        child: IgnorePointer(
          ignoring: !_chromeVisible,
          child: AnimatedOpacity(
            opacity: _chromeVisible ? 1 : 0,
            duration: const Duration(milliseconds: 180),
            child: child.child,
          ),
        ),
      );

  Widget _zoomControls() {
    final scale = _scale;
    Widget btn(IconData icon, VoidCallback? onTap) => IconButton(
          onPressed: onTap,
          icon: Icon(icon, size: 22),
          color: Colors.white,
          disabledColor: Colors.white30,
        );
    return Container(
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: Colors.white12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          btn(
              Icons.zoom_out_rounded,
              scale > 1.01
                  ? () => _zoomTo(scale - _step, _viewportCenter())
                  : null),
          SizedBox(
            width: 52,
            child: Text(
              '${(scale * 100).round()}%',
              textAlign: TextAlign.center,
              style: const TextStyle(
                  color: Colors.white,
                  fontSize: 12.5,
                  fontWeight: FontWeight.w700),
            ),
          ),
          btn(
              Icons.zoom_in_rounded,
              scale < _maxScale - 0.01
                  ? () => _zoomTo(scale + _step, _viewportCenter())
                  : null),
        ],
      ),
    );
  }
}

/// Swipeable photo carousel with page dots; tapping a photo opens it in
/// [ImageViewer] at that index.
class ImageCarousel extends StatefulWidget {
  final List<String> images;
  final double height;
  final BorderRadius borderRadius;
  final String? title;
  final Widget Function(BuildContext context)? placeholder;

  const ImageCarousel({
    super.key,
    required this.images,
    this.height = 220,
    this.borderRadius = const BorderRadius.all(Radius.circular(20)),
    this.title,
    this.placeholder,
  });

  @override
  State<ImageCarousel> createState() => _ImageCarouselState();
}

class _ImageCarouselState extends State<ImageCarousel> {
  final PageController _controller = PageController();
  int _index = 0;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final urls = widget.images;
    if (urls.isEmpty) {
      return SizedBox(
        height: widget.height,
        child: ClipRRect(
          borderRadius: widget.borderRadius,
          child: widget.placeholder?.call(context) ??
              ColoredBox(color: ty.surface),
        ),
      );
    }
    return SizedBox(
      height: widget.height,
      child: ClipRRect(
        borderRadius: widget.borderRadius,
        child: Stack(
          fit: StackFit.expand,
          children: [
            PageView.builder(
              controller: _controller,
              itemCount: urls.length,
              onPageChanged: (i) => setState(() => _index = i),
              itemBuilder: (context, i) => GestureDetector(
                onTap: () => ImageViewer.open(context,
                    images: urls, initialIndex: i, title: widget.title),
                child: CachedNetworkImage(
                  imageUrl: urls[i],
                  fit: BoxFit.cover,
                  memCacheWidth: 1080,
                  placeholder: (ctx, __) =>
                      widget.placeholder?.call(ctx) ??
                      ColoredBox(color: ty.surface),
                  errorWidget: (ctx, __, ___) =>
                      widget.placeholder?.call(ctx) ??
                      ColoredBox(color: ty.surface),
                ),
              ),
            ),
            // Expand hint so the tap-to-view affordance is discoverable.
            Positioned(
              top: 10,
              right: 10,
              child: IgnorePointer(
                child: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
                  decoration: BoxDecoration(
                    color: Colors.black.withValues(alpha: 0.45),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.zoom_out_map_rounded,
                          color: Colors.white, size: 14),
                      if (urls.length > 1) ...[
                        const SizedBox(width: 4),
                        Text('${_index + 1}/${urls.length}',
                            style: const TextStyle(
                                color: Colors.white,
                                fontSize: 11.5,
                                fontWeight: FontWeight.w700)),
                      ],
                    ],
                  ),
                ),
              ),
            ),
            if (urls.length > 1)
              Positioned(
                bottom: 10,
                left: 0,
                right: 0,
                child: IgnorePointer(
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: List.generate(urls.length, (i) {
                      final active = i == _index;
                      return AnimatedContainer(
                        duration: const Duration(milliseconds: 200),
                        margin: const EdgeInsets.symmetric(horizontal: 3),
                        width: active ? 18 : 6,
                        height: 6,
                        decoration: BoxDecoration(
                          color: active
                              ? Colors.white
                              : Colors.white.withValues(alpha: 0.55),
                          borderRadius: BorderRadius.circular(3),
                        ),
                      );
                    }),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
