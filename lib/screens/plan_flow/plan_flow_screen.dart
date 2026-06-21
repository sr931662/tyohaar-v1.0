import 'package:flutter/material.dart';

import '../../theme/colors.dart';
import '../../theme/typography.dart';
import '../../data/sample_data.dart';
import '../../data/models.dart';
import '../../widgets/avatar.dart';
import '../../widgets/emblem.dart';
import '../../widgets/photo_placeholder.dart';
import '../../widgets/ty_button.dart';
import '../../widgets/ty_chip.dart';
import '../../widgets/common.dart';
import 'package:tyohaar/screens/booking_confirmation_screen.dart';

/// The "plan a celebration" flow — five gentle steps, one warm question
class PlanFlowScreen extends StatefulWidget {
  final int startStep;
  const PlanFlowScreen({super.key, this.startStep = 0});

  @override
  State<PlanFlowScreen> createState() => _PlanFlowScreenState();
}

class _PlanFlowScreenState extends State<PlanFlowScreen> {
  static const _stepCount = 5;
  late int _step = widget.startStep.clamp(0, _stepCount - 1);

  Occasion _occasion = TyData.occasions.first;
  final _nameCtrl = TextEditingController(text: 'Diya turns One');
  final _placeCtrl = TextEditingController(text: 'The Courtyard, Jaipur');
  final Set<String> _vibes = {'Intimate', 'Traditional'};
  final List<Guest> _guests = TyData.seedGuests().take(4).toList();
  InvitationTemplate _invite = TyData.invitations.first;
  Package? _pkg;
  Address _address = TyData.addresses.first;
  DateTime _eventDate = DateTime.now().add(const Duration(days: 20));

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

  void _finish() {
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const BookingConfirmationScreen()),
      (route) => false,
    );
  }

  int get _totalGuests => _guests.fold<int>(0, (s, g) => s + g.count);

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
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
            // header: back + step count + progress
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
            // body
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
            // footer
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
      return TyButton('Proceed To Payment',
          full: true, icon: Icons.payment_rounded, onTap: _finish);
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

  // ── step 1: Occasions ──
  Widget _occasionStep(BuildContext context) {
    final ty = context.ty;
    return Column(
      children: [
        _occasionGroup(context, 'Life Events', TyData.occasions.where((o) => o.category == 'life').toList()),
        const SizedBox(height: 24),
        _occasionGroup(context, 'Major Festivals', TyData.occasions.where((o) => o.category == 'major_festival').toList()),
        const SizedBox(height: 24),
        _occasionGroup(context, 'Minor Festivals', TyData.occasions.where((o) => o.category == 'minor_festival').toList()),
      ],
    );
  }

  Widget _occasionGroup(BuildContext context, String label, List<Occasion> list) {
    final ty = context.ty;
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
            final on = _occasion.id == o.id;
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
                    Text(o.en, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w700)),
                  ],
                ),
              ),
            );
          }).toList(),
        ),
      ],
    );
  }

  // ── step 2: Details & Invitations ──
  Widget _detailsStep(BuildContext context) {
    final ty = context.ty;
    final minDate = DateTime.now().add(const Duration(days: 15)); // Mock rule
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
            children: TyData.vibes
                .map((v) => TyChip(
                      label: v,
                      active: _vibes.contains(v),
                      onTap: () => setState(() =>
                          _vibes.contains(v) ? _vibes.remove(v) : _vibes.add(v)),
                    ))
                .toList(),
          ),
        ),
        const SizedBox(height: 12),
        _field(context, 'Invitation Template', _invitationPicker(context)),
      ],
    );
  }

  Widget _invitationPicker(BuildContext context) {
    final ty = context.ty;
    return Column(
      children: [
        Container(
          height: 120,
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: ty.surface,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: ty.line),
          ),
          child: Row(
            children: [
              Container(
                width: 80,
                decoration: BoxDecoration(
                  color: ty.saffronSoft,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(Icons.mail_outline_rounded, size: 32, color: Colors.orange),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(_invite.name, style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
                    Text('Style: ${_invite.mood}', style: TyType.sans(12, color: ty.ink2)),
                    const SizedBox(height: 8),
                    Text('Preview changes with mood ✨', style: TyType.sans(11, color: ty.saffronDeep)),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        SizedBox(
          height: 80,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: TyData.invitations.length,
            separatorBuilder: (_, __) => const SizedBox(width: 10),
            itemBuilder: (context, i) {
              final inv = TyData.invitations[i];
              final on = _invite.id == inv.id;
              return GestureDetector(
                onTap: () => setState(() => _invite = inv),
                child: Container(
                  width: 80,
                  decoration: BoxDecoration(
                    color: ty.surface,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: on ? ty.saffron : ty.line, width: on ? 2 : 1),
                  ),
                  child: Center(child: Icon(Icons.image_outlined, color: on ? ty.saffron : ty.ink3)),
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  // ── step 3: Guests ──
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
            Text('guests confirmed', style: TyType.sans(14, color: ty.ink2)),
            const Spacer(),
            TyButton('Add Guest', kind: TyButtonKind.ghost, onTap: () {}),
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
            _inviteMethod(context, Icons.chat_bubble_outline_rounded, 'WhatsApp'),
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

  // ── step 4: Packages ──
  Widget _packageStep(BuildContext context) {
    final ty = context.ty;
    return Column(
      children: TyData.packages.map((p) {
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
                    p.coverImage.startsWith('assets/')
                        ? ClipRRect(
                            borderRadius: BorderRadius.circular(20),
                            child: Image.asset(p.coverImage, height: 160, width: double.infinity, fit: BoxFit.cover),
                          )
                        : Container(
                            height: 160,
                            width: double.infinity,
                            decoration: BoxDecoration(color: ty.tint(p.tint).withOpacity(0.1), borderRadius: BorderRadius.circular(20)),
                            child: Center(child: Icon(Icons.celebration_rounded, color: ty.tint(p.tint), size: 40)),
                          ),
                    Positioned(
                      top: 12,
                      left: 12,
                      child: TyPill(p.theme),
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
                Text(p.description, style: TyType.sans(13, color: ty.ink2)),
                const SizedBox(height: 16),
                Wrap(
                  spacing: 8, runSpacing: 8,
                  children: p.inclusions.take(3).map((inc) => Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                    decoration: BoxDecoration(color: ty.surface2, borderRadius: BorderRadius.circular(8)),
                    child: Text(inc, style: TyType.sans(11, color: ty.ink)),
                  )).toList(),
                ),
                if (p.inclusions.length > 3) ...[
                  const SizedBox(height: 8),
                  Text('+${p.inclusions.length - 3} more inclusions', style: TyType.sans(11, color: ty.saffronDeep, weight: FontWeight.w600)),
                ],
              ],
            ),
          ),
        );
      }).toList(),
    );
  }

  // ── step 5: Summary ──
  Widget _summaryStep(BuildContext context) {
    final ty = context.ty;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _summaryCard(context, 'Celebration', '${_occasion.en} - ${_nameCtrl.text}'),
        _summaryCard(context, 'Package & Theme', '${_pkg?.name} (${_pkg?.theme})'),
        _summaryCard(context, 'Date & Time', '${_eventDate.day} ${_eventDate.month} · 6:30 PM'),
        _summaryCard(context, 'Guest Count', '$_totalGuests Guests (${_guests.length} Households)'),
        const SizedBox(height: 16),
        _sectionHeader('Address'),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: _cardDeco(ty),
          child: Column(
            children: [
              ...TyData.addresses.map((addr) => RadioListTile<Address>(
                value: addr,
                groupValue: _address,
                activeColor: ty.saffron,
                contentPadding: EdgeInsets.zero,
                title: Text(addr.label, style: TyType.sans(14, weight: FontWeight.w700)),
                subtitle: Text(addr.fullAddress, style: TyType.sans(12, color: ty.ink2)),
                onChanged: (v) => setState(() => _address = v!),
              )),
              const Divider(),
              TyButton('Add New Address', kind: TyButtonKind.ghost, leadingIcon: Icons.add_location_alt_outlined, onTap: () {}),
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
              _priceRow('Package Base Price', _pkg?.price ?? 0),
              _priceRow('Guest Add-on (x$_totalGuests)', _totalGuests * 150),
              _priceRow('Tyohaar Fee', 1500),
              const Divider(height: 24),
              _priceRow('Total Amount', (_pkg?.price ?? 0) + (_totalGuests * 150) + 1500, bold: true),
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
          Text('₹${amount.toString().replaceAllMapped(RegExp(r'(\d{1,3})(?=(\d{3})+(?!\d))'), (Match m) => '${m[1]},')}', 
              style: TyType.sans(14, color: ty.ink, weight: bold ? FontWeight.w800 : FontWeight.w600)),
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

  // ── shared bits ──
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
