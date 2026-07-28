import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

import '../../../theme/colors.dart';
import '../../../theme/typography.dart';

/// Shared bulk import/export overflow-menu action, used identically by
/// [VendorCommonItemsScreen] and [VendorPackageItemsScreen] — the only
/// difference between the two is which vendor_service.dart methods get
/// passed in and the localized copy.
class ItemImportExportMenu extends StatelessWidget {
  final Future<List<int>> Function(String format) getTemplate;
  final Future<List<int>> Function(String format) exportItems;
  final Future<Map<String, dynamic>> Function(PlatformFile file) importItems;
  final VoidCallback onImported;

  final String importLabel;
  final String exportLabel;
  final String templateLabel;
  final String chooseFormatTitle;
  final String importResultTitle;
  final String Function(int created, int updated, int errors) resultSummary;
  final String closeLabel;
  final String importFailedMessage;
  final String exportFailedMessage;

  const ItemImportExportMenu({
    super.key,
    required this.getTemplate,
    required this.exportItems,
    required this.importItems,
    required this.onImported,
    required this.importLabel,
    required this.exportLabel,
    required this.templateLabel,
    required this.chooseFormatTitle,
    required this.importResultTitle,
    required this.resultSummary,
    required this.closeLabel,
    required this.importFailedMessage,
    required this.exportFailedMessage,
  });

  Future<String?> _pickFormat(BuildContext context) {
    return showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(chooseFormatTitle),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, 'xlsx'), child: const Text('XLSX')),
          TextButton(onPressed: () => Navigator.pop(context, 'csv'), child: const Text('CSV')),
        ],
      ),
    );
  }

  Future<void> _handleTemplate(BuildContext context) async {
    final format = await _pickFormat(context);
    if (format == null || !context.mounted) return;
    final bytes = await getTemplate(format);
    if (!context.mounted) return;
    await _shareBytes(context, bytes, 'items_template.$format');
  }

  Future<void> _handleExport(BuildContext context) async {
    final format = await _pickFormat(context);
    if (format == null || !context.mounted) return;
    try {
      final bytes = await exportItems(format);
      if (!context.mounted) return;
      await _shareBytes(context, bytes, 'items_export.$format');
    } catch (_) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(exportFailedMessage)));
      }
    }
  }

  Future<void> _shareBytes(BuildContext context, List<int> bytes, String filename) async {
    final dir = await getTemporaryDirectory();
    final file = await File('${dir.path}/$filename').writeAsBytes(bytes);
    await Share.shareXFiles([XFile(file.path)]);
  }

  Future<void> _handleImport(BuildContext context) async {
    final picked = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['csv', 'xlsx'],
      withData: true,
    );
    final file = (picked != null && picked.files.isNotEmpty) ? picked.files.first : null;
    if (file == null || !context.mounted) return;
    try {
      final result = await importItems(file);
      if (!context.mounted) return;
      final created = (result['created'] as num?)?.toInt() ?? 0;
      final updated = (result['updated'] as num?)?.toInt() ?? 0;
      final errors = (result['errors'] as num?)?.toInt() ?? 0;
      final rowResults = (result['row_results'] as List?) ?? const [];
      final errorRows = rowResults
          .whereType<Map>()
          .where((r) => r['action'] == 'error')
          .take(3)
          .map((r) => 'Row ${r['row']}${r['name'] != null ? ' (${r['name']})' : ''}: ${r['error']}')
          .join('\n');
      onImported();
      if (!context.mounted) return;
      await showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: Text(importResultTitle),
          content: Text([resultSummary(created, updated, errors), if (errorRows.isNotEmpty) errorRows].join('\n\n')),
          actions: [TextButton(onPressed: () => Navigator.pop(context), child: Text(closeLabel))],
        ),
      );
    } catch (_) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(importFailedMessage)));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return PopupMenuButton<String>(
      icon: Icon(Icons.more_vert, color: context.ty.ink),
      onSelected: (value) {
        switch (value) {
          case 'import':
            _handleImport(context);
            break;
          case 'export':
            _handleExport(context);
            break;
          case 'template':
            _handleTemplate(context);
            break;
        }
      },
      itemBuilder: (context) => [
        PopupMenuItem(value: 'import', child: Text(importLabel, style: TyType.sans(14))),
        PopupMenuItem(value: 'export', child: Text(exportLabel, style: TyType.sans(14))),
        PopupMenuItem(value: 'template', child: Text(templateLabel, style: TyType.sans(14))),
      ],
    );
  }
}
