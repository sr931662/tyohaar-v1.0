import 'package:flutter/material.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/models.dart';
import '../widgets/avatar.dart';
import '../widgets/photo_placeholder.dart';
import '../widgets/ty_button.dart';
import '../widgets/common.dart';

/// Partner detail — gallery, packages, reviews and a sticky book/chat bar.
class VendorDetailScreen extends StatefulWidget {
  final Vendor vendor;
  const VendorDetailScreen({super.key, required this.vendor});

  @override
  State<VendorDetailScreen> createState() => _VendorDetailScreenState();
}

class _VendorDetailScreenState extends State<VendorDetailScreen> {
  int _pkg = 1;

  static const _packages = [
    ['Half Day', '4 hours · 1 photographer', '₹65,000'],
    ['Full Celebration', 'Full day · 2 shooters + album', '₹1.4L'],
    ['The Whole Story', 'Multi-day · film + premium album', '₹2.6L'],
  ];

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final v = widget.vendor;

    return Scaffold(
      backgroundColor: ty.paper,
      body: Stack(
        children: [
          ListView(
            padding: EdgeInsets.zero,
            children: [
              // hero
              Stack(
                children: [
                  PhotoPlaceholder(tint: v.tint, height: 300, arch: false, radius: BorderRadius.zero),
                  Positioned.fill(
                    child: DecoratedBox(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          begin: Alignment.bottomCenter,
                          end: Alignment.topCenter,
                          colors: [ty.paper, Colors.black.withOpacity(0.12)],
                          stops: const [0.02, 1],
                        ),
                      ),
                    ),
                  ),
                  Positioned(
                    top: MediaQuery.of(context).padding.top + 8,
                    left: 18,
                    right: 18,
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        _glassButton(Icons.chevron_left_rounded,
                            () => Navigator.of(context).maybePop()),
                        _glassButton(Icons.share_outlined, () {}),
                      ],
                    ),
                  ),
                  Positioned(
                    left: 18,
                    bottom: 14,
                    child: Row(
                      children: [
                        for (final t in const ['rose', 'saffron', 'gold'])
                          Padding(
                            padding: const EdgeInsets.only(right: 8),
                            child: ClipRRect(
                              borderRadius: BorderRadius.circular(11),
                              child: SizedBox(
                                width: 46,
                                height: 46,
                                child: PhotoPlaceholder(tint: t, arch: false),
                              ),
                            ),
                          ),
                        Container(
                          width: 46,
                          height: 46,
                          alignment: Alignment.center,
                          decoration: BoxDecoration(
                            color: Colors.white.withOpacity(0.22),
                            borderRadius: BorderRadius.circular(11),
                          ),
                          child: const Text('+24',
                              style: TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.w700,
                                  fontSize: 12)),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(18, 18, 18, 120),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(v.cat.toUpperCase(),
                        style: TyType.eyebrow(11.5, color: ty.saffronDeep)),
                    const SizedBox(height: 3),
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(child: Text(v.name, style: TyType.display(30, color: ty.ink))),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            Row(children: [
                              Icon(Icons.star_rounded, color: ty.gold, size: 16),
                              const SizedBox(width: 3),
                              Text(v.rating.toStringAsFixed(1),
                                  style: TyType.sans(16, color: ty.ink, weight: FontWeight.w800)),
                            ]),
                            Text('208 reviews', style: TyType.sans(11.5, color: ty.ink3)),
                          ],
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Row(children: [
                      Icon(Icons.place_outlined, size: 15, color: ty.ink2),
                      const SizedBox(width: 6),
                      Text('Jaipur · serves all Rajasthan',
                          style: TyType.sans(13, color: ty.ink2)),
                    ]),
                    const SizedBox(height: 18),
                    Row(
                      children: [
                        _trust(context, Icons.verified_outlined, 'Verified'),
                        const SizedBox(width: 10),
                        _trust(context, Icons.schedule_rounded, '5 yrs'),
                        const SizedBox(width: 10),
                        _trust(context, Icons.movie_outlined, 'Cinematic'),
                      ],
                    ),
                    const SizedBox(height: 26),
                    Text('About', style: TyType.sans(16, color: ty.ink, weight: FontWeight.w800)),
                    const SizedBox(height: 8),
                    Text(
                      'Award-winning storytellers blending candid moments with cinematic '
                      'frames. We’ve documented over 400 celebrations across India — from '
                      'intimate naming ceremonies to grand weddings.',
                      style: TyType.sans(14.5, color: ty.ink2, height: 1.6),
                    ),
                    const SizedBox(height: 26),
                    Text('Packages',
                        style: TyType.sans(16, color: ty.ink, weight: FontWeight.w800)),
                    const SizedBox(height: 10),
                    for (int i = 0; i < _packages.length; i++) _pkgRow(context, i),
                    const SizedBox(height: 26),
                    Text('What families say',
                        style: TyType.sans(16, color: ty.ink, weight: FontWeight.w800)),
                    const SizedBox(height: 10),
                    _review(context),
                  ],
                ),
              ),
            ],
          ),
          // sticky CTA
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: Container(
              padding: EdgeInsets.fromLTRB(
                  18, 12, 18, MediaQuery.of(context).padding.bottom + 14),
              decoration: BoxDecoration(
                color: ty.paper.withOpacity(0.96),
                border: Border(top: BorderSide(color: ty.line2)),
              ),
              child: Row(
                children: [
                  Container(
                    width: 52,
                    height: 52,
                    decoration: BoxDecoration(
                      color: ty.surface,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: ty.line),
                    ),
                    child: Icon(Icons.chat_bubble_outline_rounded, color: ty.ink, size: 22),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TyButton(
                      'Add to celebration · ${_packages[_pkg][2]}',
                      full: true,
                      onTap: () => Navigator.of(context).maybePop(),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _glassButton(IconData icon, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 42,
        height: 42,
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.2),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Icon(icon, color: Colors.white, size: 20),
      ),
    );
  }

  Widget _trust(BuildContext context, IconData icon, String label) {
    final ty = context.ty;
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 13, horizontal: 6),
        decoration: BoxDecoration(
          color: ty.surface2,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: ty.line),
        ),
        child: Column(
          children: [
            Icon(icon, color: ty.saffron, size: 19),
            const SizedBox(height: 5),
            Text(label, style: TyType.sans(11.5, color: ty.ink, weight: FontWeight.w600)),
          ],
        ),
      ),
    );
  }

  Widget _pkgRow(BuildContext context, int i) {
    final ty = context.ty;
    final selected = _pkg == i;
    final p = _packages[i];
    return GestureDetector(
      onTap: () => setState(() => _pkg = i),
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.all(15),
        decoration: BoxDecoration(
          color: selected ? ty.saffronSoft : ty.surface,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(
            color: selected ? ty.saffron : ty.line,
            width: selected ? 1.5 : 1,
          ),
        ),
        child: Row(
          children: [
            Container(
              width: 22,
              height: 22,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(
                  color: selected ? ty.saffron : ty.line,
                  width: selected ? 7 : 2,
                ),
              ),
            ),
            const SizedBox(width: 13),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(p[0], style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
                  Text(p[1], style: TyType.sans(12.5, color: ty.ink2)),
                ],
              ),
            ),
            Text(p[2], style: TyType.sans(15, color: ty.ink, weight: FontWeight.w800)),
          ],
        ),
      ),
    );
  }

  Widget _review(BuildContext context) {
    final ty = context.ty;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: ty.surface,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: ty.line),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const TyAvatar(name: 'Ananya', index: 1, size: 36),
              const SizedBox(width: 10),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Ananya I.',
                      style: TyType.sans(13.5, color: ty.ink, weight: FontWeight.w700)),
                  Text('★★★★★', style: TextStyle(color: ty.gold, fontSize: 11)),
                ],
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            '“They captured my mother’s 70th so tenderly — every frame made us cry. '
            'Worth every rupee.”',
            style: TyType.sans(13.5, color: ty.ink2, height: 1.55),
          ),
        ],
      ),
    );
  }
}
