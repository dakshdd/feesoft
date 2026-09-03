import 'dart:convert';
import 'dart:io' show Platform;
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;

class ApiService {
  static const String localUrl = "http://127.0.0.1:5000";
  static const String emulatorUrl = "http://10.0.2.2:5000";
  static String wifiUrl = "http://192.168.1.8:5000"; // अपने LAN IP डालो

  String get baseUrl {
    if (kIsWeb) return localUrl;
    if (Platform.isAndroid) return _isEmulator ? emulatorUrl : wifiUrl;
    if (Platform.isIOS) return localUrl;
    if (Platform.isWindows || Platform.isLinux) return localUrl;
    return wifiUrl;
  }

  bool get _isEmulator {
    // Simple check: assume emulator if Android
    return Platform.isAndroid;
  }

  /// Fetch student fee details
  Future<Map<String, dynamic>> fetchFee(String admnNo) async {
    try {
      final res = await http
          .get(Uri.parse("$baseUrl/fee/api/details/$admnNo"))
          .timeout(const Duration(seconds: 20));

      if (res.statusCode == 200) {
        return json.decode(res.body);
      } else {
        throw ApiException("Server error: ${res.statusCode}");
      }
    } catch (e) {
      throw ApiException("Network error: $e");
    }
  }

  /// Record payment
  Future<Map<String, dynamic>> recordPayment(
      String admnNo, double amount, String month) async {
    try {
      final res = await http
          .post(
        Uri.parse("$baseUrl/fee/api/pay"),
        headers: {"Content-Type": "application/json"},
        body: json.encode({
          "adm_code": admnNo,
          "amount": amount,
          "month": month,
          "mode": "Cash"
        }),
      )
          .timeout(const Duration(seconds: 20));

      if (res.statusCode == 200) {
        return json.decode(res.body);
      } else {
        throw ApiException("Server error: ${res.statusCode}");
      }
    } catch (e) {
      throw ApiException("Network error: $e");
    }
  }

  /// Get monthly total
  Future<Map<String, dynamic>> getMonthTotal(String admnNo, String month) async {
    try {
      final res = await http
          .get(Uri.parse("$baseUrl/fee/api/month_total?adm_code=$admnNo&month=$month"))
          .timeout(const Duration(seconds: 20));

      if (res.statusCode == 200) {
        return json.decode(res.body);
      } else {
        throw ApiException("Server error: ${res.statusCode}");
      }
    } catch (e) {
      throw ApiException("Network error: $e");
    }
  }

  /// Get next unpaid month
  Future<Map<String, dynamic>> getNextMonth(String admnNo) async {
    try {
      final res = await http
          .get(Uri.parse("$baseUrl/fee/api/next_month?adm_code=$admnNo"))
          .timeout(const Duration(seconds: 20));

      if (res.statusCode == 200) {
        return json.decode(res.body);
      } else {
        throw ApiException("Server error: ${res.statusCode}");
      }
    } catch (e) {
      throw ApiException("Network error: $e");
    }
  }
}

class ApiException implements Exception {
  final String message;
  ApiException(this.message);
  @override
  String toString() => message;
}
