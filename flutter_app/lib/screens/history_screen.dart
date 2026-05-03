import 'package:flutter/material.dart';
import '../services/api_service.dart';
import 'analysis_screen.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  List<Map<String, dynamic>> _history = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final items = await ApiService.listHistory();
    if (mounted) {
      setState(() {
        _history = List<Map<String, dynamic>>.from(items);
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('选题记录')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _history.isEmpty
              ? const Center(child: Text('暂无记录'))
              : ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: _history.length,
                  itemBuilder: (ctx, i) {
                    final item = _history[i];
                    return Card(
                      margin: const EdgeInsets.only(bottom: 8),
                      child: ListTile(
                        leading: CircleAvatar(
                          backgroundColor: (item['feasibility_score'] ?? 0) >= 70
                              ? Colors.green
                              : (item['feasibility_score'] ?? 0) >= 40
                                  ? Colors.orange
                                  : Colors.red,
                          child: Text(
                            '${item['feasibility_score'] ?? '?'}',
                            style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold),
                          ),
                        ),
                        title: Text(item['topic_input'] ?? '未知', maxLines: 1, overflow: TextOverflow.ellipsis),
                        subtitle: Text((item['created_at']?.toString() ?? '').substring(0, 10)),
                        onTap: () async {
                          try {
                            final full = await ApiService.getTopic(item['id']);
                            if (mounted) {
                              Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder: (_) => AnalysisScreen(report: full, onSaved: () => _load()),
                                ),
                              );
                            }
                          } catch (_) {}
                        },
                      ),
                    );
                  },
                ),
    );
  }
}
