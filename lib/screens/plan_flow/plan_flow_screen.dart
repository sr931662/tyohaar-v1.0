import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:intl/intl.dart';

import 'package:tyohaar/theme/assets.dart';
import '../../theme/colors.dart';
import '../../theme/responsive.dart';
import '../../theme/typography.dart';
import '../../data/models.dart';
import '../../data/package_units.dart';
import '../../data/auth_manager.dart';
import '../../data/services/package_service.dart';
import '../../data/services/user_service.dart';
import '../../data/services/booking_service.dart';
import '../../data/services/payment_service.dart';
import '../../utils/currency.dart';
import '../../utils/log.dart';
import 'package:tyohaar/screens/email_verification_screen.dart';
import 'package:tyohaar/screens/payment_screen.dart';
import 'package:tyohaar/screens/manage_address_screen.dart' show AddressFormSheet;
import '../../widgets/photo_placeholder.dart';
import '../../widgets/state_screens.dart';
import '../../widgets/ty_button.dart';
import '../../widgets/ty_rating_stars.dart';
import '../../widgets/common.dart';
import '../../widgets/occasion_grid.dart';
import '../../l10n/generated/app_localizations.dart';

/// Which stage of the flow a step represents — used to locate a step
/// dynamically (jump-to-edit from Summary, gating "Continue") now that the
/// step list itself is built dynamically (the Occasion step is only present
/// when no [PlanFlowScreen.initialOccasion] was supplied, and Customize is
/// only present when the selected package actually supports it).
enum _StepKind { occasion, package, items, customize, delivery, summary }

class _StepDef {
  final _StepKind kind;
  final String title;
  final String subtitle;
  final Widget Function(BuildContext) build;
  const _StepDef({required this.kind, required this.title, required this.subtitle, required this.build});
}

class PlanFlowScreen extends StatefulWidget {
  // Pre-selects an occasion chosen before entering the flow (e.g. tapped
  // directly from the home screen's occasion grid), so the flow can start on
  // the package step instead of asking the customer to pick the occasion
  // again. When omitted, the flow opens with the occasion picker.
  final Occasion? initialOccasion;
  const PlanFlowScreen({super.key, this.initialOccasion});

  @override
  State<PlanFlowScreen> createState() => _PlanFlowScreenState();
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

  // Step list is built dynamically by _steps (occasion is skipped when
  // initialOccasion is supplied; customize is skipped when the package
  // doesn't support it) — see _StepKind / _StepDef above.
  int _step = 0;

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
  Package? _pkg;
  CelebrationTheme? _theme;
  // Preset (catalog) theme vs. customer-picked balloon colours — mutually
  // exclusive; switching modes clears the other's selection.
  bool _useCustomTheme = false;
  // Selected palette colour names, in pick order. Capped at
  // _maxCustomColours: the backend accepts a single balloon colour or a
  // 2/3/4-colour combination (BookingCreate.validate_balloon_colors).
  final List<String> _balloonColors = [];
  static const int _maxCustomColours = 4;
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

  /// Mirrors the server's MAX_CUSTOMIZATION_LENGTH, so the field stops the
  /// customer at the same point the API would silently truncate them.
  static const int _maxCustomizationLength = 100;

  // item.id -> what the customer picked or typed for that item (the
  // characters wanted on a marquee letter set, say). Only ever holds ids of
  // lines that actually ask for something.
  final Map<String, String> _itemChoices = {};

  List<PackageServiceLine> _packageServices = [];
  // service.id -> chosen quantity, mirrors _itemQuantities.
  final Map<String, int> _serviceQuantities = {};
  // service.id -> picked choice, mirrors _itemChoices.
  final Map<String, String> _serviceChoices = {};

  // The balloon colour/theme step only makes sense when both the package
  // supports customization AND the selected occasion allows it — admins
  // turn this off per-occasion for religious/cultural occasions (Mehndi,
  // Haldi, Diwali, etc.) where a balloon décor setup would look out of
  // place. All other package customizations (items/services) stay
  // unaffected by this flag.
  bool get _showBalloonTheme =>
      (_pkg?.isCustomizable ?? false) && (_occasion?.allowBalloonTheme ?? true);

  // The step list is dynamic: the Occasion step only appears when no
  // initialOccasion was supplied, and Customize only appears once a
  // customizable package is selected — so both length and content shift as
  // the customer moves through the flow.
  List<_StepDef> get _steps {
    final l10n = AppLocalizations.of(context)!;
    return [
      if (widget.initialOccasion == null)
        _StepDef(
          kind: _StepKind.occasion,
          title: l10n.planFlowOccasionStepTitle,
          subtitle: l10n.planFlowOccasionStepSubtitle,
          build: _occasionStep,
        ),
      _StepDef(
        kind: _StepKind.package,
        title: l10n.planFlowPackageStepTitle,
        subtitle: l10n.planFlowPackageStepSubtitle,
        build: _packageStep,
      ),
      _StepDef(
        kind: _StepKind.items,
        title: l10n.planFlowItemsStepTitle,
        subtitle: l10n.planFlowItemsStepSubtitle,
        build: _packageItemsStep,
      ),
      if (_showBalloonTheme)
        _StepDef(
          kind: _StepKind.customize,
          title: l10n.planFlowCustomizeStepTitle,
          subtitle: l10n.planFlowCustomizeStepSubtitle,
          build: _themeStep,
        ),
      _StepDef(
        kind: _StepKind.delivery,
        title: l10n.planFlowDetailsStepTitle,
        subtitle: l10n.planFlowDetailsStepSubtitle,
        build: _deliveryStep,
      ),
      _StepDef(
        kind: _StepKind.summary,
        title: l10n.planFlowSummaryStepTitle,
        subtitle: l10n.planFlowSummaryStepSubtitle,
        build: _summaryStep,
      ),
    ];
  }

  /// Index of the first step of [kind] in the current dynamic step list, or
  /// -1 if that stage isn't part of this flow right now (e.g. Occasion when
  /// an initialOccasion was supplied, or Customize for a non-customizable
  /// package).
  int _indexOf(_StepKind kind) => _steps.indexWhere((s) => s.kind == kind);

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
        // Addresses are per-user. A guest has none and the endpoint 401s,
        // which used to take the whole screen down with it — browsing the
        // plan flow signed-out is a supported path, and the address is only
        // needed at the delivery step, which already gates on sign-in.
        if (AuthManager.instance.isAuthenticated)
          _userService.getAddresses().catchError((e) {
            logDebug('Error loading addresses: $e');
            return <Address>[];
          })
        else
          Future<List<Address>>.value(const <Address>[]),
        _packageService.listThemes().catchError((_) => <CelebrationTheme>[]),
      ]);
      setState(() {
        _occasions = results[0] as List<Occasion>;
        _addresses = results[1] as List<Address>;
        _themes = results[2] as List<CelebrationTheme>;
        if (widget.initialOccasion != null) {
          _occasion = _occasions.cast<Occasion?>().firstWhere(
                (o) => o?.id == widget.initialOccasion!.id,
                orElse: () => widget.initialOccasion,
              );
        } else if (_occasions.isNotEmpty) {
          _occasion = _occasions.first;
        }
        if (_addresses.isNotEmpty) _address = _addresses.first;
        _isLoading = false;
      });
      // Fire-and-forget: warm the on-device cache for every occasion card
      // image so the grid renders instantly (no per-card network fetch)
      // even on a fresh install where nothing has been cached yet.
      _precacheOccasionImages(_occasions);
      if (_occasion != null) _loadPackagesForOccasion(_occasion!.id);
    } catch (e, st) {
      logError('plan_flow.loadData', e, st);
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
    } catch (e, st) {
      logError('plan_flow.loadPackagesForOccasion', e, st);
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

  /// Ids of lines that are in the booking, offer choices, and have none
  /// picked. "Marquee LED, unspecified number" is not an order a vendor can
  /// fulfil, so the items step will not advance while any remain.
  List<String> get _unansweredChoices => [
        for (final i in _packageItems)
          if (i.needsCustomization &&
              _itemQuantities.containsKey(i.id) &&
              (_itemChoices[i.id]?.isEmpty ?? true))
            i.id,
        for (final s in _packageServices)
          if (s.needsCustomization &&
              _serviceQuantities.containsKey(s.id) &&
              (_serviceChoices[s.id]?.isEmpty ?? true))
            s.id,
      ];

  void _next() {
    final steps = _steps;
    if (steps[_step].kind == _StepKind.items && _unansweredChoices.isNotEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(AppLocalizations.of(context)!.planFlowChoiceRequiredMessage)),
      );
      return;
    }
    if (steps[_step].kind == _StepKind.package && _pkg != null && !_itemsLoadAttempted && !_loadingItems) {
      _loadPackageItems();
    }
    if (_step < steps.length - 1) {
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

    // A guest plans the whole celebration signed out — occasion, package,
    // add-ons, the lot — and only needs an account at the moment the booking
    // becomes real. Asking here turns what used to be a bare 401 into the
    // normal sign-in gate, and the flow resumes on this same step afterwards.
    if (!AuthManager.instance.isAuthenticated) {
      AuthManager.instance.checkAuth(
        context,
        action: AppLocalizations.of(context)!.planFlowAuthActionBookCelebration,
      );
      return;
    }

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

      // Custom colours are only sent when the customer actually picked some;
      // the mode is derived from how many they chose (the backend accepts
      // 1-4 colours: single, dual, triple, or quad), so there is no separate
      // switch for the count to get wrong.
      final usingCustomColours = _showBalloonTheme && _useCustomTheme && _balloonColors.isNotEmpty;
      final balloonColorsHex = _balloonColors.map((name) => _balloonColorPalette[name]!).toList();
      const balloonModeByCount = {1: 'single', 2: 'dual', 3: 'triple', 4: 'quad'};

      final booking = await _bookingService.createBooking({
        'package_id': _pkg?.id,
        'occasion_id': _occasion?.id,
        'scheduled_date': _eventDate.toIso8601String().split('T').first,
        'venue_address': _address?.fullAddress,
        'celebration_title': _occasion != null ? '${_occasion!.name} Celebration' : 'My Celebration',
        'address_id': _address?.id,
        'theme_id': _showBalloonTheme && !_useCustomTheme ? _theme?.id : null,
        if (usingCustomColours)
          'custom_theme_colors': {
            'primary': balloonColorsHex[0],
            if (balloonColorsHex.length > 1) 'secondary': balloonColorsHex[1],
            if (balloonColorsHex.length > 2) 'tertiary': balloonColorsHex[2],
            if (balloonColorsHex.length > 3) 'quaternary': balloonColorsHex[3],
          },
        'item_ids': optionalSelected,
        'item_quantities': _itemQuantities.map((id, qty) => MapEntry(id, qty)),
        'service_ids': optionalServicesSelected,
        'service_quantities': _serviceQuantities.map((id, qty) => MapEntry(id, qty)),
        // Only for lines actually in the booking — the maps can still hold a
        // pick for an add-on the customer selected and then switched off.
        if (_itemChoices.isNotEmpty)
          'item_customizations': {
            for (final e in _itemChoices.entries)
              if (_itemQuantities.containsKey(e.key)) e.key: e.value,
          },
        if (_serviceChoices.isNotEmpty)
          'service_customizations': {
            for (final e in _serviceChoices.entries)
              if (_serviceQuantities.containsKey(e.key)) e.key: e.value,
          },
        if (usingCustomColours) ...{
          'balloon_color_mode': balloonModeByCount[balloonColorsHex.length] ?? 'single',
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
    final steps = _steps;
    final step = _step.clamp(0, steps.length - 1);

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
                        icon: step == 0 ? Icons.close_rounded : Icons.chevron_left_rounded,
                        onTap: _back,
                      ),
                      const Spacer(),
                      Text(l10n.planFlowStepIndicator(step + 1, steps.length),
                          style: TyType.sans(12.5, color: ty.ink2, weight: FontWeight.w700)),
                      const Spacer(),
                      const SizedBox(width: 42),
                    ],
                  ),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      for (int i = 0; i < steps.length; i++)
                        Expanded(
                          child: Container(
                            margin: EdgeInsets.only(right: i == steps.length - 1 ? 0 : 6),
                            height: 5,
                            decoration: BoxDecoration(
                              color: i <= step ? ty.saffron : ty.line,
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
                  Text(steps[step].title, style: TyType.display(29, color: ty.ink)),
                  const SizedBox(height: 6),
                  Text(steps[step].subtitle, style: TyType.sans(14.5, color: ty.ink2, height: 1.5)),
                  const SizedBox(height: 22),
                  steps[step].build(context),
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.fromLTRB(18, 12, 18, 16),
              decoration: BoxDecoration(
                border: Border(top: BorderSide(color: ty.line2)),
              ),
              child: _footer(context, steps, step),
            ),
          ],
        ),
      ),
    );
  }

  Widget _footer(BuildContext context, List<_StepDef> steps, int step) {
    final l10n = AppLocalizations.of(context)!;
    if (step == steps.length - 1) {
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
        enabled: steps[step].kind == _StepKind.package ? _pkg != null : true,
        icon: Icons.chevron_right_rounded,
        onTap: _next);
  }

  // ── Step 0: Occasion ────────────────────────────────────────────────────

  Widget _occasionStep(BuildContext context) {
    return OccasionGrid(
      occasions: _occasions,
      selectedId: _occasion?.id,
      onSelect: (o) {
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
    );
  }

  // ── Step: Delivery Details ──────────────────────────────────────────────

  Widget _deliveryStep(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final minDate = DateTime.now().add(const Duration(days: 15));
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
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
    // An address is saved against an account, so this is the one planning
    // step a guest cannot complete. Ask for sign-in rather than letting the
    // save fail with a 401 after they have typed the whole thing out.
    if (!AuthManager.instance.isAuthenticated) {
      AuthManager.instance.checkAuth(
        context,
        action: AppLocalizations.of(context)!.planFlowAuthActionSaveAddress,
      );
      return;
    }

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

  // ── Step: Package ────────────────────────────────────────────────────────

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
    return Column(
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

  /// Side length of an item/service row's photo. Sized to let the product
  /// actually read on the row — these are decor pieces the customer is
  /// choosing by look, and the previous 44px chip showed little more than a
  /// colour. Still a left thumbnail rather than a package-style hero, so a
  /// list of ten add-ons stays scannable and the toggle stays in reach.
  static const double _lineThumbnailSize = 80;

  /// A photo for an item/service row — the real image when one exists,
  /// otherwise a tinted tile with an icon inferred from the name (never a
  /// blank gap), matching how Occasions always show an Emblem.
  ///
  /// [hasGallery] marks rows that open a gallery on tap, which gets a small
  /// badge so the affordance is visible rather than guessed at.
  Widget _lineThumbnail(
    BuildContext context, {
    String? imageUrl,
    required String name,
    bool hasGallery = false,
  }) {
    final ty = context.ty;
    final icon = _lineItemIcon(name);
    const size = _lineThumbnailSize;
    return Stack(
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(12),
          child: Container(
            width: size,
            height: size,
            color: ty.saffronSoft,
            alignment: Alignment.center,
            child: (imageUrl != null && imageUrl.isNotEmpty)
                ? CachedNetworkImage(
                    imageUrl: imageUrl,
                    width: size,
                    height: size,
                    fit: BoxFit.cover,
                    memCacheWidth: 240,
                    errorWidget: (_, __, ___) => Icon(icon, color: ty.saffronDeep, size: 30),
                    placeholder: (_, __) => Icon(icon, color: ty.saffronDeep, size: 30),
                  )
                : Icon(icon, color: ty.saffronDeep, size: 30),
          ),
        ),
        if (hasGallery)
          Positioned(
            right: 4,
            bottom: 4,
            child: Container(
              padding: const EdgeInsets.all(3),
              decoration: BoxDecoration(
                color: Colors.black.withValues(alpha: 0.55),
                borderRadius: BorderRadius.circular(6),
              ),
              child: const Icon(Icons.photo_library_rounded, size: 12, color: Colors.white),
            ),
          ),
      ],
    );
  }

  Widget _itemRow(BuildContext context, PackageItem item, {required bool locked}) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final selected = _itemQuantities.containsKey(item.id);
    final qty = _itemQuantities[item.id] ?? item.quantity;
    // allImageUrls, not imageUrls: the portals set an item's photo as its
    // cover_image_url, and most items have only that — reading the gallery
    // list alone left every one of them on the fallback icon.
    final images = item.allImageUrls;
    final thumbnail = images.isNotEmpty ? images.first : item.iconUrl;

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
                onTap: images.length > 1 ? () => _openItemGallery(context, item) : null,
                child: _lineThumbnail(context, imageUrl: thumbnail, name: item.name, hasGallery: images.length > 1),
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
                      // Singular: the price is for one of them, so a "sets"
                      // line must read "₹500 / set", not "₹500 / sets".
                      locked
                          ? l10n.planFlowItemPriceLabel(formatPrice(item.unitPrice), packageUnitSingular(item.unit, fallback: l10n.planFlowUnitFallback))
                          : l10n.planFlowAddOnPriceLabel(formatPrice(item.unitPrice), packageUnitSingular(item.unit, fallback: l10n.planFlowUnitFallback)),
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
          if (item.needsCustomization && (locked || selected)) ...[
            const SizedBox(height: 8),
            _customizationField(
              context,
              choices: item.choices,
              prompt: item.customizationPrompt,
              value: _itemChoices[item.id],
              onChanged: (v) => setState(() {
                if (v == null) {
                  _itemChoices.remove(item.id);
                } else {
                  _itemChoices[item.id] = v;
                }
              }),
            ),
          ],
          if (item.isQuantityAdjustable && (locked || selected)) ...[
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                Text(l10n.planFlowQuantityLabel(packageUnitLabel(item.unit).toLowerCase()), style: TyType.sans(12, color: ty.ink3)),
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

  /// Dropdown for a line whose vendor defined a set of selectable values —
  /// the number on a marquee LED being the case this was built for.
  ///
  /// The options come from the line itself rather than anything hardcoded
  /// here, so a vendor adding a new customisable add-on in the portal needs
  /// no app change. Starts unset, and the customer must pick before the step
  /// will advance, since "Marquee LED, unspecified number" is not an order
  /// the vendor can fulfil.
  /// What the customer has to tell the vendor about a customisable line.
  ///
  /// Two shapes, decided by the line itself rather than anything named here,
  /// so adding a customisable add-on in the portal needs no app change:
  ///
  ///  * a fixed `choices` list renders a dropdown;
  ///  * otherwise a free-text box under the line's own prompt — a marquee
  ///    letter set, where the vendor needs the actual characters (letters,
  ///    numbers, symbols) and no list could cover them.
  Widget _customizationField(
    BuildContext context, {
    required List<String> choices,
    required String? prompt,
    required String? value,
    required ValueChanged<String?> onChanged,
  }) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final unanswered = value == null || value.isEmpty;

    if (choices.isNotEmpty) {
      return Row(
        mainAxisAlignment: MainAxisAlignment.end,
        children: [
          Text(l10n.planFlowChoiceLabel, style: TyType.sans(12, color: ty.ink3)),
          const SizedBox(width: 10),
          Container(
            constraints: const BoxConstraints(minWidth: 96),
            padding: const EdgeInsets.symmetric(horizontal: 12),
            decoration: BoxDecoration(
              color: ty.surface2,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                // An unanswered line is the one thing blocking this step, so
                // say so on the control itself, not only in a banner.
                color: unanswered ? ty.saffron : ty.line,
              ),
            ),
            child: DropdownButtonHideUnderline(
              child: DropdownButton<String>(
                value: value,
                isDense: true,
                hint: Text(l10n.planFlowChoiceHint, style: TyType.sans(12.5, color: ty.ink3)),
                style: TyType.sans(13, color: ty.ink, weight: FontWeight.w600),
                dropdownColor: ty.surface,
                items: choices
                    .map((c) => DropdownMenuItem(value: c, child: Text(c)))
                    .toList(),
                onChanged: onChanged,
              ),
            ),
          ),
        ],
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          prompt?.trim().isNotEmpty == true ? prompt!.trim() : l10n.planFlowCustomizationDefaultPrompt,
          style: TyType.sans(12, color: ty.ink3),
        ),
        const SizedBox(height: 6),
        TextFormField(
          initialValue: value,
          maxLength: _maxCustomizationLength,
          textCapitalization: TextCapitalization.characters,
          style: TyType.sans(13.5, color: ty.ink, weight: FontWeight.w600),
          decoration: InputDecoration(
            isDense: true,
            hintText: l10n.planFlowCustomizationHint,
            hintStyle: TyType.sans(12.5, color: ty.ink3),
            filled: true,
            fillColor: ty.surface2,
            counterText: '',
            contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: BorderSide(color: ty.line),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: BorderSide(color: unanswered ? ty.saffron : ty.line),
            ),
          ),
          onChanged: (v) => onChanged(v.trim().isEmpty ? null : v),
        ),
      ],
    );
  }

  Widget _serviceRow(BuildContext context, PackageServiceLine service, {required bool locked}) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final selected = _serviceQuantities.containsKey(service.id);
    final qty = _serviceQuantities[service.id] ?? service.quantity;
    final images = service.allImageUrls;
    final thumbnail = images.isNotEmpty ? images.first : service.iconUrl;

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
                onTap: images.length > 1 ? () => _openServiceGallery(context, service) : null,
                child: _lineThumbnail(context, imageUrl: thumbnail, name: service.name, hasGallery: images.length > 1),
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
                          ? l10n.planFlowItemPriceLabel(formatPrice(service.unitPrice), packageUnitSingular(service.unit, fallback: l10n.planFlowUnitFallback))
                          : l10n.planFlowAddOnPriceLabel(formatPrice(service.unitPrice), packageUnitSingular(service.unit, fallback: l10n.planFlowUnitFallback)),
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
          if (service.needsCustomization && (locked || selected)) ...[
            const SizedBox(height: 8),
            _customizationField(
              context,
              choices: service.choices,
              prompt: service.customizationPrompt,
              value: _serviceChoices[service.id],
              onChanged: (v) => setState(() {
                if (v == null) {
                  _serviceChoices.remove(service.id);
                } else {
                  _serviceChoices[service.id] = v;
                }
              }),
            ),
          ],
          if (service.isQuantityAdjustable && (locked || selected)) ...[
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                Text(l10n.planFlowQuantityLabel(packageUnitLabel(service.unit).toLowerCase()), style: TyType.sans(12, color: ty.ink3)),
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
      builder: (_) => _ItemImageGalleryScreen(images: service.allImageUrls, title: service.name),
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
      builder: (_) => _ItemImageGalleryScreen(images: item.allImageUrls, title: item.name),
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
    final occasionIdx = _indexOf(_StepKind.occasion);
    final packageIdx = _indexOf(_StepKind.package);
    final itemsIdx = _indexOf(_StepKind.items);
    final customizeIdx = _indexOf(_StepKind.customize);
    final deliveryIdx = _indexOf(_StepKind.delivery);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _summaryCard(context, l10n.planFlowSummaryCelebrationLabel, _occasion?.name ?? '',
            onEdit: occasionIdx == -1 ? null : () => _jumpTo(occasionIdx)),
        _summaryCard(context, l10n.planFlowSummaryPackageLabel, _pkg?.name ?? '', onEdit: () => _jumpTo(packageIdx)),
        if (_showBalloonTheme && !_useCustomTheme && _theme != null)
          _summaryCard(context, l10n.planFlowSummaryThemeLabel, _theme!.name, onEdit: () => _jumpTo(customizeIdx)),
        if (_showBalloonTheme && _useCustomTheme && _balloonColors.isNotEmpty)
          _summaryCard(
            context,
            l10n.planFlowSummaryBalloonColoursLabel,
            _balloonColors.map((n) => _balloonColorLabel(context, n)).join(', '),
            onEdit: () => _jumpTo(customizeIdx),
          ),
        if (mandatoryItems.isNotEmpty)
          _summaryCard(context, l10n.planFlowSummaryIncludedItemsLabel,
              mandatoryItems.map((i) => i.name).join(', '), onEdit: () => _jumpTo(itemsIdx)),
        if (mandatoryServices.isNotEmpty)
          _summaryCard(context, l10n.planFlowSummaryIncludedServicesLabel,
              mandatoryServices.map((s) => s.name).join(', '), onEdit: () => _jumpTo(itemsIdx)),
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
          ].join(', '), onEdit: () => _jumpTo(itemsIdx)),
        _summaryCard(context, l10n.planFlowSummaryDateTimeLabel,
            l10n.planFlowDateTimeSummaryValue(DateFormat('d MMMM yyyy').format(_eventDate), l10n.planFlowDefaultEventTime),
            onEdit: () => _jumpTo(deliveryIdx)),
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
