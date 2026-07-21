import 'package:flutter/material.dart';

import '../../../theme/colors.dart';
import '../../../theme/responsive.dart';
import '../../../theme/typography.dart';
import '../../../data/models.dart';
import '../../../data/services/booking_service.dart';
import 'vendor_booking_detail_screen.dart';

const _statusOptions = [
  ('', 'All Statuses'),
  ('pending', 'Pending'),
  ('confirmed', 'Confirmed'),
  ('in_progress', 'In Progress'),
  ('completed', 'Completed'),
  ('cancelled', 'Cancelled'),
];

class VendorBookingsScreen extends StatefulWidget {
  const VendorBookingsScreen({super.key});

  @override
  State<VendorBookingsScreen> createState() => _VendorBookingsScreenState();
}

class _VendorBookingsScreenState extends State<VendorBookingsScreen> {
  final _bookingService = BookingService();
  final _searchCtrl = TextEditingController();
  String _status = '';
  List<Booking> _bookings = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  Future<void> _load({String? status, String? search}) async {
    final targetStatus = status ?? _status;
    final targetSearch = search ?? _searchCtrl.text.trim();

    setState(() => _isLoading = true);
    try {
      final result = await _bookingService.listVendorBookings(
        search: targetSearch,
        status: targetStatus,
      );
      if (mounted) {
        setState(() { 
          _bookings = result['items'] as List<Booking>; 
          _isLoading = false; 
        });
      }
    } catch (_) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final resp = context.resp;

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: EdgeInsets.fromLTRB(resp.w(18), resp.h(4), resp.w(18), resp.h(10)),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  TextField(
                    controller: _searchCtrl,
                    decoration: InputDecoration(
                      hintText: 'Search by booking # or customer…',
                      prefixIcon: const Icon(Icons.search),
                      filled: true,
                      fillColor: ty.surface,
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: ty.line)),
                      isDense: true,
                    ),
                    onSubmitted: (val) => _load(search: val.trim()),
                  ),
                  SizedBox(height: resp.h(10)),
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(
                      children: _statusOptions.map((s) {
                        final isSelected = _status == s.$1;
                        return Padding(
                          padding: const EdgeInsets.only(right: 8),
                          child: ChoiceChip(
                            label: Text(s.$2),
                            labelStyle: TyType.sans(12.5, 
                              color: isSelected ? ty.onPrimary : ty.ink2,
                              weight: isSelected ? FontWeight.w700 : FontWeight.w600,
                            ),
                            selected: isSelected,
                            selectedColor: ty.saffron,
                            backgroundColor: ty.surface,
                            checkmarkColor: ty.onPrimary,
                            side: BorderSide(color: isSelected ? ty.saffron : ty.line),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                            onSelected: (val) { 
                              if (val) {
                                setState(() => _status = s.$1); 
                                _load(status: s.$1);
                              }
                            },
                          ),
                        );
                      }).toList(),
                    ),
                  ),
                ],
              ),
            ),
            Expanded(
              child: _isLoading
                  ? const Center(child: CircularProgressIndicator())
                  : _bookings.isEmpty
                      ? Center(child: Text('No bookings found', style: TyType.sans(14, color: ty.ink2)))
                      : RefreshIndicator(
                          onRefresh: _load,
                          child: ListView.separated(
                            padding: EdgeInsets.symmetric(horizontal: resp.w(18), vertical: resp.h(10)),
                            itemCount: _bookings.length,
                            separatorBuilder: (_, __) => SizedBox(height: resp.h(10)),
                            itemBuilder: (context, i) => _bookingCard(context, _bookings[i]),
                          ),
                        ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _bookingCard(BuildContext context, Booking b) {
    final ty = context.ty;
    final statusColor = {
      'pending': Colors.orange,
      'confirmed': Colors.blue,
      'in_progress': Colors.purple,
      'completed': Colors.green,
      'cancelled': Colors.red,
    }[b.status] ?? ty.ink3;

    return GestureDetector(
      onTap: () => Navigator.of(context)
          .push(MaterialPageRoute(builder: (_) => VendorBookingDetailScreen(bookingId: b.id)))
          .then((_) => _load()),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(14), border: Border.all(color: ty.line)),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(b.bookingNumber, style: TyType.sans(13, color: ty.ink3, weight: FontWeight.w600)),
                  const SizedBox(height: 2),
                  Text(b.packageName ?? 'Package', style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
                  const SizedBox(height: 4),
                  Text('${b.scheduledDate.day}/${b.scheduledDate.month}/${b.scheduledDate.year} · ₹${b.totalAmount.toStringAsFixed(0)}',
                      style: TyType.sans(12.5, color: ty.ink2)),
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: BoxDecoration(color: statusColor.withOpacity(0.12), borderRadius: BorderRadius.circular(99)),
              child: Text(b.status.replaceAll('_', ' '), style: TyType.sans(11, color: statusColor, weight: FontWeight.w700)),
            ),
          ],
        ),
      ),
    );
  }
}
