import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shimmer/shimmer.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/models.dart';
import '../data/services/user_service.dart';
import '../widgets/ty_button.dart';
import '../widgets/common.dart';
import '../l10n/generated/app_localizations.dart';
import 'address/address_flow.dart';

class ManageAddressScreen extends StatefulWidget {
  const ManageAddressScreen({super.key});

  @override
  State<ManageAddressScreen> createState() => _ManageAddressScreenState();
}

class _ManageAddressScreenState extends State<ManageAddressScreen> {
  List<Address> _addresses = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final addresses = await context.read<UserService>().getAddresses();
      if (mounted) setState(() { _addresses = addresses; _loading = false; });
    } catch (_) {
      // Looked up here (after the await), not at the top of this method —
      // when _load() is invoked from initState(), fetching this before any
      // await runs synchronously inside initState's call stack, which
      // throws ("dependOnInheritedWidgetOfExactType... called before
      // initState() completed") because Localizations isn't attached yet.
      if (mounted) setState(() { _error = AppLocalizations.of(context)!.manageAddressLoadError; _loading = false; });
    }
  }

  Future<void> _delete(String addressId) async {
    final l10n = AppLocalizations.of(context)!;
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(l10n.manageAddressDeleteDialogTitle),
        content: Text(l10n.manageAddressDeleteConfirmMessage),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(l10n.commonCancel)),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: Text(l10n.manageAddressDeleteButtonLabel, style: const TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
    if (confirm != true || !mounted) return;
    try {
      await context.read<UserService>().deleteAddress(addressId);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(l10n.manageAddressRemovedMessage)),
        );
        _load();
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(l10n.manageAddressDeleteError)),
        );
      }
    }
  }

  Future<void> _openAddForm() async {
    final userService = context.read<UserService>();
    final saved = await showAddAddressFlow(context, save: (data) => userService.addAddress(data));
    if (saved != null) _load();
  }

  Future<void> _openEditForm(Address addr) async {
    final userService = context.read<UserService>();
    final saved = await showEditAddressFlow(context, addr, save: (data) => userService.updateAddress(addr.id, data));
    if (saved != null) _load();
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: l10n.manageAddressTitle),
      body: _loading
          ? _buildSkeleton(ty)
          : _error != null
              ? _buildError(ty, context)
              : ListView(
                  padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
                  children: [
                    if (_addresses.isEmpty) _buildEmpty(ty, context),
                    ..._addresses.map((addr) => _addressCard(context, addr)),
                    const SizedBox(height: 24),
                    TyButton(
                      l10n.manageAddressAddButtonLabel,
                      full: true,
                      leadingIcon: Icons.add_location_alt_outlined,
                      onTap: _openAddForm,
                    ),
                  ],
                ),
    );
  }

  Widget _buildSkeleton(TyColors ty) {
    return Shimmer.fromColors(
      baseColor: ty.line,
      highlightColor: ty.surface2,
      child: ListView(
        padding: const EdgeInsets.all(20),
        children: List.generate(2, (_) => Container(
          margin: const EdgeInsets.only(bottom: 16),
          height: 90,
          decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(20)),
        )),
      ),
    );
  }

  Widget _buildError(TyColors ty, BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.error_outline_rounded, size: 48, color: ty.rose),
            const SizedBox(height: 12),
            Text(_error!, style: TyType.sans(14, color: ty.ink2)),
            const SizedBox(height: 16),
            TextButton(onPressed: _load, child: Text(l10n.commonTryAgain, style: TyType.sans(14, color: ty.saffron, weight: FontWeight.w700))),
          ],
        ),
      ),
    );
  }

  Widget _buildEmpty(TyColors ty, BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Padding(
      padding: const EdgeInsets.only(bottom: 24, top: 20),
      child: Column(
        children: [
          Icon(Icons.place_outlined, size: 48, color: ty.ink3),
          const SizedBox(height: 12),
          Text(l10n.manageAddressEmptyMessage, style: TyType.sans(14, color: ty.ink2)),
        ],
      ),
    );
  }

  Widget _addressCard(BuildContext context, Address addr) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final isHome = addr.addressType == 'home';

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: ty.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: addr.isDefault ? ty.saffron : ty.line, width: addr.isDefault ? 1.5 : 1),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: ty.saffron.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(isHome ? Icons.home_rounded : Icons.work_rounded, color: ty.saffron, size: 20),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Flexible(
                      child: Text(addr.label,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TyType.sans(16, color: ty.ink, weight: FontWeight.w700)),
                    ),
                    if (addr.isDefault) ...[
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                        decoration: BoxDecoration(color: ty.saffronSoft, borderRadius: BorderRadius.circular(6)),
                        child: Text(l10n.manageAddressDefaultBadgeLabel, style: TyType.eyebrow(9, color: ty.saffron)),
                      ),
                    ],
                  ],
                ),
                const SizedBox(height: 4),
                if (addr.recipientName != null)
                  Text(
                      addr.recipientPhone != null
                          ? l10n.manageAddressRecipientNamePhoneLine(addr.recipientName!, addr.recipientPhone!)
                          : addr.recipientName!,
                      style: TyType.sans(12.5, color: ty.ink, weight: FontWeight.w600)),
                Text(addr.addressLine1, style: TyType.sans(13, color: ty.ink2, height: 1.4)),
                if (addr.addressLine2 != null && addr.addressLine2!.isNotEmpty)
                  Text(addr.addressLine2!, style: TyType.sans(13, color: ty.ink2, height: 1.4)),
                if (addr.landmark != null && addr.landmark!.isNotEmpty)
                  Text(l10n.manageAddressNearLandmarkLabel(addr.landmark!), style: TyType.sans(12, color: ty.ink3, height: 1.4)),
                Text(l10n.manageAddressCityStateLine(addr.city, addr.state, addr.postalCode), style: TyType.sans(13, color: ty.ink2, height: 1.4)),
                const SizedBox(height: 12),
                Row(
                  children: [
                    GestureDetector(
                      onTap: () => _openEditForm(addr),
                      child: Text(l10n.manageAddressEditButtonLabel, style: TyType.sans(13, color: ty.saffron, weight: FontWeight.w700)),
                    ),
                    const SizedBox(width: 20),
                    GestureDetector(
                      onTap: () => _delete(addr.id),
                      child: Text(l10n.manageAddressRemoveButtonLabel, style: TyType.sans(13, color: ty.rose, weight: FontWeight.w700)),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
