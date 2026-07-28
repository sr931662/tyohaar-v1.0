import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/services/support_service.dart';
import '../widgets/common.dart';
import '../widgets/state_screens.dart';
import '../widgets/ty_button.dart';
import '../l10n/generated/app_localizations.dart';

class TicketDetailScreen extends StatefulWidget {
  final SupportTicket ticket;
  const TicketDetailScreen({super.key, required this.ticket});

  @override
  State<TicketDetailScreen> createState() => _TicketDetailScreenState();
}

class _TicketDetailScreenState extends State<TicketDetailScreen> {
  final SupportService _supportService = SupportService();
  final _replyCtrl = TextEditingController();
  List<SupportMessage> _messages = [];
  late SupportTicket _ticket;
  bool _isLoading = true;
  bool _error = false;
  bool _isSending = false;

  bool get _isClosed => _ticket.status == 'closed' || _ticket.status == 'resolved';

  @override
  void initState() {
    super.initState();
    _ticket = widget.ticket;
    _load();
  }

  @override
  void dispose() {
    _replyCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() { _isLoading = true; _error = false; });
    try {
      final results = await Future.wait([
        _supportService.getTicket(_ticket.id),
        _supportService.listMessages(_ticket.id),
      ]);
      if (mounted) {
        setState(() {
          _ticket = results[0] as SupportTicket;
          _messages = results[1] as List<SupportMessage>;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) setState(() { _isLoading = false; _error = true; });
    }
  }

  Future<void> _send() async {
    final text = _replyCtrl.text.trim();
    if (text.isEmpty) return;
    setState(() => _isSending = true);
    try {
      await _supportService.addMessage(_ticket.id, text);
      _replyCtrl.clear();
      await _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(AppLocalizations.of(context)!.ticketDetailSendError)),
        );
      }
    } finally {
      if (mounted) setState(() => _isSending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: l10n.myTicketsTicketNumberLabel(_ticket.ticketNumber)),
      body: Column(
        children: [
          Container(
            width: double.infinity,
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 16),
            decoration: BoxDecoration(border: Border(bottom: BorderSide(color: ty.line2))),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(_ticket.subject, style: TyType.display(18, color: ty.ink)),
                const SizedBox(height: 6),
                Text(_ticket.description, style: TyType.sans(13.5, color: ty.ink2, height: 1.6)),
                if (_ticket.resolutionSummary != null) ...[
                  const SizedBox(height: 10),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: ty.saffronSoft.withValues(alpha: 0.3),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(l10n.ticketDetailResolutionLabel(_ticket.resolutionSummary!), style: TyType.sans(12.5, color: ty.ink2)),
                  ),
                ],
              ],
            ),
          ),
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _error
                    ? TyStateScreen.error(context, onAction: _load)
                    : _messages.isEmpty
                        ? Center(
                            child: Text(l10n.ticketDetailNoRepliesMessage, style: TyType.sans(13, color: ty.ink3)),
                          )
                        : ListView.builder(
                            padding: const EdgeInsets.all(20),
                            itemCount: _messages.length,
                            itemBuilder: (_, i) => _messageBubble(context, _messages[i]),
                          ),
          ),
          if (_isClosed)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(border: Border(top: BorderSide(color: ty.line2))),
              child: Text(
                l10n.ticketDetailClosedMessage(_ticket.status),
                textAlign: TextAlign.center,
                style: TyType.sans(12.5, color: ty.ink3),
              ),
            )
          else
            SafeArea(
              top: false,
              child: Container(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
                decoration: BoxDecoration(border: Border(top: BorderSide(color: ty.line2))),
                child: Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _replyCtrl,
                        style: TyType.sans(14, color: ty.ink),
                        decoration: InputDecoration(
                          hintText: l10n.ticketDetailReplyHint,
                          hintStyle: TyType.sans(14, color: ty.ink3),
                          filled: true,
                          fillColor: ty.surface2,
                          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(24),
                            borderSide: BorderSide.none,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    TyButton(
                      _isSending ? l10n.ticketDetailSendingButtonLabel : l10n.ticketDetailSendButtonLabel,
                      enabled: !_isSending,
                      onTap: _send,
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _messageBubble(BuildContext context, SupportMessage msg) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final isMine = msg.isMine;
    return Align(
      alignment: isMine ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 14),
        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.75),
        child: Column(
          crossAxisAlignment: isMine ? CrossAxisAlignment.end : CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: isMine ? ty.saffron : ty.surface2,
                borderRadius: BorderRadius.circular(14),
              ),
              child: Text(
                msg.body,
                style: TyType.sans(13.5, color: isMine ? Colors.white : ty.ink, height: 1.5),
              ),
            ),
            const SizedBox(height: 4),
            Text(
              l10n.ticketDetailMessageSenderTimeLabel(
                isMine ? l10n.ticketDetailYouLabel : l10n.ticketDetailSupportLabel,
                DateFormat('d MMM, h:mm a').format(msg.createdAt),
              ),
              style: TyType.sans(11, color: ty.ink3),
            ),
          ],
        ),
      ),
    );
  }
}
