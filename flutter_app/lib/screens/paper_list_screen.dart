import 'dart:io';
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import '../services/api_service.dart';
import 'paper_reading_screen.dart';

class PaperListScreen extends StatefulWidget {
  const PaperListScreen({super.key});

  @override
  State<PaperListScreen> createState() => _PaperListScreenState();
}

class _PaperListScreenState extends State<PaperListScreen> {
  List<dynamic> _papers = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadPapers();
  }

  Future<void> _deletePaper(int index) async {
    final p = _papers[index];
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('删除论文'),
        content: Text('确定要删除「${p['title'] ?? '未知'}」吗？'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('取消')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('删除', style: TextStyle(color: Colors.red))),
        ],
      ),
    );
    if (confirm == true) {
      try {
        await ApiService.deletePaper(p['id']);
        setState(() => _papers.removeAt(index));
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('已删除')));
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('删除失败: $e')));
        }
      }
    }
  }

  Future<void> _loadPapers() async {
    setState(() => _loading = true);
    try {
      final papers = await ApiService.listPapers();
      setState(() {
        _papers = papers;
        _loading = false;
      });
    } catch (e) {
      setState(() => _loading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('加载失败: $e')));
      }
    }
  }

  Future<void> _uploadPaper() async {
    final proceed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('上传论文'),
        content: const Text('请上传PDF格式的论文文件。\n\n上传后系统会自动解析全文并生成三级摘要和检测题，请耐心等待约15-30秒。\n\n支持：纯文本PDF（推荐）\n不支持：扫描版/图片PDF'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('取消')),
          ElevatedButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('选择文件')),
        ],
      ),
    );
    if (proceed != true) return;
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom, allowedExtensions: ['pdf'], withData: true,
    );
    if (result == null || result.files.isEmpty) return;
    final file = result.files.first;
    if (file.path == null) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('文件路径为空')));
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('文件过大，请上传小于50MB的PDF')));
      return;
    }
    if (file.size < 1000) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('文件过小，请上传有效的PDF文件')));
      return;
    }
    setState(() => _loading = true);
    try {
      final resp = await ApiService.uploadPaper(File(file.path!));
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('上传成功: ${resp['title'] ?? ''}')));
      await _loadPapers();
    } catch (e) {
      setState(() => _loading = false);
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('上传失败: $e')));
    }
  }

  String _levelLabel(int l) => ['摘要版', '精读版', '完整版'][l];
  Color _statusColor(String s) => s == 'completed' ? Colors.green : s == 'reading' ? Colors.orange : Colors.grey;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('我的论文'),
        actions: [IconButton(icon: const Icon(Icons.refresh), onPressed: _loadPapers)],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _papers.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.folder_open, size: 64, color: Colors.grey),
                      const SizedBox(height: 16),
                      const Text('还没有论文', style: TextStyle(color: Colors.grey)),
                      const SizedBox(height: 8),
                      const Text('请上传PDF格式的学术论文', style: TextStyle(color: Colors.grey, fontSize: 13)),
                      const SizedBox(height: 16),
                      ElevatedButton(onPressed: _uploadPaper, child: const Text('上传论文')),
                    ],
                  ),
                )
              : ListView.builder(
                  itemCount: _papers.length,
                  padding: const EdgeInsets.all(16),
                  itemBuilder: (ctx, i) {
                    final p = _papers[i];
                    final level = p['current_level'] ?? 0;
                    final status = p['status'] ?? 'not_started';
                    return Dismissible(
                      key: ValueKey(p['id']),
                      direction: DismissDirection.endToStart,
                      confirmDismiss: (_) async {
                        await _deletePaper(i);
                        return false;
                      },
                      background: Container(
                        alignment: Alignment.centerRight,
                        padding: const EdgeInsets.only(right: 20),
                        color: Colors.red,
                        child: const Icon(Icons.delete, color: Colors.white),
                      ),
                      child: Card(
                        margin: const EdgeInsets.only(bottom: 12),
                        child: ListTile(
                          leading: CircleAvatar(
                            backgroundColor: _statusColor(status),
                            child: const Icon(Icons.article, color: Colors.white, size: 20),
                          ),
                          title: Text(p['title'] ?? '未知标题', maxLines: 1, overflow: TextOverflow.ellipsis),
                          subtitle: Text('${p['authors'] ?? ''}  \u00b7 ${_levelLabel(level)}'),
                          trailing: const Icon(Icons.chevron_right),
                          onTap: () {
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (_) => PaperReadingScreen(paperId: p['id'], title: p['title'] ?? ''),
                              ),
                            ).then((_) => _loadPapers());
                          },
                        ),
                      ),
                    );
                  },
                ),
      floatingActionButton: FloatingActionButton(
        onPressed: _uploadPaper,
        child: const Icon(Icons.upload_file),
      ),
    );
  }
}
