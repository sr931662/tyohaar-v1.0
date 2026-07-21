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
      backgroundColor: Colors.transparent,
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _vendor == null
              ? Center(child: Text('Set up your vendor profile first.', style: TyType.sans(14, color: ty.ink2)))
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
                    children: [
                      Container(
                        padding: const EdgeInsets.all(20),
                        decoration: BoxDecoration(
                          color: ty.surface, 
                          borderRadius: BorderRadius.circular(16), 
                          border: Border.all(color: ty.line),
                          boxShadow: [
                            BoxShadow(color: Colors.black.withOpacity(0.02), blurRadius: 8, offset: const Offset(0, 2)),
                          ],
                        ),
                        child: Row(
                          children: [
                            Text(_vendor!.averageRating.toStringAsFixed(1), style: TyType.display(36, color: ty.ink)),
                            const SizedBox(width: 16),
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(children: List.generate(5, (i) => Icon(
                                      i < _vendor!.averageRating.round() ? Icons.star_rounded : Icons.star_border_rounded,
                                      color: ty.gold, size: 20,
                                    ))),
                                const SizedBox(height: 2),
                                Text('${_vendor!.reviewCount} verified reviews', style: TyType.sans(12.5, color: ty.ink2, weight: FontWeight.w600)),
                              ],
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 24),
                      if (_reviews.isEmpty)
                        Center(
                          child: Padding(
                            padding: const EdgeInsets.only(top: 40),
                            child: Column(
                              children: [
                                Icon(Icons.rate_review_outlined, size: 48, color: ty.ink3.withOpacity(0.5)),
                                const SizedBox(height: 16),
                                Text('No reviews yet', style: TyType.sans(14, color: ty.ink2)),
                              ],
                            ),
                          ),
                        )
                      else
                        ..._reviews.map((r) => Container(
                              margin: const EdgeInsets.only(bottom: 12),
                              padding: const EdgeInsets.all(16),
                              decoration: BoxDecoration(
                                color: ty.surface, 
                                borderRadius: BorderRadius.circular(16), 
                                border: Border.all(color: ty.line),
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(children: [
                                    Row(children: List.generate(5, (i) => Icon(
                                          i < r.rating ? Icons.star_rounded : Icons.star_border_rounded,
                                          color: ty.gold, size: 14,
                                        ))),
                                    const Spacer(),
                                    Text('${r.createdAt.day}/${r.createdAt.month}/${r.createdAt.year}', style: TyType.sans(11, color: ty.ink3, weight: FontWeight.w600)),
                                  ]),
                                  if (r.title != null && r.title!.isNotEmpty) ...[
                                    const SizedBox(height: 8),
                                    Text(r.title!, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w700)),
                                  ],
                                  if (r.body != null && r.body!.isNotEmpty) ...[
                                    const SizedBox(height: 4),
                                    Text(r.body!, style: TyType.sans(13.5, color: ty.ink2)),
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
