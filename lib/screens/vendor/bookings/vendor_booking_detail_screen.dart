import 'package:flutter/material.dart';

import '../../../theme/colors.dart';
import '../../../theme/typography.dart';
import '../../../data/models.dart';
import '../../../data/services/booking_service.dart';
import '../../../widgets/state_screens.dart';

class VendorBookingDetailScreen extends StatefulWidget {
  final String bookingId;
  const VendorBookingDetailScreen({super.key, required this.bookingId});

  @override
  State<VendorBookingDetailScreen> createState() => _VendorBookingDetailScreenState();
}

class _VendorBookingDetailScreenState extends State<VendorBookingDetailScreen> with SingleTickerProviderStateMixin {
  final _bookingService = BookingService();
  late final TabController _tabController = TabController(length: 3, vsync: this);
  Booking? _booking;
  List<Map<String, dynamic>> _history = [];
  List<Map<String, dynamic>> _statusHistory = [];
  bool _isLoading = true;
  bool _isActing = false;
  bool _historyLoaded = false;
  bool _historyError = false;

  @override
  void initState() {
    super.initState();
    _load();
    _tabController.addListener(() {
      if (_tabController.index == 2 && !_historyLoaded) _loadHistory();
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() => _isLoading = true);
    try {
      final booking = await _bookingService.getBookingDetails(widget.bookingId);
      if (mounted) setState(() { _booking = booking; _isLoading = false; });
    } catch (_) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _loadHistory() async {
    setState(() => _historyError = false);
    try {
      final results = await Future.wait([
        _bookingService.getBookingHistory(widget.bookingId),
        _bookingService.getBookingStatusHistory(widget.bookingId),
      ]);
      if (mounted) {
        setState(() {
          _history = results[0];
          _statusHistory = results[1];
          _historyLoaded = true;
        });
      }
    } catch (_) {
      if (mounted) setState(() { _historyLoaded = true; _historyError = true; });
    }
  }

  Future<void> _start() async {
    setState(() => _isActing = true);
    try {
      final b = await _bookingService.startBooking(widget.bookingId);
      if (mounted) setState(() { _booking = b; _isActing = false; });
    } catch (e) {
      if (mounted) {
        setState(() => _isActing = false);
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Could not start service.')));
      }
    }
  }

  Future<void> _complete() async {
    setState(() => _isActing = true);
    try {
      final b = await _bookingService.completeBooking(widget.bookingId);
      if (mounted) setState(() { _booking = b; _isActing = false; });
    } catch (e) {
      if (mounted) {
        setState(() => _isActing = false);
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Could not mark complete.')));
      }
    }
  }

  Future<void> _setPst() async {
    final now = DateTime.now();
    final date = await showDatePicker(context: context, initialDate: now, firstDate: now, lastDate: now.add(const Duration(days: 90)));
    if (date == null || !mounted) return;
    final time = await showTimePicker(context: context, initialTime: TimeOfDay.now());
    if (time == null || !mounted) return;
    final dt = DateTime(date.year, date.month, date.day, time.hour, time.minute);
    setState(() => _isActing = true);
    try {
      final b = await _bookingService.setPreparationStartTime(widget.bookingId, dt);
      if (mounted) setState(() { _booking = b; _isActing = false; });
    } catch (_) {
      if (mounted) {
        setState(() => _isActing = false);
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Could not update prep time.')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;

    if (_isLoading) {
      return Scaffold(backgroundColor: ty.paper, appBar: AppBar(), body: const Center(child: CircularProgressIndicator()));
    }
    if (_booking == null) {
      return Scaffold(backgroundColor: ty.paper, appBar: AppBar(), body: const Center(child: Text('Booking not found')));
    }

    final b = _booking!;

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: AppBar(
        title: Text(b.bookingNumber),
        bottom: TabBar(controller: _tabController, tabs: const [Tab(text: 'Overview'), Tab(text: 'Items'), Tab(text: 'History')]),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildOverview(ty, b),
          _buildItems(ty),
          _buildHistory(ty),
        ],
      ),
    );
  }

  Widget _buildOverview(TyColors ty, Booking b) {
    return ListView(
      padding: const EdgeInsets.all(18),
      children: [
        if (b.celebrationTitle != null && b.celebrationTitle!.isNotEmpty)
          _row(ty, 'Celebration', b.celebrationTitle!),
        _row(ty, 'Package', b.packageName ?? '—'),
        if (b.themeName != null && b.themeName!.isNotEmpty)
          _row(ty, 'Customization Theme', b.themeName!),
        _row(ty, 'Status', b.status.replaceAll('_', ' ')),
        _row(ty, 'Payment', b.paymentStatus.replaceAll('_', ' ')),
        _row(ty, 'Scheduled', '${b.scheduledDate.day}/${b.scheduledDate.month}/${b.scheduledDate.year}'),
        _row(ty, 'Total', '₹${b.totalAmount.toStringAsFixed(0)}'),
        _row(ty, 'Paid', '₹${b.amountPaid.toStringAsFixed(0)}'),
        _row(ty, 'Due', '₹${b.amountDue.toStringAsFixed(0)}'),
        if (b.specialInstructions != null && b.specialInstructions!.isNotEmpty)
          _row(ty, 'Instructions', b.specialInstructions!),
        if (b.preparationStartAt != null)
          _row(ty, 'Prep Start', b.preparationStartAt.toString()),
        const SizedBox(height: 20),
        if (b.status == 'confirmed') ...[
          ElevatedButton(onPressed: _isActing ? null : _start, child: const Text('Start Service')),
          const SizedBox(height: 10),
          OutlinedButton(onPressed: _isActing ? null : _setPst, child: const Text('Set Preparation Start Time')),
        ] else if (b.status == 'in_progress') ...[
          ElevatedButton(onPressed: _isActing ? null : _complete, child: const Text('Mark Complete')),
          const SizedBox(height: 10),
          OutlinedButton(onPressed: _isActing ? null : _setPst, child: const Text('Update Preparation Start Time')),
        ],
      ],
    );
  }

  Widget _buildItems(TyColors ty) {
    final items = _booking!.items;
    if (items.isEmpty) return Center(child: Text('No items', style: TyType.sans(14, color: ty.ink2)));
    return ListView.separated(
      padding: const EdgeInsets.all(18),
      itemCount: items.length,
      separatorBuilder: (_, __) => const SizedBox(height: 10),
      itemBuilder: (context, i) {
        final item = items[i];
        return Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(12), border: Border.all(color: ty.line)),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(item.name, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w700)),
                    Text('Qty ${item.quantity} · ₹${item.unitPrice.toStringAsFixed(0)} each', style: TyType.sans(12.5, color: ty.ink2)),
                  ],
                ),
              ),
              Text('₹${item.finalPrice.toStringAsFixed(0)}', style: TyType.sans(14, color: ty.ink, weight: FontWeight.w700)),
            ],
          ),
        );
      },
    );
  }

  Widget _buildHistory(TyColors ty) {
    if (!_historyLoaded) return const Center(child: CircularProgressIndicator());
    if (_historyError) {
      return TyStateScreen.error(onAction: () {
        setState(() => _historyLoaded = false);
        _loadHistory();
      });
    }
    if (_statusHistory.isEmpty && _history.isEmpty) {
      return Center(child: Text('No history yet', style: TyType.sans(14, color: ty.ink2)));
    }
    return ListView(
      padding: const EdgeInsets.all(18),
      children: [
        if (_statusHistory.isNotEmpty) ...[
          Text('Status Changes', style: TyType.sans(14, color: ty.ink, weight: FontWeight.w700)),
          const SizedBox(height: 8),
          ..._statusHistory.map((s) => _historyRow(ty, '${s['from_status'] ?? '—'} → ${s['to_status'] ?? '—'}', s['created_at']?.toString())),
          const SizedBox(height: 16),
        ],
        if (_history.isNotEmpty) ...[
          Text('Event Log', style: TyType.sans(14, color: ty.ink, weight: FontWeight.w700)),
          const SizedBox(height: 8),
          ..._history.map((e) => _historyRow(ty, e['event_label']?.toString() ?? e['event_type']?.toString() ?? 'Event', e['created_at']?.toString())),
        ],
      ],
    );
  }

  Widget _historyRow(TyColors ty, String label, String? date) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(
          children: [
            Icon(Icons.circle, size: 8, color: ty.saffron),
            const SizedBox(width: 10),
            Expanded(child: Text(label, style: TyType.sans(13, color: ty.ink))),
            if (date != null) Text(date.split('T').first, style: TyType.sans(11.5, color: ty.ink3)),
          ],
        ),
      );

  Widget _row(TyColors ty, String label, String value) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label, style: TyType.sans(13, color: ty.ink2)),
            const SizedBox(width: 12),
            Expanded(child: Text(value, textAlign: TextAlign.end, style: TyType.sans(13, color: ty.ink, weight: FontWeight.w600))),
          ],
        ),
      );
}
