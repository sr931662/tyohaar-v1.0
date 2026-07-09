import 'package:flutter/material.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/services/feedback_service.dart';
import '../widgets/common.dart';
import '../widgets/ty_button.dart';

const Map<String, String> feedbackCategoryOptions = {
  'General': 'general',
  'Bug Report': 'bug_report',
  'Feature Request': 'feature_request',
  'Vendor Experience': 'vendor_experience',
  'App Experience': 'app_experience',
  'Other': 'other',
};

class FeedbackScreen extends StatefulWidget {
  const FeedbackScreen({super.key});

  @override
  State<FeedbackScreen> createState() => _FeedbackScreenState();
}

class _FeedbackScreenState extends State<FeedbackScreen> {
  final FeedbackService _feedbackService = FeedbackService();
  final _commentsCtrl = TextEditingController();
  int _rating = 0;
  String _category = 'General';
  bool _isSubmitting = false;
  bool _submitted = false;

  @override
  void dispose() {
    _commentsCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_rating == 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select a rating.')),
      );
      return;
    }
    setState(() => _isSubmitting = true);
    try {
      await _feedbackService.submitFeedback(
        rating: _rating,
        category: feedbackCategoryOptions[_category] ?? 'general',
        comments: _commentsCtrl.text,
      );
      if (mounted) setState(() { _isSubmitting = false; _submitted = true; });
    } catch (e) {
      if (mounted) {
        setState(() => _isSubmitting = false);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not submit feedback. Please try again.')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;

    if (_submitted) {
      return Scaffold(
        backgroundColor: ty.paper,
        appBar: tyAppBar(context, title: 'Feedback'),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(32),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.check_circle_rounded, size: 56, color: ty.leaf),
                const SizedBox(height: 20),
                Text('Thanks for your feedback!', style: TyType.display(20, color: ty.ink)),
                const SizedBox(height: 8),
                Text(
                  'We read every submission and use it to improve Tyohaar.',
                  textAlign: TextAlign.center,
                  style: TyType.sans(13.5, color: ty.ink3, height: 1.5),
                ),
                const SizedBox(height: 24),
                TyButton('Done', onTap: () => Navigator.of(context).pop()),
              ],
            ),
          ),
        ),
      );
    }

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: 'Share Feedback'),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
        children: [
          Text('How was your experience?', style: TyType.display(18, color: ty.ink)),
          const SizedBox(height: 6),
          Text(
            'Your feedback helps us make Tyohaar better for everyone.',
            style: TyType.sans(13.5, color: ty.ink3, height: 1.5),
          ),
          const SizedBox(height: 24),
          Center(
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: List.generate(5, (i) {
                final starIndex = i + 1;
                final filled = starIndex <= _rating;
                return GestureDetector(
                  onTap: () => setState(() => _rating = starIndex),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 6),
                    child: Icon(
                      filled ? Icons.star_rounded : Icons.star_outline_rounded,
                      size: 40,
                      color: filled ? ty.saffron : ty.line2,
                    ),
                  ),
                );
              }),
            ),
          ),
          const SizedBox(height: 28),
          Text('Category', style: TyType.sans(12, color: ty.ink3, weight: FontWeight.w600)),
          const SizedBox(height: 10),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            decoration: BoxDecoration(
              color: ty.surface2,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: ty.line),
            ),
            child: DropdownButtonHideUnderline(
              child: DropdownButton<String>(
                value: _category,
                isExpanded: true,
                items: feedbackCategoryOptions.keys
                    .map((label) => DropdownMenuItem(value: label, child: Text(label, style: TyType.sans(14, color: ty.ink))))
                    .toList(),
                onChanged: (v) => setState(() => _category = v ?? _category),
              ),
            ),
          ),
          const SizedBox(height: 20),
          Text('Comments (optional)', style: TyType.sans(12, color: ty.ink3, weight: FontWeight.w600)),
          const SizedBox(height: 10),
          Container(
            decoration: BoxDecoration(
              color: ty.surface2,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: ty.line),
            ),
            child: TextField(
              controller: _commentsCtrl,
              maxLines: 5,
              maxLength: 2000,
              style: TyType.sans(14, color: ty.ink),
              decoration: InputDecoration(
                hintText: 'Tell us more...',
                hintStyle: TyType.sans(14, color: ty.ink3),
                contentPadding: const EdgeInsets.all(16),
                border: InputBorder.none,
              ),
            ),
          ),
          const SizedBox(height: 24),
          TyButton(
            _isSubmitting ? 'Submitting...' : 'Submit Feedback',
            full: true,
            enabled: !_isSubmitting,
            onTap: _submit,
          ),
        ],
      ),
    );
  }
}
