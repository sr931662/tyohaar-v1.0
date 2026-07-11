import '../api_client.dart';

class TermsVersion {
  final String id;
  final String content;
  final String version;
  final DateTime effectiveDate;

  TermsVersion({
    required this.id,
    required this.content,
    required this.version,
    required this.effectiveDate,
  });

  factory TermsVersion.fromJson(Map<String, dynamic> json) {
    return TermsVersion(
      id: json['id'] as String,
      content: json['content'] as String? ?? '',
      version: json['version'] as String? ?? '1.0',
      effectiveDate: DateTime.tryParse(json['effective_date'] as String? ?? '') ?? DateTime.now(),
    );
  }
}

class PrivacyPolicyVersion {
  final String id;
  final String content;
  final String version;
  final DateTime effectiveDate;

  PrivacyPolicyVersion({
    required this.id,
    required this.content,
    required this.version,
    required this.effectiveDate,
  });

  factory PrivacyPolicyVersion.fromJson(Map<String, dynamic> json) {
    return PrivacyPolicyVersion(
      id: json['id'] as String,
      content: json['content'] as String? ?? '',
      version: json['version'] as String? ?? '1.0',
      effectiveDate: DateTime.tryParse(json['effective_date'] as String? ?? '') ?? DateTime.now(),
    );
  }
}

class CancellationPolicyVersion {
  final String id;
  final String content;
  final String version;
  final DateTime effectiveDate;

  CancellationPolicyVersion({
    required this.id,
    required this.content,
    required this.version,
    required this.effectiveDate,
  });

  factory CancellationPolicyVersion.fromJson(Map<String, dynamic> json) {
    return CancellationPolicyVersion(
      id: json['id'] as String,
      content: json['content'] as String? ?? '',
      version: json['version'] as String? ?? '1.0',
      effectiveDate: DateTime.tryParse(json['effective_date'] as String? ?? '') ?? DateTime.now(),
    );
  }
}

class CityOption {
  final String id;
  final String name;
  final String stateId;

  CityOption({required this.id, required this.name, required this.stateId});

  factory CityOption.fromJson(Map<String, dynamic> json) {
    return CityOption(
      id: json['id'] as String,
      name: json['name'] as String,
      stateId: json['state_id'] as String? ?? '',
    );
  }
}

class StateOption {
  final String id;
  final String name;

  StateOption({required this.id, required this.name});

  factory StateOption.fromJson(Map<String, dynamic> json) {
    return StateOption(
      id: json['id'] as String,
      name: json['name'] as String,
    );
  }
}

class FaqItem {
  final String id;
  final String question;
  final String answer;
  final String? category;

  FaqItem({required this.id, required this.question, required this.answer, this.category});

  factory FaqItem.fromJson(Map<String, dynamic> json) {
    return FaqItem(
      id: json['id'] as String,
      question: json['question'] as String? ?? '',
      answer: json['answer'] as String? ?? '',
      category: json['faq_category'] as String?,
    );
  }
}

class CommonService {
  final ApiClient _api = ApiClient();

  Future<TermsVersion> getTerms() async {
    final response = await _api.dio.get('common/terms');
    return TermsVersion.fromJson(response.data['data'] as Map<String, dynamic>);
  }

  Future<PrivacyPolicyVersion> getPrivacyPolicy() async {
    final response = await _api.dio.get('common/privacy-policy');
    return PrivacyPolicyVersion.fromJson(response.data['data'] as Map<String, dynamic>);
  }

  Future<CancellationPolicyVersion> getCancellationPolicy() async {
    final response = await _api.dio.get('common/cancellation-policy');
    return CancellationPolicyVersion.fromJson(response.data['data'] as Map<String, dynamic>);
  }

  Future<List<StateOption>> listStates() async {
    final response = await _api.dio.get('common/states');
    final List list = (response.data['data'] ?? []) as List;
    return list.map((item) => StateOption.fromJson(item as Map<String, dynamic>)).toList();
  }

  Future<List<CityOption>> listCities({String? stateId}) async {
    final response = await _api.dio.get('common/cities', queryParameters: {
      if (stateId != null) 'state_id': stateId,
    });
    final List list = (response.data['data'] ?? []) as List;
    return list.map((item) => CityOption.fromJson(item as Map<String, dynamic>)).toList();
  }

  Future<List<CityOption>> searchCities(String query) async {
    final response = await _api.dio.get('common/cities/search', queryParameters: {'q': query});
    final List list = (response.data['data'] ?? []) as List;
    return list.map((item) => CityOption.fromJson(item as Map<String, dynamic>)).toList();
  }

  Future<List<FaqItem>> listFaqs({String? category}) async {
    final response = await _api.dio.get('common/faqs', queryParameters: {
      if (category != null) 'category': category,
    });
    final List list = (response.data['data'] ?? []) as List;
    return list.map((item) => FaqItem.fromJson(item as Map<String, dynamic>)).toList();
  }
}
