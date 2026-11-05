import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../theme/responsive.dart';
import '../data/auth_manager.dart';
import '../data/city_preference.dart';
import '../data/models.dart';
import '../data/services/package_service.dart';
import '../data/services/user_service.dart';
import '../utils/currency.dart';
import '../utils/log.dart';
import '../widgets/photo_placeholder.dart';
import '../widgets/common.dart';
import '../widgets/state_screens.dart';
import '../widgets/invitation_hero.dart';
import '../widgets/occasion_grid.dart';
import '../l10n/generated/app_localizations.dart';
import 'events/invitation_entry_screen.dart';
import 'manage_address_screen.dart';
import 'package:tyohaar/screens/package_detail_screen.dart';
import 'package:tyohaar/screens/plan_flow/plan_flow_screen.dart';

class HomeScreen extends StatefulWidget {
  final ScrollController? scrollController;
  const HomeScreen({super.key, this.scrollController});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final PackageService _packageService = PackageService();
  final UserService _userService = UserService();

  List<Package> _featured = [];
  bool _featuredIsFallback = false;
  String? _cityName;
  List<Occasion> _occasions = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadData();
    CityPreference.instance.addListener(_onCityPreferenceChanged);
  }

  @override
  void dispose() {
    CityPreference.instance.removeListener(_onCityPreferenceChanged);
    super.dispose();
  }

  void _onCityPreferenceChanged() {
    if (mounted) _loadData();
  }

  /// The city to filter packages by: the user's confirmed preference (from
  /// a GPS suggestion or the sidebar's city picker) if set, otherwise their default
  /// (or first) saved address.
  Future<String?> _loadCity() async {
    if (CityPreference.instance.activeCity != null) {
      return CityPreference.instance.activeCity;
    }
    if (!AuthManager.instance.isAuthenticated) return null;
    try {
      final addresses = await _userService.getAddresses();
      if (addresses.isEmpty) return null;
      final address = addresses.firstWhere((a) => a.isDefault, orElse: () => addresses.first);
      final city = address.city.trim();
      return city.isEmpty ? null : city;
    } catch (e) {
      logDebug('Error loading addresses: $e');
      return null;
    }
  }

  /// Featured packages for the customer's city. Never crosses into other
  /// cities' inventory: if the city is known, results are strictly scoped
  /// to it (falling back to any non-featured package in that same city, then
  /// an honest empty section — not another city's packages). Only when the
  /// city is genuinely unknown do we show generic featured packages, since
  /// there's nothing to localize by. `_featuredIsFallback` tracks whether
  /// "Popular" (any package) or "Featured" copy applies.
  Future<List<Package>> _loadFeatured(String? city) async {
    try {
      if (city != null) {
        final slug = city.toLowerCase().replaceAll(RegExp(r'\s+'), '-');
        final inCity = await _packageService.listPackages(featured: true, city: slug);
        if (inCity.isNotEmpty) {
          _featuredIsFallback = false;
          return inCity;
        }
        // Known city, nothing featured yet — stay in that city rather than
        // leaking another city's packages into a "Featured near you" rail.
        final anyInCity = await _packageService.listPackages(city: slug);
        _featuredIsFallback = true;
        return anyInCity.take(8).toList();
      }
      final featured = await _packageService.listPackages(featured: true);
      _featuredIsFallback = false;
      return featured;
    } catch (e) {
      logError('home.loadFeatured', e);
      return <Package>[];
    }
  }

  Future<void> _loadData() async {
    try {
      final city = await _loadCity();
      final results = await Future.wait([
        _loadFeatured(city),
        _packageService.listOccasions().catchError((e) {
          logDebug('Error loading occasions: $e');
          return <Occasion>[];
        }),
      ]);

      setState(() {
        _cityName = city;
        _featured = results[0] as List<Package>;
        _occasions = results[1] as List<Occasion>;
        _isLoading = false;
        _error = null;
      });
    } catch (e, st) {
      logError('home.loadData', e, st);
      if (mounted) setState(() { _error = 'Could not load home data.'; _isLoading = false; });
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
    final l10n = AppLocalizations.of(context)!;

    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return TyStateScreen.error(context, onAction: _loadData);
    }

    return RefreshIndicator(
      onRefresh: _loadData,
      color: ty.saffron,
      child: ListView(
        controller: widget.scrollController,
        padding: EdgeInsets.only(bottom: MediaQuery.of(context).padding.bottom),
        children: [
        InvitationHero(
          onExplore: () => _push(context, const InvitationEntryScreen(), authAction: l10n.homeAuthActionManageInvitations),
        ),

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
                SectionHeader(l10n.homeBrowseByOccasionHeader),
                SizedBox(height: resp.h(4)),
                OccasionGrid(
                  occasions: _occasions,
                  onSelect: (o) => _push(context, PlanFlowScreen(initialOccasion: o)),
                ),
                SizedBox(height: resp.h(12)),
              ],

            ],
          ),
        ),
      ],
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
                          memCacheWidth: 600,
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

  /// "Featured Packages in `<city>`" when the customer's address city is
  /// known; otherwise "near you" with a "Set city" action that opens the
  /// address flow (home reloads on return via [_push]).
  Widget _featuredHeader(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final canSetCity = _cityName == null && AuthManager.instance.isAuthenticated;
    final label = _featuredIsFallback ? l10n.homePopularPackagesLabel : l10n.homeFeaturedPackagesLabel;
    return SectionHeader(
      _cityName != null ? l10n.homePackagesInCityHeader(label, _cityName!) : l10n.homePackagesNearYouHeader(label),
      action: canSetCity ? l10n.homeSetCityActionLabel : null,
      onAction: canSetCity
          ? () => _push(context, const ManageAddressScreen(), authAction: l10n.homeAuthActionManageAddress)
          : null,
    );
  }

}
