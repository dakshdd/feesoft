import 'package:flutter/material.dart';
import 'dart:convert'; // Needed for base64Decode
import 'services/api_service.dart'; // Import ApiService

class FeeEntryScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Fee Entry')),
      body: FeeForm(), // ✅ embed the form here
    );
  }
}

class FeeForm extends StatefulWidget {
  @override
  _FeeFormState createState() => _FeeFormState();
}

class _FeeFormState extends State<FeeForm> {
  final TextEditingController _admnController = TextEditingController();
  final TextEditingController _paidController = TextEditingController();
  final ApiService api = ApiService();

  bool _isLoading = false;
  String _result = "";
  String? _studentPhoto;

  String? _name, _className, _totalFee, _paidFee, _balanceFee;

  // 👇 Month selector
  String _selectedMonth = "April";
  final List<String> _months = [
    "April","May","June","July","August","September",
    "October","November","December","January","February","March"
  ];

  @override
  void dispose() {
    _admnController.dispose();
    _paidController.dispose();
    super.dispose();
  }

  Future<void> fetchFee(String admnNo) async {
    setState(() {
      _isLoading = true;
      _result = "";
    });
    try {
      final data = await api.fetchFee(admnNo);
      setState(() {
        if (data.containsKey('error')) {
          _result = "❌ ${data['error']}";
          _studentPhoto = null;
        } else {
          _name = data['student_name'];
          _className = data['class'];
          _totalFee = data['total_fee'].toString();
          _paidFee = data['paid_fee'].toString();
          _balanceFee = data['balance_fee'].toString();

          _studentPhoto =
          (data['photo'] != null && data['photo'].toString().isNotEmpty)
              ? data['photo']
              : null;
        }
      });
    } catch (e) {
      setState(() => _result = "🌐 Network error: $e");
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> recordPayment(String admnNo, double paidAmount, String month) async {
    setState(() => _isLoading = true);
    try {
      final data = await api.recordPayment(admnNo, paidAmount, month);
      setState(() {
        _result = data['status'] == "success"
            ? "✅ Payment recorded successfully"
            : "❌ Error: ${data['error'] ?? data['message']}";
      });
    } catch (e) {
      setState(() => _result = "🌐 Network error: $e");
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Widget _buildStudentInfo() {
    if (_name == null) return SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text("👤 Name: $_name"),
        Text("🏫 Class: $_className"),
        Text("💰 Total Fee: $_totalFee"),
        Text("✅ Paid Fee: $_paidFee"),
        Text("📉 Balance Fee: $_balanceFee"),
      ],
    );
  }

  Widget _buildPhoto() {
    if (_studentPhoto == null) {
      return Icon(Icons.person, size: 120, color: Colors.grey);
    }
    if (_studentPhoto!.startsWith("http")) {
      return Image.network(
        _studentPhoto!,
        height: 150,
        width: 150,
        fit: BoxFit.cover,
      );
    }
    try {
      return Image.memory(
        base64Decode(_studentPhoto!),
        height: 150,
        width: 150,
        fit: BoxFit.cover,
      );
    } catch (_) {
      return Icon(Icons.person, size: 120, color: Colors.grey);
    }
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        children: [
          // Admission No Card
          Card(
            elevation: 4,
            shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12)),
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                children: [
                  TextField(
                    controller: _admnController,
                    decoration: InputDecoration(
                      labelText: "Admission No",
                      prefixIcon: Icon(Icons.school),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(10),
                      ),
                    ),
                  ),
                  SizedBox(height: 12),
                  ElevatedButton.icon(
                    onPressed: () {
                      final admnNo = _admnController.text.trim();
                      if (admnNo.isEmpty) {
                        setState(() => _result = "❌ Please enter Admission No");
                        return;
                      }
                      fetchFee(admnNo);
                    },
                    icon: Icon(Icons.search),
                    label: Text("Search Fee"),
                    style: ElevatedButton.styleFrom(
                      minimumSize: Size(double.infinity, 50),
                      backgroundColor: Colors.yellow,
                    ),
                  ),
                ],
              ),
            ),
          ),

          SizedBox(height: 20),

          // Payment Card
          Card(
            elevation: 4,
            shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12)),
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                children: [
                  TextField(
                    controller: _paidController,
                    decoration: InputDecoration(
                      labelText: "Paid Amount",
                      prefixIcon: Icon(Icons.currency_rupee),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(10),
                      ),
                    ),
                    keyboardType: TextInputType.number,
                  ),
                  SizedBox(height: 12),

                  // Month dropdown
                  DropdownButtonFormField<String>(
                    value: _selectedMonth,
                    items: _months.map((m) =>
                        DropdownMenuItem(value: m, child: Text(m))
                    ).toList(),
                    onChanged: (val) {
                      setState(() => _selectedMonth = val!);
                    },
                    decoration: InputDecoration(
                      labelText: "Select Month",
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(10),
                      ),
                    ),
                  ),

                  SizedBox(height: 12),

                  ElevatedButton.icon(
                    onPressed: () {
                      final admnNo = _admnController.text.trim();
                      final paidAmount =
                          double.tryParse(_paidController.text) ?? 0.0;
                      if (admnNo.isEmpty || paidAmount <= 0) {
                        setState(() => _result =
                        "❌ Please enter valid Admission No & Amount");
                        return;
                      }
                      recordPayment(admnNo, paidAmount, _selectedMonth);
                    },
                    icon: Icon(Icons.payment),
                    label: Text("Record Payment"),
                    style: ElevatedButton.styleFrom(
                      minimumSize: Size(double.infinity, 50),
                      backgroundColor: Colors.greenAccent,
                    ),
                  ),
                ],
              ),
            ),
          ),

          SizedBox(height: 20),

          // Student Photo
          _buildPhoto(),

          SizedBox(height: 20),

          // Student Info
          _buildStudentInfo(),

          SizedBox(height: 20),

          // Result Text
          if (_result.isNotEmpty)
            Text(
              _result,
              style: TextStyle(
                fontSize: 16,
                color: _result.contains("✅")
                    ? Colors.green
                    : Colors.redAccent,
              ),
            ),

          if (_isLoading) CircularProgressIndicator(),
        ],
      ),
    );
  }
}
