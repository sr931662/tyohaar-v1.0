import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:share_plus/share_plus.dart';

import '../data/models.dart';
import '../data/package_units.dart';
import '../data/services/booking_service.dart';
import '../data/services/color_service.dart';
import '../l10n/generated/app_localizations.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../utils/currency.dart';
import '../widgets/common.dart';
import '../widgets/line_kind_badge.dart';
import '../widgets/state_screens.dart';
import '../widgets/ty_button.dart';

/// Everything about one booking in one place — what was booked (every line
/// labelled rental / keep / service), the balloon colours and finish, the
/// price breakdown — and the invoice as a PDF the customer can download.
class BookingDetailScreen extends StatefulWidget {
  final String bookingId;
  const BookingDetailScreen({super.key, required this.bookingId});

  @override
  State<BookingDetailScreen> createState() => _BookingDetailScreenState();
}

class _BookingDetailScreenState extends State<BookingDetailScreen> {
  final _service = BookingService();
  Map<String, dynamic>? _booking;
  List<BookingLine> _lines = const [];
  Map<String, String> _colourNames = const {};
  bool _loading = true;
  bool _error = false;
  bool _downloading = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = false;
    });
    try {
      final results = await Future.wait([
        _service.getBookingDetailJson(widget.bookingId),
        _service.getBookingLines(widget.bookingId),
      ]);
      final booking = results[0] as Map<String, dynamic>;
      // Names for the colours the customer chose; the hex still shows if the
      // palette can't be fetched or the colour has since been retired.
      var names = <String, String>{
        for (final c in fallbackBalloonPalette) c.hex.toLowerCase(): c.name
      };
      try {
        for (final c in await ColorService().balloonColors()) {
          names[c.hex.toLowerCase()] = c.name;
        }
      } catch (_) {}
      if (!mounted) return;
      setState(() {
        _booking = booking;
        _lines = results[1] as List<BookingLine>;
        _colourNames = names;
        _loading = false;
      });
    } catch (_) {
      if (mounted) {
        setState(() {
          _loading = false;
          _error = true;
        });
      }
    }
  }

  Future<void> _downloadInvoice() async {
    if (_downloading) return;
    final l10n = AppLocalizations.of(context)!;
    setState(() => _downloading = true);
    try {
      final invoice = await _service.downloadInvoicePdf(widget.bookingId);
      await Share.shareXFiles(
        [
          XFile.fromData(Uint8List.fromList(invoice.bytes),
              mimeType: 'application/pdf', name: invoice.filename)
        ],
        subject: invoice.filename,
        fileNameOverrides: [invoice.filename],
      );
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(l10n.bookingDetailDownloadError)));
      }
    } finally {
      if (mounted) setState(() => _downloading = false);
    }
  }

  double _n(String key) => asDouble(_booking?[key]);

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: l10n.bookingDetailTitle),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error || _booking == null
              ? TyStateScreen.error(context, onAction: _load)
              : _content(context),
    );
  }

  Widget _content(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final b = _booking!;
    final date = asDateTime(b['scheduled_date']);
    final colours = ((b['balloon_colors'] ?? []) as List).cast<String>();
    final finish = b['balloon_finish'] as String?;
    final discount = _n('discount_amount');
    final usedKinds = [
      for (final k in LineKind.values)
        if (_lines.any((l) => LineKind.parse(l.kind) == k)) k
    ];

    return RefreshIndicator(
      onRefresh: _load,
      color: ty.saffron,
      child: ListView(
        padding: EdgeInsets.fromLTRB(18, 8, 18, 28 + MediaQuery.paddingOf(context).bottom),
        children: [
          Text(b['package_name'] as String? ?? l10n.myBookingsCustomBookingFallback,
              style: TyType.display(24, color: ty.ink)),
          const SizedBox(height: 4),
          Text('${l10n.bookingDetailBookingNo} ${b['booking_number']}',
              style: TyType.sans(13, color: ty.ink3)),
          const SizedBox(height: 14),
          _card(ty, [
            _row(ty, Icons.event_rounded, DateFormat('EEEE, d MMMM yyyy').format(date)),
            if (b['celebration_title'] != null)
              _row(ty, Icons.celebration_outlined, b['celebration_title'] as String),
            _row(ty, Icons.flag_outlined,
                '${_title(b['booking_status'])} · ${l10n.bookingDetailPayment(_title(b['payment_status']))}'),
          ]),
          if (colours.isNotEmpty || finish != null) ...[
            const SizedBox(height: 18),
            Text(l10n.bookingDetailBalloonHeading, style: TyType.eyebrow(11, color: ty.ink3)),
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.all(14),
              decoration: _box(ty),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Wrap(spacing: 14, runSpacing: 10, children: [
                  for (var i = 0; i < colours.length; i++)
                    Row(mainAxisSize: MainAxisSize.min, children: [
                      Container(
                        width: 22,
                        height: 22,
                        decoration: BoxDecoration(
                            color: _hex(colours[i]),
                            shape: BoxShape.circle,
                            border: Border.all(color: ty.line)),
                      ),
                      const SizedBox(width: 6),
                      Text(
                          '${i + 1}. ${_colourNames[colours[i].toLowerCase()] ?? colours[i].toUpperCase()}',
                          style: TyType.sans(13.5, color: ty.ink, weight: FontWeight.w600)),
                    ]),
                ]),
                if (finish != null) ...[
                  const SizedBox(height: 10),
                  Text(l10n.bookingDetailFinish(finish),
                      style: TyType.sans(13.5, color: ty.ink2, weight: FontWeight.w600)),
                ],
              ]),
            ),
          ],
          const SizedBox(height: 18),
          Text(l10n.bookingDetailItemsHeading, style: TyType.eyebrow(11, color: ty.ink3)),
          const SizedBox(height: 8),
          if (_lines.isEmpty)
            Text(l10n.bookingDetailPackageOnly, style: TyType.sans(13, color: ty.ink3))
          else
            for (final line in _lines) _lineTile(ty, l10n, line),
          if (usedKinds.isNotEmpty) ...[
            const SizedBox(height: 6),
            Container(
              padding: const EdgeInsets.fromLTRB(14, 12, 14, 6),
              decoration: _box(ty),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(l10n.lineKindLegendHeading, style: TyType.eyebrow(10.5, color: ty.ink3)),
                const SizedBox(height: 8),
                DefaultTextStyle(
                    style: TextStyle(color: ty.ink), child: LineKindLegend(kinds: usedKinds)),
              ]),
            ),
          ],
          const SizedBox(height: 18),
          Text(l10n.bookingDetailPriceHeading, style: TyType.eyebrow(11, color: ty.ink3)),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(14),
            decoration: _box(ty),
            child: Column(children: [
              _money(ty, l10n.bookingDetailSubtotal, _n('subtotal')),
              if (discount > 0) _money(ty, l10n.bookingDetailDiscount, -discount),
              _money(ty, l10n.bookingDetailGst, _n('tax_amount')),
              const Divider(height: 20),
              _money(ty, l10n.bookingDetailTotal, _n('total_amount'), bold: true),
              if (_n('amount_paid') > 0) _money(ty, l10n.bookingDetailPaid, _n('amount_paid')),
              _money(ty, l10n.bookingDetailDue, _n('amount_due'), bold: true),
            ]),
          ),
          const SizedBox(height: 22),
          TyButton(
            _downloading ? l10n.bookingDetailDownloading : l10n.bookingDetailDownload,
            full: true,
            enabled: !_downloading,
            leadingIcon: Icons.picture_as_pdf_rounded,
            onTap: _downloadInvoice,
          ),
          const SizedBox(height: 8),
          Text(l10n.bookingDetailDownloadHint,
              textAlign: TextAlign.center, style: TyType.sans(12, color: ty.ink3)),
        ],
      ),
    );
  }

  Widget _lineTile(TyColors ty, AppLocalizations l10n, BookingLine line) {
    final kind = LineKind.parse(line.kind);
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: _box(ty),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        LineKindBadge(kind),
        const SizedBox(width: 10),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(line.name, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w700)),
            if (line.isAddon)
              Text(l10n.bookingDetailAddOn, style: TyType.sans(11.5, color: ty.ink3)),
            if (line.note != null && line.note!.isNotEmpty)
              Text(l10n.bookingDetailCustom(line.note!),
                  style: TyType.sans(12.5, color: ty.saffronDeep, weight: FontWeight.w700)),
            Text(
              '${line.quantity}${line.unit != null ? ' ${packageUnitLabel(line.unit).toLowerCase()}' : ''} × ${formatRupees(line.unitPrice)}',
              style: TyType.sans(12, color: ty.ink3),
            ),
          ]),
        ),
        const SizedBox(width: 8),
        Text(formatRupees(line.finalPrice),
            style: TyType.sans(14, color: ty.ink, weight: FontWeight.w800)),
      ]),
    );
  }

  Widget _money(TyColors ty, String label, double amount, {bool bold = false}) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          Flexible(
            child: Text(label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TyType.sans(13.5,
                    color: bold ? ty.ink : ty.ink2,
                    weight: bold ? FontWeight.w700 : FontWeight.w500)),
          ),
          const SizedBox(width: 8),
          Text(
            amount < 0 ? '-${formatRupees(-amount)}' : formatRupees(amount),
            style: TyType.sans(14, color: ty.ink, weight: bold ? FontWeight.w800 : FontWeight.w600),
          ),
        ]),
      );

  Widget _card(TyColors ty, List<Widget> rows) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
        decoration: _box(ty),
        child: Column(children: rows),
      );

  Widget _row(TyColors ty, IconData icon, String text) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Row(children: [
          Icon(icon, size: 19, color: ty.ink3),
          const SizedBox(width: 12),
          Expanded(
              child: Text(text, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w600))),
        ]),
      );

  BoxDecoration _box(TyColors ty) => BoxDecoration(
      color: ty.surface,
      borderRadius: BorderRadius.circular(16),
      border: Border.all(color: ty.line));

  static String _title(Object? raw) {
    final s = (raw as String? ?? '').replaceAll('_', ' ');
    return s.isEmpty ? s : s[0].toUpperCase() + s.substring(1);
  }

  static Color _hex(String hex) {
    final h = hex.replaceAll('#', '');
    return Color(int.tryParse('FF$h', radix: 16) ?? 0xFF888888);
  }
}
