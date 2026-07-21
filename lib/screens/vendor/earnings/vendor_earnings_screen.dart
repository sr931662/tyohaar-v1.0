import 'package:flutter/material.dart';

import '../../../theme/colors.dart';
import '../../../theme/typography.dart';
import '../../../data/vendor_models.dart';
import '../../../data/services/vendor_service.dart';

class VendorEarningsScreen extends StatefulWidget {
  const VendorEarningsScreen({super.key});

  @override
  State<VendorEarningsScreen> createState() => _VendorEarningsScreenState();
}

class _VendorEarningsScreenState extends State<VendorEarningsScreen> {
  final _vendorService = VendorService();
  VendorEarnings? _earnings;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _isLoading = true);
    try {
      final earnings = await _vendorService.getEarnings();
      if (mounted) setState(() { _earnings = earnings; _isLoading = false; });
    } catch (_) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: AppBar(title: const Text('Earnings')),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _earnings == null
              ? Center(child: Text('Could not load earnings.', style: TyType.sans(14, color: ty.ink2)))
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(
                    padding: const EdgeInsets.all(18),
                    children: [
                      Row(
                        children: [
                          Expanded(child: _metricCard(ty, 'Total Collected', '₹${_earnings!.totalCollected.toStringAsFixed(0)}')),
                          const SizedBox(width: 10),
                          Expanded(child: _metricCard(ty, 'Pending', '₹${_earnings!.pending.toStringAsFixed(0)}')),
                        ],
                      ),
                      const SizedBox(height: 10),
                      _metricCard(ty, 'Bookings Paid', '${_earnings!.bookingsPaid}'),
                      const SizedBox(height: 20),
                      Text('Payment History', style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
                      const SizedBox(height: 10),
                      if (_earnings!.history.isEmpty)
                        Text('No payments yet', style: TyType.sans(13, color: ty.ink2))
                      else
                        ..._earnings!.history.map((p) => Container(
                              margin: const EdgeInsets.only(bottom: 10),
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(12), border: Border.all(color: ty.line)),
                              child: Row(
                                children: [
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(p.paymentNumber ?? p.id.substring(0, 8), style: TyType.sans(13, color: ty.ink, weight: FontWeight.w700)),
                                        Text('${p.method ?? '—'} · ${p.createdAt.day}/${p.createdAt.month}/${p.createdAt.year}',
                                            style: TyType.sans(11.5, color: ty.ink2)),
                                      ],
                                    ),
                                  ),
                                  Column(
                                    crossAxisAlignment: CrossAxisAlignment.end,
                                    children: [
                                      Text('₹${p.amount.toStringAsFixed(0)}', style: TyType.sans(14, color: ty.ink, weight: FontWeight.w700)),
                                      Text(p.status, style: TyType.sans(11, color: ty.ink3)),
                                    ],
                                  ),
                                ],
                              ),
                            )),
                    ],
                  ),
                ),
    );
  }

  Widget _metricCard(TyColors ty, String label, String value) => Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(14), border: Border.all(color: ty.line)),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: TyType.sans(12.5, color: ty.ink2)),
            const SizedBox(height: 6),
            Text(value, style: TyType.display(20, color: ty.ink)),
          ],
        ),
      );
}
