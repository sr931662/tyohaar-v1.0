import '../api_client.dart';
import '../models.dart';

class WalletService {
  final ApiClient _api = ApiClient();

  Future<Wallet> getWallet() async {
    final response = await _api.dio.get('wallets/me');
    return Wallet.fromJson(response.data['data']);
  }

  Future<List<WalletTransaction>> listTransactions() async {
    final response = await _api.dio.get('wallets/me/transactions');
    final List list = response.data['data']['items'];
    return list.map((item) => WalletTransaction.fromJson(item)).toList();
  }
}
