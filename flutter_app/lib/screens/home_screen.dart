import 'package:flutter/material.dart';
import '../services/api_service.dart';
import 'analysis_screen.dart';
import 'paper_list_screen.dart';
import 'history_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _topicCtl = TextEditingController();
  final _bgCtl = TextEditingController();
  final _constraintCtl = TextEditingController();
  List<Map<String, dynamic>> _favorites = [];
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    _loadFavorites();
  }

  @override
  void dispose() {
    _topicCtl.dispose();
    _bgCtl.dispose();
    _constraintCtl.dispose();
    super.dispose();
  }

  Future<void> _loadFavorites() async {
    final items = await ApiService.listFavorites();
    if (mounted) setState(() => _favorites = List<Map<String, dynamic>>.from(items));
  }

  Future<void> _analyze() async {
    if (_topicCtl.text.trim().isEmpty) return;
    setState(() => _loading = true);
    try {
      final result = await ApiService.analyzeTopic({
        'topic': _topicCtl.text,
        'background': _bgCtl.text,
        'constraint': _constraintCtl.text,
      });
      if (mounted) {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => AnalysisScreen(report: result, onSaved: () {}),
          ),
        ).then((_) => _loadFavorites());
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('分析失败: $e')),
        );
      }
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('学', style: TextStyle(color: theme.colorScheme.primary)),
            const Text('搭子'),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.history),
            tooltip: '选题记录',
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const HistoryScreen()),
            ).then((_) => _loadFavorites()),
          ),
          IconButton(
            icon: const Icon(Icons.article_outlined),
            tooltip: '我的论文',
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const PaperListScreen()),
            ),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                  children: [
                    TextField(
                      controller: _topicCtl,
                      decoration: const InputDecoration(
                        labelText: '研究方向',
                        hintText: '例如: AI for Code Generation',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _bgCtl,
                      decoration: const InputDecoration(
                        labelText: '你的背景（可选）',
                        hintText: '例如: 会Python, 学过机器学习',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _constraintCtl,
                      decoration: const InputDecoration(
                        labelText: '限制条件（可选）',
                        hintText: '例如: 不想做纯NLP',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 20),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton(
                        onPressed: _loading ? null : _analyze,
                        child: _loading
                            ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                            : const Text('分析', style: TextStyle(fontSize: 16)),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('我的收藏', style: theme.textTheme.titleMedium),
                TextButton.icon(
                  icon: const Icon(Icons.history, size: 18),
                  label: const Text('选题记录'),
                  onPressed: () => Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => const HistoryScreen()),
                  ).then((_) => _loadFavorites()),
                ),
              ],
            ),
            const SizedBox(height: 8),
            ..._favorites.map((item) => Card(
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
                    title: Text(
                      item['display_title'] ?? '未知推荐',
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    subtitle: Text(
                      '${item['topic_input'] ?? ''}  \u00b7 ${(item['created_at']?.toString() ?? '').substring(0, 10)}',
                      style: const TextStyle(fontSize: 12),
                    ),
                    onTap: () async {
                      try {
                        final full = await ApiService.getTopic(item['id']);
                        if (mounted) {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (_) => AnalysisScreen(report: full, onSaved: () => _loadFavorites()),
                            ),
                          );
                        }
                      } catch (_) {}
                    },
                  ),
                )),
            if (_favorites.isEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 40),
                child: Center(
                  child: Column(
                    children: [
                      Icon(Icons.bookmark_border, size: 48, color: Colors.grey.shade500),
                      const SizedBox(height: 8),
                      Text('还没有收藏的选题', style: TextStyle(color: Colors.grey.shade500)),
                      const SizedBox(height: 4),
                      Text('分析研究方向后可以收藏', style: TextStyle(color: Colors.grey.shade600, fontSize: 13)),
                    ],
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
