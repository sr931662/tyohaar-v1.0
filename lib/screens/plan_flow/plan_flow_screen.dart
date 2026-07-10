import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:intl/intl.dart';
import 'package:flutter_contacts/flutter_contacts.dart';
import 'package:permission_handler/permission_handler.dart';

import 'package:tyohaar/theme/assets.dart';
import '../../theme/colors.dart';
import '../../theme/typography.dart';
import '../../data/models.dart';
import '../../data/services/package_service.dart';
import '../../data/services/user_service.dart';
import '../../data/services/booking_service.dart';
import 'package:tyohaar/screens/payment_screen.dart';
import 'package:tyohaar/screens/send_invitations_screen.dart';
import 'package:tyohaar/screens/manage_address_screen.dart' show AddressFormSheet;
import '../../widgets/avatar.dart';
import '../../widgets/emblem.dart';
import '../../widgets/photo_placeholder.dart';
import '../../widgets/ty_button.dart';
import '../../widgets/ty_chip.dart';
import '../../widgets/common.dart';

class PlanFlowScreen extends StatefulWidget {
  final int startStep;
  const PlanFlowScreen({super.key, this.startStep = 0});

  @override
  State<PlanFlowScreen> createState() => _PlanFlowScreenState();
}

const _venueTypes = ['Home', 'Banquet Hall', 'Outdoor / Garden', 'Hotel'];
const _colorPalettes = ['Gold', 'Blush Pink', 'Sky Blue', 'Sage Green', 'Lavender', 'Multicolor'];

class _PlanFlowScreenState extends State<PlanFlowScreen> {
  final PackageService _packageService = PackageService();
  final UserService _userService = UserService();
  final BookingService _bookingService = BookingService();
  bool _isSubmitting = false;

  // 0 Occasion · 1 Details · 2 Guests · 3 Package · 4 Package Items · 5 Summary
  static const _stepCount = 6;
  late int _step = widget.startStep.clamp(0, _stepCount - 1);

  List<Occasion> _occasions = [];
  List<Package> _packages = [];
  List<Address> _addresses = [];
  List<CelebrationTheme> _themes = [];
  bool _isLoading = true;

  Occasion? _occasion;
  final _nameCtrl = TextEditingController();
  final Set<String> _vibes = {};
  String? _venueType;
  final Set<String> _colorPalette = {};
  final List<PlannedGuest> _plannedGuests = [];
  Package? _pkg;
  CelebrationTheme? _theme;
  Address? _address;
  DateTime _eventDate = DateTime.now().add(const Duration(days: 30));

  List<PackageItem> _packageItems = [];
  bool _loadingItems = false;
  final Set<String> _selectedItemIds = {};

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    try {
      final results = await Future.wait([
        _packageService.listOccasions(),
        _packageService.listPackages(),
        _userService.getAddresses(),
        _packageService.listThemes().catchError((_) => <CelebrationTheme>[]),
      ]);
      setState(() {
        _occasions = results[0] as List<Occasion>;
        _packages = results[1] as List<Package>;
        _addresses = results[2] as List<Address>;
        _themes = results[3] as List<CelebrationTheme>;
        if (_occasions.isNotEmpty) _occasion = _occasions.first;
        if (_addresses.isNotEmpty) _address = _addresses.first;
        _isLoading = false;
      });
    } catch (e) {
      debugPrint('Error loading plan flow data: $e');
      setState(() => _isLoading = false);
    }
  }

  Future<void> _loadPackageItems() async {
    if (_pkg == null) return;
    setState(() => _loadingItems = true);
    try {
      final items = await _packageService.listPackageItems(_pkg!.id);
      setState(() {
        _packageItems = items;
        _selectedItemIds
          ..clear()
          ..addAll(items.where((i) => i.isMandatory).map((i) => i.id));
        _loadingItems = false;
      });
    } catch (e) {
      debugPrint('Error loading package items: $e');
      setState(() => _loadingItems = false);
    }
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    super.dispose();
  }

  void _next() {
    if (_step == 3 && _pkg != null && _packageItems.isEmpty && !_loadingItems) {
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
    setState(() => _isSubmitting = true);
    try {
      final optionalSelected = _packageItems
          .where((i) => !i.isMandatory && _selectedItemIds.contains(i.id))
          .map((i) => i.id)
          .toList();

      final notes = <String>[
        if (_vibes.isNotEmpty) 'Mood: ${_vibes.join(', ')}',
        if (_venueType != null) 'Venue type: $_venueType',
        if (_colorPalette.isNotEmpty) 'Color palette: ${_colorPalette.join(', ')}',
      ].join(' · ');

      final booking = await _bookingService.createBooking({
        'package_id': _pkg?.id,
        'occasion_id': _occasion?.id,
        'scheduled_date': _eventDate.toIso8601String().split('T').first,
        'venue_address': _address?.fullAddress,
        'celebration_title': _nameCtrl.text.isNotEmpty ? _nameCtrl.text : 'My Celebration',
        'address_id': _address?.id,
        'theme_id': (_pkg?.isCustomizable ?? false) ? _theme?.id : null,
        'item_ids': optionalSelected,
        'special_instructions': notes.isNotEmpty ? notes : null,
      });
      if (!mounted) return;
      Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => PaymentScreen(
            bookingId: booking.id,
            amount: booking.totalAmount,
            packageName: _pkg?.name ?? 'Celebration Package',
            scheduledDate: DateFormat('d MMMM yyyy').format(_eventDate),
            celebrationId: booking.celebrationId,
            plannedGuests: _plannedGuests,
          ),
        ),
      );
    } catch (e) {
      debugPrint('Error creating booking: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not create booking. Please try again.')),
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

    final titles = [
      ['What shall we celebrate?', 'Every milestone deserves to be held with care.'],
      ['Tell us the details', 'The little things help us shape your plan.'],
      ['Who’s coming together?', 'Group by household — the way families really gather.'],
      ['Choose your package', 'Hand-picked experiences, curated for families like yours.'],
      ['Package items', 'Everything included, plus a few extras if you\'d like them.'],
      ['Order Summary', 'Review your celebration plan before we get started.'],
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
                      Text('Step ${_step + 1} of $_stepCount',
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
    if (_step == _stepCount - 1) {
      return TyButton(
        _isSubmitting ? 'Creating Booking...' : 'Proceed To Payment',
        full: true,
        icon: Icons.payment_rounded,
        enabled: !_isSubmitting && _pkg != null,
        onTap: _finish,
      );
    }
    return TyButton('Continue',
        full: true,
        enabled: _step == 3 ? _pkg != null : true,
        icon: Icons.chevron_right_rounded,
        onTap: _next);
  }

  Widget _stepBody(BuildContext context) {
    switch (_step) {
      case 0:
        return _occasionStep(context);
      case 1:
        return _detailsStep(context);
      case 2:
        return _guestsStep(context);
      case 3:
        return _packageStep(context);
      case 4:
        return _packageItemsStep(context);
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

    return Column(
      children: [
        if (milestones.isNotEmpty) ...[
          _occasionGroup(context, 'Milestones', milestones),
          const SizedBox(height: 24),
        ],
        if (memories.isNotEmpty) ...[
          _occasionGroup(context, 'Memories', memories),
          const SizedBox(height: 24),
        ],
        if (growth.isNotEmpty) ...[
          _occasionGroup(context, 'Growth', growth),
          const SizedBox(height: 24),
        ],
        if (others.isNotEmpty)
          _occasionGroup(context, 'Other Moments', others),
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
            final c = ty.tint(o.tint);

            final String? networkImage = o.thumbnailUrl;
            final String? localImage = OccasionAssets.getRelatedBackground(o.name);
            final bool hasImage = networkImage != null || localImage != null;

            return GestureDetector(
              onTap: () => setState(() => _occasion = o),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                decoration: BoxDecoration(
                  color: on ? Color.alphaBlend(c.withOpacity(0.1), ty.surface) : ty.surface,
                  borderRadius: BorderRadius.circular(18),
                  border: Border.all(color: on ? Colors.transparent : ty.line, width: 1),
                ),
                foregroundDecoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(18),
                  border: on ? Border.all(color: c, width: 2.5) : null,
                ),
                clipBehavior: Clip.antiAlias,
                child: Stack(
                  children: [
                    if (hasImage)
                      Positioned.fill(
                        child: networkImage != null
                            ? CachedNetworkImage(
                                imageUrl: networkImage,
                                fit: BoxFit.cover,
                                errorWidget: (context, url, error) => localImage != null
                                    ? Image.asset(localImage, fit: BoxFit.cover)
                                    : const SizedBox(),
                              )
                            : Image.asset(localImage!, fit: BoxFit.cover),
                      ),
                    if (hasImage)
                      Positioned.fill(
                        child: Container(
                          decoration: BoxDecoration(
                            gradient: LinearGradient(
                              begin: Alignment.topCenter,
                              end: Alignment.bottomCenter,
                              colors: [
                                Colors.black.withOpacity(0.15),
                                Colors.black.withOpacity(0.6),
                              ],
                            ),
                          ),
                        ),
                      ),
                    Padding(
                      padding: const EdgeInsets.all(12),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Emblem(
                            icon: o.icon,
                            tint: hasImage ? 'white' : o.tint,
                            size: 28,
                          ),
                          const Spacer(),
                          Text(
                            o.name,
                            style: TyType.sans(14,
                                color: hasImage ? Colors.white : ty.ink,
                                weight: FontWeight.w700),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            );
          }).toList(),
        ),
      ],
    );
  }

  // ── Step 1: Details ─────────────────────────────────────────────────────

  Widget _detailsStep(BuildContext context) {
    final minDate = DateTime.now().add(const Duration(days: 15));
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _field(context, 'What shall we call it?', _textInput(context, _nameCtrl)),
        Row(
          children: [
            Expanded(child: _field(context, 'When',
                _staticInput(context, Icons.event, DateFormat('d MMMM yyyy').format(_eventDate),
                onTap: () async {
                  final d = await showDatePicker(
                    context: context,
                    initialDate: _eventDate.isBefore(minDate) ? minDate : _eventDate,
                    firstDate: minDate,
                    lastDate: DateTime.now().add(const Duration(days: 365)));
                  if (d != null) setState(() => _eventDate = d);
                }))),
            const SizedBox(width: 12),
            Expanded(child: _field(context, 'Time', _staticInput(context, null, '6:30 PM'))),
          ],
        ),
        _field(context, 'Where', _addressPicker(context)),
        _field(
          context,
          'Venue type',
          Wrap(
            spacing: 9,
            runSpacing: 9,
            children: _venueTypes
                .map((v) => TyChip(
                      label: v,
                      active: _venueType == v,
                      onTap: () => setState(() => _venueType = _venueType == v ? null : v),
                    ))
                .toList(),
          ),
        ),
        _field(
          context,
          'The mood',
          Wrap(
            spacing: 9,
            runSpacing: 9,
            children: ['Intimate', 'Grand', 'Traditional', 'Modern']
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
          'Color palette',
          Wrap(
            spacing: 9,
            runSpacing: 9,
            children: _colorPalettes
                .map((v) => TyChip(
                      label: v,
                      active: _colorPalette.contains(v),
                      onTap: () => setState(() =>
                          _colorPalette.contains(v) ? _colorPalette.remove(v) : _colorPalette.add(v)),
                    ))
                .toList(),
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
                Text('Add new address', style: TyType.sans(13.5, color: ty.saffron, weight: FontWeight.w700)),
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

  // ── Step 2: Guests ──────────────────────────────────────────────────────

  Widget _guestsStep(BuildContext context) {
    final ty = context.ty;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.all(18),
          decoration: _cardDeco(ty),
          child: Row(children: [
            Text('$_totalGuests', style: TyType.display(36, color: ty.ink)),
            const SizedBox(width: 8),
            Text('guests added', style: TyType.sans(14, color: ty.ink2)),
          ]),
        ),
        const SizedBox(height: 16),
        Text('INVITE VIA', style: TyType.eyebrow(11, color: ty.ink3)),
        const SizedBox(height: 12),
        Row(
          children: [
            _inviteMethod(context, Icons.person_add_outlined, 'Manual', _openAddGuestManually),
            _inviteMethod(context, Icons.contacts_outlined, 'Contacts', _importFromContacts),
          ],
        ),
        const SizedBox(height: 24),
        if (_plannedGuests.isNotEmpty) Text('GUEST LIST', style: TyType.eyebrow(11, color: ty.ink3)),
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
          'Invitations are sent via WhatsApp once your booking and payment are confirmed.',
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
            Text('Add Guest', style: TyType.display(22, color: ty.ink)),
            const SizedBox(height: 20),
            _textInput(context, nameCtrl),
            const SizedBox(height: 12),
            _textInput(context, phoneCtrl, icon: Icons.phone_outlined),
            const SizedBox(height: 24),
            TyButton('Add', full: true, onTap: () => Navigator.pop(ctx, true)),
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
          const SnackBar(content: Text('Contacts permission is needed to import guests.')),
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
            _plannedGuests.add(PlannedGuest(name: c.displayName ?? 'Guest', phone: phone));
          }
        });
      }
    } catch (e) {
      debugPrint('Contact import failed: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not read contacts. Please try again.')),
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

  // ── Step 3: Package ─────────────────────────────────────────────────────

  Widget _packageStep(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        GridView.count(
          crossAxisCount: 2,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: 12,
          crossAxisSpacing: 12,
          childAspectRatio: 0.72,
          children: _packages.map((p) => _packageCard(context, p)).toList(),
        ),
        if (_pkg?.isCustomizable ?? false) _themeStep(context),
      ],
    );
  }

  Widget _packageCard(BuildContext context, Package p) {
    final ty = context.ty;
    final on = _pkg?.id == p.id;
    return GestureDetector(
      onTap: () => setState(() { _pkg = p; _packageItems = []; }),
      child: Container(
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: ty.surface,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: on ? ty.saffron : ty.line, width: on ? 2 : 1),
          boxShadow: on ? [BoxShadow(color: ty.saffron.withOpacity(0.12), blurRadius: 8, offset: const Offset(0, 3))] : null,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Stack(
              children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(14),
                  child: CachedNetworkImage(
                    imageUrl: p.coverImageUrl ?? '',
                    height: 90,
                    width: double.infinity,
                    fit: BoxFit.cover,
                    placeholder: (context, url) => PhotoPlaceholder(tint: p.tint, height: 90, arch: false),
                    errorWidget: (context, url, error) {
                      final local = OccasionAssets.getRelatedBackground(p.name);
                      if (local != null) return Image.asset(local, height: 90, fit: BoxFit.cover);
                      return PhotoPlaceholder(tint: p.tint, height: 90, arch: false);
                    },
                  ),
                ),
                Positioned(
                  top: 8, right: 8,
                  child: TyPill('₹${(p.price / 1000).toStringAsFixed(0)}K'),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(p.name, maxLines: 1, overflow: TextOverflow.ellipsis, style: TyType.display(15, color: ty.ink)),
            const SizedBox(height: 2),
            Text(p.description ?? '', maxLines: 2, overflow: TextOverflow.ellipsis, style: TyType.sans(11.5, color: ty.ink2, height: 1.3)),
            const Spacer(),
            GestureDetector(
              onTap: () => _openPackageDetail(context, p),
              child: Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Text('Expand for details', style: TyType.sans(11.5, color: ty.saffron, weight: FontWeight.w700)),
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
                _pkg?.id == p.id ? 'Selected' : 'Select This Package',
                full: true,
                enabled: _pkg?.id != p.id,
                onTap: () {
                  setState(() { _pkg = p; _packageItems = []; });
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
    if (_themes.isEmpty) return const SizedBox();
    return Padding(
      padding: const EdgeInsets.only(top: 20, bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('CHOOSE A COLOR THEME', style: TyType.eyebrow(11, color: ty.ink3)),
          const SizedBox(height: 4),
          Text('This package is customizable — pick the palette for your celebration.',
              style: TyType.sans(12.5, color: ty.ink2)),
          const SizedBox(height: 12),
          SizedBox(
            height: 96,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: _themes.length,
              separatorBuilder: (_, __) => const SizedBox(width: 12),
              itemBuilder: (context, i) {
                final t = _themes[i];
                final on = _theme?.id == t.id;
                Color hexToColor(String hex) {
                  final h = hex.replaceAll('#', '');
                  return Color(int.parse('FF$h', radix: 16));
                }
                final swatch = hexToColor(t.primaryColorHex);
                return GestureDetector(
                  onTap: () => setState(() => _theme = on ? null : t),
                  child: Column(
                    children: [
                      Container(
                        width: 56,
                        height: 56,
                        decoration: BoxDecoration(
                          color: swatch,
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: on ? ty.saffron : Colors.transparent,
                            width: 3,
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: swatch.withOpacity(0.35),
                              blurRadius: 8,
                              offset: const Offset(0, 3),
                            ),
                          ],
                        ),
                        child: on
                            ? const Icon(Icons.check_rounded, color: Colors.white)
                            : null,
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
              },
            ),
          ),
        ],
      ),
    );
  }

  // ── Step 4: Package Items ───────────────────────────────────────────────

  Widget _packageItemsStep(BuildContext context) {
    final ty = context.ty;
    if (_loadingItems) return const Center(child: Padding(padding: EdgeInsets.all(40), child: CircularProgressIndicator()));
    if (_pkg == null) return const SizedBox();
    if (_packageItems.isEmpty) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _loadPackageItems());
      return const Center(child: Padding(padding: EdgeInsets.all(40), child: CircularProgressIndicator()));
    }

    final mandatory = _packageItems.where((i) => i.isMandatory).toList();
    final optional = _packageItems.where((i) => !i.isMandatory).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (mandatory.isNotEmpty) ...[
          Text('INCLUDED', style: TyType.eyebrow(11, color: ty.ink3)),
          const SizedBox(height: 10),
          ...mandatory.map((item) => _itemRow(context, item, locked: true)),
          const SizedBox(height: 20),
        ],
        if (optional.isNotEmpty) ...[
          Text('OPTIONAL ADD-ONS', style: TyType.eyebrow(11, color: ty.ink3)),
          const SizedBox(height: 10),
          ...optional.map((item) => _itemRow(context, item, locked: false)),
        ],
        if (mandatory.isEmpty && optional.isEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 24),
            child: Text('This package has no configurable items.', style: TyType.sans(13, color: ty.ink3)),
          ),
      ],
    );
  }

  Widget _itemRow(BuildContext context, PackageItem item, {required bool locked}) {
    final ty = context.ty;
    final selected = _selectedItemIds.contains(item.id);
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: _cardDeco(ty),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(item.name, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w600)),
                if (item.description != null)
                  Text(item.description!, style: TyType.sans(11.5, color: ty.ink2), maxLines: 2, overflow: TextOverflow.ellipsis),
                if (!locked)
                  Text('+ ₹${item.unitPrice.toStringAsFixed(0)}', style: TyType.sans(12.5, color: ty.saffron, weight: FontWeight.w700)),
              ],
            ),
          ),
          if (locked)
            Icon(Icons.check_circle_rounded, color: ty.saffron, size: 22)
          else
            Switch.adaptive(
              value: selected,
              activeTrackColor: ty.saffron,
              onChanged: (v) => setState(() {
                if (v) _selectedItemIds.add(item.id); else _selectedItemIds.remove(item.id);
              }),
            ),
        ],
      ),
    );
  }

  // ── Step 5: Summary ─────────────────────────────────────────────────────

  Widget _summaryStep(BuildContext context) {
    final ty = context.ty;
    final selectedOptional = _packageItems.where((i) => !i.isMandatory && _selectedItemIds.contains(i.id)).toList();
    final itemsTotal = selectedOptional.fold<double>(0, (s, i) => s + i.unitPrice);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _summaryCard(context, 'Celebration', '${_occasion?.name} - ${_nameCtrl.text}', onEdit: () => _jumpTo(0)),
        _summaryCard(context, 'Package', _pkg?.name ?? '', onEdit: () => _jumpTo(3)),
        if ((_pkg?.isCustomizable ?? false) && _theme != null)
          _summaryCard(context, 'Theme', _theme!.name, onEdit: () => _jumpTo(3)),
        if (selectedOptional.isNotEmpty)
          _summaryCard(context, 'Add-ons', selectedOptional.map((i) => i.name).join(', '), onEdit: () => _jumpTo(4)),
        _summaryCard(context, 'Date & Time', '${DateFormat('d MMMM yyyy').format(_eventDate)} · 6:30 PM', onEdit: () => _jumpTo(1)),
        _summaryCard(context, 'Guest Count', '$_totalGuests Guests', onEdit: () => _jumpTo(2)),
        const SizedBox(height: 16),
        _sectionHeader('Address'),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: _cardDeco(ty),
          child: Column(
            children: [
              if (_addresses.isEmpty)
                TyButton('Add Address', kind: TyButtonKind.ghost, leadingIcon: Icons.add_location_alt_outlined, onTap: _openAddAddress)
              else
                ..._addresses.map((addr) => RadioListTile<Address>(
                  value: addr,
                  groupValue: _address,
                  activeColor: ty.saffron,
                  contentPadding: EdgeInsets.zero,
                  title: Text(addr.label, style: TyType.sans(14, weight: FontWeight.w700)),
                  subtitle: Text(addr.fullAddress, style: TyType.sans(12, color: ty.ink2)),
                  onChanged: (v) => setState(() => _address = v!),
                )),
            ],
          ),
        ),
        const SizedBox(height: 24),
        _sectionHeader('Price Breakdown'),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: _cardDeco(ty),
          child: Column(
            children: [
              _priceRow('Package Base Price', _pkg?.price.toInt() ?? 0),
              if (itemsTotal > 0) _priceRow('Add-ons', itemsTotal.toInt()),
              _priceRow('Tyohaar Fee', 1500),
              const Divider(height: 24),
              _priceRow('Total Amount', (_pkg?.price.toInt() ?? 0) + itemsTotal.toInt() + 1500, bold: true),
            ],
          ),
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
          Text(label, style: TyType.sans(13, color: bold ? ty.ink : ty.ink2, weight: bold ? FontWeight.w700 : FontWeight.w500)),
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
    return Padding(
      padding: const EdgeInsets.only(bottom: 18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label,
              style: TyType.sans(12.5, color: ty.ink2, weight: FontWeight.w700)),
          const SizedBox(height: 8),
          child,
        ],
      ),
    );
  }

  Widget _textInput(BuildContext context, TextEditingController ctrl, {IconData? icon}) {
    final ty = context.ty;
    return TextField(
      controller: ctrl,
      style: TyType.sans(15.5, color: ty.ink, weight: FontWeight.w500),
      decoration: InputDecoration(
        isDense: true,
        prefixIcon: icon == null ? null : Icon(icon, size: 18, color: ty.ink2),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
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
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 15),
        decoration: BoxDecoration(
          color: ty.surface,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: ty.line, width: 1.5),
        ),
        child: Row(
          children: [
            if (icon != null) ...[
              Icon(icon, size: 17, color: ty.ink2),
              const SizedBox(width: 8),
            ],
            Text(value, style: TyType.sans(15, color: ty.ink, weight: FontWeight.w500)),
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
    final filtered = widget.contacts
        .where((c) => (c.displayName ?? '').toLowerCase().contains(_query.toLowerCase()))
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
            Text('Select Guests', style: TyType.display(20, color: ty.ink)),
            const SizedBox(height: 12),
            TextField(
              onChanged: (v) => setState(() => _query = v),
              decoration: InputDecoration(
                isDense: true,
                hintText: 'Search contacts',
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
                    title: Text(c.displayName ?? 'Unknown', style: TyType.sans(14, color: ty.ink, weight: FontWeight.w600)),
                    subtitle: Text(c.phones.first.number, style: TyType.sans(12, color: ty.ink2)),
                    onChanged: (v) => setState(() {
                      if (v == true) _selected.add(c); else _selected.remove(c);
                    }),
                  );
                },
              ),
            ),
            Padding(
              padding: EdgeInsets.fromLTRB(0, 12, 0, MediaQuery.of(context).padding.bottom + 16),
              child: TyButton(
                _selected.isEmpty ? 'Select contacts' : 'Add ${_selected.length} guest${_selected.length == 1 ? '' : 's'}',
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
