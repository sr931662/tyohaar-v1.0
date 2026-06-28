import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shimmer/shimmer.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/models.dart';
import '../data/services/user_service.dart';
import '../widgets/ty_button.dart';
import '../widgets/common.dart';

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
      if (mounted) setState(() { _error = 'Could not load addresses.'; _loading = false; });
    }
  }

  Future<void> _delete(String addressId) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete address?'),
        content: const Text('This address will be permanently removed.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Delete', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
    if (confirm != true || !mounted) return;
    try {
      await context.read<UserService>().deleteAddress(addressId);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Address removed.')),
        );
        _load();
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not delete. Please try again.')),
        );
      }
    }
  }

  Future<void> _openAddForm() async {
    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => _AddressFormSheet(
        onSave: (data) async {
          await context.read<UserService>().addAddress(data);
        },
      ),
    );
    _load();
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: 'Manage Addresses'),
      body: _loading
          ? _buildSkeleton(ty)
          : _error != null
              ? _buildError(ty)
              : ListView(
                  padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
                  children: [
                    if (_addresses.isEmpty) _buildEmpty(ty),
                    ..._addresses.map((addr) => _addressCard(context, addr)),
                    const SizedBox(height: 24),
                    TyButton(
                      'Add New Address',
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

  Widget _buildError(TyColors ty) {
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
            TextButton(onPressed: _load, child: Text('Try Again', style: TyType.sans(14, color: ty.saffron, weight: FontWeight.w700))),
          ],
        ),
      ),
    );
  }

  Widget _buildEmpty(TyColors ty) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 24, top: 20),
      child: Column(
        children: [
          Icon(Icons.place_outlined, size: 48, color: ty.ink3),
          const SizedBox(height: 12),
          Text('No addresses saved', style: TyType.sans(14, color: ty.ink2)),
        ],
      ),
    );
  }

  Widget _addressCard(BuildContext context, Address addr) {
    final ty = context.ty;
    final isHome = addr.label.toLowerCase() == 'home';

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: ty.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: ty.line),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: ty.saffron.withOpacity(0.1),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(isHome ? Icons.home_rounded : Icons.work_rounded, color: ty.saffron, size: 20),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(addr.label, style: TyType.sans(16, color: ty.ink, weight: FontWeight.w700)),
                const SizedBox(height: 4),
                Text(addr.fullAddress, style: TyType.sans(13, color: ty.ink2, height: 1.4)),
                const SizedBox(height: 12),
                Row(
                  children: [
                    GestureDetector(
                      onTap: () => _delete(addr.id),
                      child: Text('Remove', style: TyType.sans(13, color: ty.rose, weight: FontWeight.w700)),
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

class _AddressFormSheet extends StatefulWidget {
  final Future<void> Function(Map<String, dynamic> data) onSave;
  const _AddressFormSheet({required this.onSave});

  @override
  State<_AddressFormSheet> createState() => _AddressFormSheetState();
}

class _AddressFormSheetState extends State<_AddressFormSheet> {
  final _line1Ctrl = TextEditingController();
  final _cityCtrl = TextEditingController();
  final _stateCtrl = TextEditingController();
  final _pinCtrl = TextEditingController();
  String _label = 'Home';
  bool _saving = false;
  String? _error;

  @override
  void dispose() {
    _line1Ctrl.dispose();
    _cityCtrl.dispose();
    _stateCtrl.dispose();
    _pinCtrl.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final line1 = _line1Ctrl.text.trim();
    final city = _cityCtrl.text.trim();
    final state = _stateCtrl.text.trim();
    final pin = _pinCtrl.text.trim();
    if (line1.isEmpty || city.isEmpty || state.isEmpty || pin.isEmpty) {
      setState(() => _error = 'Please fill in all fields.');
      return;
    }
    setState(() { _saving = true; _error = null; });
    try {
      await widget.onSave({
        'label': _label,
        'address_line_1': line1,
        'city': city,
        'state': state,
        'postal_code': pin,
        'country': 'India',
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Address saved!')),
        );
        Navigator.pop(context);
      }
    } catch (_) {
      if (mounted) setState(() { _saving = false; _error = 'Could not save. Please try again.'; });
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return Container(
      padding: EdgeInsets.fromLTRB(24, 24, 24, MediaQuery.of(context).viewInsets.bottom + 32),
      decoration: BoxDecoration(
        color: ty.paper,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(32)),
      ),
      child: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Center(
              child: Container(
                width: 40, height: 4,
                decoration: BoxDecoration(color: ty.line, borderRadius: BorderRadius.circular(2)),
              ),
            ),
            const SizedBox(height: 20),
            Text('Add Address', style: TyType.display(22, color: ty.ink)),
            const SizedBox(height: 20),
            // Label picker
            Row(
              children: ['Home', 'Work', 'Other'].map((l) => Padding(
                padding: const EdgeInsets.only(right: 8),
                child: GestureDetector(
                  onTap: () => setState(() => _label = l),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    decoration: BoxDecoration(
                      color: _label == l ? ty.saffron : ty.surface,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: _label == l ? ty.saffron : ty.line),
                    ),
                    child: Text(l, style: TyType.sans(13, color: _label == l ? Colors.white : ty.ink, weight: FontWeight.w600)),
                  ),
                ),
              )).toList(),
            ),
            const SizedBox(height: 16),
            _field(ty, 'ADDRESS LINE 1', 'e.g. 42 Gandhi Road', _line1Ctrl),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(child: _field(ty, 'CITY', 'Jaipur', _cityCtrl)),
                const SizedBox(width: 12),
                Expanded(child: _field(ty, 'STATE', 'Rajasthan', _stateCtrl)),
              ],
            ),
            const SizedBox(height: 12),
            _field(ty, 'PIN CODE', '302001', _pinCtrl, type: TextInputType.number),
            if (_error != null) ...[
              const SizedBox(height: 12),
              Text(_error!, style: TyType.sans(13, color: ty.rose)),
            ],
            const SizedBox(height: 24),
            TyButton(_saving ? 'Saving...' : 'Save Address', full: true, enabled: !_saving, onTap: _save),
          ],
        ),
      ),
    );
  }

  Widget _field(TyColors ty, String label, String hint, TextEditingController ctrl,
      {TextInputType type = TextInputType.text}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: TyType.eyebrow(10, color: ty.ink3)),
        const SizedBox(height: 6),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
          decoration: BoxDecoration(
            color: ty.surface,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: ty.line),
          ),
          child: TextField(
            controller: ctrl,
            keyboardType: type,
            style: TyType.sans(14, color: ty.ink),
            decoration: InputDecoration(
              hintText: hint,
              hintStyle: TyType.sans(14, color: ty.ink3),
              border: InputBorder.none,
            ),
          ),
        ),
      ],
    );
  }
}
