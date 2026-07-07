import 'package:flutter/material.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/services/support_service.dart';
import '../widgets/ty_button.dart';
import '../widgets/common.dart';

class RaiseTicketScreen extends StatefulWidget {
  const RaiseTicketScreen({super.key});

  @override
  State<RaiseTicketScreen> createState() => _RaiseTicketScreenState();
}

class _RaiseTicketScreenState extends State<RaiseTicketScreen> {
  final SupportService _supportService = SupportService();
  String _category = 'Planning';
  final _descCtrl = TextEditingController();
  bool _isSubmitting = false;

  @override
  void dispose() {
    _descCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final description = _descCtrl.text.trim();
    if (description.length < 20) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please describe your issue in at least 20 characters.')),
      );
      return;
    }

    setState(() => _isSubmitting = true);
    try {
      await _supportService.createTicket(
        category: ticketCategoryOptions[_category] ?? 'general',
        subject: 'Ticket: $_category',
        description: description,
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Ticket raised successfully!')),
        );
        Navigator.of(context).pop();
      }
    } catch (e) {
      debugPrint('Error raising ticket: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Failed to raise ticket. Please try again.')),
        );
      }
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: 'Raise a Ticket'),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
        children: [
          Text('Tell us what’s wrong', style: TyType.display(24, color: ty.ink)),
          const SizedBox(height: 8),
          Text('We usually respond within 2-4 business hours.', style: TyType.sans(14, color: ty.ink2)),
          const SizedBox(height: 32),
          
          _fieldLabel(context, 'Category'),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            decoration: BoxDecoration(
              color: ty.surface,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: ty.line, width: 1.5),
            ),
            child: DropdownButtonHideUnderline(
              child: DropdownButton<String>(
                value: _category,
                isExpanded: true,
                icon: Icon(Icons.keyboard_arrow_down_rounded, color: ty.ink2),
                style: TyType.sans(15, color: ty.ink, weight: FontWeight.w600),
                onChanged: (v) => setState(() => _category = v!),
                items: ['Planning', 'Packages', 'Payments', 'Technical Issue', 'Others']
                    .map((s) => DropdownMenuItem(value: s, child: Text(s)))
                    .toList(),
              ),
            ),
          ),
          
          const SizedBox(height: 24),
          
          _fieldLabel(context, 'Description'),
          const SizedBox(height: 12),
          TextField(
            controller: _descCtrl,
            maxLines: 6,
            style: TyType.sans(15, color: ty.ink),
            decoration: InputDecoration(
              hintText: 'Describe your issue in detail (at least 20 characters)...',
              hintStyle: TyType.sans(14, color: ty.ink3),
              filled: true,
              fillColor: ty.surface,
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(16),
                borderSide: BorderSide(color: ty.line, width: 1.5),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(16),
                borderSide: BorderSide(color: ty.saffron, width: 1.5),
              ),
            ),
          ),
          
          const SizedBox(height: 24),
          
          _fieldLabel(context, 'Attachments (Optional)'),
          const SizedBox(height: 12),
          GestureDetector(
            onTap: () {},
            child: Container(
              height: 100,
              decoration: BoxDecoration(
                color: ty.surface2,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: ty.line, style: BorderStyle.solid),
              ),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.add_a_photo_outlined, color: ty.ink3, size: 28),
                  const SizedBox(height: 8),
                  Text('Add screenshots', style: TyType.sans(12, color: ty.ink3, weight: FontWeight.w600)),
                ],
              ),
            ),
          ),
          
          const SizedBox(height: 48),
          
          TyButton(
            _isSubmitting ? 'Submitting...' : 'Submit Ticket', 
            full: true, 
            enabled: !_isSubmitting && _descCtrl.text.isNotEmpty,
            onTap: _submit
          ),
        ],
      ),
    );
  }

  Widget _fieldLabel(BuildContext context, String label) {
    return Text(label.toUpperCase(), style: TyType.eyebrow(11, color: context.ty.ink3));
  }
}
