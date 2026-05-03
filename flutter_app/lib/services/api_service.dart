import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;

class ApiService {
  static String baseUrl = 'http://8.130.162.192:8080';
  static final http.Client _client = http.Client();

  // ========== Topic APIs ==========
  static Future<Map<String, dynamic>> analyzeTopic(Map<String, String> body) async {
    final resp = await _client.post(
      Uri.parse('$baseUrl/api/topic/analyze'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    if (resp.statusCode != 200) throw Exception('分析失败: ${resp.body}');
    return jsonDecode(utf8.decode(resp.bodyBytes));
  }

  static Future<void> favoriteTopic(int id, bool favorite) async {
    await _client.post(
      Uri.parse('$baseUrl/api/topic/favorite'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'id': id, 'favorite': favorite}),
    );
  }

  static Future<List<dynamic>> listFavorites() async {
    final resp = await _client.get(Uri.parse('$baseUrl/api/topic/favorites'));
    if (resp.statusCode != 200) return [];
    return jsonDecode(utf8.decode(resp.bodyBytes));
  }

  static Future<List<dynamic>> listHistory() async {
    final resp = await _client.get(Uri.parse('$baseUrl/api/topic/history'));
    if (resp.statusCode != 200) return [];
    return jsonDecode(utf8.decode(resp.bodyBytes));
  }

  static Future<Map<String, dynamic>> getTopic(int id) async {
    final resp = await _client.get(Uri.parse('$baseUrl/api/topic/$id'));
    if (resp.statusCode != 200) throw Exception('获取失败');
    return jsonDecode(utf8.decode(resp.bodyBytes));
  }

  // ========== Paper APIs ==========
  static Future<Map<String, dynamic>> uploadPaper(File file) async {
    final request = http.MultipartRequest('POST', Uri.parse('$baseUrl/api/paper/upload'));
    request.files.add(await http.MultipartFile.fromPath('file', file.path,
        filename: file.path.split('/').last));
    final streamed = await request.send();
    final resp = await http.Response.fromStream(streamed);
    if (resp.statusCode != 200) throw Exception('上传失败: ${resp.body}');
    return jsonDecode(utf8.decode(resp.bodyBytes));
  }

  static Future<List<dynamic>> listPapers() async {
    final resp = await _client.get(Uri.parse('$baseUrl/api/paper/'));
    if (resp.statusCode != 200) return [];
    return jsonDecode(utf8.decode(resp.bodyBytes));
  }

  static Future<void> deletePaper(int id) async {
    final resp = await _client.delete(Uri.parse('$baseUrl/api/paper/$id'));
    if (resp.statusCode != 200) throw Exception('删除失败');
  }

  static Future<Map<String, dynamic>> getPaper(int id) async {
    final resp = await _client.get(Uri.parse('$baseUrl/api/paper/$id'));
    if (resp.statusCode != 200) throw Exception('获取失败');
    return jsonDecode(utf8.decode(resp.bodyBytes));
  }

  static Future<Map<String, dynamic>> summarizePaper(int id, String level) async {
    final resp = await _client.post(
      Uri.parse('$baseUrl/api/paper/$id/summarize'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'level': level}),
    );
    if (resp.statusCode != 200) throw Exception('生成摘要失败');
    return jsonDecode(utf8.decode(resp.bodyBytes));
  }
}
