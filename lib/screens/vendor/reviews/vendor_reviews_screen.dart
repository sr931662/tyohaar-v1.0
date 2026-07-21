import 'package:flutter/material.dart';

import '../../../theme/colors.dart';
import '../../../theme/typography.dart';
import '../../../data/vendor_models.dart';
import '../../../data/services/vendor_service.dart';

class VendorReviewsScreen extends StatefulWidget {
  const VendorReviewsScreen({super.key});

  @override
  State<VendorReviewsScreen> createState() => _VendorReviewsScreenState();
}

class _VendorReviewsScreenState extends State<VendorReviewsScreen> {
  final _vendorService = VendorService();
  VendorBusinessProfile? _vendor;
  List<VendorReview> _reviews = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _isLoading = true);
    try {
      final vendor = await _vendorService.getMe();
      if (vendor == null) {
        setState(() => _isLoading = false);
        return;
      }
      final reviews = await _vendorService.listReviews(vendor.id);
      if (mounted) setState(() { _vendor = vendor; _reviews = reviews; _isLoading = false; });
    } catch (_) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: AppBar(title: const Text('Reviews')),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _vendor == null
              ? Center(child: Text('Set up your vendor profile first.', style: TyType.sans(14, color: ty.ink2)))
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(
                    padding: const EdgeInsets.all(18),
                    children: [
                      Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(14), border: Border.all(color: ty.line)),
                        child: Row(
                          children: [
                            Text(_vendor!.averageRating.toStringAsFixed(1), style: TyType.display(32, color: ty.ink)),
                            const SizedBox(width: 12),
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(children: List.generate(5, (i) => Icon(
                                      i < _vendor!.averageRating.round() ? Icons.star_rounded : Icons.star_border_rounded,
                                      color: Colors.amber, size: 18,
                                    ))),
                                Text('${_vendor!.reviewCount} reviews', style: TyType.sans(12.5, color: ty.ink2)),
                              ],
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 16),
                      if (_reviews.isEmpty)
                        Text('No reviews yet', style: TyType.sans(14, color: ty.ink2))
                      else
                        ..._reviews.map((r) => Container(
                              margin: const EdgeInsets.only(bottom: 10),
                              padding: const EdgeInsets.all(14),
                              decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(14), border: Border.all(color: ty.line)),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(children: [
                                    Row(children: List.generate(5, (i) => Icon(
                                          i < r.rating ? Icons.star_rounded : Icons.star_border_rounded,
                                          color: Colors.amber, size: 14,
                                        ))),
                                    const Spacer(),
                                    Text('${r.createdAt.day}/${r.createdAt.month}/${r.createdAt.year}', style: TyType.sans(11, color: ty.ink3)),
                                  ]),
                                  if (r.title != null && r.title!.isNotEmpty) ...[
                                    const SizedBox(height: 6),
                                    Text(r.title!, style: TyType.sans(13.5, color: ty.ink, weight: FontWeight.w700)),
                                  ],
                                  if (r.body != null && r.body!.isNotEmpty) ...[
                                    const SizedBox(height: 4),
                                    Text(r.body!, style: TyType.sans(13, color: ty.ink2)),
                                  ],
                                ],
                              ),
                            )),
                    ],
                  ),
                ),
    );
  }
}
