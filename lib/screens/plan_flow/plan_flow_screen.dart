import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:intl/intl.dart';
import 'package:flutter_contacts/flutter_contacts.dart' hide Address;
import 'package:permission_handler/permission_handler.dart';

import 'package:tyohaar/theme/assets.dart';
import '../../theme/colors.dart';
import '../../theme/responsive.dart';
import '../../theme/typography.dart';
import '../../data/models.dart';
import '../../data/auth_manager.dart';
import '../../data/services/package_service.dart';
import '../../data/services/user_service.dart';
import '../../data/services/booking_service.dart';
import '../../data/services/payment_service.dart';
import '../../utils/currency.dart';
import '../../utils/log.dart';
import 'package:tyohaar/screens/email_verification_screen.dart';
import 'package:tyohaar/screens/payment_screen.dart';
import 'package:tyohaar/screens/send_invitations_screen.dart';
import 'package:tyohaar/screens/manage_address_screen.dart' show AddressFormSheet;
import '../../widgets/avatar.dart';
import '../../widgets/photo_placeholder.dart';
import '../../widgets/state_screens.dart';
import '../../widgets/ty_button.dart';
import '../../widgets/ty_chip.dart';
import '../../widgets/ty_rating_stars.dart';
import '../../widgets/common.dart';
import '../../l10n/generated/app_localizations.dart';

class PlanFlowScreen extends StatefulWidget {
  final int startStep;
  const PlanFlowScreen({super.key, this.startStep = 0});

  @override
  State<PlanFlowScreen> createState() => _PlanFlowScreenState();
}

// Localized display labels — depend on BuildContext, so these are functions
// rather than top-level consts; call sites (all within this file) pass the
// context they already have available.
List<String> _colorPalettes(BuildContext context) {
  final l10n = AppLocalizations.of(context)!;
  return [
    l10n.planFlowColorGold,
    l10n.planFlowColorBlushPink,
    l10n.planFlowColorSkyBlue,
    l10n.planFlowColorSageGreen,
    l10n.planFlowColorLavender,
    l10n.planFlowColorMulticolor,
  ];
}

// Curated, reliably-stockable balloon colours — must match the backend's
// BALLOON_COLOR_PALETTE (app/core/constants.py) exactly by hex value, since
// the server only accepts booking colours drawn from that same list.
const _balloonColorPalette = <String, String>{
  'Red': '#E63946',
  'Gold': '#D4AF37',
  'Rose Gold': '#E8B4B8',
  'Pink': '#F48FB1',
  'Sky Blue': '#87CEEB',
  'Navy Blue': '#1E3A5F',
  'White': '#FFFFFF',
  'Black': '#1C1C1C',
  'Silver': '#C0C0C0',
  'Purple': '#8E44AD',
  'Green': '#2ECC71',
  'Orange': '#F39C12',
  'Yellow': '#F1C40F',
};

// Display label for a balloon colour name. The map keys above stay in
// English — they're used as stable identifiers (selection state, hex
// lookup at booking submission) — only the rendered label is localized.
String _balloonColorLabel(BuildContext context, String name) {
  final l10n = AppLocalizations.of(context)!;
  switch (name) {
    case 'Red':
      return l10n.planFlowBalloonColorRed;
    case 'Gold':
      return l10n.planFlowBalloonColorGold;
    case 'Rose Gold':
      return l10n.planFlowBalloonColorRoseGold;
    case 'Pink':
      return l10n.planFlowBalloonColorPink;
    case 'Sky Blue':
      return l10n.planFlowBalloonColorSkyBlue;
    case 'Navy Blue':
      return l10n.planFlowBalloonColorNavyBlue;
    case 'White':
      return l10n.planFlowBalloonColorWhite;
    case 'Black':
      return l10n.planFlowBalloonColorBlack;
    case 'Silver':
      return l10n.planFlowBalloonColorSilver;
    case 'Purple':
      return l10n.planFlowBalloonColorPurple;
    case 'Green':
      return l10n.planFlowBalloonColorGreen;
    case 'Orange':
      return l10n.planFlowBalloonColorOrange;
    case 'Yellow':
      return l10n.planFlowBalloonColorYellow;
    default:
      return name;
  }
}

Color _hexToColor(String hex) {
  final h = hex.replaceAll('#', '');
  return Color(int.parse('FF$h', radix: 16));
}

class _PlanFlowScreenState extends State<PlanFlowScreen> {
  final PackageService _packageService = PackageService();
  final UserService _userService = UserService();
  final BookingService _bookingService = BookingService();
  final PaymentService _paymentService = PaymentService();
  bool _isSubmitting = false;

  // Coupon entry — automatic discounts need no UI (applied silently by the
  // backend at booking creation); this only handles the optional code path.
  final _couponCtrl = TextEditingController();
  DiscountPreview? _discountPreview;
  bool _couponLoading = false;
  String? _couponError;

  // 0 Occasion · 1 Package · 2 Package Items · 3 Details (Create an Invite) · 4 Guests · 5 Summary
  static const _stepCount = 6;
  late int _step = widget.startStep.clamp(0, _stepCount - 1);

  List<Occasion> _occasions = [];
  List<Package> _packages = [];
  bool _loadingPackages = false;
  List<Address> _addresses = [];
  List<CelebrationTheme> _themes = [];
  bool _isLoading = true;
  bool _loadError = false;
  bool _packagesError = false;
  bool _itemsError = false;

  Occasion? _occasion;
  final _nameCtrl = TextEditingController();
  final _notesCtrl = TextEditingController();
  final Set<String> _vibes = {};
  final Set<String> _colorPalette = {};
  final List<PlannedGuest> _plannedGuests = [];
  Package? _pkg;
  CelebrationTheme? _theme;
  // Preset (catalog) theme vs. customer-picked balloon colours — mutually
  // exclusive; switching modes clears the other's selection.
  bool _useCustomTheme = false;
  // Selected palette colour names, in pick order. Capped at
  // _maxCustomColours: the backend only accepts a single balloon colour or a
  // two-colour combination (BookingCreate.validate_balloon_colors).
  final List<String> _balloonColors = [];
  static const int _maxCustomColours = 2;
  Address? _address;
  DateTime _eventDate = DateTime.now().add(const Duration(days: 30));

  List<PackageItem> _packageItems = [];
  bool _loadingItems = false;
  // Guards against re-triggering a fetch every frame when a package
  // genuinely has zero items — without this, the empty-list check in
  // _packageItemsStep would loop forever instead of settling on the
  // "no configurable items" message.
  bool _itemsLoadAttempted = false;
  // item.id -> chosen quantity. Presence in this map means the item is
  // included in the booking (mandatory items are always present).
  final Map<String, int> _itemQuantities = {};

  List<PackageServiceLine> _packageServices = [];
  // service.id -> chosen quantity, mirrors _itemQuantities.
  final Map<String, int> _serviceQuantities = {};

  // The balloon colour/theme step only makes sense when both the package
  // supports customization AND the selected occasion allows it — admins
  // turn this off per-occasion for religious/cultural occasions (Mehndi,
  // Haldi, Diwali, etc.) where a balloon décor setup would look out of
  // place. All other package customizations (items/services) stay
  // unaffected by this flag.
  bool get _showBalloonTheme =>
      (_pkg?.isCustomizable ?? false) && (_occasion?.allowBalloonTheme ?? true);

  // Common items/services are vendor-wide reusable add-ons shared across
  // many packages (PackageItem.isCommon doc: "attached to the package
  // rather than defined specifically for it") — they're never bundled into
  // a single package's base price, so they're always presented (and
  // priced) here as opt-in add-ons, regardless of the backend's
  // is_mandatory flag. Only package-specific items can be genuinely
  // included in the price.
  bool _isIncludedItem(PackageItem i) => i.isMandatory && !i.isCommon;
  bool _isIncludedService(PackageServiceLine s) => s.isMandatory && !s.isCommon;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() {
      _isLoading = true;
      _loadError = false;
    });
    try {
      final results = await Future.wait([
        _packageService.listOccasions(),
        _userService.getAddresses(),
        _packageService.listThemes().catchError((_) => <CelebrationTheme>[]),
      ]);
      setState(() {
        _occasions = results[0] as List<Occasion>;
        _addresses = results[1] as List<Address>;
        _themes = results[2] as List<CelebrationTheme>;
        if (_occasions.isNotEmpty) _occasion = _occasions.first;
        if (_addresses.isNotEmpty) _address = _addresses.first;
        _isLoading = false;
      });
      // Fire-and-forget: warm the on-device cache for every occasion card
      // image so the grid renders instantly (no per-card network fetch)
      // even on a fresh install where nothing has been cached yet.
      _precacheOccasionImages(_occasions);
      if (_occasion != null) _loadPackagesForOccasion(_occasion!.id);
    } catch (e) {
      logDebug('Error loading plan flow data: $e');
      setState(() { _isLoading = false; _loadError = true; });
    }
  }

  // Packages are re-fetched (not client-side filtered) whenever the selected
  // occasion changes, so "Choose your package" only ever shows packages that
  // actually apply to what the customer is celebrating.
  Future<void> _loadPackagesForOccasion(String occasionId) async {
    setState(() { _loadingPackages = true; _packagesError = false; });
    try {
      final packages = await _packageService.listPackages(occasionId: occasionId);
      if (mounted) setState(() { _packages = packages; _loadingPackages = false; });
    } catch (e) {
      logDebug('Error loading packages for occasion: $e');
      if (mounted) setState(() { _loadingPackages = false; _packagesError = true; });
    }
  }

  Future<void> _precacheOccasionImages(List<Occasion> occasions) async {
    // Occasion cards on this screen render only the 3D icon (o.iconUrl), no
    // photography — precache that, not the hero/thumbnail banners.
    final urls = occasions
        .map((o) => o.iconUrl)
        .whereType<String>()
        .where((u) => u.isNotEmpty)
        .toSet();
    for (final url in urls) {
      if (!mounted) return;
      try {
        await precacheImage(CachedNetworkImageProvider(url), context);
      } catch (_) {
        // Non-fatal — the card falls back to its bundled local asset image.
      }
    }
  }

  Future<void> _loadPackageItems() async {
    if (_pkg == null) return;
    setState(() { _loadingItems = true; _itemsError = false; _itemsLoadAttempted = true; });
    try {
      final results = await Future.wait([
        _packageService.listPackageItems(_pkg!.id),
        _packageService.listPackageServices(_pkg!.id),
      ]);
      final items = results[0] as List<PackageItem>;
      final services = results[1] as List<PackageServiceLine>;
      setState(() {
        _packageItems = items;
        _itemQuantities.clear();
        for (final i in items.where(_isIncludedItem)) {
          _itemQuantities[i.id] = i.quantity;
        }
        _packageServices = services;
        _serviceQuantities.clear();
        for (final s in services.where(_isIncludedService)) {
          _serviceQuantities[s.id] = s.quantity;
        }
        _loadingItems = false;
      });
    } catch (e) {
      logDebug('Error loading package items: $e');
      setState(() { _loadingItems = false; _itemsError = true; });
    }
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    _notesCtrl.dispose();
    _couponCtrl.dispose();
    super.dispose();
  }

  // Mandatory items and services are charged on top of Package.price by the
  // backend, so every subtotal shown to (or previewed for) the customer has
  // to count them.
  double get _includedLinesTotal {
    final items = _packageItems.where(_isIncludedItem).fold<double>(
      0, (s, i) => s + i.unitPrice * (_itemQuantities[i.id] ?? i.quantity),
    );
    final services = _packageServices.where(_isIncludedService).fold<double>(
      0, (s, svc) => s + svc.unitPrice * (_serviceQuantities[svc.id] ?? svc.quantity),
    );
    return items + services;
  }

  Future<void> _applyCoupon() async {
    final code = _couponCtrl.text.trim();
    if (code.isEmpty) return;
    setState(() { _couponLoading = true; _couponError = null; });
    try {
      final basePrice = _pkg?.price ?? 0;
      final selectedOptional = _packageItems.where((i) => !_isIncludedItem(i) && _itemQuantities.containsKey(i.id));
      final itemsTotal = selectedOptional.fold<double>(
        0, (s, i) => s + i.unitPrice * (_itemQuantities[i.id] ?? i.quantity),
      );
      final selectedOptionalServices = _packageServices.where((s) => !_isIncludedService(s) && _serviceQuantities.containsKey(s.id));
      final servicesTotal = selectedOptionalServices.fold<double>(
        0, (s, svc) => s + svc.unitPrice * (_serviceQuantities[svc.id] ?? svc.quantity),
      );
      final preview = await _paymentService.previewDiscount(
        subtotal: basePrice + _includedLinesTotal + itemsTotal + servicesTotal,
        packageId: _pkg?.id,
        occasionId: _occasion?.id,
        couponCode: code,
      );
      setState(() {
        _discountPreview = preview;
        _couponError = preview.couponError;
      });
    } catch (e) {
      setState(() => _couponError = AppLocalizations.of(context)!.planFlowCouponValidationError);
    } finally {
      if (mounted) setState(() => _couponLoading = false);
    }
  }

  void _next() {
    if (_step == 1 && _pkg != null && !_itemsLoadAttempted && !_loadingItems) {
      _loadPackageItems();
    }
    if (_step < _stepCount - 1) {
      setState(() => _step++);
    } else {
      _finish();
    }
  }

  void _back() {
    if (_step == 0) {
      Navigator.of(context).maybePop();
    } else {
      setState(() => _step--);
    }
  }

  void _jumpTo(int step) => setState(() => _step = step);

  Future<void> _finish() async {
    if (_isSubmitting) return;

    // Email verification is only required at the point of actually booking
    // an event — gate the actual booking creation call, not the planning
    // steps leading up to it.
    final user = AuthManager.instance.currentUser;
    if (user != null && user.role == 'customer' && !user.emailVerified) {
      final verified = await Navigator.push<bool>(
        context,
        MaterialPageRoute(
          builder: (_) => EmailVerificationScreen(email: user.email ?? '', popOnVerify: true),
        ),
      );
      if (verified != true || !mounted) return;
    }

    setState(() => _isSubmitting = true);
    try {
      final optionalSelected = _packageItems
          .where((i) => !_isIncludedItem(i) && _itemQuantities.containsKey(i.id))
          .map((i) => i.id)
          .toList();
      final optionalServicesSelected = _packageServices
          .where((s) => !_isIncludedService(s) && _serviceQuantities.containsKey(s.id))
          .map((s) => s.id)
          .toList();

      final notes = <String>[
        if (_vibes.isNotEmpty) 'Mood: ${_vibes.join(', ')}',
        if (_colorPalette.isNotEmpty) 'Color palette: ${_colorPalette.join(', ')}',
      ].join(' · ');

      // Custom colours are only sent when the customer actually picked some;
      // the mode is derived from how many they chose (the backend accepts
      // exactly 1 for SINGLE and exactly 2 for DUAL), so there is no separate
      // single/dual switch for them to get wrong.
      final usingCustomColours = _showBalloonTheme && _useCustomTheme && _balloonColors.isNotEmpty;
      final balloonColorsHex = _balloonColors.map((name) => _balloonColorPalette[name]!).toList();

      final booking = await _bookingService.createBooking({
        'package_id': _pkg?.id,
        'occasion_id': _occasion?.id,
        'scheduled_date': _eventDate.toIso8601String().split('T').first,
        'venue_address': _address?.fullAddress,
        'celebration_title': _nameCtrl.text.isNotEmpty ? _nameCtrl.text : 'My Celebration',
        'address_id': _address?.id,
        'theme_id': _showBalloonTheme && !_useCustomTheme ? _theme?.id : null,
        if (usingCustomColours)
          'custom_theme_colors': {
            'primary': balloonColorsHex.first,
            if (balloonColorsHex.length > 1) 'secondary': balloonColorsHex[1],
          },
        'item_ids': optionalSelected,
        'item_quantities': _itemQuantities.map((id, qty) => MapEntry(id, qty)),
        'service_ids': optionalServicesSelected,
        'service_quantities': _serviceQuantities.map((id, qty) => MapEntry(id, qty)),
        'special_instructions': notes.isNotEmpty ? notes : null,
        'customization_note': _notesCtrl.text.trim().isNotEmpty ? _notesCtrl.text.trim() : null,
        if (usingCustomColours) ...{
          'balloon_color_mode': balloonColorsHex.length > 1 ? 'dual' : 'single',
          'balloon_colors': balloonColorsHex,
        },
        if (_couponCtrl.text.trim().isNotEmpty && _couponError == null)
          'coupon_code': _couponCtrl.text.trim(),
      });
      if (!mounted) return;
      // pushReplacement (not push) so backing out of PaymentScreen can't
      // return to this resubmittable Summary step and create a duplicate
      // booking/celebration.
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (_) => PaymentScreen(
            bookingId: booking.id,
            amount: booking.totalAmount,
            packageName: _pkg?.name ?? AppLocalizations.of(context)!.planFlowDefaultPackageName,
            scheduledDate: DateFormat('d MMMM yyyy').format(_eventDate),
            celebrationId: booking.celebrationId,
            plannedGuests: _plannedGuests,
          ),
        ),
      );
    } catch (e) {
      logDebug('Error creating booking: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(AppLocalizations.of(context)!.planFlowCreateBookingError)),
        );
      }
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  int get _totalGuests => _plannedGuests.length;

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;

    if (_isLoading) {
      return Scaffold(backgroundColor: ty.paper, body: const Center(child: CircularProgressIndicator()));
    }

    if (_loadError) {
      return Scaffold(backgroundColor: ty.paper, body: TyStateScreen.error(context, onAction: _loadData));
    }

    final l10n = AppLocalizations.of(context)!;
    final titles = [
      [l10n.planFlowOccasionStepTitle, l10n.planFlowOccasionStepSubtitle],
      [l10n.planFlowPackageStepTitle, l10n.planFlowPackageStepSubtitle],
      [l10n.planFlowItemsStepTitle, l10n.planFlowItemsStepSubtitle],
      [l10n.planFlowDetailsStepTitle, l10n.planFlowDetailsStepSubtitle],
      [l10n.planFlowGuestsStepTitle, l10n.planFlowGuestsStepSubtitle],
      [l10n.planFlowSummaryStepTitle, l10n.planFlowSummaryStepSubtitle],
    ];

    return Scaffold(
      backgroundColor: ty.paper,
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(18, 12, 18, 12),
              child: Column(
                children: [
                  Row(
                    children: [
                      ChromeIconButton(
                        icon: _step == 0 ? Icons.close_rounded : Icons.chevron_left_rounded,
                        onTap: _back,
                      ),
                      const Spacer(),
                      Text(l10n.planFlowStepIndicator(_step + 1, _stepCount),
                          style: TyType.sans(12.5, color: ty.ink2, weight: FontWeight.w700)),
                      const Spacer(),
                      const SizedBox(width: 42),
                    ],
                  ),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      for (int i = 0; i < _stepCount; i++)
                        Expanded(
                          child: Container(
                            margin: EdgeInsets.only(right: i == _stepCount - 1 ? 0 : 6),
                            height: 5,
                            decoration: BoxDecoration(
                              color: i <= _step ? ty.saffron : ty.line,
                              borderRadius: BorderRadius.circular(3),
                            ),
                          ),
                        ),
                    ],
                  ),
                ],
              ),
            ),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.fromLTRB(18, 8, 18, 24),
                children: [
                  Text(titles[_step][0], style: TyType.display(29, color: ty.ink)),
                  const SizedBox(height: 6),
                  Text(titles[_step][1], style: TyType.sans(14.5, color: ty.ink2, height: 1.5)),
                  const SizedBox(height: 22),
                  _stepBody(context),
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.fromLTRB(18, 12, 18, 16),
              decoration: BoxDecoration(
                border: Border(top: BorderSide(color: ty.line2)),
              ),
              child: _footer(context),
            ),
          ],
        ),
      ),
    );
  }

  Widget _footer(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    if (_step == _stepCount - 1) {
      return TyButton(
        _isSubmitting ? l10n.planFlowCreatingBookingLabel : l10n.planFlowProceedToPaymentLabel,
        full: true,
        icon: Icons.payment_rounded,
        enabled: !_isSubmitting && _pkg != null,
        onTap: _finish,
      );
    }
    return TyButton(l10n.planFlowContinueButtonLabel,
        full: true,
        enabled: _step == 1 ? _pkg != null : true,
        icon: Icons.chevron_right_rounded,
        onTap: _next);
  }

  Widget _stepBody(BuildContext context) {
    switch (_step) {
      case 0:
        return _occasionStep(context);
      case 1:
        return _packageStep(context);
      case 2:
        return _packageItemsStep(context);
      case 3:
        return _detailsStep(context);
      case 4:
        return _guestsStep(context);
      default:
        return _summaryStep(context);
    }
  }

  // ── Step 0: Occasion ────────────────────────────────────────────────────

  Widget _occasionStep(BuildContext context) {
    final milestones = _occasions.where((o) {
      final n = o.name.toLowerCase();
      return n.contains('birth') || n.contains('anniv') || n.contains('grad') || n.contains('baby') || n.contains('shower');
    }).toList();

    final memories = _occasions.where((o) {
      final n = o.name.toLowerCase();
      return n.contains('wedding') || n.contains('mehndi') || n.contains('haldi') || n.contains('sangeet') || n.contains('marriage') || n.contains('engagement') || n.contains('roka');
    }).toList();

    final growth = _occasions.where((o) {
      final n = o.name.toLowerCase();
      return n.contains('corporate') || n.contains('annual') || n.contains('office') || n.contains('growth') || n.contains('seminar') || n.contains('workshop');
    }).toList();

    final others = _occasions.where((o) {
      return !milestones.contains(o) && !memories.contains(o) && !growth.contains(o);
    }).toList();

    final l10n = AppLocalizations.of(context)!;
    return Column(
      children: [
        if (milestones.isNotEmpty) ...[
          _occasionGroup(context, l10n.planFlowMilestonesGroupLabel, milestones),
          const SizedBox(height: 24),
        ],
        if (memories.isNotEmpty) ...[
          _occasionGroup(context, l10n.planFlowMemoriesGroupLabel, memories),
          const SizedBox(height: 24),
        ],
        if (growth.isNotEmpty) ...[
          _occasionGroup(context, l10n.planFlowGrowthGroupLabel, growth),
          const SizedBox(height: 24),
        ],
        if (others.isNotEmpty)
          _occasionGroup(context, l10n.planFlowOtherMomentsGroupLabel, others),
      ],
    );
  }

  Widget _occasionGroup(BuildContext context, String label, List<Occasion> list) {
    final ty = context.ty;
    if (list.isEmpty) return const SizedBox();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label.toUpperCase(), style: TyType.eyebrow(11, color: ty.ink3)),
        const SizedBox(height: 12),
        GridView.count(
          crossAxisCount: 2,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: 10,
          crossAxisSpacing: 10,
          childAspectRatio: 1.3,
          children: list.map((o) {
            final on = _occasion?.id == o.id;
            final c = o.themeColor ?? ty.tint(o.tint);
            final String? iconUrl = o.iconUrl;
            final bool hasIcon = iconUrl != null && iconUrl.isNotEmpty;

            return GestureDetector(
              onTap: () {
                if (_occasion?.id == o.id) return;
                setState(() {
                  _occasion = o;
                  // A package chosen for the previous occasion may not even
                  // apply to this one — clear it so the customer re-picks
                  // from the freshly filtered list rather than carrying
                  // forward a stale, possibly-mismatched selection.
                  _pkg = null;
                  _packageItems = [];
                  _itemsLoadAttempted = false;
                  _itemQuantities.clear();
                  _packageServices = [];
                  _serviceQuantities.clear();
                });
                _loadPackagesForOccasion(o.id);
              },
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                decoration: BoxDecoration(
                  // No photography here by design — occasion cards are a
                  // flat tint plus the vendor/admin-supplied 3D icon, never
                  // an AI-generated background image.
                  color: Color.alphaBlend(c.withValues(alpha: on ? 0.16 : 0.08), ty.surface),
                  borderRadius: BorderRadius.circular(18),
                  border: Border.all(color: on ? Colors.transparent : ty.line, width: 1),
                ),
                foregroundDecoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(18),
                  border: on ? Border.all(color: c, width: 2.5) : null,
                ),
                clipBehavior: Clip.antiAlias,
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(10, 10, 10, 8),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      Expanded(
                        child: Center(
                          child: hasIcon
                              ? CachedNetworkImage(
                                  imageUrl: iconUrl,
                                  fit: BoxFit.contain,
                                  errorWidget: (_, __, ___) => Icon(o.icon, size: 44, color: c),
                                  placeholder: (_, __) => Icon(o.icon, size: 44, color: c.withValues(alpha: 0.4)),
                                )
                              : Icon(o.icon, size: 44, color: c),
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        o.name,
                        textAlign: TextAlign.center,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TyType.sans(13.5, color: ty.ink, weight: FontWeight.w700),
                      ),
                    ],
                  ),
                ),
              ),
            );
          }).toList(),
        ),
      ],
    );
  }

  // ── Step 3: Details (Create an Invite) ──────────────────────────────────

  Widget _detailsStep(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final minDate = DateTime.now().add(const Duration(days: 15));
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _field(context, l10n.planFlowCelebrationNameLabel, _textInput(context, _nameCtrl)),
        Row(
          children: [
            Expanded(child: _field(context, l10n.planFlowWhenLabel,
                _staticInput(context, Icons.event, DateFormat('d MMMM yyyy').format(_eventDate),
                onTap: () async {
                  final d = await showDatePicker(
                    context: context,
                    initialDate: _eventDate.isBefore(minDate) ? minDate : _eventDate,
                    firstDate: minDate,
                    lastDate: DateTime.now().add(const Duration(days: 365)));
                  if (d != null) setState(() => _eventDate = d);
                }))),
            SizedBox(width: context.resp.w(12)),
            Expanded(child: _field(context, l10n.planFlowTimeLabel, _staticInput(context, null, l10n.planFlowDefaultEventTime))),
          ],
        ),
        _field(context, l10n.planFlowWhereLabel, _addressPicker(context)),
        _field(
          context,
          l10n.planFlowMoodLabel,
          Wrap(
            spacing: 9,
            runSpacing: 9,
            children: [l10n.planFlowVibeIntimate, l10n.planFlowVibeGrand, l10n.planFlowVibeTraditional, l10n.planFlowVibeModern]
                .map((v) => TyChip(
                      label: v,
                      active: _vibes.contains(v),
                      onTap: () => setState(() =>
                          _vibes.contains(v) ? _vibes.remove(v) : _vibes.add(v)),
                    ))
                .toList(),
          ),
        ),
        _field(
          context,
          l10n.planFlowColorPaletteLabel,
          Wrap(
            spacing: 9,
            runSpacing: 9,
            children: _colorPalettes(context)
                .map((v) => TyChip(
                      label: v,
                      active: _colorPalette.contains(v),
                      onTap: () => setState(() =>
                          _colorPalette.contains(v) ? _colorPalette.remove(v) : _colorPalette.add(v)),
                    ))
                .toList(),
          ),
        ),
        _field(
          context,
          l10n.planFlowAdditionalNotesLabel,
          _textInput(
            context,
            _notesCtrl,
            maxLines: 3,
          ),
        ),
      ],
    );
  }

  Widget _addressPicker(BuildContext context) {
    final ty = context.ty;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ..._addresses.map((addr) {
          final on = _address?.id == addr.id;
          return GestureDetector(
            onTap: () => setState(() => _address = addr),
            child: Container(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              decoration: BoxDecoration(
                color: on ? ty.saffronSoft : ty.surface,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: on ? ty.saffron : ty.line, width: on ? 1.5 : 1),
              ),
              child: Row(
                children: [
                  Icon(on ? Icons.radio_button_checked_rounded : Icons.radio_button_off_rounded,
                      size: 18, color: on ? ty.saffron : ty.ink3),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(addr.label, style: TyType.sans(13.5, color: ty.ink, weight: FontWeight.w700)),
                        Text(addr.fullAddress, style: TyType.sans(12, color: ty.ink2), maxLines: 2, overflow: TextOverflow.ellipsis),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          );
        }),
        GestureDetector(
          onTap: _openAddAddress,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
            decoration: BoxDecoration(
              color: ty.surface,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: ty.line, style: BorderStyle.solid),
            ),
            child: Row(
              children: [
                Icon(Icons.add_location_alt_outlined, size: 18, color: ty.saffron),
                const SizedBox(width: 10),
                Flexible(
                  child: Text(AppLocalizations.of(context)!.planFlowAddNewAddressLabel,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TyType.sans(13.5, color: ty.saffron, weight: FontWeight.w700)),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Future<void> _openAddAddress() async {
    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => AddressFormSheet(
        onSave: (data) async {
          final addr = await _userService.addAddress(data);
          if (mounted) setState(() { _addresses = [..._addresses, addr]; _address = addr; });
        },
      ),
    );
  }

  // ── Step 4: Guests ──────────────────────────────────────────────────────

  Widget _guestsStep(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.all(18),
          decoration: _cardDeco(ty),
          child: Row(children: [
            Text('$_totalGuests', style: TyType.display(36, color: ty.ink)),
            const SizedBox(width: 8),
            Flexible(
              child: Text(l10n.planFlowGuestsAddedLabel, style: TyType.sans(14, color: ty.ink2)),
            ),
          ]),
        ),
        const SizedBox(height: 16),
        Text(l10n.planFlowInviteViaLabel, style: TyType.eyebrow(11, color: ty.ink3)),
        const SizedBox(height: 12),
        Row(
          children: [
            _inviteMethod(context, Icons.person_add_outlined, l10n.planFlowInviteMethodManualLabel, _openAddGuestManually),
            _inviteMethod(context, Icons.contacts_outlined, l10n.planFlowInviteMethodContactsLabel, _importFromContacts),
          ],
        ),
        const SizedBox(height: 24),
        if (_plannedGuests.isNotEmpty) Text(l10n.planFlowGuestListLabel, style: TyType.eyebrow(11, color: ty.ink3)),
        const SizedBox(height: 10),
        ..._plannedGuests.asMap().entries.map((e) {
          final g = e.value;
          return Container(
            margin: const EdgeInsets.only(bottom: 10),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            decoration: _cardDeco(ty),
            child: Row(
              children: [
                TyAvatar(name: g.name, index: e.key, size: 40),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(g.name, style: TyType.sans(14.5, color: ty.ink, weight: FontWeight.w600)),
                      if (g.phone != null) Text(g.phone!, style: TyType.sans(12, color: ty.ink2)),
                    ],
                  ),
                ),
                GestureDetector(
                  onTap: () => setState(() => _plannedGuests.removeAt(e.key)),
                  child: Icon(Icons.close_rounded, size: 20, color: ty.ink3),
                ),
              ],
            ),
          );
        }),
        Text(
          l10n.planFlowInvitationsWhatsAppNotice,
          style: TyType.sans(12, color: ty.ink3, height: 1.4),
        ),
      ],
    );
  }

  Future<void> _openAddGuestManually() async {
    final nameCtrl = TextEditingController();
    final phoneCtrl = TextEditingController();
    final ty = context.ty;
    final result = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => Container(
        padding: EdgeInsets.fromLTRB(24, 24, 24, MediaQuery.of(ctx).viewInsets.bottom + 32),
        decoration: BoxDecoration(color: ty.paper, borderRadius: const BorderRadius.vertical(top: Radius.circular(32))),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(AppLocalizations.of(ctx)!.planFlowAddGuestTitle, style: TyType.display(22, color: ty.ink)),
            const SizedBox(height: 20),
            _textInput(context, nameCtrl, hintText: AppLocalizations.of(ctx)!.planFlowAddGuestNameHint),
            const SizedBox(height: 12),
            _textInput(context, phoneCtrl,
                icon: Icons.phone_outlined,
                hintText: AppLocalizations.of(ctx)!.planFlowAddGuestPhoneHint,
                helperText: AppLocalizations.of(ctx)!.planFlowAddGuestPhoneFormatHelperText),
            const SizedBox(height: 24),
            TyButton(AppLocalizations.of(ctx)!.planFlowAddGuestConfirmLabel, full: true, onTap: () => Navigator.pop(ctx, true)),
          ],
        ),
      ),
    );
    if (result == true && nameCtrl.text.trim().isNotEmpty) {
      setState(() => _plannedGuests.add(PlannedGuest(
        name: nameCtrl.text.trim(),
        phone: phoneCtrl.text.trim().isNotEmpty ? phoneCtrl.text.trim() : null,
      )));
    }
  }

  Future<void> _importFromContacts() async {
    final status = await Permission.contacts.request();
    if (!status.isGranted) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(AppLocalizations.of(context)!.planFlowContactsPermissionNeededMessage)),
        );
      }
      return;
    }
    try {
      final contacts = await FlutterContacts.getContacts(withProperties: true);
      final withPhones = contacts.where((c) => c.phones.isNotEmpty).toList();
      if (!mounted) return;
      final selected = await showModalBottomSheet<List<Contact>>(
        context: context,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        builder: (ctx) => _ContactPickerSheet(contacts: withPhones),
      );
      if (selected != null && selected.isNotEmpty) {
        setState(() {
          for (final c in selected) {
            final phone = c.phones.first.number;
            if (_plannedGuests.any((g) => g.phone == phone)) continue;
            _plannedGuests.add(PlannedGuest(name: c.displayName, phone: phone));
          }
        });
      }
    } catch (e) {
      logDebug('Contact import failed: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(AppLocalizations.of(context)!.planFlowContactsImportError)),
        );
      }
    }
  }

  Widget _inviteMethod(BuildContext context, IconData icon, String label, VoidCallback onTap) {
    final ty = context.ty;
    return Expanded(
      child: GestureDetector(
        onTap: onTap,
        child: Column(
          children: [
            Container(
              width: 50, height: 50,
              decoration: BoxDecoration(color: ty.surface2, borderRadius: BorderRadius.circular(14)),
              child: Icon(icon, color: ty.ink2, size: 22),
            ),
            const SizedBox(height: 6),
            Text(label, style: TyType.sans(10, color: ty.ink2)),
          ],
        ),
      ),
    );
  }

  // ── Step 1: Package ─────────────────────────────────────────────────────

  Widget _packageStep(BuildContext context) {
    final ty = context.ty;

    if (_loadingPackages) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 60),
        child: Center(child: CircularProgressIndicator()),
      );
    }

    if (_packagesError) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 40),
        child: TyStateScreen.error(
          context,
          onAction: () => _occasion != null ? _loadPackagesForOccasion(_occasion!.id) : null,
        ),
      );
    }

    if (_packages.isEmpty) {
      final l10n = AppLocalizations.of(context)!;
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 40),
        child: Center(
          child: Text(
            l10n.planFlowNoPackagesAvailableMessage(_occasion?.name ?? l10n.planFlowThisOccasionFallback),
            textAlign: TextAlign.center,
            style: TyType.sans(14, color: ty.ink2),
          ),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        GridView.builder(
          // A fixed mainAxisExtent (not childAspectRatio) sizes each cell to
          // what the card's content actually needs — 112px image + name +
          // optional rating row + 2-line description + CTA, plus padding —
          // regardless of screen width. childAspectRatio scales height with
          // width, so on anything wider than the ~320dp phone it was tuned
          // for, the Spacer() inside _packageCard was filling a large dead
          // gap between the description and "Expand for details".
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 2,
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            mainAxisExtent: 262,
          ),
          itemCount: _packages.length,
          itemBuilder: (context, i) => _packageCard(context, _packages[i]),
        ),
        if (_showBalloonTheme) _themeStep(context),
      ],
    );
  }

  Future<void> _toggleLikePackage(Package p) async {
    final wasLiked = p.isLiked;
    final index = _packages.indexWhere((x) => x.id == p.id);
    if (index == -1) return;
    setState(() {
      _packages[index] = p.copyWith(isLiked: !wasLiked, likeCount: p.likeCount + (wasLiked ? -1 : 1));
      if (_pkg?.id == p.id) _pkg = _packages[index];
    });
    try {
      final result = wasLiked
          ? await _packageService.unlikePackage(p.id)
          : await _packageService.likePackage(p.id);
      if (!mounted) return;
      setState(() {
        _packages[index] = _packages[index].copyWith(
          isLiked: result['is_liked'] as bool,
          likeCount: result['like_count'] as int,
        );
        if (_pkg?.id == p.id) _pkg = _packages[index];
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _packages[index] = p;
        if (_pkg?.id == p.id) _pkg = p;
      });
    }
  }

  Widget _packageCard(BuildContext context, Package p) {
    final ty = context.ty;
    final on = _pkg?.id == p.id;
    return GestureDetector(
      onTap: () => setState(() {
        _pkg = p;
        _packageItems = [];
        _itemsLoadAttempted = false;
        _packageServices = [];
        // A previously-picked theme or colour pair is meaningless if the
        // newly-selected package isn't customizable, so always start fresh
        // on reselection.
        _theme = null;
        _balloonColors.clear();
      }),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        curve: Curves.easeOut,
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: ty.surface,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: on ? ty.saffron : ty.line, width: on ? 2 : 1),
          boxShadow: [
            on
                ? BoxShadow(color: ty.saffron.withValues(alpha: 0.22), blurRadius: 16, offset: const Offset(0, 5))
                : BoxShadow(color: Colors.black.withValues(alpha: 0.16), blurRadius: 10, offset: const Offset(0, 3)),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Stack(
              children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(15),
                  child: SizedBox(
                    height: 112,
                    width: double.infinity,
                    child: Stack(
                      fit: StackFit.expand,
                      children: [
                        CachedNetworkImage(
                          imageUrl: p.coverImageUrl ?? '',
                          fit: BoxFit.cover,
                          placeholder: (context, url) => PhotoPlaceholder(tint: p.tint, arch: false),
                          errorWidget: (context, url, error) {
                            final local = OccasionAssets.getRelatedBackground(p.name);
                            if (local != null) return Image.asset(local, fit: BoxFit.cover);
                            return PhotoPlaceholder(tint: p.tint, arch: false);
                          },
                        ),
                        // Subtle scrim so the price pill and heart stay legible
                        // over bright photos without needing opaque chips.
                        DecoratedBox(
                          decoration: BoxDecoration(
                            gradient: LinearGradient(
                              begin: Alignment.topCenter,
                              end: Alignment.bottomCenter,
                              colors: [Colors.black.withValues(alpha: 0.28), Colors.transparent],
                              stops: const [0.0, 0.5],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                Positioned(
                  top: 8, right: 8,
                  child: TyPill(formatPrice(p.price)),
                ),
                Positioned(
                  top: 8, left: 8,
                  child: GestureDetector(
                    onTap: () => _toggleLikePackage(p),
                    child: Container(
                      padding: const EdgeInsets.all(5),
                      decoration: BoxDecoration(
                        color: Colors.black.withValues(alpha: 0.35),
                        shape: BoxShape.circle,
                      ),
                      child: Icon(
                        p.isLiked ? Icons.favorite_rounded : Icons.favorite_border_rounded,
                        size: 16,
                        color: p.isLiked ? Colors.redAccent : Colors.white,
                      ),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 11),
            Text(p.name, maxLines: 1, overflow: TextOverflow.ellipsis, style: TyType.display(16, color: ty.ink)),
            const SizedBox(height: 3),
            if ((p.averageRating ?? 0) > 0 || p.reviewCount > 0)
              Padding(
                padding: const EdgeInsets.only(bottom: 3),
                child: Row(
                  children: [
                    TyRatingStars(rating: p.averageRating ?? 0, size: 12),
                    const SizedBox(width: 4),
                    Text('(${p.reviewCount})', style: TyType.sans(10.5, color: ty.ink3)),
                  ],
                ),
              ),
            Text(p.description ?? '', maxLines: 2, overflow: TextOverflow.ellipsis, style: TyType.sans(11.5, color: ty.ink2, height: 1.35)),
            const Spacer(),
            GestureDetector(
              onTap: () => _openPackageDetail(context, p),
              child: Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(AppLocalizations.of(context)!.planFlowExpandForDetailsLabel, style: TyType.sans(11.5, color: ty.saffron, weight: FontWeight.w700)),
                    const SizedBox(width: 2),
                    Icon(Icons.arrow_forward_rounded, size: 13, color: ty.saffron),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _openPackageDetail(BuildContext context, Package p) {
    final ty = context.ty;
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => DraggableScrollableSheet(
        initialChildSize: 0.75,
        maxChildSize: 0.95,
        expand: false,
        builder: (ctx, scrollCtrl) => Container(
          decoration: BoxDecoration(color: ty.paper, borderRadius: const BorderRadius.vertical(top: Radius.circular(32))),
          child: ListView(
            controller: scrollCtrl,
            padding: const EdgeInsets.fromLTRB(24, 24, 24, 32),
            children: [
              Center(
                child: Container(
                  width: 40, height: 4,
                  decoration: BoxDecoration(color: ty.line, borderRadius: BorderRadius.circular(2)),
                ),
              ),
              const SizedBox(height: 20),
              ClipRRect(
                borderRadius: BorderRadius.circular(20),
                child: CachedNetworkImage(
                  imageUrl: p.coverImageUrl ?? '',
                  height: 180, width: double.infinity, fit: BoxFit.cover,
                  placeholder: (context, url) => PhotoPlaceholder(tint: p.tint, height: 180, arch: false),
                  errorWidget: (context, url, error) => PhotoPlaceholder(tint: p.tint, height: 180, arch: false),
                ),
              ),
              const SizedBox(height: 16),
              Text(p.name, style: TyType.display(24, color: ty.ink)),
              const SizedBox(height: 6),
              Text('₹${p.price.toStringAsFixed(0)}', style: TyType.sans(16, color: ty.saffron, weight: FontWeight.w800)),
              const SizedBox(height: 12),
              Text(p.description ?? '', style: TyType.sans(14, color: ty.ink2, height: 1.5)),
              const SizedBox(height: 24),
              TyButton(
                _pkg?.id == p.id ? AppLocalizations.of(ctx)!.planFlowSelectedLabel : AppLocalizations.of(ctx)!.planFlowSelectThisPackageLabel,
                full: true,
                enabled: _pkg?.id != p.id,
                onTap: () {
                  setState(() {
                    _pkg = p;
                    _packageItems = [];
                    _itemsLoadAttempted = false;
                    _packageServices = [];
                    // A previously-picked theme or colour pair is meaningless
                    // if the newly-selected package isn't customizable, so
                    // always start fresh on reselection.
                    _theme = null;
                    _balloonColors.clear();
                  });
                  Navigator.pop(ctx);
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _themeStep(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    return Padding(
      padding: const EdgeInsets.only(top: 20, bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(l10n.planFlowChooseBalloonColoursLabel, style: TyType.eyebrow(11, color: ty.ink3)),
          const SizedBox(height: 4),
          Text(l10n.planFlowCustomizableThemeHint,
              style: TyType.sans(12.5, color: ty.ink2)),
          const SizedBox(height: 12),
          // A preset theme and a custom colour pick are two answers to the
          // same question, so they are one either/or choice rather than two
          // stacked sections the customer can fill in contradictorily.
          Row(
            children: [
              Expanded(
                child: _themeModeTab(
                  context,
                  label: l10n.planFlowPresetThemesLabel,
                  selected: !_useCustomTheme,
                  onTap: () => setState(() {
                    _useCustomTheme = false;
                    _balloonColors.clear();
                  }),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _themeModeTab(
                  context,
                  label: l10n.planFlowCustomColourLabel,
                  selected: _useCustomTheme,
                  onTap: () => setState(() {
                    _useCustomTheme = true;
                    _theme = null;
                  }),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          if (!_useCustomTheme)
            _themes.isEmpty
                ? Text(l10n.planFlowNoPresetThemesMessage, style: TyType.sans(12.5, color: ty.ink3))
                : SizedBox(
                    height: 96,
                    child: ListView.separated(
                      scrollDirection: Axis.horizontal,
                      itemCount: _themes.length,
                      separatorBuilder: (_, __) => const SizedBox(width: 12),
                      itemBuilder: (context, i) => _presetThemeSwatch(context, _themes[i]),
                    ),
                  )
          else
            _customColourSection(context),
        ],
      ),
    );
  }

  Widget _themeModeTab(BuildContext context, {required String label, required bool selected, required VoidCallback onTap}) {
    final ty = context.ty;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 10),
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: selected ? ty.saffron.withValues(alpha: 0.12) : ty.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: selected ? ty.saffron : ty.line),
        ),
        child: Text(
          label,
          style: TyType.sans(13, color: selected ? ty.saffron : ty.ink2, weight: FontWeight.w700),
        ),
      ),
    );
  }

  Widget _presetThemeSwatch(BuildContext context, CelebrationTheme t) {
    final ty = context.ty;
    final on = _theme?.id == t.id;
    // Themes may define 1, 2, or 4 colors — render exactly the ones present
    // instead of assuming a fixed 4-color palette (single/dual-color themes
    // are as valid as full ones).
    final paletteColors = [
      t.colors['primary'],
      t.colors['secondary'],
      t.colors['accent'],
      t.colors['background'],
    ].whereType<String>().where((h) => h.isNotEmpty).map(_hexToColor).toList();
    if (paletteColors.isEmpty) paletteColors.add(ty.saffron);
    return GestureDetector(
      onTap: () => setState(() => _theme = on ? null : t),
      child: Column(
        children: [
          Container(
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(
                color: on ? ty.saffron : Colors.transparent,
                width: 3,
              ),
              boxShadow: [
                BoxShadow(
                  color: paletteColors.first.withValues(alpha: 0.35),
                  blurRadius: 8,
                  offset: const Offset(0, 3),
                ),
              ],
            ),
            child: Stack(
              alignment: Alignment.center,
              children: [
                ClipOval(
                  child: paletteColors.length == 1
                      ? Container(color: paletteColors[0])
                      : paletteColors.length == 2
                          ? Row(
                              children: [
                                Expanded(child: Container(color: paletteColors[0])),
                                Expanded(child: Container(color: paletteColors[1])),
                              ],
                            )
                          : Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Expanded(
                                  child: Row(
                                    children: [
                                      Expanded(child: Container(color: paletteColors[0])),
                                      Expanded(child: Container(color: paletteColors[1])),
                                    ],
                                  ),
                                ),
                                Expanded(
                                  child: Row(
                                    children: [
                                      Expanded(child: Container(color: paletteColors[2])),
                                      Expanded(child: Container(color: paletteColors.length > 3 ? paletteColors[3] : paletteColors[2])),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                ),
                if (on)
                  Container(
                    decoration: const BoxDecoration(
                      color: Colors.black38,
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(Icons.check_rounded, color: Colors.white),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 6),
          SizedBox(
            width: 68,
            child: Text(
              t.name,
              textAlign: TextAlign.center,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TyType.sans(11, color: ty.ink2, weight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }

  // One palette, one selection — pick a single accent colour or a two-colour
  // combination. There is no separate single/dual switch: the mode follows
  // from how many colours are picked.
  Widget _customColourSection(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(l10n.planFlowCustomColourHint, style: TyType.sans(12.5, color: ty.ink2)),
        const SizedBox(height: 14),
        Wrap(
          spacing: 12,
          runSpacing: 12,
          children: _balloonColorPalette.entries.map((entry) {
            final name = entry.key;
            final color = _hexToColor(entry.value);
            final on = _balloonColors.contains(name);
            return GestureDetector(
              onTap: () => setState(() {
                if (on) {
                  _balloonColors.remove(name);
                } else {
                  // At the cap, the oldest pick makes way for the new one so
                  // tapping a colour always visibly does something.
                  if (_balloonColors.length >= _maxCustomColours) {
                    _balloonColors.removeAt(0);
                  }
                  _balloonColors.add(name);
                }
              }),
              child: Column(
                children: [
                  Container(
                    width: 40,
                    height: 40,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      color: color,
                      shape: BoxShape.circle,
                      border: Border.all(color: on ? ty.saffron : ty.line, width: on ? 3 : 1),
                      boxShadow: on
                          ? [BoxShadow(color: ty.saffron.withValues(alpha: 0.35), blurRadius: 6, offset: const Offset(0, 2))]
                          : null,
                    ),
                    child: on
                        ? Icon(Icons.check_rounded,
                            color: color.computeLuminance() > 0.6 ? Colors.black87 : Colors.white, size: 18)
                        : null,
                  ),
                  const SizedBox(height: 4),
                  SizedBox(
                    width: 56,
                    child: Text(
                      _balloonColorLabel(context, name),
                      textAlign: TextAlign.center,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TyType.sans(10.5, color: ty.ink2),
                    ),
                  ),
                ],
              ),
            );
          }).toList(),
        ),
      ],
    );
  }

  // ── Step 2: Package Items ───────────────────────────────────────────────

  Widget _packageItemsStep(BuildContext context) {
    final ty = context.ty;
    if (_pkg == null) return const SizedBox();
    // Only ever schedule one fetch per package selection — _itemsLoadAttempted
    // flips true as soon as the request starts, so a package with genuinely
    // zero items settles on the "no configurable items" message below instead
    // of re-triggering a fetch on every rebuild forever.
    if (!_itemsLoadAttempted && !_loadingItems) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _loadPackageItems());
    }
    if (_loadingItems) return const Center(child: Padding(padding: EdgeInsets.all(40), child: CircularProgressIndicator()));
    if (_itemsError) {
      return Padding(
        padding: const EdgeInsets.all(40),
        child: TyStateScreen.error(context, onAction: _loadPackageItems),
      );
    }

    final l10n = AppLocalizations.of(context)!;
    final specificItems = _packageItems.where((i) => !i.isCommon).toList();
    final commonItems = _packageItems.where((i) => i.isCommon).toList();

    Widget section(String heading, List<PackageItem> items, {bool isCommonGroup = false}) {
      if (items.isEmpty) return const SizedBox();
      if (isCommonGroup) {
        // Common items are vendor-wide reusable add-ons, never bundled into
        // this package's price — always shown as opt-in add-ons (quantity
        // starts at 0), regardless of the backend's is_mandatory flag.
        return Padding(
          padding: const EdgeInsets.only(bottom: 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(heading, style: TyType.sans(13, color: ty.ink, weight: FontWeight.w700)),
              const SizedBox(height: 12),
              Text(l10n.planFlowAddOnsLabel, style: TyType.eyebrow(11, color: ty.ink3)),
              const SizedBox(height: 10),
              ...items.map((item) => _itemRow(context, item, locked: false)),
            ],
          ),
        );
      }
      final mandatory = items.where((i) => i.isMandatory).toList();
      final optional = items.where((i) => !i.isMandatory).toList();
      return Padding(
        padding: const EdgeInsets.only(bottom: 20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(heading, style: TyType.sans(13, color: ty.ink, weight: FontWeight.w700)),
            const SizedBox(height: 12),
            if (mandatory.isNotEmpty) ...[
              Text(l10n.planFlowIncludedLabel, style: TyType.eyebrow(11, color: ty.ink3)),
              const SizedBox(height: 10),
              ...mandatory.map((item) => _itemRow(context, item, locked: true)),
              const SizedBox(height: 20),
            ],
            if (optional.isNotEmpty) ...[
              Text(l10n.planFlowOptionalAddOnsLabel, style: TyType.eyebrow(11, color: ty.ink3)),
              const SizedBox(height: 10),
              ...optional.map((item) => _itemRow(context, item, locked: false)),
            ],
          ],
        ),
      );
    }

    final specificServices = _packageServices.where((s) => !s.isCommon).toList();
    final commonServices = _packageServices.where((s) => s.isCommon).toList();

    Widget serviceSection(String heading, List<PackageServiceLine> services, {bool isCommonGroup = false}) {
      if (services.isEmpty) return const SizedBox();
      if (isCommonGroup) {
        // Common services are vendor-wide professional services offered
        // across many packages, never bundled into this package's price —
        // always shown as opt-in add-ons (quantity starts at 0), regardless
        // of the backend's is_mandatory flag.
        return Padding(
          padding: const EdgeInsets.only(bottom: 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(heading, style: TyType.sans(13, color: ty.ink, weight: FontWeight.w700)),
              const SizedBox(height: 12),
              Text(l10n.planFlowProfessionalServicesLabel, style: TyType.eyebrow(11, color: ty.ink3)),
              const SizedBox(height: 10),
              ...services.map((service) => _serviceRow(context, service, locked: false)),
            ],
          ),
        );
      }
      final mandatory = services.where((s) => s.isMandatory).toList();
      final optional = services.where((s) => !s.isMandatory).toList();
      return Padding(
        padding: const EdgeInsets.only(bottom: 20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(heading, style: TyType.sans(13, color: ty.ink, weight: FontWeight.w700)),
            const SizedBox(height: 12),
            if (mandatory.isNotEmpty) ...[
              Text(l10n.planFlowIncludedLabel, style: TyType.eyebrow(11, color: ty.ink3)),
              const SizedBox(height: 10),
              ...mandatory.map((service) => _serviceRow(context, service, locked: true)),
              const SizedBox(height: 20),
            ],
            if (optional.isNotEmpty) ...[
              Text(l10n.planFlowOptionalAddOnsLabel, style: TyType.eyebrow(11, color: ty.ink3)),
              const SizedBox(height: 10),
              ...optional.map((service) => _serviceRow(context, service, locked: false)),
            ],
          ],
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        section(l10n.planFlowPackageSpecificItemsHeading, specificItems),
        section(l10n.planFlowCommonItemsHeading, commonItems, isCommonGroup: true),
        serviceSection(l10n.planFlowPackageSpecificServicesHeading, specificServices),
        serviceSection(l10n.planFlowCommonServicesHeading, commonServices, isCommonGroup: true),
        if (_packageItems.isEmpty && _packageServices.isEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 24),
            child: Text(l10n.planFlowNoConfigurableItemsMessage, style: TyType.sans(13, color: ty.ink3)),
          ),
      ],
    );
  }

  /// Best-effort icon for a package item/service line, keyed off its name —
  /// there's no backend category field for these (unlike Occasions, which
  /// send `icon_name`), so this fills the same visual role Emblem's IconData
  /// fallback plays there, keeping every row recognisable even with no photo.
  static IconData _lineItemIcon(String name) {
    final n = name.toLowerCase();
    if (n.contains('photo') || n.contains('video') || n.contains('camera') || n.contains('reel')) {
      return Icons.camera_alt_rounded;
    }
    if (n.contains('led') || n.contains('light')) return Icons.lightbulb_rounded;
    if (n.contains('cooler') || n.contains(' ac ') || n.contains('fan')) return Icons.ac_unit_rounded;
    if (n.contains('balloon')) return Icons.celebration_rounded;
    if (n.contains('cake')) return Icons.cake_rounded;
    if (n.contains('kite') || n.contains('prop') || n.contains('toy')) return Icons.toys_rounded;
    if (n.contains('flower') || n.contains('decor')) return Icons.local_florist_rounded;
    if (n.contains('music') || n.contains('dj') || n.contains('sound')) return Icons.music_note_rounded;
    if (n.contains('food') || n.contains('catering') || n.contains('cake')) return Icons.restaurant_rounded;
    if (n.contains('backdrop') || n.contains('banner') || n.contains('marquee') || n.contains('letter')) {
      return Icons.wallpaper_rounded;
    }
    return Icons.auto_awesome_rounded;
  }

  /// A 44×44 thumbnail for an item/service row — a real photo when one
  /// exists, otherwise a tinted tile with an icon inferred from the name
  /// (never a blank gap), matching how Occasions always show an Emblem.
  Widget _lineThumbnail(BuildContext context, {String? imageUrl, required String name}) {
    final ty = context.ty;
    final icon = _lineItemIcon(name);
    return ClipRRect(
      borderRadius: BorderRadius.circular(10),
      child: Container(
        width: 44,
        height: 44,
        color: ty.saffronSoft,
        alignment: Alignment.center,
        child: (imageUrl != null && imageUrl.isNotEmpty)
            ? CachedNetworkImage(
                imageUrl: imageUrl,
                width: 44,
                height: 44,
                fit: BoxFit.cover,
                errorWidget: (_, __, ___) => Icon(icon, color: ty.saffronDeep, size: 20),
                placeholder: (_, __) => Icon(icon, color: ty.saffronDeep, size: 20),
              )
            : Icon(icon, color: ty.saffronDeep, size: 20),
      ),
    );
  }

  Widget _itemRow(BuildContext context, PackageItem item, {required bool locked}) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final selected = _itemQuantities.containsKey(item.id);
    final qty = _itemQuantities[item.id] ?? item.quantity;
    final thumbnail = item.imageUrls.isNotEmpty ? item.imageUrls.first : item.iconUrl;

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: _cardDeco(ty),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              GestureDetector(
                onTap: item.imageUrls.length > 1 ? () => _openItemGallery(context, item) : null,
                child: _lineThumbnail(context, imageUrl: thumbnail, name: item.name),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(item.name, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w600)),
                    if (item.description != null)
                      Text(item.description!, style: TyType.sans(11.5, color: ty.ink2), maxLines: 2, overflow: TextOverflow.ellipsis),
                    // Priced on every row, mandatory ones included: they are
                    // charged on top of the package base price, so hiding
                    // their price made the running total unexplainable.
                    Text(
                      locked
                          ? l10n.planFlowItemPriceLabel(formatPrice(item.unitPrice), item.unit ?? l10n.planFlowUnitFallback)
                          : l10n.planFlowAddOnPriceLabel(formatPrice(item.unitPrice), item.unit ?? l10n.planFlowUnitFallback),
                      style: TyType.sans(12.5, color: ty.saffron, weight: FontWeight.w700),
                    ),
                  ],
                ),
              ),
              if (locked && !item.isQuantityAdjustable)
                Icon(Icons.check_circle_rounded, color: ty.saffron, size: 22)
              else if (!locked)
                Switch.adaptive(
                  value: selected,
                  activeTrackColor: ty.saffron,
                  onChanged: (v) => setState(() {
                    if (v) {
                      _itemQuantities[item.id] = item.quantity;
                    } else {
                      _itemQuantities.remove(item.id);
                    }
                  }),
                ),
            ],
          ),
          if (item.isQuantityAdjustable && (locked || selected)) ...[
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                Text(l10n.planFlowQuantityLabel(item.unit ?? ''), style: TyType.sans(12, color: ty.ink3)),
                const SizedBox(width: 10),
                _qtyStepper(
                  context,
                  value: qty,
                  min: locked ? item.quantity : item.quantity,
                  max: item.maxQuantity ?? 999,
                  onChanged: (v) => setState(() => _itemQuantities[item.id] = v),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _serviceRow(BuildContext context, PackageServiceLine service, {required bool locked}) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final selected = _serviceQuantities.containsKey(service.id);
    final qty = _serviceQuantities[service.id] ?? service.quantity;
    final thumbnail = service.imageUrls.isNotEmpty ? service.imageUrls.first : service.iconUrl;

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: _cardDeco(ty),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              GestureDetector(
                onTap: service.imageUrls.length > 1 ? () => _openServiceGallery(context, service) : null,
                child: _lineThumbnail(context, imageUrl: thumbnail, name: service.name),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(service.name, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w600)),
                    if (service.description != null)
                      Text(service.description!, style: TyType.sans(11.5, color: ty.ink2), maxLines: 2, overflow: TextOverflow.ellipsis),
                    Text(
                      locked
                          ? l10n.planFlowItemPriceLabel(formatPrice(service.unitPrice), service.unit ?? l10n.planFlowUnitFallback)
                          : l10n.planFlowAddOnPriceLabel(formatPrice(service.unitPrice), service.unit ?? l10n.planFlowUnitFallback),
                      style: TyType.sans(12.5, color: ty.saffron, weight: FontWeight.w700),
                    ),
                  ],
                ),
              ),
              if (locked && !service.isQuantityAdjustable)
                Icon(Icons.check_circle_rounded, color: ty.saffron, size: 22)
              else if (!locked)
                Switch.adaptive(
                  value: selected,
                  activeTrackColor: ty.saffron,
                  onChanged: (v) => setState(() {
                    if (v) {
                      _serviceQuantities[service.id] = service.quantity;
                    } else {
                      _serviceQuantities.remove(service.id);
                    }
                  }),
                ),
            ],
          ),
          if (service.isQuantityAdjustable && (locked || selected)) ...[
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                Text(l10n.planFlowQuantityLabel(service.unit ?? ''), style: TyType.sans(12, color: ty.ink3)),
                const SizedBox(width: 10),
                _qtyStepper(
                  context,
                  value: qty,
                  min: service.quantity,
                  max: service.maxQuantity ?? 999,
                  onChanged: (v) => setState(() => _serviceQuantities[service.id] = v),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  void _openServiceGallery(BuildContext context, PackageServiceLine service) {
    Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => _ItemImageGalleryScreen(images: service.imageUrls, title: service.name),
      fullscreenDialog: true,
    ));
  }

  Widget _qtyStepper(BuildContext context, {required int value, required int min, required int max, required ValueChanged<int> onChanged}) {
    final ty = context.ty;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 4),
      decoration: BoxDecoration(
        color: ty.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: ty.line),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          IconButton(
            visualDensity: VisualDensity.compact,
            icon: Icon(Icons.remove_circle_outline_rounded, size: 20, color: value > min ? ty.ink2 : ty.line2),
            onPressed: value > min ? () => onChanged(value - 1) : null,
          ),
          SizedBox(
            width: 28,
            child: Text('$value', textAlign: TextAlign.center, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w700)),
          ),
          IconButton(
            visualDensity: VisualDensity.compact,
            icon: Icon(Icons.add_circle_outline_rounded, size: 20, color: value < max ? ty.saffron : ty.line2),
            onPressed: value < max ? () => onChanged(value + 1) : null,
          ),
        ],
      ),
    );
  }

  void _openItemGallery(BuildContext context, PackageItem item) {
    Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => _ItemImageGalleryScreen(images: item.imageUrls, title: item.name),
      fullscreenDialog: true,
    ));
  }

  // ── Step 5: Summary ─────────────────────────────────────────────────────

  Widget _summaryStep(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final mandatoryItems = _packageItems.where(_isIncludedItem).toList();
    final selectedOptional = _packageItems.where((i) => !_isIncludedItem(i) && _itemQuantities.containsKey(i.id)).toList();
    final itemsTotal = selectedOptional.fold<double>(
      0, (s, i) => s + i.unitPrice * (_itemQuantities[i.id] ?? i.quantity),
    );
    final mandatoryServices = _packageServices.where(_isIncludedService).toList();
    final selectedOptionalServices = _packageServices.where((s) => !_isIncludedService(s) && _serviceQuantities.containsKey(s.id)).toList();
    final servicesTotal = selectedOptionalServices.fold<double>(
      0, (s, svc) => s + svc.unitPrice * (_serviceQuantities[svc.id] ?? svc.quantity),
    );
    final addOnsTotal = itemsTotal + servicesTotal;
    // Mandatory lines are billed on top of the package base price server-side
    // (BookingService: subtotal = package + mandatory + selected optional), so
    // they belong in the breakdown too — leaving them out made the total shown
    // here smaller than the amount charged at payment.
    final includedTotal = _includedLinesTotal;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _summaryCard(context, l10n.planFlowSummaryCelebrationLabel,
            l10n.planFlowCelebrationSummaryValue('${_occasion?.name}', _nameCtrl.text), onEdit: () => _jumpTo(0)),
        _summaryCard(context, l10n.planFlowSummaryPackageLabel, _pkg?.name ?? '', onEdit: () => _jumpTo(1)),
        if (_showBalloonTheme && !_useCustomTheme && _theme != null)
          _summaryCard(context, l10n.planFlowSummaryThemeLabel, _theme!.name, onEdit: () => _jumpTo(1)),
        if (_showBalloonTheme && _useCustomTheme && _balloonColors.isNotEmpty)
          _summaryCard(
            context,
            l10n.planFlowSummaryBalloonColoursLabel,
            _balloonColors.map((n) => _balloonColorLabel(context, n)).join(', '),
            onEdit: () => _jumpTo(1),
          ),
        if (mandatoryItems.isNotEmpty)
          _summaryCard(context, l10n.planFlowSummaryIncludedItemsLabel,
              mandatoryItems.map((i) => i.name).join(', '), onEdit: () => _jumpTo(2)),
        if (mandatoryServices.isNotEmpty)
          _summaryCard(context, l10n.planFlowSummaryIncludedServicesLabel,
              mandatoryServices.map((s) => s.name).join(', '), onEdit: () => _jumpTo(2)),
        if (selectedOptional.isNotEmpty || selectedOptionalServices.isNotEmpty)
          _summaryCard(context, l10n.planFlowSummaryAddOnsLabel, [
            ...selectedOptional.map((i) {
              final qty = _itemQuantities[i.id] ?? i.quantity;
              return qty > 1 ? l10n.planFlowAddOnQuantityLabel(i.name, qty) : i.name;
            }),
            ...selectedOptionalServices.map((s) {
              final qty = _serviceQuantities[s.id] ?? s.quantity;
              return qty > 1 ? l10n.planFlowAddOnQuantityLabel(s.name, qty) : s.name;
            }),
          ].join(', '), onEdit: () => _jumpTo(2)),
        _summaryCard(context, l10n.planFlowSummaryDateTimeLabel,
            l10n.planFlowDateTimeSummaryValue(DateFormat('d MMMM yyyy').format(_eventDate), l10n.planFlowDefaultEventTime),
            onEdit: () => _jumpTo(3)),
        _summaryCard(context, l10n.planFlowSummaryGuestCountLabel, l10n.planFlowGuestCountValue(_totalGuests), onEdit: () => _jumpTo(4)),
        const SizedBox(height: 16),
        _sectionHeader(l10n.planFlowAddressSectionHeader),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: _cardDeco(ty),
          child: Column(
            children: [
              if (_addresses.isEmpty)
                TyButton(l10n.planFlowAddAddressButtonLabel, kind: TyButtonKind.ghost, leadingIcon: Icons.add_location_alt_outlined, onTap: _openAddAddress)
              else
                RadioGroup<Address>(
                  groupValue: _address,
                  onChanged: (v) => setState(() => _address = v!),
                  child: Column(
                    children: _addresses.map((addr) => RadioListTile<Address>(
                          value: addr,
                          activeColor: ty.saffron,
                          contentPadding: EdgeInsets.zero,
                          title: Text(addr.label, style: TyType.sans(14, weight: FontWeight.w700)),
                          subtitle: Text(addr.fullAddress, style: TyType.sans(12, color: ty.ink2)),
                        )).toList(),
                  ),
                ),
            ],
          ),
        ),
        const SizedBox(height: 24),
        _sectionHeader(l10n.planFlowPromoCodeSectionHeader),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: _cardDeco(ty),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _couponCtrl,
                      textCapitalization: TextCapitalization.characters,
                      decoration: InputDecoration(
                        hintText: l10n.planFlowPromoCodeHint,
                        border: const OutlineInputBorder(),
                        isDense: true,
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  TyButton(
                    _couponLoading ? l10n.planFlowCheckingLabel : l10n.planFlowApplyButtonLabel,
                    kind: TyButtonKind.soft,
                    onTap: _couponLoading ? null : _applyCoupon,
                  ),
                ],
              ),
              if (_couponError != null) ...[
                const SizedBox(height: 8),
                Text(_couponError!, style: TyType.sans(12.5, color: Colors.red.shade700)),
              ],
              if (_discountPreview != null && _couponError == null && _discountPreview!.appliedDiscounts.isNotEmpty) ...[
                const SizedBox(height: 8),
                Text(
                  l10n.planFlowAppliedDiscountsLabel(
                      _discountPreview!.appliedDiscounts.map((d) => d.publicOfferTitle ?? d.title).join(', ')),
                  style: TyType.sans(12.5, color: ty.saffron, weight: FontWeight.w700),
                ),
              ],
            ],
          ),
        ),
        const SizedBox(height: 16),
        _sectionHeader(l10n.planFlowPriceBreakdownSectionHeader),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: _cardDeco(ty),
          child: Builder(builder: (context) {
            // Automatic discounts already reflect in the preview once a
            // customer reaches this step (evaluated as soon as a coupon is
            // applied); the authoritative amount is always recomputed
            // server-side at booking creation regardless of what's shown here.
            final l10n = AppLocalizations.of(context)!;
            final preview = _discountPreview;
            final hasDiscount = preview != null && _couponError == null && preview.totalDiscount > 0;
            final subtotal = (_pkg?.price ?? 0) + includedTotal + addOnsTotal;
            final tax = (hasDiscount ? (subtotal - preview.totalDiscount) : subtotal) * 0.18;
            final total = hasDiscount ? (subtotal - preview.totalDiscount) + tax : subtotal + tax;
            return Column(
              children: [
                _priceRow(l10n.planFlowPackageBasePriceLabel, _pkg?.price.toInt() ?? 0),
                if (includedTotal > 0) _priceRow(l10n.planFlowSummaryIncludedItemsLabel, includedTotal.toInt()),
                if (addOnsTotal > 0) _priceRow(l10n.planFlowSummaryAddOnsLabel, addOnsTotal.toInt()),
                if (hasDiscount) _priceRow(l10n.planFlowDiscountLabel, -preview.totalDiscount.toInt()),
                _priceRow(l10n.planFlowGstLabel, tax.toInt()),
                const Divider(height: 24),
                _priceRow(l10n.planFlowTotalAmountLabel, total.toInt(), bold: true),
              ],
            );
          }),
        ),
      ],
    );
  }

  Widget _summaryCard(BuildContext context, String label, String value, {VoidCallback? onEdit}) {
    final ty = context.ty;
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: _cardDeco(ty),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label.toUpperCase(), style: TyType.eyebrow(10, color: ty.ink3)),
                const SizedBox(height: 4),
                Text(value, style: TyType.sans(14.5, color: ty.ink, weight: FontWeight.w600)),
              ],
            ),
          ),
          GestureDetector(
            onTap: onEdit,
            child: Icon(Icons.edit_outlined, size: 16, color: ty.ink3),
          ),
        ],
      ),
    );
  }

  Widget _priceRow(String label, int amount, {bool bold = false}) {
    final ty = context.ty;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Flexible(
            child: Text(label,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: TyType.sans(13, color: bold ? ty.ink : ty.ink2, weight: bold ? FontWeight.w700 : FontWeight.w500)),
          ),
          const SizedBox(width: 8),
          Text('₹$amount', style: TyType.sans(14, color: ty.ink, weight: bold ? FontWeight.w800 : FontWeight.w600)),
        ],
      ),
    );
  }

  Widget _sectionHeader(String label) {
    return Padding(
      padding: const EdgeInsets.only(left: 4, bottom: 8),
      child: Text(label.toUpperCase(), style: TyType.eyebrow(11, color: Colors.grey)),
    );
  }

  Widget _field(BuildContext context, String label, Widget child) {
    final ty = context.ty;
    final resp = context.resp;
    return Padding(
      padding: EdgeInsets.only(bottom: resp.h(18)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TyType.sans(resp.sp(12.5), color: ty.ink2, weight: FontWeight.w700)),
          SizedBox(height: resp.h(8)),
          child,
        ],
      ),
    );
  }

  Widget _textInput(BuildContext context, TextEditingController ctrl,
      {IconData? icon, int maxLines = 1, String? hintText, String? helperText}) {
    final ty = context.ty;
    final resp = context.resp;
    return TextField(
      controller: ctrl,
      maxLines: maxLines,
      style: TyType.sans(resp.sp(15.5), color: ty.ink, weight: FontWeight.w500),
      decoration: InputDecoration(
        isDense: true,
        prefixIcon: icon == null ? null : Icon(icon, size: resp.sp(18), color: ty.ink2),
        hintText: hintText,
        helperText: helperText,
        contentPadding: EdgeInsets.symmetric(horizontal: resp.w(16), vertical: resp.h(14)),
        filled: true,
        fillColor: ty.surface,
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: ty.line, width: 1.5),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: ty.saffron, width: 1.5),
        ),
      ),
    );
  }

  Widget _staticInput(BuildContext context, IconData? icon, String value, {VoidCallback? onTap}) {
    final ty = context.ty;
    final resp = context.resp;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: EdgeInsets.symmetric(horizontal: resp.w(16), vertical: resp.h(15)),
        decoration: BoxDecoration(
          color: ty.surface,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: ty.line, width: 1.5),
        ),
        child: Row(
          children: [
            if (icon != null) ...[
              Icon(icon, size: resp.sp(17), color: ty.ink2),
              SizedBox(width: resp.w(8)),
            ],
            Expanded(
              child: Text(value,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TyType.sans(resp.sp(15), color: ty.ink, weight: FontWeight.w500)),
            ),
          ],
        ),
      ),
    );
  }

  BoxDecoration _cardDeco(TyColors ty) => BoxDecoration(
        color: ty.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: ty.line),
      );
}

// The address add/edit form now lives in manage_address_screen.dart
// (AddressFormSheet) and is reused here to avoid two divergent copies.

class _ContactPickerSheet extends StatefulWidget {
  final List<Contact> contacts;
  const _ContactPickerSheet({required this.contacts});

  @override
  State<_ContactPickerSheet> createState() => _ContactPickerSheetState();
}

class _ContactPickerSheetState extends State<_ContactPickerSheet> {
  final Set<Contact> _selected = {};
  String _query = '';

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final filtered = widget.contacts
        .where((c) => c.displayName.toLowerCase().contains(_query.toLowerCase()))
        .toList();

    return DraggableScrollableSheet(
      initialChildSize: 0.85,
      maxChildSize: 0.95,
      expand: false,
      builder: (ctx, scrollCtrl) => Container(
        decoration: BoxDecoration(color: ty.paper, borderRadius: const BorderRadius.vertical(top: Radius.circular(32))),
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 0),
        child: Column(
          children: [
            Center(
              child: Container(
                width: 40, height: 4,
                decoration: BoxDecoration(color: ty.line, borderRadius: BorderRadius.circular(2)),
              ),
            ),
            const SizedBox(height: 16),
            Text(l10n.planFlowSelectGuestsTitle, style: TyType.display(20, color: ty.ink)),
            const SizedBox(height: 12),
            TextField(
              onChanged: (v) => setState(() => _query = v),
              decoration: InputDecoration(
                isDense: true,
                hintText: l10n.planFlowSearchContactsHint,
                prefixIcon: const Icon(Icons.search_rounded, size: 20),
                contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                filled: true,
                fillColor: ty.surface,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide(color: ty.line)),
              ),
            ),
            const SizedBox(height: 12),
            Expanded(
              child: ListView.builder(
                controller: scrollCtrl,
                itemCount: filtered.length,
                itemBuilder: (context, i) {
                  final c = filtered[i];
                  final on = _selected.contains(c);
                  return CheckboxListTile(
                    value: on,
                    activeColor: ty.saffron,
                    title: Text(c.displayName, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w600)),
                    subtitle: Text(c.phones.first.number, style: TyType.sans(12, color: ty.ink2)),
                    onChanged: (v) => setState(() {
                      if (v == true) {
                        _selected.add(c);
                      } else {
                        _selected.remove(c);
                      }
                    }),
                  );
                },
              ),
            ),
            Padding(
              padding: EdgeInsets.fromLTRB(0, 12, 0, MediaQuery.of(context).padding.bottom + 16),
              child: TyButton(
                _selected.isEmpty ? l10n.planFlowSelectContactsLabel : l10n.planFlowAddGuestsCountLabel(_selected.length),
                full: true,
                enabled: _selected.isNotEmpty,
                onTap: () => Navigator.pop(context, _selected.toList()),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Package item photo viewer ────────────────────────────────────────────────
// Same swipeable-slider pattern as the package detail screen's image
// gallery, scoped to a single package item's photos.

class _ItemImageGalleryScreen extends StatefulWidget {
  final List<String> images;
  final String title;
  const _ItemImageGalleryScreen({required this.images, required this.title});

  @override
  State<_ItemImageGalleryScreen> createState() => _ItemImageGalleryScreenState();
}

class _ItemImageGalleryScreenState extends State<_ItemImageGalleryScreen> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        title: Text(widget.title),
      ),
      body: Stack(
        children: [
          PageView.builder(
            itemCount: widget.images.length,
            onPageChanged: (i) => setState(() => _index = i),
            itemBuilder: (context, i) => InteractiveViewer(
              child: CachedNetworkImage(
                imageUrl: widget.images[i],
                fit: BoxFit.contain,
                width: double.infinity,
                height: double.infinity,
              ),
            ),
          ),
          if (widget.images.length > 1)
            Positioned(
              bottom: 24,
              left: 0,
              right: 0,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: List.generate(widget.images.length, (i) {
                  final active = i == _index;
                  return AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    margin: const EdgeInsets.symmetric(horizontal: 3),
                    width: active ? 18 : 6,
                    height: 6,
                    decoration: BoxDecoration(
                      color: active ? Colors.white : Colors.white.withValues(alpha: 0.5),
                      borderRadius: BorderRadius.circular(3),
                    ),
                  );
                }),
              ),
            ),
        ],
      ),
    );
  }
}
