import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:razorpay_flutter/razorpay_flutter.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/auth_manager.dart';
import '../data/models.dart';
import '../data/services/payment_service.dart';
import '../data/services/wallet_service.dart';
import '../widgets/common.dart';
import '../widgets/ty_button.dart';
import '../widgets/tutorial/tutorial_overlay.dart';

class WalletScreen extends StatefulWidget {
  const WalletScreen({super.key});

  @override
  State<WalletScreen> createState() => _WalletScreenState();
}

class _WalletScreenState extends State<WalletScreen> {
  final WalletService _walletService = WalletService();
  final PaymentService _paymentService = PaymentService();
  late Razorpay _razorpay;
  Wallet? _wallet;
  List<WalletTransaction> _transactions = [];
  bool _isLoading = true;
  bool _isTopupInFlight = false;
  String? _error;
  final GlobalKey _addMoneyKey = GlobalKey();

  @override
  void initState() {
    super.initState();
    _razorpay = Razorpay();
    _razorpay.on(Razorpay.EVENT_PAYMENT_SUCCESS, _handleTopupSuccess);
    _razorpay.on(Razorpay.EVENT_PAYMENT_ERROR, _handleTopupError);
    _loadWalletData();
  }

  @override
  void dispose() {
    _razorpay.clear();
    super.dispose();
  }

  Future<void> _startTopup() async {
    final amountText = await showDialog<String>(
      context: context,
      builder: (ctx) {
        final controller = TextEditingController();
        return AlertDialog(
          title: const Text('Add Money'),
          content: TextField(
            controller: controller,
            keyboardType: const TextInputType.numberWithOptions(decimal: false),
            autofocus: true,
            decoration: const InputDecoration(prefixText: '₹ ', hintText: 'Amount'),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
            TextButton(onPressed: () => Navigator.pop(ctx, controller.text), child: const Text('Continue')),
          ],
        );
      },
    );
    final amount = double.tryParse(amountText ?? '');
    if (amount == null || amount <= 0 || !mounted) return;

    setState(() => _isTopupInFlight = true);
    try {
      final order = await _paymentService.initiateWalletTopup(amount: amount);
      final user = AuthManager.instance.currentUser;
      _razorpay.open({
        'key': kRazorpayKeyId,
        'amount': order.amountPaise,
        'currency': order.currency,
        'order_id': order.orderId,
        'name': 'Tyohaar Wallet',
        'description': 'Add money to wallet',
        'prefill': {
          'contact': user?.phone ?? '',
          'email': user?.email ?? '',
          'name': user?.displayName ?? '',
        },
        'theme': {'color': '#F97316'},
      });
    } catch (e) {
      if (mounted) {
        setState(() => _isTopupInFlight = false);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not start top-up. Please try again.')),
        );
      }
    }
  }

  void _handleTopupSuccess(PaymentSuccessResponse response) {
    if (!mounted) return;
    setState(() => _isTopupInFlight = false);
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Payment received — your balance will update shortly.')),
    );
    // Wallet is credited asynchronously by the gateway webhook; refresh after a short delay.
    Future.delayed(const Duration(seconds: 3), () {
      if (mounted) _loadWalletData();
    });
  }

  void _handleTopupError(PaymentFailureResponse response) {
    if (!mounted) return;
    setState(() => _isTopupInFlight = false);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(response.message ?? 'Payment failed. Please try again.')),
    );
  }

  Future<void> _loadWalletData() async {
    setState(() { _isLoading = true; _error = null; });
    try {
      final results = await Future.wait([
        _walletService.getWallet(),
        _walletService.listTransactions(),
      ]);
      if (mounted) {
        setState(() {
          _wallet = results[0] as Wallet;
          _transactions = results[1] as List<WalletTransaction>;
          _isLoading = false;
        });
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (!mounted) return;
          TutorialOverlay.show(context, screenKey: 'wallet', steps: [
            TutorialStep(
              targetKey: _addMoneyKey,
              title: 'Top up your wallet',
              description: 'Add money here and use it for instant checkout on any booking.',
            ),
          ]);
        });
      }
    } catch (e) {
      if (mounted) setState(() { _error = 'Could not load wallet data.'; _isLoading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    
    return Scaffold(
      appBar: tyAppBar(context, title: 'Tyohaar Wallet'),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.error_outline_rounded, size: 48, color: context.ty.rose),
                      const SizedBox(height: 12),
                      Text(_error!, style: TyType.sans(14, color: context.ty.ink2)),
                      const SizedBox(height: 16),
                      TextButton(
                        onPressed: _loadWalletData,
                        child: Text('Try Again', style: TyType.sans(14, color: context.ty.saffron, weight: FontWeight.w700)),
                      ),
                    ],
                  ),
                )
              : ListView(
            padding: const EdgeInsets.all(20),
            children: [
              Container(
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [ty.saffron, ty.saffronDeep],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(24),
                  boxShadow: [
                    BoxShadow(
                      color: ty.saffron.withOpacity(0.3),
                      blurRadius: 20,
                      offset: const Offset(0, 10),
                    ),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Available Balance',
                        style: TyType.sans(14, color: Colors.white.withOpacity(0.8))),
                    const SizedBox(height: 8),
                    Text('₹${_wallet?.availableBalance ?? 0}',
                        style: TyType.display(36, color: Colors.white)),
                    const SizedBox(height: 24),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text('Tyohaar Credits: ${_wallet?.rewardPoints ?? 0}',
                            style: TyType.sans(13, color: Colors.white, weight: FontWeight.w600)),
                        const Icon(Icons.info_outline, color: Colors.white70, size: 18),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 32),
              SectionHeader('Quick Actions'),
              Row(
                children: [
                  _actionButton(context, Icons.add_circle_outline, 'Add Money',
                      onTap: _isTopupInFlight ? null : _startTopup, anchorKey: _addMoneyKey),
                  const SizedBox(width: 12),
                  _actionButton(context, Icons.history, 'History'),
                  const SizedBox(width: 12),
                  _actionButton(context, Icons.local_offer_outlined, 'Offers'),
                ],
              ),
              const SizedBox(height: 32),
              SectionHeader('Recent Transactions'),
              if (_transactions.isEmpty)
                Center(
                  child: Padding(
                    padding: const EdgeInsets.only(top: 24),
                    child: Text('No transactions yet', style: TyType.sans(14, color: ty.ink3)),
                  ),
                )
              else
                ..._transactions.take(5).map((tx) => _transactionItem(context, tx)),
              const SizedBox(height: 20),
              if (_transactions.length > 5)
                TyButton('View All Transactions', kind: TyButtonKind.ghost, full: true, onTap: () {}),
            ],
          ),
    );
  }

  Widget _actionButton(BuildContext context, IconData icon, String label, {VoidCallback? onTap, Key? anchorKey}) {
    final ty = context.ty;
    return Expanded(
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          key: anchorKey,
          padding: const EdgeInsets.symmetric(vertical: 16),
          decoration: BoxDecoration(
            color: ty.surface,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: ty.line),
          ),
          child: Column(
            children: [
              Icon(icon, color: ty.saffron, size: 24),
              const SizedBox(height: 8),
              Text(label, style: TyType.sans(12, color: ty.ink, weight: FontWeight.w600)),
            ],
          ),
        ),
      ),
    );
  }

  Widget _transactionItem(BuildContext context, WalletTransaction tx) {
    final ty = context.ty;
    final isCredit = tx.type == 'credit' || tx.type == 'refund' || tx.type == 'reward';
    final amountColor = isCredit ? ty.leaf : ty.rose;
    final amountPrefix = isCredit ? '+' : '-';
    final dateStr = DateFormat('dd MMM yyyy').format(tx.createdAt);

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: ty.surface,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: ty.line),
      ),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: ty.saffronSoft,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(Icons.payment, color: ty.saffronDeep, size: 20),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(tx.description ?? '', style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
                Text(dateStr, style: TyType.sans(12, color: ty.ink3)),
              ],
            ),
          ),
          Text('$amountPrefix₹${tx.amount}', style: TyType.sans(15, color: amountColor, weight: FontWeight.w800)),
        ],
      ),
    );
  }
}
