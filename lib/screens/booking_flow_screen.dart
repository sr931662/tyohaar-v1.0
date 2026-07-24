import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:intl/intl.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/models.dart';
import '../data/services/package_service.dart';
import '../data/services/user_service.dart';
import '../data/services/booking_service.dart';
import '../widgets/ty_button.dart';
import '../widgets/common.dart';
import '../widgets/photo_placeholder.dart';
import 'payment_screen.dart';

class BookingFlowScreen extends StatefulWidget {
  final Package package;
  final int initialGuestCount;
  const BookingFlowScreen({super.key, required this.package, this.initialGuestCount = 20});

  @override
  State<BookingFlowScreen> createState() => _BookingFlowScreenState();
}

class _BookingFlowScreenState extends State<BookingFlowScreen> {
  final PackageService _packageService = PackageService();
  final UserService _userService = UserService();
  final BookingService _bookingService = BookingService();

  int _step = 0;
  bool _isLoading = true;
  bool _isSubmitting = false;

  late Package _fullPackage;
  List<PackageItem> _allItems = [];
  final Set<String> _selectedOptionalItemIds = {};
  
  DateTime _eventDate = DateTime.now().add(const Duration(days: 15));
  TimeOfDay _eventTime = const TimeOfDay(hour: 18, minute: 30);

  final _recipientNameCtrl = TextEditingController();
  final _recipientPhoneCtrl = TextEditingController();
  final _landmarkCtrl = TextEditingController();
  final _specialNotesCtrl = TextEditingController();

  List<Address> _savedAddresses = [];
  Address? _selectedAddress;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    try {
      final results = await Future.wait([
        _packageService.getPackageDetails(widget.package.id),
        _packageService.listPackageItems(widget.package.id),
        _userService.getAddresses(),
      ]);
      
      setState(() {
        _fullPackage = results[0] as Package;
        _allItems = results[1] as List<PackageItem>;
        _savedAddresses = results[2] as List<Address>;
        if (_savedAddresses.isNotEmpty) _selectedAddress = _savedAddresses.first;
        _isLoading = false;
      });
    } catch (e) {
      debugPrint('Error loading booking flow data: $e');
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _next() {
    if (_step == 1) {
      final name = _recipientNameCtrl.text.trim();
      final phone = _recipientPhoneCtrl.text.trim();
      if (name.isEmpty || phone.isEmpty) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Please enter recipient name and phone number.')),
        );
        return;
      }
      if (!RegExp(r'^[0-9]{10}$').hasMatch(phone.replaceAll(RegExp(r'[^0-9]'), ''))) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Please enter a valid 10-digit phone number.')),
        );
        return;
      }
    }
    if (_step < 2) {
      setState(() => _step++);
    } else {
      _createBooking();
    }
  }

  void _back() {
    if (_step == 0) {
      Navigator.pop(context);
    } else {
      setState(() => _step--);
    }
  }

  Future<void> _createBooking() async {
    if (_isSubmitting) return;
    setState(() => _isSubmitting = true);

    try {
      // No existing celebration is picked in this flow — the backend
      // auto-creates a minimal one from celebration_title/venue_address/
      // scheduled_date and the package's own occasion association.
      final booking = await _bookingService.createBooking({
        'package_id': _fullPackage.id,
        'celebration_title': '${_fullPackage.name} booking',
        'scheduled_date': DateFormat('yyyy-MM-dd').format(_eventDate),
        'scheduled_start_time': '${_eventTime.hour.toString().padLeft(2, '0')}:${_eventTime.minute.toString().padLeft(2, '0')}:00',
        'address_id': _selectedAddress?.id,
        'venue_address': _landmarkCtrl.text.isNotEmpty ? _landmarkCtrl.text : null,
        'recipient_name': _recipientNameCtrl.text,
        'recipient_phone': _recipientPhoneCtrl.text,
        'special_instructions': _specialNotesCtrl.text,
        'item_ids': _selectedOptionalItemIds.toList(),
      });

      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (_) => PaymentScreen(
            bookingId: booking.id,
            amount: booking.totalAmount,
            packageName: _fullPackage.name,
            scheduledDate: DateFormat('dd MMM yyyy').format(_eventDate),
          ),
        ),
      );
    } catch (e) {
      debugPrint('Error creating booking: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Failed to create booking. Please try again.')),
        );
      }
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  double get _addonsTotal => _allItems
      .where((i) => i.isOptional && _selectedOptionalItemIds.contains(i.id))
      .fold(0.0, (sum, item) => sum + item.unitPrice);

  double get _totalPrice => _fullPackage.price + _addonsTotal; // platform fee removed

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    if (_isLoading) return const Scaffold(body: Center(child: CircularProgressIndicator()));

    final titles = [
      ['Enhance your package', 'Select optional add-ons to make it extra special.'],
      ['Delivery Details', 'Where and who should receive the celebration package?'],
      ['Review & Confirm', 'A transparent look at your celebration details.'],
    ];

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: AppBar(
        backgroundColor: ty.paper,
        elevation: 0,
        leading: ChromeIconButton(icon: Icons.chevron_left_rounded, onTap: _back),
        title: Text('Booking', style: TyType.display(20, color: ty.ink)),
        centerTitle: true,
      ),
      body: Column(
        children: [
          _progressBar(ty),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(20),
              children: [
                Text(titles[_step][0], style: TyType.display(28, color: ty.ink)),
                const SizedBox(height: 6),
                Text(titles[_step][1], style: TyType.sans(14.5, color: ty.ink2)),
                const SizedBox(height: 28),
                _stepBody(context),
              ],
            ),
          ),
          _footer(context),
        ],
      ),
    );
  }

  Widget _progressBar(TyColors ty) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
      child: Row(
        children: [
          for (int i = 0; i < 3; i++)
            Expanded(
              child: Container(
                margin: EdgeInsets.only(right: i == 2 ? 0 : 8),
                height: 4,
                decoration: BoxDecoration(
                  color: i <= _step ? ty.saffron : ty.line,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _stepBody(BuildContext context) {
    switch (_step) {
      case 0: return _addonsStep(context);
      case 1: return _deliveryStep(context);
      default: return _summaryStep(context);
    }
  }

  Widget _addonsStep(BuildContext context) {
    final optional = _allItems.where((i) => i.isOptional).toList();
    if (optional.isEmpty) {
      return Center(
        child: Column(
          children: [
            const SizedBox(height: 40),
            Icon(Icons.auto_awesome_outlined, size: 64, color: context.ty.ink3),
            const SizedBox(height: 16),
            Text('No extra add-ons needed', style: TyType.sans(16, color: context.ty.ink2)),
            const SizedBox(height: 8),
            Text('This package is already complete!', style: TyType.sans(14, color: context.ty.ink3)),
          ],
        ),
      );
    }
    return Column(
      children: optional.map((item) => _addonCard(context, item)).toList(),
    );
  }

  Widget _addonCard(BuildContext context, PackageItem item) {
    final ty = context.ty;
    final isSelected = _selectedOptionalItemIds.contains(item.id);
    return GestureDetector(
      onTap: () {
        setState(() {
          if (isSelected) _selectedOptionalItemIds.remove(item.id);
          else _selectedOptionalItemIds.add(item.id);
        });
      },
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: isSelected ? ty.saffronSoft.withOpacity(0.3) : ty.surface,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: isSelected ? ty.saffron : ty.line, width: isSelected ? 1.5 : 1),
        ),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(item.name, style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
                  if (item.description != null)
                    Text(item.description!, style: TyType.sans(12.5, color: ty.ink2), maxLines: 1, overflow: TextOverflow.ellipsis),
                ],
              ),
            ),
            const SizedBox(width: 12),
            Text('+₹${item.unitPrice.toInt()}', style: TyType.sans(14, color: ty.ink, weight: FontWeight.w800)),
            const SizedBox(width: 12),
            Icon(isSelected ? Icons.check_circle_rounded : Icons.add_circle_outline_rounded,
                color: isSelected ? ty.saffron : ty.ink3),
          ],
        ),
      ),
    );
  }

  Widget _deliveryStep(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _sectionLabel('EVENT TIMING'),
        Row(
          children: [
            Expanded(child: _staticField(context, Icons.event, DateFormat('dd MMM yyyy').format(_eventDate), onTap: _pickDate)),
            const SizedBox(width: 12),
            Expanded(child: _staticField(context, Icons.schedule, _eventTime.format(context), onTap: _pickTime)),
          ],
        ),
        const SizedBox(height: 24),
        _sectionLabel('RECEIVER DETAILS'),
        _textField(context, 'Recipient Name', _recipientNameCtrl, icon: Icons.person_outline),
        _textField(context, 'Phone Number', _recipientPhoneCtrl, icon: Icons.phone_android_outlined, type: TextInputType.phone),
        const SizedBox(height: 24),
        _sectionLabel('DELIVERY ADDRESS'),
        if (_savedAddresses.isNotEmpty) ...[
          _addressPicker(context),
          const SizedBox(height: 12),
        ],
        _textField(context, 'Building / Floor / Landmark', _landmarkCtrl, icon: Icons.location_city_outlined),
        _textField(context, 'Special Instructions', _specialNotesCtrl, icon: Icons.note_add_outlined, lines: 2),
      ],
    );
  }

  Widget _summaryStep(BuildContext context) {
    final ty = context.ty;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _infoRow('Package', _fullPackage.name),
        _infoRow('Date & Time', '${DateFormat('dd MMM').format(_eventDate)} · ${_eventTime.format(context)}'),
        _infoRow('Delivery To', _recipientNameCtrl.text.isNotEmpty ? _recipientNameCtrl.text : 'Me'),
        
        const SizedBox(height: 32),
        _sectionLabel('PRICE BREAKDOWN'),
        Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            color: ty.surface,
            borderRadius: BorderRadius.circular(22),
            border: Border.all(color: ty.line),
          ),
          child: Column(
            children: [
              _priceRow('Package Base Price', _fullPackage.price),
              if (_selectedOptionalItemIds.isNotEmpty)
                _priceRow('Selected Add-ons', _addonsTotal),
              _priceRow('GST (18%)', _totalPrice * 0.18),
              const Divider(height: 32),
              _priceRow('Grand Total', _totalPrice * 1.18, isBold: true),
            ],
          ),
        ),
      ],
    );
  }

  Widget _priceRow(String label, double amount, {bool isBold = false}) {
    final ty = context.ty;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: TyType.sans(14, color: isBold ? ty.ink : ty.ink2, weight: isBold ? FontWeight.w700 : FontWeight.w500)),
          Text('₹${amount.toInt()}', style: TyType.sans(15, color: ty.ink, weight: isBold ? FontWeight.w900 : FontWeight.w700)),
        ],
      ),
    );
  }

  Widget _infoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label.toUpperCase(), style: TyType.eyebrow(10, color: context.ty.ink3)),
          const SizedBox(height: 4),
          Text(value, style: TyType.sans(16, color: context.ty.ink, weight: FontWeight.w600)),
        ],
      ),
    );
  }

  Widget _sectionLabel(String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12, left: 4),
      child: Text(text, style: TyType.eyebrow(11, color: context.ty.ink3)),
    );
  }

  Widget _footer(BuildContext context) {
    final ty = context.ty;
    return Container(
      padding: EdgeInsets.fromLTRB(20, 16, 20, MediaQuery.of(context).padding.bottom + 16),
      decoration: BoxDecoration(
        color: ty.surface,
        border: Border(top: BorderSide(color: ty.line2)),
      ),
      child: Row(
        children: [
          if (_step == 2)
            Expanded(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Total Amount', style: TyType.sans(11, color: ty.ink3)),
                  Text('₹${(_totalPrice * 1.18).toInt()}', style: TyType.display(22, color: ty.ink)),
                ],
              ),
            ),
          Expanded(
            flex: 2,
            child: TyButton(
              _step == 2 ? (_isSubmitting ? 'Processing...' : 'Confirm & Pay') : 'Continue',
              full: true,
              enabled: !_isSubmitting,
              onTap: _next,
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _pickDate() async {
    final d = await showDatePicker(
      context: context,
      initialDate: _eventDate,
      firstDate: DateTime.now().add(const Duration(days: 7)),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );
    if (d != null) setState(() => _eventDate = d);
  }

  Future<void> _pickTime() async {
    final t = await showTimePicker(context: context, initialTime: _eventTime);
    if (t != null) setState(() => _eventTime = t);
  }

  Widget _textField(BuildContext context, String hint, TextEditingController ctrl, {IconData? icon, TextInputType type = TextInputType.text, int lines = 1}) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(color: context.ty.surface, borderRadius: BorderRadius.circular(14), border: Border.all(color: context.ty.line)),
      child: TextField(
        controller: ctrl,
        keyboardType: type,
        maxLines: lines,
        style: TyType.sans(15, weight: FontWeight.w600),
        decoration: InputDecoration(
          hintText: hint,
          prefixIcon: icon != null ? Icon(icon, size: 18, color: context.ty.ink3) : null,
          border: InputBorder.none,
          contentPadding: const EdgeInsets.all(14),
        ),
      ),
    );
  }

  Widget _staticField(BuildContext context, IconData icon, String value, {VoidCallback? onTap}) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(color: context.ty.surface, borderRadius: BorderRadius.circular(14), border: Border.all(color: context.ty.line)),
        child: Row(
          children: [
            Icon(icon, size: 18, color: context.ty.saffron),
            const SizedBox(width: 10),
            Text(value, style: TyType.sans(15, weight: FontWeight.w700)),
          ],
        ),
      ),
    );
  }

  Widget _addressPicker(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14),
      decoration: BoxDecoration(color: context.ty.surface, borderRadius: BorderRadius.circular(14), border: Border.all(color: context.ty.line)),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<Address>(
          value: _selectedAddress,
          isExpanded: true,
          items: _savedAddresses.map((a) => DropdownMenuItem(value: a, child: Text(a.label, style: TyType.sans(15, weight: FontWeight.w600)))).toList(),
          onChanged: (v) => setState(() => _selectedAddress = v),
        ),
      ),
    );
  }
}
