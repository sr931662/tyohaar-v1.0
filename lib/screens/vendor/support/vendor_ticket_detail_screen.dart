import 'package:flutter/material.dart';

import '../../../theme/colors.dart';
import '../../../theme/typography.dart';
import '../../../data/services/support_service.dart';

class VendorTicketDetailScreen extends StatefulWidget {
  final String ticketId;
  const VendorTicketDetailScreen({super.key, required this.ticketId});

  @override
  State<VendorTicketDetailScreen> createState() => _VendorTicketDetailScreenState();
}

class _VendorTicketDetailScreenState extends State<VendorTicketDetailScreen> {
  final _supportService = SupportService();
  final _replyCtrl = TextEditingController();
  SupportTicket? _ticket;
  List<SupportMessage> _messages = [];
  bool _isLoading = true;
  bool _isSending = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _replyCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() => _isLoading = true);
    try {
      final results = await Future.wait([
        _supportService.getTicket(widget.ticketId),
        _supportService.listMessages(widget.ticketId),
      ]);
      if (mounted) {
        setState(() {
          _ticket = results[0] as SupportTicket;
          _messages = results[1] as List<SupportMessage>;
          _isLoading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _send() async {
    final body = _replyCtrl.text.trim();
    if (body.isEmpty) return;
    setState(() => _isSending = true);
    try {
      await _supportService.addMessage(widget.ticketId, body);
      _replyCtrl.clear();
      await _load();
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Could not send message.')));
    } finally {
      if (mounted) setState(() => _isSending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;

    if (_isLoading) {
      return Scaffold(backgroundColor: ty.paper, appBar: AppBar(), body: const Center(child: CircularProgressIndicator()));
    }
    if (_ticket == null) {
      return Scaffold(backgroundColor: ty.paper, appBar: AppBar(), body: const Center(child: Text('Ticket not found')));
    }

    final closed = _ticket!.status == 'resolved' || _ticket!.status == 'closed';

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: AppBar(title: Text(_ticket!.subject)),
      body: Column(
        children: [
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(18),
              children: [
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(12), border: Border.all(color: ty.line)),
                  child: Text(_ticket!.description, style: TyType.sans(13.5, color: ty.ink)),
                ),
                const SizedBox(height: 16),
                ..._messages.map((m) => Align(
                      alignment: m.isMine ? Alignment.centerRight : Alignment.centerLeft,
                      child: Container(
                        margin: const EdgeInsets.only(bottom: 10),
                        padding: const EdgeInsets.all(12),
                        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.75),
                        decoration: BoxDecoration(
                          color: m.isMine ? ty.saffron.withOpacity(0.14) : ty.surface,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: ty.line),
                        ),
                        child: Text(m.body, style: TyType.sans(13, color: ty.ink)),
                      ),
                    )),
              ],
            ),
          ),
          if (!closed)
            SafeArea(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(14, 8, 14, 8),
                child: Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _replyCtrl,
                        decoration: InputDecoration(
                          hintText: 'Type a reply…',
                          filled: true,
                          fillColor: ty.surface,
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(24), borderSide: BorderSide(color: ty.line)),
                          isDense: true,
                          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    IconButton(
                      onPressed: _isSending ? null : _send,
                      icon: Icon(Icons.send_rounded, color: ty.saffron),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}
