import '../api_client.dart';
import '../models.dart';

class Budget {
  final String id;
  final String celebrationId;
  final double totalPlanned;
  final double totalSpent;
  final double remaining;
  final String status;

  Budget({
    required this.id,
    required this.celebrationId,
    required this.totalPlanned,
    required this.totalSpent,
    required this.remaining,
    required this.status,
  });

  factory Budget.fromJson(Map<String, dynamic> json) {
    return Budget(
      id: json['id'] as String,
      celebrationId: json['celebration_id'] as String,
      totalPlanned: asDouble(json['total_planned']),
      totalSpent: asDouble(json['total_spent']),
      remaining: asDouble(json['remaining']),
      status: json['lifecycle_status'] as String? ?? 'draft',
    );
  }
}

class BudgetService {
  final ApiClient _api = ApiClient();

  Future<List<Budget>> listBudgets() async {
    final response = await _api.dio.get('budgets');
    final List list = response.data['data'];
    return list.map((item) => Budget.fromJson(item)).toList();
  }

  Future<Budget?> getBudgetForCelebration(String celebrationId) async {
    final budgets = await listBudgets();
    try {
      return budgets.firstWhere((b) => b.celebrationId == celebrationId);
    } catch (_) {
      return null;
    }
  }

  Future<List<BudgetExpense>> listExpenses(String budgetId) async {
    final response = await _api.dio.get('budgets/$budgetId/expenses');
    final List list = response.data['data'];
    return list.map((item) => BudgetExpense.fromJson(item)).toList();
  }

  Future<BudgetExpense> addExpense(String budgetId, Map<String, dynamic> data) async {
    final response = await _api.dio.post('budgets/$budgetId/expenses', data: data);
    return BudgetExpense.fromJson(response.data['data']);
  }
}
