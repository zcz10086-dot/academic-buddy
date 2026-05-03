import 'package:flutter/material.dart';
import '../services/api_service.dart';

class PaperReadingScreen extends StatefulWidget {
  final int paperId;
  final String title;

  const PaperReadingScreen({super.key, required this.paperId, required this.title});

  @override
  State<PaperReadingScreen> createState() => _PaperReadingScreenState();
}

class _PaperReadingScreenState extends State<PaperReadingScreen> {
  String _content = '';
  String _level = 'summary';
  bool _loading = true;

  final List<String> _levelNames = ['摘要版', '精读版', '完整版'];
  final List<String> _levelKeys = ['summary', 'detailed', 'full'];

  @override
  void initState() {
    super.initState();
    _loadSummary();
  }

  Future<void> _loadSummary() async {
    setState(() => _loading = true);
    try {
      final resp = await ApiService.summarizePaper(widget.paperId, _level);
      setState(() {
        _content = resp['content'] ?? '暂无内容';
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _content = '加载失败: $e';
        _loading = false;
      });
    }
  }

  void _switchLevel(int level) {
    setState(() {
      _level = _levelKeys[level];
    });
    _loadSummary();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.title, maxLines: 1, overflow: TextOverflow.ellipsis),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(40),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Row(
              children: List.generate(3, (i) {
                final active = _level == _levelKeys[i];
                return Expanded(
                  child: GestureDetector(
                    onTap: () => _switchLevel(i),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 4),
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 6),
                        decoration: BoxDecoration(
                          color: active ? theme.colorScheme.primary : Colors.grey.shade300,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          _levelNames[i],
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: active ? Colors.white : Colors.grey.shade600,
                            fontSize: 12,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ),
                    ),
                  ),
                );
              }),
            ),
          ),
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : Padding(
              padding: const EdgeInsets.all(16),
              child: SingleChildScrollView(
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: theme.cardColor,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    _content.replaceAll('*', '').replaceAll('#', ''),
                    style: const TextStyle(fontSize: 15, height: 1.7, color: Colors.white),
                  ),
                ),
              ),
            ),
    );
  }
}
