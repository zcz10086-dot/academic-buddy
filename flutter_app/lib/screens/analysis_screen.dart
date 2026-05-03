import 'package:flutter/material.dart';
import '../services/api_service.dart';

class AnalysisScreen extends StatefulWidget {
  final Map<String, dynamic> report;
  final VoidCallback onSaved;

  const AnalysisScreen({super.key, required this.report, required this.onSaved});

  @override
  State<AnalysisScreen> createState() => _AnalysisScreenState();
}

class _AnalysisScreenState extends State<AnalysisScreen> {
  bool _saving = false;
  bool _favorited = false;
  String? _saveMessage;

  Future<void> _toggleFavorite() async {
    setState(() => _saving = true);
    try {
      final newVal = !_favorited;
      await ApiService.favoriteTopic(widget.report['id'], newVal);
      setState(() {
        _favorited = newVal;
        _saveMessage = newVal ? '已收藏' : '已取消收藏';
      });
      widget.onSaved();
    } catch (e) {
      _saveMessage = '操作失败';
    } finally {
      setState(() => _saving = false);
    }
  }

  Color _scoreColor(int score) {
    if (score >= 70) return Colors.green;
    if (score >= 40) return Colors.orange;
    return Colors.red;
  }

  String _scoreHint(int score) {
    if (score >= 70) return '可行性高，推荐入手';
    if (score >= 40) return '有一定挑战，建议多做准备';
    return '难度较大，建议先积累基础';
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final r = widget.report;
    final score = r['feasibility_score'] ?? 0;
    final overview = r['research_overview'] ?? '';
    final gap = r['innovation_gap'] ?? '';
    final firstStep = r['first_step'] ?? '';
    final references = (r['references'] as List<dynamic>?) ?? [];

    return Scaffold(
      appBar: AppBar(
        title: Text(r['topic_input'] ?? '分析结果', maxLines: 1, overflow: TextOverflow.ellipsis),
        actions: [
          IconButton(
            icon: Icon(_favorited ? Icons.bookmark : Icons.bookmark_border, color: _favorited ? Colors.amber : null),
            onPressed: _toggleFavorite,
            tooltip: _favorited ? '取消收藏' : '收藏',
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (_saveMessage != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Text(_saveMessage!, style: TextStyle(color: _favorited ? Colors.green : Colors.red)),
              ),
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [_scoreColor(score).withValues(alpha: 0.2), Colors.transparent],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Column(
                children: [
                  Text('可行性评分', style: theme.textTheme.titleSmall?.copyWith(color: Colors.grey)),
                  const SizedBox(height: 8),
                  Text('$score/100',
                      style: TextStyle(fontSize: 48, fontWeight: FontWeight.bold, color: _scoreColor(score))),
                  const SizedBox(height: 8),
                  Text(_scoreHint(score), style: TextStyle(color: Colors.grey.shade400)),
                ],
              ),
            ),
            const SizedBox(height: 24),
            _section(theme, '研究现状', overview),
            _section(theme, '创新空间', gap),
            _section(theme, '第一步行动', firstStep),
            const SizedBox(height: 16),
            Text('相关论文', style: theme.textTheme.titleMedium),
            const SizedBox(height: 8),
            ...references.map((ref) => Card(
                  margin: const EdgeInsets.only(bottom: 8),
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(ref['title'] ?? '', style: const TextStyle(fontWeight: FontWeight.w600)),
                        if (ref['authors'] != null) Text(ref['authors'], style: TextStyle(color: Colors.grey.shade400, fontSize: 13)),
                        if (ref['venue'] != null) Text(ref['venue'], style: TextStyle(color: Colors.grey.shade500, fontSize: 12)),
                        if (ref['url'] != null) ...[
                          const SizedBox(height: 4),
                          Text(ref['url'], style: TextStyle(color: theme.colorScheme.primary, fontSize: 12)),
                        ],
                      ],
                    ),
                  ),
                )),
          ],
        ),
      ),
    );
  }

  Widget _section(ThemeData theme, String title, dynamic content) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.5),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(
              content?.toString() ?? '',
              style: const TextStyle(fontSize: 14, height: 1.6),
            ),
          ),
        ],
      ),
    );
  }
}
