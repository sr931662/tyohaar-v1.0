import 'package:flutter/material.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/services/support_service.dart';
import '../l10n/generated/app_localizations.dart';
import '../utils/log.dart';
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
  void initState() {
    super.initState();
    _descCtrl.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _descCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final l = AppLocalizations.of(context)!;
    final description = _descCtrl.text.trim();
    if (description.length < 20) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l.raiseTicketDescriptionTooShortError)),
      );
      return;
    }

    setState(() => _isSubmitting = true);
    try {
      await _supportService.createTicket(
        category: ticketCategoryOptions(context)[_category] ?? 'general',
        subject: l.raiseTicketSubjectLabel(_category),
        description: description,
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(l.raiseTicketSuccessMessage)),
        );
        Navigator.of(context).pop();
      }
    } catch (e) {
      logDebug('Error raising ticket: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(l.raiseTicketSubmitError)),
        );
      }
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l = AppLocalizations.of(context)!;

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: l.raiseTicketTitle),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
        children: [
          Text(l.raiseTicketHeading, style: TyType.display(24, color: ty.ink)),
          const SizedBox(height: 8),
          Text(l.raiseTicketResponseTimeMessage, style: TyType.sans(14, color: ty.ink2)),
          const SizedBox(height: 32),

          _fieldLabel(context, l.raiseTicketCategoryLabel),
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
                items: ticketCategoryOptions(context).keys
                    .map((s) => DropdownMenuItem(value: s, child: Text(s)))
                    .toList(),
              ),
            ),
          ),

          const SizedBox(height: 24),

          _fieldLabel(context, l.raiseTicketDescriptionLabel),
          const SizedBox(height: 12),
          TextField(
            controller: _descCtrl,
            maxLines: 6,
            style: TyType.sans(15, color: ty.ink),
            decoration: InputDecoration(
              hintText: l.raiseTicketDescriptionHint,
              hintStyle: TyType.sans(14, color: ty.ink3),
              helperText: l.raiseTicketDescriptionFormatHelperText,
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

          _fieldLabel(context, l.raiseTicketAttachmentsLabel),
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
                  Text(l.raiseTicketAddScreenshotsLabel, style: TyType.sans(12, color: ty.ink3, weight: FontWeight.w600)),
                ],
              ),
            ),
          ),

          const SizedBox(height: 48),

          TyButton(
            _isSubmitting ? l.raiseTicketSubmittingLabel : l.raiseTicketSubmitButtonLabel,
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
