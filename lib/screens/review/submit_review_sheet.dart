import 'package:flutter/material.dart';
import '../../theme/colors.dart';
import '../../theme/typography.dart';
import '../../widgets/ty_button.dart';
import '../../widgets/ty_rating_stars.dart';

/// Reusable "write a review" bottom sheet — used for both package reviews
/// and package item reviews. The caller supplies [onSubmit], which posts to
/// whichever endpoint applies (package or item).
Future<void> showSubmitReviewSheet(
  BuildContext context, {
  required String title,
  required Future<void> Function(int rating, String? title, String? body) onSubmit,
}) {
  return showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (_) => _SubmitReviewSheet(title: title, onSubmit: onSubmit),
  );
}

class _SubmitReviewSheet extends StatefulWidget {
  final String title;
  final Future<void> Function(int rating, String? title, String? body) onSubmit;
  const _SubmitReviewSheet({required this.title, required this.onSubmit});

  @override
  State<_SubmitReviewSheet> createState() => _SubmitReviewSheetState();
}

class _SubmitReviewSheetState extends State<_SubmitReviewSheet> {
  int _rating = 0;
  final _titleCtrl = TextEditingController();
  final _bodyCtrl = TextEditingController();
  bool _submitting = false;
  String? _error;

  @override
  void dispose() {
    _titleCtrl.dispose();
    _bodyCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_rating == 0) {
      setState(() => _error = 'Please select a star rating.');
      return;
    }
    setState(() { _submitting = true; _error = null; });
    try {
      await widget.onSubmit(
        _rating,
        _titleCtrl.text.trim().isNotEmpty ? _titleCtrl.text.trim() : null,
        _bodyCtrl.text.trim().isNotEmpty ? _bodyCtrl.text.trim() : null,
      );
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      if (mounted) setState(() => _error = 'Could not submit your review. Please try again.');
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: Container(
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
        decoration: BoxDecoration(
          color: ty.paper,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Center(
              child: Container(
                width: 40, height: 4,
                decoration: BoxDecoration(color: ty.line, borderRadius: BorderRadius.circular(2)),
              ),
            ),
            const SizedBox(height: 16),
            Text(widget.title, style: TyType.display(18, color: ty.ink)),
            const SizedBox(height: 16),
            Center(
              child: TyRatingStars(
                value: _rating,
                size: 32,
                onChanged: (v) => setState(() { _rating = v; _error = null; }),
              ),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _titleCtrl,
              style: TyType.sans(14.5, color: ty.ink, weight: FontWeight.w500),
              decoration: InputDecoration(
                isDense: true,
                hintText: 'Give your review a title (optional)',
                contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                filled: true,
                fillColor: ty.surface,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide(color: ty.line, width: 1.5),
                ),
              ),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: _bodyCtrl,
              maxLines: 4,
              style: TyType.sans(14.5, color: ty.ink, weight: FontWeight.w500),
              decoration: InputDecoration(
                isDense: true,
                hintText: 'Share details about your experience (optional)',
                contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                filled: true,
                fillColor: ty.surface,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide(color: ty.line, width: 1.5),
                ),
              ),
            ),
            if (_error != null) ...[
              const SizedBox(height: 8),
              Text(_error!, style: TyType.sans(12.5, color: ty.rose)),
            ],
            const SizedBox(height: 18),
            TyButton(
              _submitting ? 'Submitting...' : 'Submit Review',
              full: true,
              enabled: !_submitting,
              onTap: _submit,
            ),
          ],
        ),
      ),
    );
  }
}
