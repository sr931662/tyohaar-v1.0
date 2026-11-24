import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:geolocator/geolocator.dart';

import '../../data/auth_manager.dart';
import '../../data/city_preference.dart';
import '../../data/models.dart';
import '../../data/serviceable_cities.dart';
import '../../data/services/common_service.dart';
import '../../data/services/place_search_service.dart';
import '../../l10n/generated/app_localizations.dart';
import '../../theme/colors.dart';
import '../../theme/typography.dart';
import '../../widgets/ty_button.dart';

/// Persists the address the customer filled in and returns the saved record.
typedef AddressSaver = Future<Address> Function(Map<String, dynamic> data);

/// Normalizes a 10-digit Indian mobile number to E.164 (+91XXXXXXXXXX),
/// which is what the backend's phone validator requires. Leaves already
/// E.164-formatted numbers untouched.
String? normalizeIndianPhone(String raw) {
  final trimmed = raw.trim();
  if (trimmed.isEmpty) return null;
  if (trimmed.startsWith('+')) return trimmed;
  final digitsOnly = trimmed.replaceAll(RegExp(r'[^0-9]'), '');
  if (digitsOnly.length == 10) return '+91$digitsOnly';
  if (digitsOnly.length == 12 && digitsOnly.startsWith('91')) return '+$digitsOnly';
  return '+$digitsOnly';
}

/// The "add an address" journey, in the order the best delivery apps use:
///
///  1. "Do you want this order at your current location?" — one tap if yes;
///  2. otherwise search the city and the area / street (suggestions as you type);
///  3. type only what a map can't know — house no. / tower / floor;
///  4. say who will be there: yourself or someone else.
///
/// Returns the saved [Address], or null if the customer backed out.
Future<Address?> showAddAddressFlow(BuildContext context, {required AddressSaver save}) async {
  final choice = await showModalBottomSheet<_LocationChoice>(
    context: context,
    backgroundColor: Colors.transparent,
    isScrollControlled: true,
    builder: (_) => const _LocationPromptSheet(),
  );
  if (choice == null || !context.mounted) return null;
  return Navigator.of(context).push<Address>(
    MaterialPageRoute(
      builder: (_) => AddressDetailsScreen(initialPlace: choice.place, save: save),
    ),
  );
}

/// Opens the same details screen pre-filled with an existing address.
Future<Address?> showEditAddressFlow(BuildContext context, Address existing, {required AddressSaver save}) {
  return Navigator.of(context).push<Address>(
    MaterialPageRoute(builder: (_) => AddressDetailsScreen(existing: existing, save: save)),
  );
}

// ── Step 1: current location? ────────────────────────────────────────────────

class _LocationChoice {
  /// Set when the customer chose their current location; null = "somewhere else".
  final PlaceSuggestion? place;
  const _LocationChoice(this.place);
}

class _LocationPromptSheet extends StatefulWidget {
  const _LocationPromptSheet();

  @override
  State<_LocationPromptSheet> createState() => _LocationPromptSheetState();
}

class _LocationPromptSheetState extends State<_LocationPromptSheet> {
  bool _locating = false;
  String? _problem;
  bool _needsSettings = false;
  PlaceSuggestion? _preview;

  @override
  void initState() {
    super.initState();
    // If permission was already granted, show where "current location" is
    // before the customer commits to it — no prompt, no wait.
    PlaceSearchService.instance.peekCurrentPlace().then((p) {
      if (mounted && p != null) setState(() => _preview = p);
    });
  }

  Future<void> _useCurrent() async {
    if (_locating) return;
    final l10n = AppLocalizations.of(context)!;
    setState(() { _locating = true; _problem = null; _needsSettings = false; });
    final result = await PlaceSearchService.instance.currentPlace();
    if (!mounted) return;
    if (result.status == CurrentPlaceStatus.found) {
      Navigator.pop(context, _LocationChoice(result.place));
      return;
    }
    setState(() {
      _locating = false;
      _needsSettings = result.status == CurrentPlaceStatus.permissionDeniedForever ||
          result.status == CurrentPlaceStatus.serviceOff;
      _problem = switch (result.status) {
        CurrentPlaceStatus.permissionDeniedForever => l10n.addrLocationDeniedForever,
        CurrentPlaceStatus.permissionDenied => l10n.addrLocationDenied,
        CurrentPlaceStatus.serviceOff => l10n.addrLocationServiceOff,
        _ => l10n.addrLocationFailed,
      };
    });
  }

  Future<void> _openSettings() async {
    if (_problem == AppLocalizations.of(context)!.addrLocationServiceOff) {
      await Geolocator.openLocationSettings();
    } else {
      await Geolocator.openAppSettings();
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    return Container(
      padding: EdgeInsets.fromLTRB(20, 14, 20, 20 + MediaQuery.of(context).padding.bottom),
      decoration: BoxDecoration(
        color: ty.paper,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Center(
            child: Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(color: ty.line, borderRadius: BorderRadius.circular(2)),
            ),
          ),
          const SizedBox(height: 22),
          Center(
            child: Container(
              width: 64,
              height: 64,
              decoration: BoxDecoration(color: ty.saffronSoft, shape: BoxShape.circle),
              child: Icon(Icons.my_location_rounded, color: ty.saffronDeep, size: 30),
            ),
          ),
          const SizedBox(height: 16),
          Text(l10n.addrLocationPromptTitle,
              textAlign: TextAlign.center, style: TyType.display(21, color: ty.ink)),
          const SizedBox(height: 20),
          _bigButton(
            ty,
            primary: true,
            onTap: _locating ? null : _useCurrent,
            child: _locating
                ? Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2.2, color: ty.onPrimary),
                      ),
                      const SizedBox(width: 10),
                      Text(l10n.addrLocating,
                          style: TyType.sans(14.5, color: ty.onPrimary, weight: FontWeight.w700)),
                    ],
                  )
                : Column(
                    children: [
                      Text(l10n.addrUseCurrentLocation,
                          textAlign: TextAlign.center,
                          style: TyType.sans(14.5, color: ty.onPrimary, weight: FontWeight.w700)),
                      if (_preview != null) ...[
                        const SizedBox(height: 3),
                        Text(
                          [_preview!.title, _preview!.subtitle].where((e) => e.isNotEmpty).join(', '),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          textAlign: TextAlign.center,
                          style: TyType.sans(12, color: ty.onPrimary.withValues(alpha: 0.85)),
                        ),
                      ],
                    ],
                  ),
          ),
          const SizedBox(height: 10),
          _bigButton(
            ty,
            primary: false,
            onTap: _locating ? null : () => Navigator.pop(context, const _LocationChoice(null)),
            child: Text(l10n.addrOtherLocation,
                style: TyType.sans(14.5, color: ty.ink, weight: FontWeight.w700)),
          ),
          if (_problem != null) ...[
            const SizedBox(height: 14),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(Icons.info_outline_rounded, size: 16, color: ty.rose),
                const SizedBox(width: 8),
                Expanded(child: Text(_problem!, style: TyType.sans(12.5, color: ty.ink2, height: 1.4))),
                if (_needsSettings)
                  TextButton(
                    onPressed: _openSettings,
                    style: TextButton.styleFrom(minimumSize: const Size(0, 32), padding: const EdgeInsets.symmetric(horizontal: 8)),
                    child: Text(l10n.addrOpenSettings,
                        style: TyType.sans(12.5, color: ty.saffronDeep, weight: FontWeight.w700)),
                  ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _bigButton(TyColors ty, {required bool primary, required Widget child, VoidCallback? onTap}) {
    return Material(
      color: primary ? ty.saffron : ty.surface,
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Container(
          constraints: const BoxConstraints(minHeight: 54),
          alignment: Alignment.center,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          decoration: primary
              ? null
              : BoxDecoration(borderRadius: BorderRadius.circular(16), border: Border.all(color: ty.line, width: 1.5)),
          child: child,
        ),
      ),
    );
  }
}

// ── Step 2-4: the details screen ─────────────────────────────────────────────

class AddressDetailsScreen extends StatefulWidget {
  final PlaceSuggestion? initialPlace;
  final Address? existing;
  final AddressSaver save;

  const AddressDetailsScreen({super.key, this.initialPlace, this.existing, required this.save});

  @override
  State<AddressDetailsScreen> createState() => _AddressDetailsScreenState();
}

class _AddressDetailsScreenState extends State<AddressDetailsScreen> {
  static const _mapsPrefix = 'Google Maps: ';
  static const _labelToType = {'Home': 'home', 'Work': 'work', 'Other': 'other'};

  final _houseCtrl = TextEditingController();
  final _pinCtrl = TextEditingController();
  final _mapsCtrl = TextEditingController();
  final _landmarkCtrl = TextEditingController();
  final _nameCtrl = TextEditingController();
  final _phoneCtrl = TextEditingController();
  final _scroll = ScrollController();

  String? _city;
  String? _state;
  // Headline of the chosen area/street and the extra locality text under it.
  String? _areaTitle;
  String? _areaLine;
  String? _street;
  double? _lat;
  double? _lon;

  bool _forSelf = true;
  String _label = 'Home';
  bool _saving = false;
  String? _saveError;

  String? _cityError, _areaError, _houseError, _pinError, _mapsError, _nameError, _phoneError;

  @override
  void initState() {
    super.initState();
    final existing = widget.existing;
    if (existing != null) {
      _city = existing.city;
      _state = existing.state;
      _areaLine = (existing.addressLine2?.isNotEmpty ?? false) ? existing.addressLine2 : existing.locality;
      _areaTitle = existing.locality ?? _areaLine;
      _houseCtrl.text = existing.addressLine1;
      _pinCtrl.text = existing.postalCode;
      _landmarkCtrl.text = existing.landmark ?? '';
      _lat = existing.latitude;
      _lon = existing.longitude;
      _label = const {'Home', 'Work', 'Other'}.contains(existing.label) ? existing.label : 'Home';
      final di = existing.deliveryInstructions;
      if (di != null && di.startsWith(_mapsPrefix)) _mapsCtrl.text = di.substring(_mapsPrefix.length);
      final me = AuthManager.instance.currentUser;
      final hasOther = (existing.recipientName ?? '').isNotEmpty &&
          existing.recipientName!.trim().toLowerCase() != (me?.fullName ?? me?.firstName ?? '').trim().toLowerCase();
      _forSelf = !hasOther;
      if (hasOther) {
        _nameCtrl.text = existing.recipientName ?? '';
        _phoneCtrl.text = _tenDigits(existing.recipientPhone ?? '');
      }
    } else {
      final place = widget.initialPlace;
      if (place != null) {
        _applyPlace(place, fromCurrentLocation: true);
      } else {
        // Start from the city the customer is already browsing in.
        _city = CityPreference.instance.activeCity;
      }
      // Coming from "somewhere else" with nothing chosen: go straight to the
      // area search rather than leaving an empty form to work out.
      if (place == null) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (mounted && _areaLine == null) _pickArea();
        });
      }
    }
    if (_state == null && _city != null) _resolveState(_city!);
  }

  @override
  void dispose() {
    for (final c in [_houseCtrl, _pinCtrl, _mapsCtrl, _landmarkCtrl, _nameCtrl, _phoneCtrl]) {
      c.dispose();
    }
    _scroll.dispose();
    super.dispose();
  }

  String _tenDigits(String raw) {
    final d = raw.replaceAll(RegExp(r'[^0-9]'), '');
    return d.length > 10 ? d.substring(d.length - 10) : d;
  }

  /// Applies a chosen place. A different city invalidates everything that was
  /// tied to the old one, so the form never mixes a Noida area with a Jaipur PIN.
  void _applyPlace(PlaceSuggestion p, {bool fromCurrentLocation = false}) {
    // Map data names cities inconsistently: Sector 93B comes back as "Greater
    // Noida" to someone who chose "Noida". When the two overlap by name, keep
    // what the customer chose rather than flipping their city (and resetting
    // their PIN and state) behind their back.
    final chosen = _city?.trim().toLowerCase();
    final returned = p.city?.trim().toLowerCase();
    final sameCity = chosen != null &&
        returned != null &&
        (chosen == returned || returned.contains(chosen) || chosen.contains(returned));
    final newCity = sameCity ? _city : (p.city ?? _city);
    final cityChanged = !sameCity && newCity != null && _city != null && newCity.toLowerCase() != _city!.toLowerCase();
    setState(() {
      if (cityChanged) {
        _pinCtrl.clear();
        _state = null;
      }
      _city = newCity;
      _state = p.state ?? _state;
      _areaTitle = p.title;
      _areaLine = p.areaLine;
      _street = p.street;
      _lat = p.latitude;
      _lon = p.longitude;
      if (p.postalCode != null) _pinCtrl.text = p.postalCode!;
      _areaError = null;
      _cityError = null;
      _pinError = null;
    });
    if (_pinCtrl.text.trim().isEmpty && p.latitude != null && p.longitude != null) {
      // Search results often lack a PIN; the device geocoder usually has it.
      PlaceSearchService.instance.reverse(p.latitude!, p.longitude!).then((r) {
        if (mounted && r?.postalCode != null && _pinCtrl.text.trim().isEmpty) {
          setState(() => _pinCtrl.text = r!.postalCode!);
        }
      }).catchError((_) {});
    }
    if (_state == null && _city != null) _resolveState(_city!);
  }

  Future<void> _resolveState(String city) async {
    try {
      final cities = await ServiceableCities.instance.load();
      final match = cities.where((c) => c.name.toLowerCase() == city.toLowerCase()).toList();
      if (match.isEmpty) return;
      final states = await CommonService().listStates();
      final st = states.where((s) => s.id == match.first.stateId).toList();
      if (mounted && st.isNotEmpty && _state == null && _city == city) setState(() => _state = st.first.name);
    } catch (_) {
      // The state can still come from the area search or be typed nowhere —
      // validation asks for the area, which supplies it.
    }
  }

  Future<void> _pickCity() async {
    final p = await _openPicker(_PickerMode.city);
    if (p == null || !mounted) return;
    final changed = _city == null || p.city == null || p.city!.toLowerCase() != _city!.toLowerCase();
    setState(() {
      if (changed) {
        // New city: the old area, PIN and pin-drop no longer apply.
        _areaTitle = _areaLine = _street = null;
        _lat = _lon = null;
        _pinCtrl.clear();
      }
      _city = p.city;
      _state = p.state;
      _cityError = null;
    });
    if (_state == null && _city != null) _resolveState(_city!);
    if (changed && mounted) _pickArea();
  }

  Future<void> _pickArea() async {
    final p = await _openPicker(_PickerMode.area);
    if (p == null || !mounted) return;
    _applyPlace(p);
  }

  Future<PlaceSuggestion?> _openPicker(_PickerMode mode) {
    FocusScope.of(context).unfocus();
    return showModalBottomSheet<PlaceSuggestion>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => _PlacePickerSheet(mode: mode, city: _city, nearLat: _lat, nearLon: _lon),
    );
  }

  // ── Link helpers ──────────────────────────────────────────────────────────

  /// Accepts what people actually paste: "maps.app.goo.gl/xyz" without a
  /// scheme, or a full google.com/maps URL. Returns null if it isn't a link.
  String? _normalizedLink(String raw) {
    final t = raw.trim();
    if (t.isEmpty) return '';
    final withScheme = RegExp(r'^https?://', caseSensitive: false).hasMatch(t) ? t : 'https://$t';
    final uri = Uri.tryParse(withScheme);
    if (uri == null || uri.host.isEmpty || !uri.host.contains('.') || t.contains(RegExp(r'\s'))) return null;
    return withScheme;
  }

  /// Coordinates embedded in a Google Maps URL, when it has them.
  (double, double)? _coordsFromLink(String link) {
    for (final re in [
      RegExp(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)'),
      RegExp(r'@(-?\d+\.\d+),(-?\d+\.\d+)'),
      RegExp(r'[?&](?:q|ll|query|destination)=(-?\d+\.\d+)(?:,|%2C)(-?\d+\.\d+)'),
    ]) {
      final m = re.firstMatch(link);
      if (m != null) return (double.parse(m.group(1)!), double.parse(m.group(2)!));
    }
    return null;
  }

  // ── Save ──────────────────────────────────────────────────────────────────

  bool _validate() {
    final l10n = AppLocalizations.of(context)!;
    final house = _houseCtrl.text.trim();
    final pin = _pinCtrl.text.trim();
    final link = _normalizedLink(_mapsCtrl.text);
    final phone = _phoneCtrl.text.replaceAll(RegExp(r'[^0-9]'), '');
    final hasCity = (_city ?? '').trim().isNotEmpty;
    final hasArea = (_areaLine ?? '').trim().isNotEmpty;

    setState(() {
      _cityError = hasCity ? null : l10n.addrSelectCityRequired;
      _areaError = hasArea ? null : l10n.addrSelectAreaRequired;
      _houseError = house.isEmpty ? l10n.addrHouseRequired : null;
      _pinError = RegExp(r'^\d{6}$').hasMatch(pin) ? null : l10n.addrPinInvalid;
      _mapsError = link == null ? l10n.addrMapsLinkInvalid : null;
      _nameError = (!_forSelf && _nameCtrl.text.trim().isEmpty) ? l10n.addrReceiverNameRequired : null;
      _phoneError = (!_forSelf && !RegExp(r'^[6-9]\d{9}$').hasMatch(phone)) ? l10n.addrReceiverPhoneInvalid : null;
    });
    final ok = [_cityError, _areaError, _houseError, _pinError, _mapsError, _nameError, _phoneError].every((e) => e == null);
    if (!ok && _scroll.hasClients) {
      // Errors can sit above the fold; bring the form back to the top so the
      // first one is seen rather than a button that seems to do nothing.
      final firstIsTop = _cityError != null || _areaError != null;
      if (firstIsTop) _scroll.animateTo(0, duration: const Duration(milliseconds: 250), curve: Curves.easeOut);
    }
    return ok;
  }

  Future<void> _save() async {
    if (_saving) return;
    FocusScope.of(context).unfocus();
    if (!_validate()) return;
    final l10n = AppLocalizations.of(context)!;

    final house = _houseCtrl.text.trim();
    // Line 1 = what only the customer knows (+ the street when we have it).
    var line1 = [house, if ((_street ?? '').isNotEmpty && !house.toLowerCase().contains(_street!.toLowerCase())) _street!].join(', ');
    if (widget.existing != null && house == widget.existing!.addressLine1) line1 = house;
    // The API wants at least 5 characters; a bare "12" is a valid house number.
    if (line1.length < 5 && (_areaTitle ?? '').isNotEmpty) line1 = '$line1, $_areaTitle';
    if (line1.length > 300) line1 = line1.substring(0, 300);

    final link = _normalizedLink(_mapsCtrl.text) ?? '';
    final linkCoords = link.isEmpty ? null : _coordsFromLink(link);
    final lat = linkCoords?.$1 ?? _lat;
    final lon = linkCoords?.$2 ?? _lon;

    final me = AuthManager.instance.currentUser;
    final String? recipientName;
    final String? recipientPhone;
    if (_forSelf) {
      // displayName falls back to the account id; only a real name is wanted here.
      final name = (me?.fullName ?? me?.firstName ?? '').trim();
      recipientName = name.isEmpty ? null : name;
      final digits = _tenDigits(me?.displayPhone ?? '');
      recipientPhone = RegExp(r'^[6-9]\d{9}$').hasMatch(digits) ? normalizeIndianPhone(digits) : null;
    } else {
      recipientName = _nameCtrl.text.trim();
      recipientPhone = normalizeIndianPhone(_tenDigits(_phoneCtrl.text));
    }

    setState(() { _saving = true; _saveError = null; });
    try {
      final saved = await widget.save({
        'address_type': _labelToType[_label] ?? 'other',
        'label': _label,
        if (recipientName != null) 'recipient_name': recipientName,
        if (recipientPhone != null) 'recipient_phone': recipientPhone,
        'address_line_1': line1,
        if ((_areaLine ?? '').isNotEmpty) 'address_line_2': _areaLine,
        if (_landmarkCtrl.text.trim().isNotEmpty) 'landmark': _landmarkCtrl.text.trim(),
        if ((_areaTitle ?? '').isNotEmpty) 'locality': _areaTitle,
        'city': _city!.trim(),
        'state': (_state ?? _city!).trim(),
        'postal_code': _pinCtrl.text.trim(),
        'country': 'India',
        if (lat != null) 'latitude': double.parse(lat.toStringAsFixed(7)),
        if (lon != null) 'longitude': double.parse(lon.toStringAsFixed(7)),
        if (link.isNotEmpty) 'delivery_instructions': '$_mapsPrefix$link',
      });
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l10n.manageAddressSavedMessage)));
      Navigator.pop(context, saved);
    } catch (_) {
      if (mounted) setState(() { _saving = false; _saveError = l10n.manageAddressSaveError; });
    }
  }

  // ── Build ─────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final editing = widget.existing != null;

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: AppBar(
        backgroundColor: ty.paper,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        scrolledUnderElevation: 0,
        leading: IconButton(
          icon: Icon(Icons.chevron_left_rounded, color: ty.ink, size: 28),
          onPressed: () => Navigator.of(context).maybePop(),
        ),
        title: Text(editing ? l10n.addrEditTitle : l10n.addrDetailsTitle,
            style: TyType.sans(17, color: ty.ink, weight: FontWeight.w700)),
        centerTitle: false,
      ),
      body: GestureDetector(
        behavior: HitTestBehavior.translucent,
        onTap: () => FocusScope.of(context).unfocus(),
        child: ListView(
          controller: _scroll,
          keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
          children: [
            _eyebrow(ty, l10n.addrSectionAddress),
            Container(
              decoration: _card(ty),
              child: Column(
                children: [
                  _PlaceTile(
                    icon: Icons.location_city_rounded,
                    label: l10n.addrCityLabel,
                    value: _city,
                    placeholder: l10n.addrSelect,
                    changeLabel: _city == null ? l10n.addrSelect : l10n.addrChange,
                    onTap: _pickCity,
                  ),
                  Divider(height: 1, color: ty.line2),
                  _PlaceTile(
                    icon: Icons.place_rounded,
                    label: l10n.addrAreaLabel,
                    value: _areaLine,
                    placeholder: l10n.addrAreaPlaceholder,
                    changeLabel: _areaLine == null ? l10n.addrSelect : l10n.addrChange,
                    onTap: _pickArea,
                  ),
                ],
              ),
            ),
            if (_cityError != null || _areaError != null)
              Padding(
                padding: const EdgeInsets.only(top: 6, left: 4),
                child: Text(_cityError ?? _areaError!, style: TyType.sans(12, color: ty.rose, weight: FontWeight.w600)),
              ),
            const SizedBox(height: 12),
            _field(
              ty,
              controller: _houseCtrl,
              hint: l10n.addrHouseHint,
              icon: Icons.home_outlined,
              error: _houseError,
              capitalization: TextCapitalization.words,
              action: TextInputAction.next,
              onChanged: () => _houseError = null,
            ),
            _field(
              ty,
              controller: _landmarkCtrl,
              hint: l10n.addrLandmarkHint,
              icon: Icons.flag_outlined,
              capitalization: TextCapitalization.words,
              action: TextInputAction.next,
            ),
            _field(
              ty,
              controller: _mapsCtrl,
              hint: l10n.addrMapsLinkHint,
              icon: Icons.map_outlined,
              keyboard: TextInputType.url,
              error: _mapsError,
              action: TextInputAction.next,
              onChanged: () => _mapsError = null,
            ),
            _field(
              ty,
              controller: _pinCtrl,
              hint: l10n.addrPinLabel,
              icon: Icons.pin_drop_outlined,
              keyboard: TextInputType.number,
              formatters: [FilteringTextInputFormatter.digitsOnly, LengthLimitingTextInputFormatter(6)],
              error: _pinError,
              action: TextInputAction.done,
              onChanged: () => _pinError = null,
            ),
            const SizedBox(height: 10),
            _eyebrow(ty, l10n.addrContactTitle),
            Container(
              decoration: _card(ty),
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Wrap, not Row: at large text sizes on a small phone the two
                  // options drop onto two lines instead of overflowing.
                  Wrap(
                    spacing: 22,
                    runSpacing: 4,
                    children: [
                      _radio(ty, l10n.addrMyself, _forSelf, () => setState(() => _forSelf = true)),
                      _radio(ty, l10n.addrSomeoneElse, !_forSelf, () => setState(() => _forSelf = false)),
                    ],
                  ),
                  AnimatedSize(
                    duration: const Duration(milliseconds: 200),
                    curve: Curves.easeOut,
                    alignment: Alignment.topCenter,
                    child: _forSelf
                        ? const SizedBox(width: double.infinity)
                        : Padding(
                            padding: const EdgeInsets.only(top: 14),
                            child: Column(
                              children: [
                                _field(
                                  ty,
                                  controller: _nameCtrl,
                                  hint: l10n.addrReceiverNameHint,
                                  icon: Icons.person_outline_rounded,
                                  capitalization: TextCapitalization.words,
                                  error: _nameError,
                                  action: TextInputAction.next,
                                  autofill: const [AutofillHints.name],
                                  onChanged: () => _nameError = null,
                                ),
                                _field(
                                  ty,
                                  controller: _phoneCtrl,
                                  hint: l10n.addrReceiverPhoneHint,
                                  prefixText: '+91  ',
                                  keyboard: TextInputType.phone,
                                  formatters: [FilteringTextInputFormatter.digitsOnly, LengthLimitingTextInputFormatter(10)],
                                  error: _phoneError,
                                  action: TextInputAction.done,
                                  autofill: const [AutofillHints.telephoneNumberNational],
                                  onChanged: () => _phoneError = null,
                                  bottomGap: 0,
                                ),
                              ],
                            ),
                          ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),
            _eyebrow(ty, l10n.addrSaveAs),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: ['Home', 'Work', 'Other'].map((l) {
                final on = _label == l;
                final text = switch (l) {
                  'Home' => l10n.manageAddressLabelHome,
                  'Work' => l10n.manageAddressLabelWork,
                  _ => l10n.manageAddressLabelOther,
                };
                return ChoiceChip(
                    label: Text(text),
                    selected: on,
                    showCheckmark: false,
                    onSelected: (_) => setState(() => _label = l),
                    selectedColor: ty.saffron,
                    backgroundColor: ty.surface,
                    side: BorderSide(color: on ? ty.saffron : ty.line),
                    labelStyle: TyType.sans(13, color: on ? ty.onPrimary : ty.ink, weight: FontWeight.w600),
                );
              }).toList(),
            ),
            if (_saveError != null) ...[
              const SizedBox(height: 14),
              Text(_saveError!, style: TyType.sans(13, color: ty.rose, weight: FontWeight.w600)),
            ],
          ],
        ),
      ),
      bottomNavigationBar: Container(
        padding: EdgeInsets.fromLTRB(20, 12, 20, MediaQuery.of(context).padding.bottom + 12),
        decoration: BoxDecoration(color: ty.surface, border: Border(top: BorderSide(color: ty.line2))),
        child: TyButton(
          _saving ? l10n.manageAddressSavingLabel : l10n.addrSaveButton,
          full: true,
          enabled: !_saving,
          onTap: _save,
        ),
      ),
    );
  }

  BoxDecoration _card(TyColors ty) => BoxDecoration(
        color: ty.surface,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: ty.line),
      );

  Widget _eyebrow(TyColors ty, String text) => Padding(
        padding: const EdgeInsets.only(left: 4, bottom: 8),
        child: Text(text.toUpperCase(), style: TyType.eyebrow(11, color: ty.ink3)),
      );

  Widget _radio(TyColors ty, String label, bool on, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(on ? Icons.radio_button_checked_rounded : Icons.radio_button_off_rounded,
                size: 20, color: on ? ty.saffron : ty.ink3),
            const SizedBox(width: 8),
            Text(label, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w600)),
          ],
        ),
      ),
    );
  }

  Widget _field(
    TyColors ty, {
    required TextEditingController controller,
    required String hint,
    IconData? icon,
    String? prefixText,
    String? error,
    TextInputType keyboard = TextInputType.text,
    TextCapitalization capitalization = TextCapitalization.none,
    TextInputAction action = TextInputAction.next,
    List<TextInputFormatter>? formatters,
    Iterable<String>? autofill,
    VoidCallback? onChanged,
    double bottomGap = 12,
  }) {
    return Padding(
      padding: EdgeInsets.only(bottom: bottomGap),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14),
            decoration: BoxDecoration(
              color: ty.surface,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: error != null ? ty.rose : ty.line, width: error != null ? 1.5 : 1),
            ),
            child: TextField(
              controller: controller,
              keyboardType: keyboard,
              textCapitalization: capitalization,
              textInputAction: action,
              inputFormatters: formatters,
              autofillHints: autofill,
              autocorrect: keyboard == TextInputType.text,
              onChanged: (_) {
                if (onChanged != null && error != null) setState(onChanged);
              },
              onTapOutside: (_) => FocusScope.of(context).unfocus(),
              style: TyType.sans(14.5, color: ty.ink, weight: FontWeight.w600),
              decoration: InputDecoration(
                hintText: hint,
                hintStyle: TyType.sans(14.5, color: ty.ink3),
                border: InputBorder.none,
                icon: icon == null ? null : Icon(icon, size: 19, color: ty.ink3),
                prefixText: prefixText,
                prefixStyle: TyType.sans(14.5, color: ty.ink2, weight: FontWeight.w700),
                contentPadding: const EdgeInsets.symmetric(vertical: 15),
              ),
            ),
          ),
          if (error != null)
            Padding(
              padding: const EdgeInsets.only(top: 5, left: 4),
              child: Text(error, style: TyType.sans(12, color: ty.rose, weight: FontWeight.w600)),
            ),
        ],
      ),
    );
  }
}

class _PlaceTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final String? value;
  final String placeholder;
  final String changeLabel;
  final VoidCallback onTap;

  const _PlaceTile({
    required this.icon,
    required this.label,
    required this.value,
    required this.placeholder,
    required this.changeLabel,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final has = (value ?? '').isNotEmpty;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(18),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        child: Row(
          children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(color: ty.saffronSoft, borderRadius: BorderRadius.circular(12)),
              child: Icon(icon, size: 20, color: ty.saffronDeep),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(label, style: TyType.sans(11.5, color: ty.ink3, weight: FontWeight.w600)),
                  const SizedBox(height: 2),
                  Text(
                    has ? value! : placeholder,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: TyType.sans(14.5, color: has ? ty.ink : ty.ink3, weight: has ? FontWeight.w700 : FontWeight.w500, height: 1.3),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: ty.saffron.withValues(alpha: 0.5)),
              ),
              child: Text(changeLabel, style: TyType.sans(12.5, color: ty.saffronDeep, weight: FontWeight.w700)),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Search sheet (city or area) ──────────────────────────────────────────────

enum _PickerMode { city, area }

class _PlacePickerSheet extends StatefulWidget {
  final _PickerMode mode;
  final String? city;
  final double? nearLat;
  final double? nearLon;

  const _PlacePickerSheet({required this.mode, this.city, this.nearLat, this.nearLon});

  @override
  State<_PlacePickerSheet> createState() => _PlacePickerSheetState();
}

class _PlacePickerSheetState extends State<_PlacePickerSheet> {
  final _ctrl = TextEditingController();
  final _focus = FocusNode();
  Timer? _debounce;

  List<PlaceSuggestion> _results = const [];
  List<PlaceSuggestion> _cities = const [];
  bool _loading = false;
  bool _error = false;
  bool _locating = false;
  String _lastQuery = '';

  bool get _isCity => widget.mode == _PickerMode.city;

  @override
  void initState() {
    super.initState();
    if (_isCity) _loadCities();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _ctrl.dispose();
    _focus.dispose();
    super.dispose();
  }

  Future<void> _loadCities() async {
    setState(() => _loading = true);
    try {
      final cities = await ServiceableCities.instance.load();
      final states = await CommonService().listStates().catchError((_) => <StateOption>[]);
      final stateName = {for (final s in states) s.id: s.name};
      if (!mounted) return;
      setState(() {
        _cities = [
          for (final c in cities)
            PlaceSuggestion(title: c.name, subtitle: stateName[c.stateId] ?? '', city: c.name, state: stateName[c.stateId]),
        ];
        _loading = false;
      });
    } catch (_) {
      if (mounted) setState(() { _loading = false; _error = true; });
    }
  }

  void _onChanged(String value) {
    _debounce?.cancel();
    final q = value.trim();
    if (_isCity) {
      setState(() => _lastQuery = q);
      return;
    }
    if (q.length < 2) {
      setState(() { _results = const []; _loading = false; _error = false; _lastQuery = q; });
      return;
    }
    setState(() { _loading = true; _error = false; });
    _debounce = Timer(const Duration(milliseconds: 350), () => _search(q));
  }

  Future<void> _search(String q) async {
    try {
      final r = await PlaceSearchService.instance.search(
        q,
        city: widget.city,
        nearLat: widget.nearLat,
        nearLon: widget.nearLon,
      );
      if (!mounted || _ctrl.text.trim() != q) return;
      setState(() { _results = r; _loading = false; _error = false; _lastQuery = q; });
    } catch (e) {
      // A cancelled request means a newer one is already on its way.
      if (!mounted || (e is Exception && e.toString().contains('cancel'))) return;
      setState(() { _loading = false; _error = true; _results = const []; _lastQuery = q; });
    }
  }

  Future<void> _useCurrent() async {
    if (_locating) return;
    final l10n = AppLocalizations.of(context)!;
    setState(() => _locating = true);
    final r = await PlaceSearchService.instance.currentPlace();
    if (!mounted) return;
    if (r.status == CurrentPlaceStatus.found) {
      Navigator.pop(context, r.place);
      return;
    }
    setState(() => _locating = false);
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(switch (r.status) {
        CurrentPlaceStatus.permissionDeniedForever => l10n.addrLocationDeniedForever,
        CurrentPlaceStatus.permissionDenied => l10n.addrLocationDenied,
        CurrentPlaceStatus.serviceOff => l10n.addrLocationServiceOff,
        _ => l10n.addrLocationFailed,
      }),
    ));
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final media = MediaQuery.of(context);

    final shown = _isCity
        ? _cities.where((c) => _lastQuery.isEmpty || c.title.toLowerCase().contains(_lastQuery.toLowerCase())).toList()
        : _results;

    return Padding(
      padding: EdgeInsets.only(top: media.padding.top + 24, bottom: media.viewInsets.bottom),
      // Material (not a decorated Container) so the list rows below can show
      // their tap ripple.
      child: Material(
        color: ty.paper,
        clipBehavior: Clip.antiAlias,
        shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(28))),
        child: Column(
          children: [
            const SizedBox(height: 10),
            Container(width: 40, height: 4, decoration: BoxDecoration(color: ty.line, borderRadius: BorderRadius.circular(2))),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 14, 16, 8),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 14),
                decoration: BoxDecoration(
                  color: ty.surface,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: ty.saffron, width: 1.5),
                ),
                child: TextField(
                  controller: _ctrl,
                  focusNode: _focus,
                  autofocus: true,
                  autocorrect: false,
                  textInputAction: TextInputAction.search,
                  onChanged: _onChanged,
                  onSubmitted: (v) { _debounce?.cancel(); if (!_isCity && v.trim().length >= 2) _search(v.trim()); },
                  style: TyType.sans(15, color: ty.ink, weight: FontWeight.w600),
                  decoration: InputDecoration(
                    hintText: _isCity ? l10n.addrSearchCityHint : l10n.addrSearchAreaHint,
                    hintStyle: TyType.sans(15, color: ty.ink3),
                    border: InputBorder.none,
                    icon: Icon(Icons.search_rounded, color: ty.ink3),
                    suffixIcon: _ctrl.text.isEmpty
                        ? null
                        : IconButton(
                            icon: Icon(Icons.close_rounded, size: 18, color: ty.ink3),
                            onPressed: () { _ctrl.clear(); _onChanged(''); },
                          ),
                    contentPadding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                ),
              ),
            ),
            if (!_isCity)
              ListTile(
                onTap: _useCurrent,
                leading: _locating
                    ? SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.2, color: ty.saffron))
                    : Icon(Icons.my_location_rounded, color: ty.saffronDeep),
                title: Text(_locating ? l10n.addrLocating : l10n.addrUseMyLocationRow,
                    style: TyType.sans(14.5, color: ty.saffronDeep, weight: FontWeight.w700)),
              ),
            if (_loading) LinearProgressIndicator(minHeight: 2, color: ty.saffron, backgroundColor: Colors.transparent),
            Expanded(child: _body(ty, l10n, shown)),
          ],
        ),
      ),
    );
  }

  Widget _body(TyColors ty, AppLocalizations l10n, List<PlaceSuggestion> shown) {
    Widget message(String text, {IconData icon = Icons.search_rounded}) => Center(
          child: Padding(
            padding: const EdgeInsets.all(32),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(icon, size: 36, color: ty.ink3),
                const SizedBox(height: 10),
                Text(text, textAlign: TextAlign.center, style: TyType.sans(13.5, color: ty.ink2, height: 1.4)),
              ],
            ),
          ),
        );

    if (_error && shown.isEmpty) return message(l10n.addrSearchError, icon: Icons.wifi_off_rounded);
    if (!_isCity && _ctrl.text.trim().length < 2) return message(l10n.addrSearchPrompt);
    if (shown.isEmpty) return _loading ? const SizedBox.shrink() : message(l10n.addrSearchNoResults);

    return ListView.separated(
      keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
      padding: const EdgeInsets.only(bottom: 24),
      itemCount: shown.length + (_isCity ? 1 : 0),
      separatorBuilder: (_, __) => Divider(height: 1, indent: 60, color: ty.line2),
      itemBuilder: (context, i) {
        if (_isCity && i == 0) {
          return Padding(
            padding: const EdgeInsets.fromLTRB(20, 6, 20, 6),
            child: Text(l10n.addrCitiesWeServe.toUpperCase(), style: TyType.eyebrow(11, color: ty.ink3)),
          );
        }
        final p = shown[_isCity ? i - 1 : i];
        return ListTile(
          onTap: () => Navigator.pop(context, p),
          leading: Icon(_isCity ? Icons.location_city_rounded : Icons.place_outlined, color: ty.ink3),
          title: Text(p.title, style: TyType.sans(14.5, color: ty.ink, weight: FontWeight.w700)),
          subtitle: p.subtitle.isEmpty
              ? null
              : Text(p.subtitle, maxLines: 2, overflow: TextOverflow.ellipsis, style: TyType.sans(12.5, color: ty.ink2)),
        );
      },
    );
  }
}
