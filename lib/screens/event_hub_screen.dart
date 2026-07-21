import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:dio/dio.dart';
import 'package:gal/gal.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:url_launcher/url_launcher.dart';

import 'package:tyohaar/theme/assets.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../theme/responsive.dart';
import '../data/models.dart';
import '../data/services/celebration_service.dart';
import '../data/services/booking_service.dart';
import '../data/services/package_service.dart';
import '../data/services/media_service.dart';
import '../utils/gallery_album.dart';
import '../widgets/avatar.dart';
import '../widgets/photo_placeholder.dart';
import '../widgets/common.dart';
import '../widgets/tutorial/tutorial_overlay.dart';
import 'guests_screen.dart';
import 'package_detail_screen.dart';

class EventHubScreen extends StatefulWidget {
  final String? celebrationId;
  const EventHubScreen({super.key, this.celebrationId});

  @override
  State<EventHubScreen> createState() => _EventHubScreenState();
}

class _EventHubScreenState extends State<EventHubScreen> {
  final CelebrationService _celebrationService = CelebrationService();
  final BookingService _bookingService = BookingService();
  final PackageService _packageService = PackageService();
  final MediaService _mediaService = MediaService();
  Celebration? _celebration;
  Booking? _booking;
  List<Guest> _guests = [];
  Package? _package;
  List<PackageItem> _packageItems = [];
  List<EventMediaItem> _eventMedia = [];
  bool _loadingMedia = false;
  String _daysLeft = '--';
  String _hoursLeft = '--';
  bool _isLoading = true;
  bool _isLiked = false;
  final GlobalKey _heroKey = GlobalKey();

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      String? id = widget.celebrationId;
      if (id == null) {
        final celebrations = await _celebrationService.listCelebrations();
        if (celebrations.isEmpty) {
          setState(() => _isLoading = false);
          return;
        }
        id = celebrations.first.id;
      }
      final detailsFuture = _celebrationService.getCelebrationDetails(id);
      final guestsFuture = _celebrationService.listGuests(id);
      final bookingsFuture = _bookingService.listByCelebration(id);

      final details = await detailsFuture;
      final guests = await guestsFuture;
      final bookings = await bookingsFuture;

      Booking? booking = bookings.isNotEmpty ? bookings.first : null;
      Package? package;
      List<PackageItem> packageItems = [];
      if (booking?.packageId != null) {
        try {
          package =
              await _packageService.getPackageDetails(booking!.packageId!);
          packageItems =
              await _packageService.listPackageItems(booking.packageId!);
        } catch (e) {
          debugPrint('Error loading package details: $e');
        }
      }

      String daysLeft = '--';
      String hoursLeft = '--';
      final eventDate = details.celebrationDate;
      if (eventDate != null) {
        if (eventDate.isAfter(DateTime.now())) {
          final diff = eventDate.difference(DateTime.now());
          daysLeft = diff.inDays.toString().padLeft(2, '0');
          hoursLeft = (diff.inHours % 24).toString().padLeft(2, '0');
        } else {
          daysLeft = '00';
          hoursLeft = '00';
        }
      }

      if (mounted) {
        setState(() {
          _celebration = details;
          _booking = booking;
          _guests = guests;
          _package = package;
          _packageItems = packageItems;
          _daysLeft = daysLeft;
          _hoursLeft = hoursLeft;
          _isLoading = false;
        });
        _loadEventMedia();
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (!mounted) return;
          TutorialOverlay.show(context, screenKey: 'event_hub', steps: [
            TutorialStep(
              targetKey: _heroKey,
              title: 'Your celebration, at a glance',
              description:
                  'Track the countdown and guest RSVPs for this event right here.',
            ),
          ]);
        });
      }
    } catch (e) {
      debugPrint('Error loading event hub: $e');
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _loadEventMedia() async {
    final booking = _booking;
    if (booking == null) return;
    setState(() => _loadingMedia = true);
    try {
      final media = await _mediaService.listBookingMedia(booking.id);
      if (mounted) setState(() => _eventMedia = media);
    } catch (e) {
      debugPrint('Error loading event media: $e');
    } finally {
      if (mounted) setState(() => _loadingMedia = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final resp = context.resp;

    if (_isLoading) {
      return Scaffold(
          backgroundColor: ty.paper,
          body: const Center(child: CircularProgressIndicator()));
    }

    if (_celebration == null) {
      return Scaffold(
        backgroundColor: ty.paper,
        appBar: tyAppBar(context, title: 'Event Hub'),
        body: Center(
            child: Text('No active celebration',
                style: TyType.sans(resp.sp(16), color: ty.ink2))),
      );
    }

    final totalGuests = _guests.length;

    final dt = _celebration?.celebrationDate;
    final date = dt != null ? '${dt.day}/${dt.month}/${dt.year}' : '';

    return Scaffold(
      backgroundColor: ty.paper,
      body: Stack(
        children: [
          Positioned.fill(
            child: RefreshIndicator(
              onRefresh: _load,
              color: ty.saffron,
              child: ListView(
                padding: EdgeInsets.zero,
                children: [
                  Stack(
                    key: _heroKey,
                    children: [
                      CachedNetworkImage(
                        imageUrl: _celebration?.heroImageUrl ?? '',
                        height: resp.h(360),
                        width: double.infinity,
                        fit: BoxFit.cover,
                        placeholder: (context, url) => PhotoPlaceholder(
                            tint: 'saffron',
                            height: resp.h(360),
                            arch: false,
                            radius: BorderRadius.zero),
                        errorWidget: (context, url, error) =>
                            OccasionAssets.getFallback(
                                _celebration?.occasionName ??
                                    _celebration?.title ??
                                    '',
                                arch: false),
                      ),
                      Positioned.fill(
                        child: DecoratedBox(
                          decoration: BoxDecoration(
                            gradient: LinearGradient(
                              begin: Alignment.bottomCenter,
                              end: Alignment.topCenter,
                              colors: [
                                ty.paper,
                                Colors.black.withOpacity(0.3),
                                Colors.black.withOpacity(0.35)
                              ],
                              stops: const [0.02, 0.55, 1],
                            ),
                          ),
                        ),
                      ),
                      Positioned(
                        left: resp.w(20),
                        right: resp.w(20),
                        bottom: resp.h(18),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            TyPill(_celebration?.occasionName ?? 'Celebration',
                                background: ty.saffron,
                                foreground: ty.onPrimary),
                            SizedBox(height: resp.h(12)),
                            Text(_celebration?.title ?? '',
                                style: TyType.display(resp.sp(38),
                                    color: Colors.white)),
                            SizedBox(height: resp.h(8)),
                            Row(children: [
                              Icon(Icons.event,
                                  size: resp.sp(16), color: Colors.white70),
                              SizedBox(width: resp.w(8)),
                              Text('$date',
                                  style: TyType.sans(resp.sp(14),
                                      color: Colors.white70)),
                            ]),
                          ],
                        ),
                      ),
                    ],
                  ),
                  Transform.translate(
                    offset: Offset(0, resp.h(-14)),
                    child: Padding(
                      padding: EdgeInsets.fromLTRB(
                          resp.w(18), 0, resp.w(18), resp.h(28)),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              _stat(context, _daysLeft, 'days'),
                              SizedBox(width: resp.w(10)),
                              _stat(context, _hoursLeft, 'hrs'),
                              SizedBox(width: resp.w(10)),
                              _stat(context, '$totalGuests', 'guests'),
                            ],
                          ),
                          SizedBox(height: resp.h(22)),
                          SectionHeader('Package details'),
                          _buildPackageSection(context),
                          SizedBox(height: resp.h(18)),
                          SectionHeader('The gathering', action: 'Manage',
                              onAction: () {
                            Navigator.of(context)
                                .push(MaterialPageRoute(
                                    builder: (_) => const GuestsScreen()))
                                .then((_) => _load());
                          }),
                          Container(
                            padding: EdgeInsets.all(resp.w(16)),
                            decoration: _card(ty, resp),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    if (_guests.isNotEmpty)
                                      SizedBox(
                                        width: resp.w(110),
                                        height: resp.h(36),
                                        child: Stack(
                                          children: [
                                            for (int i = 0;
                                                i < _guests.length.clamp(0, 4);
                                                i++)
                                              Positioned(
                                                left: i * resp.w(20.0),
                                                child: TyAvatar(
                                                    name: _guests[i].name,
                                                    index: i,
                                                    size: resp.w(36)),
                                              ),
                                          ],
                                        ),
                                      ),
                                    SizedBox(width: resp.w(8)),
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          Text('$totalGuests loved ones',
                                              style: TyType.sans(resp.sp(15),
                                                  color: ty.ink,
                                                  weight: FontWeight.w700)),
                                          Text(
                                              '${_guests.length} households invited',
                                              style: TyType.sans(resp.sp(12.5),
                                                  color: ty.ink2)),
                                        ],
                                      ),
                                    ),
                                    Icon(Icons.chevron_right_rounded,
                                        color: ty.ink3, size: resp.sp(24)),
                                  ],
                                ),
                                if (_guests.isNotEmpty) ...[
                                  SizedBox(height: resp.h(14)),
                                  Divider(color: ty.line, height: 1),
                                  SizedBox(height: resp.h(14)),
                                  _buildRsvpBreakdown(context),
                                ],
                              ],
                            ),
                          ),
                          SizedBox(height: resp.h(18)),
                          const SectionHeader('Multimedia'),
                          _EventMediaSection(
                            media: _eventMedia,
                            isLoading: _loadingMedia,
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          // Fixed top bar — sits above the scrolling content so it never
          // scrolls away, with its own scrim so the back/like buttons stay
          // legible over any hero image or card content behind them.
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: Container(
              padding: EdgeInsets.fromLTRB(
                  resp.w(18),
                  MediaQuery.of(context).padding.top + resp.h(8),
                  resp.w(18),
                  resp.h(16)),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [Colors.black.withOpacity(0.45), Colors.transparent],
                ),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  _glass(context, Icons.chevron_left_rounded,
                      () => Navigator.of(context).maybePop()),
                  _glass(
                    context,
                    _isLiked
                        ? Icons.favorite_rounded
                        : Icons.favorite_border_rounded,
                    () => setState(() => _isLiked = !_isLiked),
                    iconColor: _isLiked ? ty.rose : Colors.white,
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPackageSection(BuildContext context) {
    final ty = context.ty;
    final resp = context.resp;
    final pkg = _package;

    if (pkg == null) {
      return Container(
        padding: EdgeInsets.all(resp.w(16)),
        decoration: _card(ty, resp),
        child: Text('No package selected yet',
            style: TyType.sans(resp.sp(14), color: ty.ink2)),
      );
    }

    return GestureDetector(
      onTap: () => Navigator.of(context)
          .push(MaterialPageRoute(
              builder: (_) => PackageDetailScreen(package: pkg)))
          .then((_) => _load()),
      child: Container(
        padding: EdgeInsets.all(resp.w(16)),
        decoration: _card(ty, resp),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(resp.w(12)),
                  child: CachedNetworkImage(
                    imageUrl: pkg.coverImageUrl ?? '',
                    width: resp.w(56),
                    height: resp.w(56),
                    fit: BoxFit.cover,
                    placeholder: (context, url) => PhotoPlaceholder(
                        tint: 'saffron',
                        height: resp.w(56),
                        width: resp.w(56),
                        arch: false),
                    errorWidget: (context, url, error) => PhotoPlaceholder(
                        tint: 'saffron',
                        height: resp.w(56),
                        width: resp.w(56),
                        arch: false),
                  ),
                ),
                SizedBox(width: resp.w(12)),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(pkg.name,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TyType.sans(resp.sp(16),
                              color: ty.ink, weight: FontWeight.w700)),
                      SizedBox(height: resp.h(2)),
                      Text('₹${pkg.price.toStringAsFixed(0)}',
                          style: TyType.sans(resp.sp(13),
                              color: ty.saffronDeep, weight: FontWeight.w600)),
                    ],
                  ),
                ),
                Icon(Icons.chevron_right_rounded,
                    color: ty.ink3, size: resp.sp(22)),
              ],
            ),
            if ((_booking?.themeName ?? '').isNotEmpty) ...[
              SizedBox(height: resp.h(10)),
              Row(
                children: [
                  Icon(Icons.palette_outlined, size: resp.sp(15), color: ty.ink3),
                  SizedBox(width: resp.w(6)),
                  Text('Theme: ${_booking!.themeName}',
                      style: TyType.sans(resp.sp(12.5), color: ty.ink2)),
                ],
              ),
            ],
            if (_packageItems.isNotEmpty) ...[
              SizedBox(height: resp.h(12)),
              Divider(color: ty.line, height: 1),
              SizedBox(height: resp.h(12)),
              ..._packageItems.take(4).map((item) => Padding(
                    padding: EdgeInsets.only(bottom: resp.h(6)),
                    child: Row(
                      children: [
                        Icon(Icons.check_circle_outline_rounded,
                            size: resp.sp(15), color: ty.saffron),
                        SizedBox(width: resp.w(8)),
                        Expanded(
                          child: Text(
                              item.quantity > 1
                                  ? '${item.name} × ${item.quantity}'
                                  : item.name,
                              style: TyType.sans(resp.sp(13), color: ty.ink2)),
                        ),
                      ],
                    ),
                  )),
              if (_packageItems.length > 4)
                Text('+ ${_packageItems.length - 4} more',
                    style: TyType.sans(resp.sp(12.5), color: ty.ink3)),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildRsvpBreakdown(BuildContext context) {
    final theme = context.ty;
    final resp = context.resp;
    final attending =
        _guests.where((g) => g.displayStatus == 'attending').length;
    final declined = _guests.where((g) => g.displayStatus == 'declined').length;
    final maybe = _guests.where((g) => g.displayStatus == 'maybe').length;
    final pending = _guests.length - attending - declined - maybe;

    Widget stat(String label, int count, Color color) {
      return Expanded(
        child: Column(
          children: [
            Text('$count', style: TyType.display(resp.sp(20), color: color)),
            SizedBox(height: resp.h(2)),
            Text(label.toUpperCase(),
                style: TyType.eyebrow(resp.sp(10), color: theme.ink2)),
          ],
        ),
      );
    }

    return Row(
      children: [
        stat('Attending', attending, Colors.green.shade600),
        stat('Maybe', maybe, Colors.orange.shade600),
        stat('Declined', declined, Colors.red.shade400),
        stat('Pending', pending, theme.ink3),
      ],
    );
  }

  Widget _glass(BuildContext context, IconData icon, VoidCallback onTap,
      {Color? iconColor}) {
    final resp = context.resp;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: resp.w(42),
        height: resp.w(42),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.18),
          borderRadius: BorderRadius.circular(resp.w(14)),
        ),
        child: Icon(icon, color: iconColor ?? Colors.white, size: resp.sp(20)),
      ),
    );
  }

  Widget _stat(BuildContext context, String n, String l) {
    final ty = context.ty;
    final resp = context.resp;
    return Expanded(
      child: Container(
        padding:
            EdgeInsets.symmetric(vertical: resp.h(14), horizontal: resp.w(8)),
        decoration: _card(ty, resp),
        child: Column(
          children: [
            Text(n, style: TyType.display(resp.sp(26), color: ty.ink)),
            SizedBox(height: resp.h(4)),
            Text(l.toUpperCase(),
                style: TyType.eyebrow(resp.sp(11), color: ty.ink2)),
          ],
        ),
      ),
    );
  }

  BoxDecoration _card(TyColors ty, TyResponsive resp) => BoxDecoration(
        color: ty.surface,
        borderRadius: BorderRadius.circular(resp.w(20)),
        border: Border.all(color: ty.line),
      );
}

// ---------------------------------------------------------------------------
// MULTIMEDIA — vendor-uploaded event photos/videos, with a grid, a
// full-screen image viewer, and single/bulk save-to-gallery downloads.
// ---------------------------------------------------------------------------

class _EventMediaSection extends StatefulWidget {
  final List<EventMediaItem> media;
  final bool isLoading;
  const _EventMediaSection({required this.media, required this.isLoading});

  @override
  State<_EventMediaSection> createState() => _EventMediaSectionState();
}

class _EventMediaSectionState extends State<_EventMediaSection> {
  bool _selecting = false;
  bool _isDownloading = false;
  final Set<String> _selectedIds = {};

  void _toggleSelect(String id) {
    setState(() {
      if (_selectedIds.contains(id)) {
        _selectedIds.remove(id);
      } else {
        _selectedIds.add(id);
      }
    });
  }

  void _openImageViewer(int index) {
    final images = widget.media.where((m) => !m.isVideo).toList();
    final tappedIndex = images.indexWhere((m) => m.id == widget.media[index].id);
    Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => _EventMediaViewerScreen(
        images: images,
        initialIndex: tappedIndex < 0 ? 0 : tappedIndex,
      ),
    ));
  }

  Future<void> _openVideoExternally(EventMediaItem item) async {
    final uri = Uri.tryParse(item.url);
    if (uri == null) return;
    try {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not open the video.')),
        );
      }
    }
  }

  Future<bool> _ensureGalleryAccess() async {
    final hasAccess = await Gal.hasAccess(toAlbum: true);
    if (hasAccess) return true;
    final granted = await Gal.requestAccess(toAlbum: true);
    if (granted) return true;
    await Permission.photos.request();
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Photo library access is needed to save media.')),
      );
    }
    return false;
  }

  Future<void> _downloadOne(EventMediaItem item) async {
    if (item.isVideo) {
      final dir = await getTemporaryDirectory();
      final path = '${dir.path}/tyohaar_event_${item.id}.mp4';
      await Dio().download(item.url, path);
      await Gal.putVideo(path, album: kTyohaarGalleryAlbum);
      try {
        await File(path).delete();
      } catch (_) {}
    } else {
      final response = await Dio().get<List<int>>(
        item.url,
        options: Options(responseType: ResponseType.bytes),
      );
      final bytes = response.data;
      if (bytes == null) throw Exception('Empty media response');
      await Gal.putImageBytes(
        Uint8List.fromList(bytes),
        name: 'tyohaar_event_${item.id}',
        album: kTyohaarGalleryAlbum,
      );
    }
  }

  Future<void> _downloadSelected() async {
    if (_selectedIds.isEmpty) return;
    if (!await _ensureGalleryAccess()) return;

    setState(() => _isDownloading = true);
    var saved = 0;
    var failed = 0;
    for (final item in widget.media.where((m) => _selectedIds.contains(m.id))) {
      try {
        await _downloadOne(item);
        saved++;
      } catch (_) {
        failed++;
      }
    }
    if (mounted) {
      setState(() {
        _isDownloading = false;
        _selecting = false;
        _selectedIds.clear();
      });
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(failed == 0
            ? 'Saved $saved item${saved == 1 ? '' : 's'} to your gallery.'
            : 'Saved $saved item${saved == 1 ? '' : 's'} — $failed failed.'),
      ));
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final resp = context.resp;
    final decoration = BoxDecoration(
      color: ty.surface,
      borderRadius: BorderRadius.circular(resp.w(20)),
      border: Border.all(color: ty.line),
    );

    if (widget.isLoading) {
      return Container(
        padding: EdgeInsets.all(resp.w(24)),
        decoration: decoration,
        alignment: Alignment.center,
        child: const CircularProgressIndicator(),
      );
    }

    if (widget.media.isEmpty) {
      return Container(
        padding: EdgeInsets.all(resp.w(16)),
        decoration: decoration,
        child: Text(
          'Your vendor will share event photos and videos here once the celebration is complete.',
          style: TyType.sans(resp.sp(13), color: ty.ink2),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.end,
          children: [
            if (_selecting) ...[
              Text('${_selectedIds.length} selected',
                  style: TyType.sans(resp.sp(12.5), color: ty.ink2)),
              const Spacer(),
              TextButton(
                onPressed: _isDownloading || _selectedIds.isEmpty ? null : _downloadSelected,
                child: _isDownloading
                    ? SizedBox(
                        width: resp.w(16),
                        height: resp.w(16),
                        child: const CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Download'),
              ),
              TextButton(
                onPressed: () => setState(() {
                  _selecting = false;
                  _selectedIds.clear();
                }),
                child: const Text('Cancel'),
              ),
            ] else
              TextButton(
                onPressed: () => setState(() => _selecting = true),
                child: const Text('Select'),
              ),
          ],
        ),
        GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 3,
            mainAxisSpacing: 8,
            crossAxisSpacing: 8,
          ),
          itemCount: widget.media.length,
          itemBuilder: (context, i) {
            final item = widget.media[i];
            final selected = _selectedIds.contains(item.id);
            return GestureDetector(
              onTap: () {
                if (_selecting) {
                  _toggleSelect(item.id);
                } else if (item.isVideo) {
                  _openVideoExternally(item);
                } else {
                  _openImageViewer(i);
                }
              },
              onLongPress: () {
                setState(() => _selecting = true);
                _toggleSelect(item.id);
              },
              child: ClipRRect(
                borderRadius: BorderRadius.circular(resp.w(10)),
                child: Stack(
                  fit: StackFit.expand,
                  children: [
                    CachedNetworkImage(
                      imageUrl: item.gridThumbnailUrl,
                      fit: BoxFit.cover,
                      placeholder: (context, url) =>
                          PhotoPlaceholder(tint: 'saffron', arch: false),
                      errorWidget: (context, url, error) =>
                          PhotoPlaceholder(tint: 'saffron', arch: false),
                    ),
                    if (item.isVideo)
                      const ColoredBox(
                        color: Colors.black26,
                        child: Center(
                          child: Icon(Icons.play_circle_fill_rounded,
                              color: Colors.white, size: 30),
                        ),
                      ),
                    if (_selecting)
                      Positioned(
                        top: 4,
                        right: 4,
                        child: Icon(
                          selected ? Icons.check_circle_rounded : Icons.circle_outlined,
                          color: selected ? ty.saffron : Colors.white,
                          size: 20,
                        ),
                      ),
                  ],
                ),
              ),
            );
          },
        ),
      ],
    );
  }
}

class _EventMediaViewerScreen extends StatefulWidget {
  final List<EventMediaItem> images;
  final int initialIndex;
  const _EventMediaViewerScreen({required this.images, required this.initialIndex});

  @override
  State<_EventMediaViewerScreen> createState() => _EventMediaViewerScreenState();
}

class _EventMediaViewerScreenState extends State<_EventMediaViewerScreen> {
  late final PageController _controller =
      PageController(initialPage: widget.initialIndex);
  late int _index = widget.initialIndex;
  bool _isDownloading = false;

  Future<void> _download() async {
    final item = widget.images[_index];
    setState(() => _isDownloading = true);
    try {
      final hasAccess = await Gal.hasAccess(toAlbum: true);
      if (!hasAccess) {
        final granted = await Gal.requestAccess(toAlbum: true);
        if (!granted) {
          await Permission.photos.request();
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Photo library access is needed to save images.')),
            );
          }
          return;
        }
      }
      final response = await Dio().get<List<int>>(
        item.url,
        options: Options(responseType: ResponseType.bytes),
      );
      final bytes = response.data;
      if (bytes == null) throw Exception('Empty image response');
      await Gal.putImageBytes(
        Uint8List.fromList(bytes),
        name: 'tyohaar_event_${item.id}',
        album: kTyohaarGalleryAlbum,
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Image saved to your gallery.')),
        );
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not save the image. Please try again.')),
        );
      }
    } finally {
      if (mounted) setState(() => _isDownloading = false);
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(
        children: [
          PageView.builder(
            controller: _controller,
            itemCount: widget.images.length,
            onPageChanged: (i) => setState(() => _index = i),
            itemBuilder: (context, i) => InteractiveViewer(
              child: Center(
                child: CachedNetworkImage(
                  imageUrl: widget.images[i].url,
                  fit: BoxFit.contain,
                ),
              ),
            ),
          ),
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: SafeArea(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    IconButton(
                      icon: const Icon(Icons.close_rounded, color: Colors.white),
                      onPressed: () => Navigator.of(context).maybePop(),
                    ),
                    Text('${_index + 1} / ${widget.images.length}',
                        style: const TextStyle(color: Colors.white)),
                    IconButton(
                      icon: _isDownloading
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(
                                  strokeWidth: 2, color: Colors.white),
                            )
                          : const Icon(Icons.download_rounded, color: Colors.white),
                      onPressed: _isDownloading ? null : _download,
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
