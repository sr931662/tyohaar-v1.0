import 'package:flutter/material.dart';
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
  final UserService _userService = UserService();
  List<Address> _addresses = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadAddresses();
  }

  Future<void> _loadAddresses() async {
    try {
      final addresses = await _userService.getAddresses();
      setState(() {
        _addresses = addresses;
        _isLoading = false;
      });
    } catch (e) {
      debugPrint('Error loading addresses: $e');
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: 'Manage Address'),
      body: _isLoading 
        ? const Center(child: CircularProgressIndicator())
        : ListView(
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
            children: [
              if (_addresses.isEmpty)
                Center(child: Padding(
                  padding: const EdgeInsets.only(top: 40),
                  child: Text('No addresses saved yet', style: TyType.sans(14, color: ty.ink3)),
                ))
              else
                ..._addresses.map((addr) => _addressCard(context, addr)),
              const SizedBox(height: 24),
              TyButton('Add New Address', full: true, leadingIcon: Icons.add_location_alt_outlined, onTap: () {}),
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
            decoration: BoxDecoration(color: ty.saffron.withOpacity(0.1), borderRadius: BorderRadius.circular(12)),
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
                    Text('Edit', style: TyType.sans(13, color: ty.saffronDeep, weight: FontWeight.w700)),
                    const SizedBox(width: 24),
                    Text('Remove', style: TyType.sans(13, color: ty.rose, weight: FontWeight.w700)),
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
