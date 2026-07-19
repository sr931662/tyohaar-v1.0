import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';

import 'package:tyohaar/theme/assets.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../theme/responsive.dart';
import '../data/auth_manager.dart';
import '../data/models.dart';
import '../data/services/package_service.dart';
import '../data/services/celebration_service.dart';
import '../data/services/booking_service.dart';
import '../data/services/user_service.dart';
import '../utils/currency.dart';
import '../widgets/avatar.dart';
import '../widgets/emblem.dart';
import '../widgets/photo_placeholder.dart';
import '../widgets/progress_ring.dart';
import '../widgets/common.dart';
import '../widgets/state_screens.dart';
import 'event_hub_screen.dart';
import 'manage_address_screen.dart';
import 'membership_plan_screen.dart';
import 'package:tyohaar/screens/package_detail_screen.dart';
import 'package:tyohaar/screens/invitation_management_screen.dart';
import 'package:tyohaar/screens/occasion_detail_screen.dart';

class HomeScreen extends StatefulWidget {
  final ScrollController? scrollController;
  const HomeScreen({super.key, this.scrollController});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final PackageService _packageService = PackageService();
  final CelebrationService _celebrationService = CelebrationService();
  final BookingService _bookingService = BookingService();
  final UserService _userService = UserService();

  List<Package> _featured = [];
  String? _cityName;
  List<Occasion> _occasions = [];
  Celebration? _activeCelebration;
  Booking? _activeBooking;
  List<Guest> _guests = [];
  List<CelebrationChecklistItem> _checklist = [];
  bool _isLoading = true;
  // Tracks the separate (post-Future.wait) booking fetch so the hero card
  // can keep showing a placeholder instead of jumping straight to the
  // generic illustration fallback while the real package cover is still
  // in flight.
  bool _isBookingLoading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  /// The customer's city, taken from their default (or first) saved address.
  Future<String?> _loadCity() async {
    if (!AuthManager.instance.isAuthenticated) return null;
    try {
      final addresses = await _userService.getAddresses();
      if (addresses.isEmpty) return null;
      final address = addresses.firstWhere((a) => a.isDefault, orElse: () => addresses.first);
      final city = address.city.trim();
      return city.isEmpty ? null : city;
    } catch (e) {
      debugPrint('Error loading addresses: $e');
      return null;
    }
  }

  /// Featured packages, preferring the customer's city. Falls back to
  /// unfiltered featured packages when the city yields nothing (e.g. the
  /// free-text address city doesn't match any serviceable city slug).
  Future<List<Package>> _loadFeatured(String? city) async {
    try {
      if (city != null) {
        final slug = city.toLowerCase().replaceAll(RegExp(r'\s+'), '-');
        final inCity = await _packageService.listPackages(featured: true, city: slug);
        if (inCity.isNotEmpty) return inCity;
      }
      return await _packageService.listPackages(featured: true);
    } catch (e) {
      debugPrint('Error loading packages: $e');
      return <Package>[];
    }
  }

  Future<void> _loadData() async {
    try {
      final city = await _loadCity();
      final results = await Future.wait([
        _loadFeatured(city),
        _packageService.listOccasions().catchError((e) {
          debugPrint('Error loading occasions: $e');
          return <Occasion>[];
        }),
        _celebrationService.listCelebrations().catchError((e) {
          debugPrint('Error loading celebrations: $e');
          return <Celebration>[];
        }),
      ]);

      setState(() {
        _cityName = city;
        _featured = results[0] as List<Package>;
        _occasions = results[1] as List<Occasion>;
        final celebrations = results[2] as List<Celebration>;
        if (celebrations.isNotEmpty) {
          _activeCelebration = celebrations.first;
          _isBookingLoading = true;
          _loadGuests(_activeCelebration!.id);
          _loadChecklist(_activeCelebration!.id);
          _loadActiveBooking(_activeCelebration!.id);
        }
        _isLoading = false;
        _error = null;
      });
    } catch (e) {
      if (mounted) setState(() { _error = 'Could not load home data.'; _isLoading = false; });
    }
  }

  Future<void> _loadGuests(String celebrationId) async {
    try {
      final guests = await _celebrationService.listGuests(celebrationId);
      setState(() => _guests = guests);
    } catch (e) {
      debugPrint('Error loading guests: $e');
    }
  }

  Future<void> _loadChecklist(String celebrationId) async {
    try {
      final checklist = await _celebrationService.listChecklist(celebrationId);
      setState(() => _checklist = checklist);
    } catch (e) {
      debugPrint('Error loading checklist: $e');
    }
  }

  Future<void> _loadActiveBooking(String celebrationId) async {
    try {
      final bookings = await _bookingService.listByCelebration(celebrationId);
      if (mounted) {
        setState(() {
          if (bookings.isNotEmpty) _activeBooking = bookings.first;
          _isBookingLoading = false;
        });
      }
    } catch (e) {
      debugPrint('Error loading active booking: $e');
      if (mounted) setState(() => _isBookingLoading = false);
    }
  }

  void _push(BuildContext context, Widget page, {String? authAction}) {
    if (authAction != null) {
      AuthManager.instance.checkAuth(
        context,
        action: authAction,
        onAuthenticated: () =>
            Navigator.of(context).push(MaterialPageRoute(builder: (_) => page)).then((_) => _loadData()),
      );
    } else {
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => page)).then((_) => _loadData());
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final resp = context.resp;

    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return TyStateScreen.error(onAction: _loadData);
    }

    final totalGuests = _guests.length;
    final rsvpdGuests = _guests.where((g) => g.rsvpStatus == 'confirmed').length;
    final pct = _activeCelebration?.completionPercentage ?? 0;
    final pendingTasks = _checklist.where((t) => !t.isCompleted).toList();

    return RefreshIndicator(
      onRefresh: _loadData,
      color: ty.saffron,
      child: ListView(
        controller: widget.scrollController,
        padding: EdgeInsets.only(bottom: MediaQuery.of(context).padding.bottom),
        children: [
        _buildHeroCard(context, pct, totalGuests, pendingTasks.length),

        Padding(
          padding: EdgeInsets.fromLTRB(resp.w(18), resp.h(12), resp.w(18), resp.h(20)),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (_featured.isNotEmpty) ...[
                _featuredHeader(context),
                _packageRail(context, _featured),
                SizedBox(height: resp.h(12)),
              ],

              if (_occasions.isNotEmpty) ...[
                SectionHeader('Browse by Occasion'),
                _festivalRail(context, _occasions),
                SizedBox(height: resp.h(12)),
              ],

              _taskRow(
                context,
                'Manage Invitations',
                totalGuests > 0 ? '$totalGuests invited · $rsvpdGuests RSVP\'d' : 'No invitations yet',
                icon: Icons.mail_outline_rounded,
                onTap: () => _push(context, const InvitationManagementScreen(), authAction: 'manage invitations'),
              ),
              SizedBox(height: resp.h(12)),

              _membershipBanner(context),
              SizedBox(height: resp.h(12)),

              if (_occasions.any((o) => o.category == 'major_festival')) ...[
                SectionHeader('Popular Festivals'),
                _festivalRail(context, _occasions.where((o) => o.category == 'major_festival').toList()),
                SizedBox(height: resp.h(12)),
              ],

              if (_occasions.any((o) => o.category == 'life_event')) ...[
                SectionHeader('Life Moments'),
                _festivalRail(context, _occasions.where((o) => o.category == 'life_event').toList()),
                SizedBox(height: resp.h(12)),
              ],

              if (_occasions.any((o) => o.category == 'minor_festival')) ...[
                SectionHeader('Upcoming Celebrations'),
                _festivalRail(context, _occasions.where((o) => o.category == 'minor_festival').toList()),
              ],
            ],
          ),
        ),
      ],
    ),
  );
}

  Widget _buildHeroCard(BuildContext context, int pct, int totalGuests, int pendingTaskCount) {
    final ty = context.ty;
    final resp = context.resp;
    final double radius = resp.w(42.0);
    
    final title = _activeCelebration?.title ?? 'Start Planning';
    final dt = _activeCelebration?.celebrationDate;
    final date = dt != null ? '${dt.day}/${dt.month}/${dt.year}' : '';
    final location = _activeCelebration?.venueAddress ?? 'Select Location';
    
    // Resolve hero image and display name from occasions list if needed.
    // _activeCelebration.category is the raw category_id UUID (backend does
    // not nest the occasion object in CelebrationResponse) — never shown to
    // the user directly. Look up the matching Occasion for a human-readable name.
    String? heroUrl = _activeBooking?.packageCoverUrl ?? _activeCelebration?.heroImageUrl;
    String displayLabel = 'Celebration';

    if (_activeCelebration?.occasionId != null) {
      final occ = _occasions.cast<Occasion?>().firstWhere(
        (o) => o?.id == _activeCelebration?.occasionId,
        orElse: () => null
      );
      if (occ != null) {
        heroUrl ??= occ.heroImageUrl;
        displayLabel = occ.name;
      }
    }

    String? statusLabel;
    Color statusColor = Colors.orange;
    if (dt != null) {
      final today = DateTime.now();
      final daysLeft = DateTime(dt.year, dt.month, dt.day)
          .difference(DateTime(today.year, today.month, today.day))
          .inDays;
      if (daysLeft < 0) {
        statusLabel = 'Completed';
        statusColor = Colors.grey;
      } else if (daysLeft == 0) {
        statusLabel = 'Today!';
        statusColor = ty.rose;
      } else if (daysLeft == 1) {
        statusLabel = 'Tomorrow';
        statusColor = Colors.orange;
      } else {
        statusLabel = '$daysLeft days left';
        statusColor = Colors.orange;
      }
    }

    return GestureDetector(
      onTap: () => _push(context, const EventHubScreen(), authAction: 'view your event hub'),
      child: SizedBox(
        height: resp.h(420),
        child: Stack(
          children: [
            Positioned.fill(
              child: ClipRRect(
                borderRadius: BorderRadius.vertical(bottom: Radius.circular(radius)),
                // While the booking (and its real package cover image) is
                // still loading, keep showing a plain placeholder instead of
                // rendering an empty-URL CachedNetworkImage — that would
                // error immediately and flash the generic illustration
                // fallback before the real cover image ever gets a chance.
                child: (heroUrl == null && _isBookingLoading)
                    ? PhotoPlaceholder(tint: 'saffron', height: resp.h(440), arch: false, radius: BorderRadius.vertical(bottom: Radius.circular(radius)))
                    : CachedNetworkImage(
                        imageUrl: heroUrl ?? '',
                        fit: BoxFit.cover,
                        placeholder: (context, url) => PhotoPlaceholder(tint: 'saffron', height: resp.h(440), arch: false, radius: BorderRadius.vertical(bottom: Radius.circular(radius))),
                        errorWidget: (context, url, error) {
                          final local = _activeCelebration?.occasionName != null
                              ? OccasionAssets.getRelatedBackground(_activeCelebration!.occasionName!)
                              : null;
                          return Image.asset(
                            local ?? 'assets/images/Landing page image.png',
                            fit: BoxFit.cover,
                          );
                        },
                      ),
              ),
            ),
            Positioned(
              top: 0,
              left: 0,
              right: 0,
              height: resp.h(200),
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      Colors.black.withOpacity(ty.isDark ? 0.6 : 0.4),
                      Colors.black.withOpacity(ty.isDark ? 0.3 : 0.1),
                      Colors.transparent,
                    ],
                    stops: const [0, 0.45, 1.0],
                  ),
                ),
              ),
            ),
            Positioned.fill(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.vertical(bottom: Radius.circular(radius)),
                  gradient: LinearGradient(
                    begin: Alignment.bottomCenter,
                    end: Alignment.topCenter,
                    colors: [
                      Colors.black.withOpacity(0.85),
                      Colors.black.withOpacity(0.20),
                      Colors.transparent,
                    ],
                    stops: const [0, 0.5, 0.8],
                  ),
                ),
              ),
            ),
            Positioned(
              left: resp.w(18),
              right: resp.w(18),
              bottom: resp.h(32),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('YOUR NEXT CELEBRATION',
                      style: TyType.eyebrow(resp.sp(11.5), color: Colors.white.withOpacity(0.7))),
                  SizedBox(height: resp.h(12)),
                  Row(children: [
                    TyPill(displayLabel),
                    SizedBox(width: resp.w(8)),
                    if (statusLabel != null)
                      TyPill(statusLabel, background: statusColor, foreground: Colors.white),
                  ]),
                  SizedBox(height: resp.h(14)),
                  Text(title, style: TyType.display(resp.sp(34), color: Colors.white)),
                  SizedBox(height: resp.h(6)),
                  Row(children: [
                    Icon(Icons.event, size: resp.sp(15), color: Colors.white70),
                    SizedBox(width: resp.w(6)),
                    Text('$date · $location',
                        style: TyType.sans(resp.sp(14), color: Colors.white70)),
                  ]),
                  SizedBox(height: resp.h(20)),
                  Row(
                    children: [
                      _stackedAvatars(context, _guests, totalGuests),
                      const Spacer(),
                      _progressChip(context, pct, pendingTaskCount),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _membershipBanner(BuildContext context) {
    final ty = context.ty;
    final resp = context.resp;
    return GestureDetector(
      onTap: () => _push(context, const MembershipPlanScreen(), authAction: 'view membership plans'),
      child: Container(
      padding: EdgeInsets.all(resp.w(20)),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [ty.saffron, ty.saffronDeep],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(resp.w(24)),
        boxShadow: [
          BoxShadow(
            color: ty.saffron.withOpacity(0.3),
            blurRadius: resp.w(15),
            offset: Offset(0, resp.h(8)),
          ),
        ],
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Upgrade to Gold',
                    style: TyType.display(resp.sp(20), color: Colors.white)),
                SizedBox(height: resp.h(4)),
                Text('Get exclusive access to premium themes and early bird discounts.',
                    style: TyType.sans(resp.sp(12), color: Colors.white.withOpacity(0.9))),
              ],
            ),
          ),
          SizedBox(width: resp.w(12)),
          Container(
            padding: EdgeInsets.symmetric(horizontal: resp.w(16), vertical: resp.h(8)),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(resp.w(12)),
            ),
            child: Text('Join Now',
                style: TyType.sans(resp.sp(13), color: ty.saffronDeep, weight: FontWeight.w700)),
          ),
        ],
      ),
      ),
    );
  }

  Widget _packageRail(BuildContext context, List<Package> packages) {
    final ty = context.ty;
    final resp = context.resp;
    return SizedBox(
      height: resp.h(185),
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: packages.length,
        separatorBuilder: (_, __) => SizedBox(width: resp.w(16)),
        itemBuilder: (context, i) {
          final p = packages[i];
          return GestureDetector(
            onTap: () => _push(context, PackageDetailScreen(package: p)),
            child: SizedBox(
              width: resp.w(180),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Stack(
                    children: [
                      ClipRRect(
                        borderRadius: BorderRadius.circular(resp.w(20)),
                        child: CachedNetworkImage(
                          imageUrl: p.coverImageUrl ?? '',
                          height: resp.h(125),
                          width: double.infinity,
                          fit: BoxFit.cover,
                          placeholder: (context, url) => PhotoPlaceholder(tint: p.tint, height: resp.h(125), arch: false),
                          errorWidget: (context, url, error) => PhotoPlaceholder(tint: p.tint, height: resp.h(125), arch: false),
                        ),
                      ),
                      Positioned(
                        top: resp.h(10),
                        right: resp.w(10),
                        child: TyPill(formatPrice(p.price)),
                      ),
                    ],
                  ),
                  SizedBox(height: resp.h(10)),
                  Text(p.name,
                      style: TyType.sans(resp.sp(15), color: ty.ink, weight: FontWeight.w700)),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _festivalRail(BuildContext context, List<Occasion> festivals) {
    final ty = context.ty;
    final resp = context.resp;
    return SizedBox(
      height: resp.h(140),
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: festivals.length,
        separatorBuilder: (_, __) => SizedBox(width: resp.w(12)),
        itemBuilder: (context, i) {
          final f = festivals[i];
          return GestureDetector(
            onTap: () => _push(context, OccasionDetailScreen(occasion: f)),
            child: SizedBox(
              width: resp.w(110),
              child: Column(
                children: [
                  Emblem(
                    icon: f.icon,
                    imageUrl: f.iconUrl,
                    tint: f.tint,
                    tintColor: f.themeColor,
                    size: resp.w(80),
                  ),
                  SizedBox(height: resp.h(8)),
                  Text(f.name,
                      textAlign: TextAlign.center,
                      maxLines: 2,
                      style: TyType.sans(resp.sp(12), color: ty.ink, weight: FontWeight.w600)),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _stackedAvatars(BuildContext context, List<Guest> guests, int total) {
    final resp = context.resp;
    if (guests.isEmpty) return const SizedBox();
    return SizedBox(
      width: resp.w(112),
      height: resp.h(30),
      child: Stack(
        children: [
          for (int i = 0; i < guests.length.clamp(0, 4); i++)
            Positioned(
              left: i * resp.w(20.0),
              child: TyAvatar(name: guests[i].name, index: i, size: resp.w(30)),
            ),
          if (total > 4)
            Positioned(
              left: 4 * resp.w(20.0) - resp.w(10),
              child: Container(
                width: resp.w(30),
                height: resp.w(30),
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.22),
                  shape: BoxShape.circle,
                  border: Border.all(color: Colors.white.withOpacity(0.5), width: 2),
                ),
                child: Text('+${total - 4}',
                    style: TextStyle(
                        color: Colors.white, fontSize: resp.sp(10.5), fontWeight: FontWeight.w700)),
              ),
            ),
        ],
      ),
    );
  }

  Widget _progressChip(BuildContext context, int pct, int left) {
    final resp = context.resp;
    return Container(
      padding: EdgeInsets.symmetric(horizontal: resp.w(10), vertical: resp.h(7)),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.16),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        children: [
          ProgressRing(
            percent: pct.toDouble(),
            size: resp.w(36),
            stroke: 4,
            color: Colors.white,
            center: Text('$pct%',
                style: TextStyle(color: Colors.white, fontSize: resp.sp(10), fontWeight: FontWeight.w700)),
          ),
          SizedBox(width: resp.w(9)),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('on track',
                  style: TextStyle(color: Colors.white, fontSize: resp.sp(11))),
              Text('$left tasks left',
                  style: TextStyle(
                      color: Colors.white, fontSize: resp.sp(11), fontWeight: FontWeight.w700)),
            ],
          ),
        ],
      ),
    );
  }

  /// "Featured Packages in `<city>`" when the customer's address city is
  /// known; otherwise "near you" with a "Set city" action that opens the
  /// address flow (home reloads on return via [_push]).
  Widget _featuredHeader(BuildContext context) {
    final canSetCity = _cityName == null && AuthManager.instance.isAuthenticated;
    return SectionHeader(
      _cityName != null
          ? 'Featured Packages in $_cityName'
          : 'Featured Packages near you',
      action: canSetCity ? 'Set city' : null,
      onAction: canSetCity
          ? () => _push(context, const ManageAddressScreen(), authAction: 'manage your address')
          : null,
    );
  }

  Widget _taskRow(BuildContext context, String title, String meta, {IconData? icon, VoidCallback? onTap}) {
    final ty = context.ty;
    final resp = context.resp;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: EdgeInsets.only(bottom: resp.h(9)),
        padding: EdgeInsets.symmetric(horizontal: resp.w(14), vertical: resp.h(12)),
        decoration: _cardDecoration(ty, resp),
        child: Row(
          children: [
            Container(
              width: resp.w(34),
              height: resp.w(34),
              decoration: BoxDecoration(
                color: ty.saffronSoft,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(icon ?? Icons.schedule_rounded, color: ty.saffronDeep, size: resp.w(17)),
            ),
            SizedBox(width: resp.w(12)),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TyType.sans(resp.sp(14), color: ty.ink, weight: FontWeight.w600)),
                  SizedBox(height: resp.h(1)),
                  Text(meta, style: TyType.sans(resp.sp(11.5), color: ty.ink3)),
                ],
              ),
            ),
            Icon(Icons.chevron_right_rounded, color: ty.ink3, size: resp.w(18)),
          ],
        ),
      ),
    );
  }

  BoxDecoration _cardDecoration(TyColors ty, TyResponsive resp) => BoxDecoration(
        color: ty.surface,
        borderRadius: BorderRadius.circular(resp.w(18)),
        border: Border.all(color: ty.line),
      );
}
