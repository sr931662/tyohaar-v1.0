import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';

import '../../theme/colors.dart';
import '../../theme/typography.dart';
import '../../data/models.dart';
import '../../data/services/package_service.dart';
import '../../data/services/user_service.dart';
import '../../data/services/booking_service.dart';
import 'package:tyohaar/screens/payment_screen.dart';
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

class _PlanFlowScreenState extends State<PlanFlowScreen> {
  final PackageService _packageService = PackageService();
  final UserService _userService = UserService();
  final BookingService _bookingService = BookingService();
  bool _isSubmitting = false;

  static const _stepCount = 5;
  late int _step = widget.startStep.clamp(0, _stepCount - 1);

  List<Occasion> _occasions = [];
  List<Package> _packages = [];
  List<Address> _addresses = [];
  bool _isLoading = true;

  Occasion? _occasion;
  final _nameCtrl = TextEditingController();
  final _placeCtrl = TextEditingController();
  final Set<String> _vibes = {};
  final List<Guest> _guests = [];
  Package? _pkg;
  Address? _address;
  DateTime _eventDate = DateTime.now().add(const Duration(days: 30));

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
      ]);
      setState(() {
        _occasions = results[0] as List<Occasion>;
        _packages = results[1] as List<Package>;
        _addresses = results[2] as List<Address>;
        if (_occasions.isNotEmpty) _occasion = _occasions.first;
        if (_addresses.isNotEmpty) _address = _addresses.first;
        _isLoading = false;
      });
    } catch (e) {
      debugPrint('Error loading plan flow data: $e');
      setState(() => _isLoading = false);
    }
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    _placeCtrl.dispose();
    super.dispose();
  }

  void _next() {
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

  Future<void> _finish() async {
    if (_isSubmitting) return;
    setState(() => _isSubmitting = true);
    try {
      final booking = await _bookingService.createBooking({
        'package_id': _pkg?.id,
        'occasion_id': _occasion?.id,
        'scheduled_date': _eventDate.toIso8601String().split('T').first,
        'venue_address': _placeCtrl.text.isNotEmpty ? _placeCtrl.text : null,
        'title': _nameCtrl.text.isNotEmpty ? _nameCtrl.text : 'My Celebration',
        'address_id': _address?.id,
        'notes': _vibes.isNotEmpty ? 'Mood: ${_vibes.join(', ')}' : null,
      });
      if (!mounted) return;
      Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => PaymentScreen(
            bookingId: booking.id,
            amount: booking.totalAmount,
            packageName: _pkg?.name ?? 'Celebration Package',
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

  int get _totalGuests => _guests.fold<int>(0, (s, g) => s + g.count);

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
    if (_step == 4) {
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
      default:
        return _summaryStep(context);
    }
  }

  Widget _occasionStep(BuildContext context) {
    return Column(
      children: [
        _occasionGroup(context, 'Life Events', _occasions.where((o) => o.category == 'life_event').toList()),
        const SizedBox(height: 24),
        _occasionGroup(context, 'Major Festivals', _occasions.where((o) => o.category == 'major_festival').toList()),
        const SizedBox(height: 24),
        _occasionGroup(context, 'Other Moments', _occasions.where((o) => o.category != 'life_event' && o.category != 'major_festival').toList()),
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
            return GestureDetector(
              onTap: () => setState(() => _occasion = o),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: on ? Color.alphaBlend(c.withOpacity(0.1), ty.surface) : ty.surface,
                  borderRadius: BorderRadius.circular(18),
                  border: Border.all(color: on ? c : ty.line, width: on ? 1.5 : 1),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Emblem(icon: o.icon, tint: o.tint, size: 28),
                    const Spacer(),
                    Text(o.name, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w700)),
                  ],
                ),
              ),
            );
          }).toList(),
        ),
      ],
    );
  }

  Widget _detailsStep(BuildContext context) {
    final minDate = DateTime.now().add(const Duration(days: 15));
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _field(context, 'What shall we call it?', _textInput(context, _nameCtrl)),
        Row(
          children: [
            Expanded(child: _field(context, 'When', 
                _staticInput(context, Icons.event, '${_eventDate.day} ${_eventDate.month}', 
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
        _field(context, 'Where', _textInput(context, _placeCtrl, icon: Icons.place_outlined)),
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
      ],
    );
  }

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
            Text('guests estimated', style: TyType.sans(14, color: ty.ink2)),
            const Spacer(),
            TyButton('Add Group', kind: TyButtonKind.ghost, onTap: () {}),
          ]),
        ),
        const SizedBox(height: 16),
        Text('INVITE VIA', style: TyType.eyebrow(11, color: ty.ink3)),
        const SizedBox(height: 12),
        Row(
          children: [
            _inviteMethod(context, Icons.person_add_outlined, 'Manual'),
            _inviteMethod(context, Icons.upload_file_rounded, 'CSV'),
            _inviteMethod(context, Icons.contacts_outlined, 'Contacts'),
          ],
        ),
        const SizedBox(height: 24),
        ..._guests.asMap().entries.map((e) {
          final g = e.value;
          return Container(
            margin: const EdgeInsets.only(bottom: 10),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            decoration: _cardDeco(ty),
            child: Row(
              children: [
                TyAvatar(name: g.name, index: e.key, size: 40),
                const SizedBox(width: 12),
                Expanded(child: Text(g.name, style: TyType.sans(14.5, color: ty.ink, weight: FontWeight.w600))),
                _stepper(context, g.count, 
                  () => setState(() => g.count = (g.count - 1).clamp(1, 99)),
                  () => setState(() => g.count = g.count + 1)),
              ],
            ),
          );
        }),
      ],
    );
  }

  Widget _inviteMethod(BuildContext context, IconData icon, String label) {
    final ty = context.ty;
    return Expanded(
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
    );
  }

  Widget _packageStep(BuildContext context) {
    final ty = context.ty;
    return Column(
      children: _packages.map((p) {
        final on = _pkg?.id == p.id;
        return GestureDetector(
          onTap: () => setState(() => _pkg = p),
          child: Container(
            margin: const EdgeInsets.only(bottom: 16),
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: ty.surface,
              borderRadius: BorderRadius.circular(24),
              border: Border.all(color: on ? ty.saffron : ty.line, width: on ? 2 : 1),
              boxShadow: on ? [BoxShadow(color: ty.saffron.withOpacity(0.1), blurRadius: 10, offset: const Offset(0, 4))] : null,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Stack(
                  children: [
                    ClipRRect(
                      borderRadius: BorderRadius.circular(20),
                      child: CachedNetworkImage(
                        imageUrl: p.coverImageUrl ?? '',
                        height: 160,
                        width: double.infinity,
                        fit: BoxFit.cover,
                        placeholder: (context, url) => PhotoPlaceholder(tint: p.tint, height: 160, arch: false),
                        errorWidget: (context, url, error) => PhotoPlaceholder(tint: p.tint, height: 160, arch: false),
                      ),
                    ),
                    Positioned(
                      top: 12,
                      left: 12,
                      child: TyPill(p.slug ?? p.name),
                    ),
                    Positioned(
                      top: 12,
                      right: 12,
                      child: TyPill('₹${(p.price / 1000).toStringAsFixed(0)}K'),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Text(p.name, style: TyType.display(22, color: ty.ink)),
                const SizedBox(height: 4),
                Text(p.description ?? '', style: TyType.sans(13, color: ty.ink2)),
              ],
            ),
          ),
        );
      }).toList(),
    );
  }

  Widget _summaryStep(BuildContext context) {
    final ty = context.ty;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _summaryCard(context, 'Celebration', '${_occasion?.name} - ${_nameCtrl.text}'),
        _summaryCard(context, 'Package', _pkg?.name ?? ''),
        _summaryCard(context, 'Date & Time', '${_eventDate.day} ${_eventDate.month} · 6:30 PM'),
        _summaryCard(context, 'Guest Count', '$_totalGuests Guests'),
        const SizedBox(height: 16),
        _sectionHeader('Address'),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: _cardDeco(ty),
          child: Column(
            children: [
              if (_addresses.isEmpty)
                TyButton('Add Address', kind: TyButtonKind.ghost, leadingIcon: Icons.add_location_alt_outlined, onTap: () {})
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
              _priceRow('Tyohaar Fee', 1500),
              const Divider(height: 24),
              _priceRow('Total Amount', (_pkg?.price.toInt() ?? 0) + 1500, bold: true),
            ],
          ),
        ),
      ],
    );
  }

  Widget _summaryCard(BuildContext context, String label, String value) {
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
          Icon(Icons.edit_outlined, size: 16, color: ty.ink3),
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

  Widget _stepper(BuildContext context, int value, VoidCallback onMinus, VoidCallback onPlus) {
    final ty = context.ty;
    Widget btn(IconData i, VoidCallback f) => GestureDetector(
          onTap: f,
          child: Container(
            width: 30,
            height: 30,
            decoration: BoxDecoration(
              color: ty.surface2,
              borderRadius: BorderRadius.circular(9),
              border: Border.all(color: ty.line),
            ),
            child: Icon(i, size: 16, color: ty.ink),
          ),
        );
    return Row(
      children: [
        btn(Icons.remove_rounded, onMinus),
        SizedBox(
          width: 26,
          child: Text('$value',
              textAlign: TextAlign.center,
              style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
        ),
        btn(Icons.add_rounded, onPlus),
      ],
    );
  }

  BoxDecoration _cardDeco(TyColors ty) => BoxDecoration(
        color: ty.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: ty.line),
      );
}
