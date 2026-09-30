import re
import sys
from enum import EnumMeta
from typing import Annotated, Type, List, Union, get_args, get_origin
from pydantic import BaseModel
from .OpenapiModel import OpenAPIModel
from ..AccessRights.AccessRights import AccessRight
from ..LaiaUser.Role import Role
from ...Domain.Shared.Utils.logger import _logger

def main_dart(app_name: str, models: List[OpenAPIModel]):
    auth_models = [model for model in models if model.extensions.get('x-auth') and not model.model_name.startswith("Body_") and not model.model_name.endswith("Update")]
    
    clean_auth_models = []
    seen = set()
    for m in auth_models:
        c_name = m.model_name.replace('-Input', '').replace('-Output', '')
        if c_name not in seen:
            seen.add(c_name)
            clean_auth_models.append((c_name, m))

    import_statements = '\n'.join([f"import 'package:{app_name}/models/{name.lower()}.dart';" for name, _ in clean_auth_models])
    auth_screens = ', '.join([f"'{name}': {name}LoginWidget()" for name, _ in clean_auth_models])

    file_content = f"""{import_statements}
import 'package:{app_name}/screens/home.dart';"""+f"""
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_quill/flutter_quill.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:{app_name}/theme/theme_app.dart';"""+"""

final GlobalKey<NavigatorState> navigatorKey = GlobalKey<NavigatorState>();

void main() {
  runApp(
    const ProviderScope(
      child: MyApp(),
    ));
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'LAIA',
      debugShowCheckedModeBanner: false,
      navigatorKey: navigatorKey,
      theme: AppTheme.light(),
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        FlutterQuillLocalizations.delegate,
      ],
      supportedLocales: const [
        Locale('en'),
        Locale('es'),
      ],
      home: """+f"""{ "SplashScreen()" if clean_auth_models else "Home()" }"""+""",
    );
  }
}
"""
    if clean_auth_models:
      file_content = file_content + """
class SplashScreen extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AsyncValue<bool> tokenVerificationResult = ref.watch(verifyToken"""+f"""{clean_auth_models[0][0]}"""+"""Provider);

    return Scaffold(
      body: tokenVerificationResult.when(
        data: (isValid) {
          if (isValid) {
            return Home();
          } else {
            return """+f"""{ ''.join([clean_auth_models[0][0], 'LoginWidget();']) if len(clean_auth_models) == 1 else f"DynamicLogInScreen(widgetMap: const {{ {auth_screens} }});"}"""+"""
          }
        },
        loading: () => Center(
          child: CircularProgressIndicator(),
        ),
        error: (error, stackTrace) {
          return Container();
        },
      ),
    );
  }
}
"""
    return file_content

def api_dart():
    return """const String baseURL = String.fromEnvironment('API_URL', defaultValue: 'http://localhost:8000');
//const String baseURL = 'http://10.0.2.2:8000';

// Android emmulator
// const String baseURL = 'http://10.0.2.2:8000';
"""

def styles_dart():
    return """import 'dart:ui';

class Styles {
  static const primaryColor = Color.fromARGB(255, 210, 223, 224);
  static const secondaryColor = Color.fromARGB(255, 236, 243, 242);
  static const buttonPrimaryColor = Color.fromARGB(255, 210, 223, 224);
  static const buttonPrimaryColorHover = Color.fromARGB(255, 165, 194, 191);
  static const dashboardBlock = Color.fromARGB(255, 196, 209, 208);
  static const polygonColor = Color.fromARGB(118, 104, 161, 51);
}
"""

def generic_dart(app_name: str):
    return f"""import 'package:laia_annotations/laia_annotations.dart';
import 'package:{app_name}/theme/theme_app.dart';
import 'package:{app_name}/config/styles.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_map_arcgis/flutter_map_arcgis.dart';
import 'package:latlong2/latlong.dart';
import 'package:flutter_map/src/layer/polygon_layer/polygon_layer.dart' as flutter_map;
import 'package:{app_name}/models/geometry.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_quill/flutter_quill.dart';
import 'dart:convert';
import 'dart:typed_data';
import 'image_picker_helper.dart';
import 'imgproxy_helper.dart';"""+"""

part 'generic_widgets.g.dart';

@genericWidgets
class GenericWidgets {}
"""

def image_picker_helper_dart() -> str:
    return """export 'image_picker_stub.dart'
    if (dart.library.html) 'image_picker_web.dart';
"""

def image_picker_stub_dart() -> str:
    return """class ImagePickerHelper {
  static void pickImage(Function(List<int>, String) onPicked) {}
  static void pickFile(Function(List<int>, String) onPicked, [String? accept]) {}
  static void Function() setupDropZone({
    required Function(bool) onDragStateChanged,
    required Function(List<int>, String) onFileDropped,
  }) => () {};
  static void downloadFile(String url, [String? filename]) {}
}

typedef FilePickerHelper = ImagePickerHelper;
"""

def image_picker_web_dart() -> str:
    return """// ignore_for_file: avoid_web_libraries_in_flutter

import 'dart:html' as html;
import 'dart:typed_data';

class ImagePickerHelper {
  static void pickImage(Function(List<int>, String) onPicked) {
    final input = html.FileUploadInputElement()..accept = 'image/*';
    input.click();
    input.onChange.first.then((_) => _readFile(input.files?.firstOrNull, onPicked));
  }

  static void pickFile(Function(List<int>, String) onPicked, [String? accept]) {
    final input = html.FileUploadInputElement();
    if (accept != null && accept.isNotEmpty) {
      input.accept = accept;
    }
    input.click();
    input.onChange.first.then((_) => _readFile(input.files?.firstOrNull, onPicked));
  }

  static void Function() setupDropZone({
    required Function(bool) onDragStateChanged,
    required Function(List<int>, String) onFileDropped,
  }) {
    final s1 = html.window.onDragOver.listen((e) { e.preventDefault(); onDragStateChanged(true); });
    final s2 = html.window.onDragLeave.listen((_) => onDragStateChanged(false));
    final s3 = html.window.onDrop.listen((e) {
      e.preventDefault();
      onDragStateChanged(false);
      _readFile(e.dataTransfer.files?.firstOrNull, onFileDropped);
    });
    return () { s1.cancel(); s2.cancel(); s3.cancel(); };
  }

  static void downloadFile(String url, [String? filename]) {
    final anchor = html.AnchorElement(href: url)
      ..target = '_blank';
    if (filename != null && filename.isNotEmpty) {
      anchor.download = filename;
    }
    anchor.click();
  }

  static void _readFile(html.File? file, Function(List<int>, String) cb) {
    if (file == null) return;
    final reader = html.FileReader()..readAsArrayBuffer(file);
    reader.onLoadEnd.first.then((_) {
      final res = reader.result;
      if (res is Uint8List) cb(res.toList(), file.name);
      else if (res is ByteBuffer) cb(Uint8List.view(res).toList(), file.name);
    });
  }
}

typedef FilePickerHelper = ImagePickerHelper;
"""

def imgproxy_helper_dart() -> str:
    return """class ImgproxyHelper {
  /// Genera la URL limpia a través de la API del backend (compatible con MinIO, Imgproxy, Cloudinary y S3)
  static String buildUrl({
    required String imagePath,
    String? apiBaseUrl,
    int width = 0,
    int height = 0,
    String resize = 'fill',
    String? gravity,
    String format = 'webp',
  }) {
    if (imagePath.isEmpty) return '';
    if (imagePath.startsWith('http://') || imagePath.startsWith('https://')) {
      return imagePath;
    }

    final clean = imagePath.replaceAll(RegExp(r'^/+'), '');
    final base = (apiBaseUrl != null && apiBaseUrl.isNotEmpty)
        ? apiBaseUrl.replaceAll(RegExp(r'/+$'), '')
        : '';

    final query = <String>['raw=true'];
    if (width > 0) query.add('width=\$width');
    if (height > 0) query.add('height=\$height');
    if (resize.isNotEmpty && resize != 'fit') query.add('resizing_type=\$resize');
    if (gravity != null && gravity.isNotEmpty) query.add('gravity=\$gravity');
    if (format.isNotEmpty && format != 'original') query.add('format=\$format');

    final prefix = base.isNotEmpty ? '\$base/download' : '/download';
    final qs = query.join('&');
    return '\$prefix/\$clean?\$qs';
  }
}

typedef StorageHelper = ImgproxyHelper;
"""

def media_gallery_screen_dart(app_name: str) -> str:
    return f"""import 'package:{app_name}/config/api.dart';
import 'package:{app_name}/generic/image_picker_helper.dart';
import 'package:{app_name}/generic/imgproxy_helper.dart';
""" + """import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class GalleryScreen extends StatefulWidget {
  final bool showAppBar;
  const GalleryScreen({super.key, this.showAppBar = false});

  @override
  State<GalleryScreen> createState() => _GalleryScreenState();
}

class _GalleryScreenState extends State<GalleryScreen> {
  bool _isLoading = true;
  String? _errorMessage;
  List<Map<String, dynamic>> _photos = [];
  final Map<String, String> _presignedCache = {};

  String _selectedBucket = 'originals';
  final List<String> _allowedBuckets = const ['originals', 'public', 'processed'];
  final TextEditingController _prefixController = TextEditingController();
  String _activeFilter = 'all'; // 'all', 'images', 'files'

  @override
  void initState() {
    super.initState();
    _fetchPhotos();
  }

  @override
  void dispose() {
    _prefixController.dispose();
    super.dispose();
  }

  String _itemKey(Map<String, dynamic> it) =>
      (it['key'] ?? it['image_id'] ?? it['path'] ?? it['filename'] ?? '').toString();

  bool _isImage(String name) {
    final ext = name.toLowerCase().split('.').last;
    return const {'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp', 'avif'}.contains(ext);
  }

  String _getFileExtension(String name) =>
      name.contains('.') ? name.split('.').last.toUpperCase() : 'FILE';

  IconData _fileIcon(String ext) {
    final e = ext.toLowerCase();
    if (e == 'pdf') return Icons.picture_as_pdf_rounded;
    if (['doc', 'docx'].contains(e)) return Icons.description_rounded;
    if (['xls', 'xlsx', 'csv'].contains(e)) return Icons.table_chart_rounded;
    if (['zip', 'rar', '7z'].contains(e)) return Icons.folder_zip_rounded;
    return Icons.insert_drive_file_rounded;
  }

  Color _fileColor(String ext) {
    final e = ext.toLowerCase();
    if (e == 'pdf') return Colors.red.shade700;
    if (['doc', 'docx'].contains(e)) return Colors.blue.shade700;
    if (['xls', 'xlsx', 'csv'].contains(e)) return Colors.green.shade700;
    if (['zip', 'rar', '7z'].contains(e)) return Colors.amber.shade800;
    return Colors.blueGrey.shade700;
  }

  List<Map<String, dynamic>> get _filteredPhotos {
    if (_activeFilter == 'images') return _photos.where((it) => _isImage(_itemKey(it))).toList();
    if (_activeFilter == 'files') return _photos.where((it) => !_isImage(_itemKey(it))).toList();
    return _photos;
  }

  int get _imageCount => _photos.where((it) => _isImage(_itemKey(it))).length;
  int get _fileCount => _photos.where((it) => !_isImage(_itemKey(it))).length;

  String _formatFileSize(dynamic size) {
    if (size is num && size > 0) {
      if (size < 1024) return '$size B';
      if (size < 1024 * 1024) return '${(size / 1024).toStringAsFixed(1)} KB';
      return '${(size / (1024 * 1024)).toStringAsFixed(1)} MB';
    }
    return '';
  }

  Future<void> _fetchPhotos() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final prefs = await SharedPreferences.getInstance();
      final token = prefs.getString("token");
      final headers = <String, String>{
        'Content-Type': 'application/json',
      };
      if (token != null && token.isNotEmpty) {
        headers['Authorization'] = 'Bearer $token';
      }

      final queryParams = <String, String>{
        'bucket': _selectedBucket,
        'recursive': 'true',
      };
      if (_prefixController.text.trim().isNotEmpty) {
        queryParams['prefix'] = _prefixController.text.trim();
      }

      final uri = Uri.parse('$baseURL/admin/files/explorer').replace(queryParameters: queryParams);
      http.Response? response;

      try {
        final res = await http.get(uri, headers: headers);
        if (res.statusCode == 200 || res.statusCode == 403) {
          response = res;
        }
      } catch (_) {}

      // Fallback si no está disponible la ruta de admin
      if (response == null || (response.statusCode != 200 && response.statusCode != 403)) {
        final fallbackEndpoints = [
          '$baseURL/storage/$_selectedBucket',
          '$baseURL/photos',
          '$baseURL/storage',
        ];
        for (final endpoint in fallbackEndpoints) {
          try {
            final res = await http.get(Uri.parse(endpoint), headers: headers);
            if (res.statusCode == 200) {
              response = res;
              break;
            }
          } catch (_) {}
        }
      }

      if (response != null && response.statusCode == 200) {
        final decoded = jsonDecode(response.body);
        final List<Map<String, dynamic>> items = [];

        if (decoded is Map && decoded['files'] is List) {
          for (final item in decoded['files']) {
            if (item is Map) {
              items.add(Map<String, dynamic>.from(item));
            }
          }
        } else if (decoded is List) {
          for (final item in decoded) {
            if (item is Map) {
              items.add(Map<String, dynamic>.from(item));
            } else if (item is String) {
              items.add({'key': item});
            }
          }
        } else if (decoded is Map && decoded['items'] is List) {
          for (final item in decoded['items']) {
            if (item is Map) {
              items.add(Map<String, dynamic>.from(item));
            }
          }
        }

        if (mounted) {
          setState(() {
            _photos = items;
            _isLoading = false;
          });
        }
      } else if (response != null && response.statusCode == 403) {
        if (mounted) {
          setState(() {
            _errorMessage = 'Restricted access: Backoffice admin permissions required';
            _isLoading = false;
          });
        }
      } else {
        if (mounted) {
          setState(() {
            _errorMessage = 'Could not load files from bucket "$_selectedBucket"';
            _isLoading = false;
          });
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = 'Error connecting to server: $e';
          _isLoading = false;
        });
      }
    }
  }

  Future<String?> _getDownloadUrl(String key, [Map<String, dynamic>? options]) async {
    if (key.isEmpty) return null;

    final isDefault = (options == null || options.isEmpty);
    if (isDefault && _presignedCache.containsKey(key)) {
      return _presignedCache[key];
    }

    if (key.startsWith('http://') || key.startsWith('https://')) {
      if (isDefault) _presignedCache[key] = key;
      return key;
    }

    try {
      final prefs = await SharedPreferences.getInstance();
      final token = prefs.getString("token");
      final headers = <String, String>{};
      if (token != null && token.isNotEmpty) {
        headers['Authorization'] = 'Bearer $token';
      }

      final cleanKey = key.replaceAll(RegExp(r'^/+'), '');
      String query = '';
      if (options != null && options.isNotEmpty) {
        final params = options.entries
            .where((e) => e.value != null && e.value.toString().isNotEmpty)
            .map((e) => '${Uri.encodeComponent(e.key.toString())}=${Uri.encodeComponent(e.value.toString())}')
            .join('&');
        if (params.isNotEmpty) query = '?$params';
      }
      final res = await http.get(Uri.parse('$baseURL/download/$cleanKey$query'), headers: headers);
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        final url = data['url']?.toString();
        if (url != null) {
          if (isDefault) {
            _presignedCache[key] = url;
          }
          return url;
        }
      }
    } catch (_) {}
    if (options != null && options.isNotEmpty) {
      final w = options['width'] as int? ?? 0;
      final h = options['height'] as int? ?? 0;
      return ImgproxyHelper.buildUrl(
        imagePath: key,
        apiBaseUrl: baseURL,
        width: w,
        height: h,
        resize: options['resizing_type']?.toString() ?? 'fill',
        gravity: options['gravity']?.toString(),
        format: options['format']?.toString() ?? 'webp',
      );
    }
    return null;
  }

  Future<String?> _resolveImageUrl(Map<String, dynamic> photo) async {
    final preview = (photo['preview_url'] ?? photo['url'] ?? photo['download_url'] ?? '').toString();
    if (preview.isNotEmpty && (preview.startsWith('http://') || preview.startsWith('https://'))) {
      try {
        final parsed = Uri.parse(preview);
        final baseUri = Uri.parse(baseURL);
        // Si el backend devolvió el host interno de Docker 'minio', sustituir por el host de la API
        if (parsed.host == 'minio' || (parsed.host == 'localhost' && baseUri.host != 'localhost' && baseUri.host.isNotEmpty)) {
          return parsed.replace(host: baseUri.host).toString();
        }
      } catch (_) {}
      return preview;
    }

    final key = (photo['key'] ?? photo['image_id'] ?? photo['path'] ?? photo['id'] ?? '').toString();
    if (key.isEmpty) return null;
    return await _getDownloadUrl(key);
  }

  void _showDownloadOptionsDialog(BuildContext context, String key, String defaultUrl, String defaultFilename) {
    String selectedSize = 'original';
    String selectedShape = 'fit';
    String selectedFormat = 'original';
    bool downloading = false;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDialogState) {
          return Dialog(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            child: Container(
              width: 500,
              padding: const EdgeInsets.all(24),
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.download_rounded, size: 24),
                        const SizedBox(width: 8),
                        const Expanded(
                          child: Text(
                            "Download Options",
                            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                          ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.close, size: 20),
                          onPressed: () => Navigator.of(ctx).pop(),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    const Text("Dimensions / Size:", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        ChoiceChip(label: const Text("Original", style: TextStyle(fontSize: 12)), selected: selectedSize == 'original', onSelected: (_) => setDialogState(() => selectedSize = 'original')),
                        ChoiceChip(label: const Text("Thumbnail (150x150)", style: TextStyle(fontSize: 12)), selected: selectedSize == '150x150', onSelected: (_) => setDialogState(() => selectedSize = '150x150')),
                        ChoiceChip(label: const Text("Avatar (256x256)", style: TextStyle(fontSize: 12)), selected: selectedSize == 'avatar_256', onSelected: (_) => setDialogState(() {
                          selectedSize = 'avatar_256';
                          selectedShape = 'square';
                        })),
                        ChoiceChip(label: const Text("Medium (800x600)", style: TextStyle(fontSize: 12)), selected: selectedSize == '800x600', onSelected: (_) => setDialogState(() => selectedSize = '800x600')),
                        ChoiceChip(label: const Text("Large (1280x720)", style: TextStyle(fontSize: 12)), selected: selectedSize == '1280x720', onSelected: (_) => setDialogState(() => selectedSize = '1280x720')),
                      ],
                    ),
                    const SizedBox(height: 16),
                    const Text("Crop / Aspect Ratio:", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        ChoiceChip(label: const Text("Keep aspect ratio (Fit)", style: TextStyle(fontSize: 12)), selected: selectedShape == 'fit', onSelected: (_) => setDialogState(() => selectedShape = 'fit')),
                        ChoiceChip(label: const Text("Square 1:1 (Smart Fill)", style: TextStyle(fontSize: 12)), selected: selectedShape == 'square', onSelected: (_) => setDialogState(() => selectedShape = 'square')),
                        ChoiceChip(label: const Text("Landscape 16:9", style: TextStyle(fontSize: 12)), selected: selectedShape == '16:9', onSelected: (_) => setDialogState(() => selectedShape = '16:9')),
                        ChoiceChip(label: const Text("Photo 4:3", style: TextStyle(fontSize: 12)), selected: selectedShape == '4:3', onSelected: (_) => setDialogState(() => selectedShape = '4:3')),
                        ChoiceChip(label: const Text("Portrait 9:16", style: TextStyle(fontSize: 12)), selected: selectedShape == '9:16', onSelected: (_) => setDialogState(() => selectedShape = '9:16')),
                      ],
                    ),
                    const SizedBox(height: 16),
                    const Text("Output format:", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        ChoiceChip(label: const Text("Original", style: TextStyle(fontSize: 12)), selected: selectedFormat == 'original', onSelected: (_) => setDialogState(() => selectedFormat = 'original')),
                        ChoiceChip(label: const Text("WebP", style: TextStyle(fontSize: 12)), selected: selectedFormat == 'webp', onSelected: (_) => setDialogState(() => selectedFormat = 'webp')),
                        ChoiceChip(label: const Text("PNG", style: TextStyle(fontSize: 12)), selected: selectedFormat == 'png', onSelected: (_) => setDialogState(() => selectedFormat = 'png')),
                        ChoiceChip(label: const Text("JPEG / JPG", style: TextStyle(fontSize: 12)), selected: selectedFormat == 'jpeg', onSelected: (_) => setDialogState(() => selectedFormat = 'jpeg')),
                      ],
                    ),
                    const SizedBox(height: 24),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: [
                        TextButton(
                          onPressed: downloading ? null : () => Navigator.of(ctx).pop(),
                          child: const Text("Cancel"),
                        ),
                        const SizedBox(width: 8),
                        FilledButton.icon(
                          icon: downloading
                              ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                              : const Icon(Icons.download_rounded, size: 18),
                          label: Text(downloading ? "Processing..." : "Download"),
                          onPressed: downloading ? null : () async {
                            setDialogState(() => downloading = true);
                            final options = <String, dynamic>{};
                            int? w;
                            int? h;
                            if (selectedSize == '150x150') { w = 150; h = 150; }
                            else if (selectedSize == 'avatar_256') {
                              w = 256; h = 256;
                              options['resizing_type'] = 'fill';
                              options['gravity'] = 'sm';
                            }
                            else if (selectedSize == '800x600') { w = 800; h = 600; }
                            else if (selectedSize == '1280x720') { w = 1280; h = 720; }

                            if (selectedShape == 'square') {
                              options['resizing_type'] = 'fill';
                              options['gravity'] = 'sm';
                              if (w != null && h == null) h = w;
                              else if (h != null && w == null) w = h;
                              else if (w == null && h == null) { w = 500; h = 500; }
                            } else if (selectedShape == '16:9') {
                              options['resizing_type'] = 'fill';
                              options['gravity'] = 'ce';
                              if (w == null && h == null) { w = 1280; h = 720; }
                            } else if (selectedShape == '4:3') {
                              options['resizing_type'] = 'fill';
                              options['gravity'] = 'ce';
                              if (w == null && h == null) { w = 800; h = 600; }
                            } else if (selectedShape == '9:16') {
                              options['resizing_type'] = 'fill';
                              options['gravity'] = 'sm';
                              if (w == null && h == null) { w = 720; h = 1280; }
                            } else if (w != null || h != null) {
                              options['resizing_type'] = 'fit';
                            }
                            if (w != null && w > 0) options['width'] = w;
                            if (h != null && h > 0) options['height'] = h;
                            if (selectedFormat != 'original') options['format'] = selectedFormat;

                            String? targetUrl;
                            if (options.isNotEmpty) {
                              targetUrl = await _getDownloadUrl(key, options);
                            }
                            targetUrl ??= defaultUrl;

                            final dotIdx = defaultFilename.lastIndexOf('.');
                            String nameWithoutExt = dotIdx > 0 ? defaultFilename.substring(0, dotIdx) : defaultFilename;
                            String ext = dotIdx > 0 ? defaultFilename.substring(dotIdx + 1) : 'jpg';
                            if (selectedFormat != 'original') ext = selectedFormat;
                            String dimSuffix = (w != null && h != null) ? '_${w}x${h}' : (w != null ? '_w$w' : (h != null ? '_h$h' : ''));
                            String shapeSuffix = selectedShape != 'fit' ? '_$selectedShape' : '';
                            final finalFilename = '$nameWithoutExt$dimSuffix$shapeSuffix.$ext';

                            ImagePickerHelper.downloadFile(targetUrl, finalFilename);
                            if (mounted) {
                              Navigator.of(ctx).pop();
                              ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Download started")));
                            }
                          },
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  void _showPhotoDialog(BuildContext context, String key, String? downloadUrl, String filename, [Map<String, dynamic>? photo]) {
    showDialog(
      context: context,
      builder: (ctx) => Dialog(
        backgroundColor: Colors.transparent,
        insetPadding: const EdgeInsets.all(16),
        child: Container(
          constraints: const BoxConstraints(maxWidth: 850, maxHeight: 750),
          decoration: BoxDecoration(
            color: Theme.of(context).cardColor,
            borderRadius: BorderRadius.circular(16),
            boxShadow: const [
              BoxShadow(
                color: Colors.black26,
                blurRadius: 16,
                offset: Offset(0, 4),
              ),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                child: Row(
                  children: [
                    const Icon(Icons.image_outlined, size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        filename,
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.close_rounded),
                      tooltip: 'Close',
                      onPressed: () => Navigator.of(ctx).pop(),
                    ),
                  ],
                ),
              ),
              const Divider(height: 1),
              Expanded(
                child: downloadUrl != null && downloadUrl.isNotEmpty
                    ? InteractiveViewer(
                        clipBehavior: Clip.antiAlias,
                        maxScale: 4.0,
                        child: Center(
                          child: Image.network(
                            downloadUrl,
                            fit: BoxFit.contain,
                            loadingBuilder: (_, child, progress) {
                              if (progress == null) return child;
                              return const Center(child: CircularProgressIndicator());
                            },
                            errorBuilder: (_, __, ___) => const Center(
                              child: Icon(Icons.broken_image_outlined, size: 48, color: Colors.grey),
                            ),
                          ),
                        ),
                      )
                    : const Center(
                        child: Text('Could not get image preview URL'),
                      ),
              ),
              const Divider(height: 1),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                child: Row(
                  children: [
                    const Spacer(),
                    if (downloadUrl != null && downloadUrl.isNotEmpty)
                      FilledButton.icon(
                        icon: const Icon(Icons.download_rounded, size: 18),
                        label: const Text('Download'),
                        onPressed: () => _showDownloadOptionsDialog(context, key, downloadUrl, filename),
                      ),
                    const SizedBox(width: 8),
                    TextButton(
                      child: const Text('Close'),
                      onPressed: () => Navigator.of(ctx).pop(),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _showFileDialog(BuildContext context, String key, String? downloadUrl, String filename, [Map<String, dynamic>? file]) {
    final ext = _getFileExtension(filename);
    final color = _fileColor(ext);
    final size = _formatFileSize(file?['size']);

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Row(
          children: [
            Icon(_fileIcon(ext), color: color),
            const SizedBox(width: 8),
            Expanded(child: Text(filename, style: const TextStyle(fontSize: 16), overflow: TextOverflow.ellipsis)),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Center(
              child: Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(color: color.withOpacity(0.12), shape: BoxShape.circle),
                child: Icon(_fileIcon(ext), size: 48, color: color),
              ),
            ),
            const SizedBox(height: 16),
            if (size.isNotEmpty) Text('Size: $size', style: const TextStyle(fontSize: 13)),
            const SizedBox(height: 4),
            Text('Bucket: $_selectedBucket', style: const TextStyle(fontSize: 13)),
            const SizedBox(height: 4),
            Text('Key: $key', style: const TextStyle(fontSize: 12, color: Colors.grey), overflow: TextOverflow.ellipsis),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text('Close')),
          FilledButton.icon(
            icon: const Icon(Icons.download_rounded, size: 18),
            label: const Text('Download'),
            style: FilledButton.styleFrom(backgroundColor: color),
            onPressed: () async {
              final url = downloadUrl ?? await _getDownloadUrl(key);
              if (url != null && url.isNotEmpty) {
                ImagePickerHelper.downloadFile(url, filename);
                if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Download started')));
              }
            },
          ),
        ],
      ),
    );
  }


  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: widget.showAppBar
          ? AppBar(
              title: const Text('File & Media Explorer'),
              actions: [
                IconButton(
                  icon: const Icon(Icons.refresh_rounded),
                  tooltip: 'Refresh',
                  onPressed: _fetchPhotos,
                ),
              ],
            )
          : null,
      body: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Wrap(
              spacing: 12,
              runSpacing: 12,
              crossAxisAlignment: WrapCrossAlignment.center,
              alignment: WrapAlignment.spaceBetween,
              children: [
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: Theme.of(context).primaryColor.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Icon(Icons.perm_media_rounded, color: Theme.of(context).primaryColor, size: 24),
                    ),
                    const SizedBox(width: 12),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'File & Media Explorer',
                          style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                        ),
                        Text(
                          _isLoading ? 'Loading...' : '${_filteredPhotos.length} items in "$_selectedBucket"',
                          style: TextStyle(fontSize: 13, color: Colors.grey[600]),
                        ),
                      ],
                    ),
                  ],
                ),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10),
                      decoration: BoxDecoration(
                        border: Border.all(color: Colors.grey.withOpacity(0.3)),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: DropdownButtonHideUnderline(
                        child: DropdownButton<String>(
                          value: _selectedBucket,
                          icon: const Icon(Icons.arrow_drop_down, size: 20),
                          items: _allowedBuckets.map((b) => DropdownMenuItem(
                            value: b,
                            child: Text(b, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500)),
                          )).toList(),
                          onChanged: (newBucket) {
                            if (newBucket != null && newBucket != _selectedBucket) {
                              setState(() => _selectedBucket = newBucket);
                              _fetchPhotos();
                            }
                          },
                        ),
                      ),
                    ),
                    SizedBox(
                      width: 180,
                      height: 40,
                      child: TextField(
                        controller: _prefixController,
                        style: const TextStyle(fontSize: 13),
                        decoration: InputDecoration(
                          hintText: 'Prefix (e.g. users/)',
                          hintStyle: TextStyle(fontSize: 12, color: Colors.grey[400]),
                          contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                          isDense: true,
                          suffixIcon: IconButton(
                            icon: const Icon(Icons.search, size: 18),
                            onPressed: _fetchPhotos,
                          ),
                        ),
                        onSubmitted: (_) => _fetchPhotos(),
                      ),
                    ),
                    IconButton.filledTonal(
                      icon: const Icon(Icons.refresh_rounded),
                      tooltip: 'Refresh',
                      onPressed: _fetchPhotos,
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              children: [
                ChoiceChip(
                  avatar: const Icon(Icons.apps_rounded, size: 16),
                  label: Text('All (${_photos.length})', style: const TextStyle(fontSize: 12)),
                  selected: _activeFilter == 'all',
                  onSelected: (_) => setState(() => _activeFilter = 'all'),
                ),
                ChoiceChip(
                  avatar: const Icon(Icons.image_outlined, size: 16),
                  label: Text('Images ($_imageCount)', style: const TextStyle(fontSize: 12)),
                  selected: _activeFilter == 'images',
                  onSelected: (_) => setState(() => _activeFilter = 'images'),
                ),
                ChoiceChip(
                  avatar: const Icon(Icons.insert_drive_file_outlined, size: 16),
                  label: Text('Files ($_fileCount)', style: const TextStyle(fontSize: 12)),
                  selected: _activeFilter == 'files',
                  onSelected: (_) => setState(() => _activeFilter = 'files'),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Expanded(
              child: _isLoading
                  ? const Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          CircularProgressIndicator(),
                          SizedBox(height: 16),
                          Text('Querying MinIO...', style: TextStyle(color: Colors.grey)),
                        ],
                      ),
                    )
                  : _errorMessage != null
                      ? Center(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(Icons.error_outline_rounded, size: 48, color: Colors.redAccent),
                              const SizedBox(height: 12),
                              Text(_errorMessage!, style: const TextStyle(color: Colors.grey)),
                              const SizedBox(height: 16),
                              FilledButton.icon(
                                icon: const Icon(Icons.refresh_rounded),
                                label: const Text('Retry'),
                                onPressed: _fetchPhotos,
                              ),
                            ],
                          ),
                        )
                      : _filteredPhotos.isEmpty
                          ? Center(
                              child: Column(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(Icons.folder_open_rounded, size: 64, color: Colors.grey[400]),
                                  const SizedBox(height: 12),
                                  Text(
                                    'No files found in "$_selectedBucket"',
                                    style: TextStyle(color: Colors.grey[600], fontSize: 16),
                                  ),
                                ],
                              ),
                            )
                          : GridView.builder(
                              gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                                maxCrossAxisExtent: 240,
                                crossAxisSpacing: 16,
                                mainAxisSpacing: 16,
                                childAspectRatio: 1.0,
                              ),
                              itemCount: _filteredPhotos.length,
                              itemBuilder: (context, index) {
                                final photo = _filteredPhotos[index];
                                final key = (photo['key'] ?? photo['image_id'] ?? photo['path'] ?? '').toString();
                                final filename = (photo['filename'] ?? key.split('/').last).toString();
                                final sizeStr = _formatFileSize(photo['size']);
                                final isImg = _isImage(filename.isNotEmpty ? filename : key);

                                return FutureBuilder<String?>(
                                  future: _resolveImageUrl(photo),
                                  builder: (context, snapshot) {
                                    final downloadUrl = snapshot.data;
                                    final ext = _getFileExtension(filename.isNotEmpty ? filename : key);
                                    final fileColor = _fileColor(ext);

                                      return Card(
                                        elevation: 2,
                                        clipBehavior: Clip.antiAlias,
                                        shape: RoundedRectangleBorder(
                                          borderRadius: BorderRadius.circular(12),
                                          side: BorderSide(color: Colors.grey.withOpacity(0.2)),
                                        ),
                                        child: InkWell(
                                          onTap: () => isImg
                                              ? _showPhotoDialog(context, key, downloadUrl, filename, photo)
                                              : _showFileDialog(context, key, downloadUrl, filename, photo),
                                          child: Stack(
                                            fit: StackFit.expand,
                                            children: [
                                              if (isImg)
                                                (downloadUrl != null && downloadUrl.isNotEmpty)
                                                    ? Image.network(
                                                        downloadUrl,
                                                        fit: BoxFit.cover,
                                                        errorBuilder: (_, __, ___) => const Center(child: Icon(Icons.broken_image_rounded, size: 36, color: Colors.grey)),
                                                      )
                                                    : const Center(child: Icon(Icons.image_not_supported_outlined, size: 36, color: Colors.grey))
                                              else
                                                Container(
                                                color: fileColor.withOpacity(0.08),
                                                child: Column(
                                                  mainAxisAlignment: MainAxisAlignment.center,
                                                  children: [
                                                    Container(
                                                      padding: const EdgeInsets.all(12),
                                                      decoration: BoxDecoration(
                                                        color: fileColor.withOpacity(0.15),
                                                        shape: BoxShape.circle,
                                                      ),
                                                      child: Icon(_fileIcon(ext), size: 40, color: fileColor),
                                                    ),
                                                    const SizedBox(height: 8),
                                                    Container(
                                                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                                      decoration: BoxDecoration(
                                                        color: fileColor,
                                                        borderRadius: BorderRadius.circular(6),
                                                      ),
                                                      child: Text(
                                                        ext,
                                                        style: const TextStyle(
                                                          color: Colors.white,
                                                          fontSize: 10,
                                                          fontWeight: FontWeight.bold,
                                                          letterSpacing: 0.5,
                                                        ),
                                                      ),
                                                    ),
                                                    const SizedBox(height: 28),
                                                  ],
                                                ),
                                              ),
                                              Positioned(
                                                bottom: 0,
                                                left: 0,
                                                right: 0,
                                                child: Container(
                                                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                                                  decoration: BoxDecoration(
                                                    gradient: LinearGradient(
                                                      begin: Alignment.bottomCenter,
                                                      end: Alignment.topCenter,
                                                      colors: [
                                                        Colors.black.withOpacity(0.8),
                                                        Colors.transparent,
                                                      ],
                                                    ),
                                                  ),
                                                  child: Row(
                                                    children: [
                                                      Expanded(
                                                        child: Column(
                                                          crossAxisAlignment: CrossAxisAlignment.start,
                                                          mainAxisSize: MainAxisSize.min,
                                                          children: [
                                                            Text(
                                                              filename,
                                                              style: const TextStyle(
                                                                color: Colors.white,
                                                                fontSize: 12,
                                                                fontWeight: FontWeight.w500,
                                                              ),
                                                              maxLines: 1,
                                                              overflow: TextOverflow.ellipsis,
                                                            ),
                                                            if (sizeStr.isNotEmpty)
                                                              Text(
                                                                sizeStr,
                                                                style: TextStyle(
                                                                  color: Colors.white.withOpacity(0.7),
                                                                  fontSize: 10,
                                                                ),
                                                              ),
                                                          ],
                                                        ),
                                                      ),
                                                      IconButton(
                                                        icon: const Icon(Icons.download_rounded, color: Colors.white, size: 18),
                                                        tooltip: 'Download',
                                                        padding: EdgeInsets.zero,
                                                        constraints: const BoxConstraints(),
                                                        onPressed: () async {
                                                          final url = downloadUrl ?? await _getDownloadUrl(key);
                                                          if (url != null && url.isNotEmpty) {
                                                            ImagePickerHelper.downloadFile(url, filename);
                                                            if (mounted) {
                                                              ScaffoldMessenger.of(context).showSnackBar(
                                                                const SnackBar(content: Text('Download started')),
                                                              );
                                                            }
                                                          }
                                                        },
                                                      ),
                                                    ],
                                                  ),
                                                ),
                                              ),
                                            ],
                                          ),
                                        ),
                                      );
                                  },
                                );
                              },
                            ),
            ),
          ],
        ),
      ),
    );
  }
}
"""

def backend_settings_screen_dart(app_name: str) -> str:
    return f"""import 'package:{app_name}/config/api.dart';
import 'package:{app_name}/screens/home.dart';
""" + """import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class BackendSettingsScreen extends StatefulWidget {
  final String? apiBaseUrl;
  final bool showAppBar;
  const BackendSettingsScreen({super.key, this.apiBaseUrl, this.showAppBar = true});

  @override
  State<BackendSettingsScreen> createState() => _BackendSettingsScreenState();
}

class _BackendSettingsScreenState extends State<BackendSettingsScreen> {
  bool _isAuthenticated = false;
  bool _isLoading = false;
  String _adminPassword = '';
  String _searchFilter = '';

  List<Map<String, dynamic>> _envVars = [];
  final Map<String, TextEditingController> _controllers = {};
  final Map<String, bool> _obscureMap = {};

  String get _activeBaseUrl => widget.apiBaseUrl ?? baseURL;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _showSudoVerificationDialog();
    });
  }

  @override
  void dispose() {
    for (var c in _controllers.values) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _showSudoVerificationDialog() async {
    final passwordController = TextEditingController();
    bool obscure = true;
    String? localError;

    final result = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              title: const Row(
                children: [
                  Icon(Icons.admin_panel_settings, color: Colors.blueAccent),
                  SizedBox(width: 10),
                  Text('Administrator Verification'),
                ],
              ),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'This action allows viewing and modifying critical backend environment variables. Please enter your administrator password to proceed.',
                    style: TextStyle(fontSize: 13, color: Colors.black87),
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: passwordController,
                    obscureText: obscure,
                    autofocus: true,
                    decoration: InputDecoration(
                      labelText: 'Administrator Password',
                      border: const OutlineInputBorder(),
                      errorText: localError,
                      prefixIcon: const Icon(Icons.lock_outline),
                      suffixIcon: IconButton(
                        icon: Icon(obscure ? Icons.visibility : Icons.visibility_off),
                        onPressed: () => setDialogState(() => obscure = !obscure),
                      ),
                    ),
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(ctx).pop(false),
                  child: const Text('Cancel'),
                ),
                ElevatedButton(
                  onPressed: () {
                    final pass = passwordController.text.trim();
                    if (pass.isEmpty) {
                      setDialogState(() {
                        localError = 'Password is required';
                      });
                      return;
                    }
                    _adminPassword = pass;
                    Navigator.of(ctx).pop(true);
                  },
                  child: const Text('Verify'),
                ),
              ],
            );
          },
        );
      },
    );

    if (result == true) {
      _fetchEnvironmentVariables();
    } else {
      if (mounted) {
        _goToHome();
      }
    }
  }

  void _goToHome() {
    Navigator.of(context).pushAndRemoveUntil(
      PageRouteBuilder(pageBuilder: (_, __, ___) => const Home()),
      (route) => false,
    );
  }

  Future<String?> _getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('token') ?? prefs.getString('access_token');
  }

  Future<void> _fetchEnvironmentVariables() async {
    setState(() => _isLoading = true);
    final token = await _getToken();

    try {
      final res = await http.get(
        Uri.parse('$_activeBaseUrl/admin/settings/env'),
        headers: {
          'Authorization': 'Bearer $token',
          'X-Admin-Password': _adminPassword,
        },
      );

      if (res.statusCode == 200) {
        final data = json.decode(res.body);
        final list = List<Map<String, dynamic>>.from(data['variables'] ?? []);

        setState(() {
          _isAuthenticated = true;
          _envVars = list;
          for (var item in list) {
            final key = item['key'] as String;
            final val = item['value']?.toString() ?? '';
            final isSecret = item['is_secret'] == true;
            _controllers[key] = TextEditingController(text: val);
            _obscureMap[key] = isSecret;
          }
        });
      } else {
        String errMsg = 'Verification failed';
        try {
          errMsg = json.decode(res.body)['detail'] ?? errMsg;
        } catch (_) {}
        _showErrorSnackBar(errMsg);
        _showSudoVerificationDialog();
      }
    } catch (e) {
      _showErrorSnackBar('Connection error: $e');
    } finally {
      setState(() => _isLoading = false);
    }
  }

  void _addVariable(String key, String defaultValue, bool isSecret) {
    if (_envVars.any((e) => e['key'] == key)) return;
    setState(() {
      _envVars.add({
        'key': key,
        'value': defaultValue,
        'is_secret': isSecret,
      });
      _controllers[key] = TextEditingController(text: defaultValue);
      _obscureMap[key] = isSecret;
    });
  }

  void _removeVariable(String key) {
    setState(() {
      _envVars.removeWhere((e) => e['key'] == key);
      _controllers[key]?.dispose();
      _controllers.remove(key);
      _obscureMap.remove(key);
    });
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Removed $key'), duration: const Duration(seconds: 1)),
    );
  }

  Future<void> _showAddVariableDialog() async {
    final keyController = TextEditingController();
    final valController = TextEditingController();
    bool isSecret = false;

    await showDialog(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              title: const Text('Add Environment Variable'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(
                    controller: keyController,
                    autofocus: true,
                    decoration: const InputDecoration(
                      labelText: 'Variable Name (e.g. CLOUDINARY_API_KEY)',
                      border: OutlineInputBorder(),
                    ),
                    textCapitalization: TextCapitalization.characters,
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: valController,
                    decoration: const InputDecoration(
                      labelText: 'Initial Value',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 8),
                  CheckboxListTile(
                    title: const Text('Is secret / sensitive?', style: TextStyle(fontSize: 14)),
                    value: isSecret,
                    onChanged: (v) => setDialogState(() => isSecret = v ?? false),
                    controlAffinity: ListTileControlAffinity.leading,
                    contentPadding: EdgeInsets.zero,
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(ctx).pop(),
                  child: const Text('Cancel'),
                ),
                ElevatedButton(
                  onPressed: () {
                    final k = keyController.text.trim().toUpperCase();
                    if (k.isNotEmpty) {
                      _addVariable(k, valController.text.trim(), isSecret);
                      Navigator.of(ctx).pop();
                    }
                  },
                  child: const Text('Add'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  Future<void> _saveEnvironmentVariables() async {
    setState(() => _isLoading = true);
    final token = await _getToken();

    final Map<String, String> payload = {};
    for (var entry in _controllers.entries) {
      payload[entry.key] = entry.value.text;
    }

    try {
      final res = await http.put(
        Uri.parse('$_activeBaseUrl/admin/settings/env'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
          'X-Admin-Password': _adminPassword,
        },
        body: json.encode({'variables': payload}),
      );

      if (res.statusCode == 200) {
        final data = json.decode(res.body);
        final bool restartRequired = data['requires_restart'] ?? false;

        if (mounted) {
          if (restartRequired) {
            showDialog(
              context: context,
              builder: (ctx) => AlertDialog(
                title: const Row(
                  children: [
                    Icon(Icons.warning_amber_rounded, color: Colors.orange),
                    SizedBox(width: 8),
                    Text('Restart Required'),
                  ],
                ),
                content: const Text(
                  'Environment variables saved successfully. Changes to port or database connection require a backend server restart to take effect.',
                ),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.of(ctx).pop(),
                    child: const Text('OK'),
                  ),
                ],
              ),
            );
          } else {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('Settings updated successfully'),
                backgroundColor: Colors.green,
              ),
            );
          }
        }
      } else {
        String errMsg = 'Save failed';
        try {
          errMsg = json.decode(res.body)['detail'] ?? errMsg;
        } catch (_) {}
        _showErrorSnackBar(errMsg);
      }
    } catch (e) {
      _showErrorSnackBar('Save error: $e');
    } finally {
      setState(() => _isLoading = false);
    }
  }

  void _showErrorSnackBar(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: Colors.red),
    );
  }

  @override
  Widget build(BuildContext context) {
    final filteredList = _envVars.where((item) {
      final key = (item['key'] as String).toLowerCase();
      return key.contains(_searchFilter.toLowerCase());
    }).toList();

    return Scaffold(
      appBar: widget.showAppBar
          ? AppBar(
              leading: IconButton(
                icon: const Icon(Icons.arrow_back),
                tooltip: 'Back to Home',
                onPressed: _goToHome,
              ),
              title: const Text('Backend Settings'),
              actions: [
                if (_isAuthenticated) ...[
                  IconButton(
                    icon: const Icon(Icons.add_box_outlined),
                    tooltip: 'Add Variable',
                    onPressed: _showAddVariableDialog,
                  ),
                  IconButton(
                    icon: const Icon(Icons.refresh_rounded),
                    tooltip: 'Refresh',
                    onPressed: _fetchEnvironmentVariables,
                  ),
                ],
              ],
            )
          : null,
      body: !_isAuthenticated
          ? Center(
              child: _isLoading
                  ? const CircularProgressIndicator()
                  : Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        ElevatedButton.icon(
                          onPressed: _showSudoVerificationDialog,
                          icon: const Icon(Icons.lock_open),
                          label: const Text('Unlock Settings'),
                        ),
                        const SizedBox(height: 12),
                        TextButton.icon(
                          onPressed: _goToHome,
                          icon: const Icon(Icons.arrow_back),
                          label: const Text('Back to Home'),
                        ),
                      ],
                    ),
            )
          : _isLoading
              ? const Center(child: CircularProgressIndicator())
              : Column(
                  children: [
                    Padding(
                      padding: const EdgeInsets.fromLTRB(12, 12, 12, 4),
                      child: TextField(
                        decoration: InputDecoration(
                          hintText: 'Search environment variable...',
                          prefixIcon: const Icon(Icons.search),
                          suffixIcon: IconButton(
                            icon: const Icon(Icons.add_circle, color: Colors.blueAccent),
                            tooltip: 'Add Variable',
                            onPressed: _showAddVariableDialog,
                          ),
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                          contentPadding: const EdgeInsets.symmetric(horizontal: 16),
                        ),
                        onChanged: (val) => setState(() => _searchFilter = val),
                      ),
                    ),
                    Expanded(
                      child: ListView.builder(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                        itemCount: filteredList.length,
                        itemBuilder: (context, index) {
                          final item = filteredList[index];
                          final key = item['key'] as String;
                          final isSecret = item['is_secret'] == true;
                          final isObscured = _obscureMap[key] ?? false;
                          final controller = _controllers[key];
                          final isStorageProvider = key == 'STORAGE_PROVIDER';

                          return Card(
                            margin: const EdgeInsets.only(bottom: 10),
                            elevation: isStorageProvider ? 3 : 1.5,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(8),
                              side: isStorageProvider
                                  ? const BorderSide(color: Colors.blueAccent, width: 1.5)
                                  : BorderSide.none,
                            ),
                            child: Padding(
                              padding: const EdgeInsets.all(12.0),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      Expanded(
                                        child: Text(
                                          key,
                                          style: TextStyle(
                                            fontWeight: FontWeight.bold,
                                            fontFamily: 'monospace',
                                            fontSize: 13,
                                            color: isStorageProvider
                                                ? Colors.blue.shade800
                                                : Colors.blueGrey,
                                          ),
                                        ),
                                      ),
                                      IconButton(
                                        icon: const Icon(Icons.copy, size: 16, color: Colors.grey),
                                        tooltip: 'Copy value',
                                        padding: EdgeInsets.zero,
                                        constraints: const BoxConstraints(),
                                        onPressed: () {
                                          if (controller != null) {
                                            Clipboard.setData(ClipboardData(text: controller.text));
                                            ScaffoldMessenger.of(context).showSnackBar(
                                              SnackBar(content: Text('Copied $key to clipboard')),
                                            );
                                          }
                                        },
                                      ),
                                      const SizedBox(width: 8),
                                      IconButton(
                                        icon: const Icon(Icons.delete_outline, size: 18, color: Colors.redAccent),
                                        tooltip: 'Remove $key',
                                        padding: EdgeInsets.zero,
                                        constraints: const BoxConstraints(),
                                        onPressed: () => _removeVariable(key),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 6),
                                  TextField(
                                    controller: controller,
                                    obscureText: isObscured,
                                    decoration: InputDecoration(
                                      isDense: true,
                                      border: const OutlineInputBorder(),
                                      suffixIcon: isSecret
                                          ? IconButton(
                                              icon: Icon(
                                                isObscured ? Icons.visibility : Icons.visibility_off,
                                                size: 20,
                                              ),
                                              onPressed: () {
                                                setState(() {
                                                  _obscureMap[key] = !isObscured;
                                                });
                                              },
                                            )
                                          : null,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          );
                        },
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.all(16),
                      width: double.infinity,
                      child: ElevatedButton.icon(
                        style: ElevatedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        ),
                        icon: const Icon(Icons.save),
                        label: const Text('Save Configuration', style: TextStyle(fontSize: 16)),
                        onPressed: _saveEnvironmentVariables,
                      ),
                    ),
                  ],
                ),
    );
  }
}
"""

def http_client(app_name: str) -> str:
    return f"""export 'package:http/http.dart'
    hide Client, get, post, put, delete, patch, head;

import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:{app_name}/config/api.dart';
import 'package:{app_name}/main.dart';
import 'package:{app_name}/models/user.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class Client extends http.BaseClient {{
  final http.Client _inner;

  Client([http.Client? inner]) : _inner = inner ?? http.Client();

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {{
    Uint8List? savedBody;
    if (request is http.Request) {{
      savedBody = request.bodyBytes;
    }}

    var streamedResponse = await _inner.send(request);
    var response = await http.Response.fromStream(streamedResponse);

    print('INTERCEPTOR: status code ${{response.statusCode}}');
    print('INTERCEPTOR: body ${{response.body}}');

    try {{
      final decoded = jsonDecode(response.body);
      if (decoded is Map && decoded.containsKey("refresh_token")) {{
        final refreshToken = decoded["refresh_token"];
        if (refreshToken is String && refreshToken.isNotEmpty) {{
          final prefs = await SharedPreferences.getInstance();
          await prefs.setString("refresh_token", refreshToken);
          print("Nuevo refresh_token guardado en SharedPreferences");
        }}
      }}
    }} catch (e) {{
      print("No se pudo parsear el body como JSON: $e");
    }}

    if (response.statusCode == 401 ||
        (_hasExpiredToken(response.body))) {{
      print("Interceptado 401 - intentando refresh token...");
      final newToken = await handle401();
      if (newToken != null) {{
        final cloned = await _cloneRequest(request, newToken, savedBody);
        streamedResponse = await _inner.send(cloned);
        response = await http.Response.fromStream(streamedResponse);
      }}
    }}

    final newStream =
        Stream<List<int>>.fromIterable([utf8.encode(response.body)]);
    return http.StreamedResponse(
      newStream,
      response.statusCode,
      headers: response.headers,
      request: streamedResponse.request,
      reasonPhrase: streamedResponse.reasonPhrase,
    );
  }}

  bool _hasExpiredToken(String body) {{
    try {{
      final decoded = jsonDecode(body);
      return decoded is Map && decoded['detail'] == "401: Token has expired";
    }} catch (_) {{
      return false;
    }}
  }}

  Future<http.BaseRequest> _cloneRequest(
    http.BaseRequest request,
    String newToken,
    Uint8List? savedBody,
  ) async {{
    final headers = Map<String, String>.from(request.headers);
    headers['Authorization'] = 'Bearer $newToken';

    if (request is http.Request) {{
      final newRequest = http.Request(request.method, request.url);
      newRequest.headers.addAll(headers);
      if (savedBody != null && savedBody.isNotEmpty) {{
        newRequest.bodyBytes = savedBody;
      }}
      return newRequest;
    }}

    if (request is http.MultipartRequest) {{
      final newRequest = http.MultipartRequest(request.method, request.url);
      newRequest.headers.addAll(headers);
      newRequest.fields.addAll(request.fields);
      newRequest.files.addAll(request.files);
      return newRequest;
    }}

    throw Exception(
        'Tipo de request no soportado: ${{request.runtimeType}}');
  }}
}}

Future<String?> handle401() async {{
  final prefs = await SharedPreferences.getInstance();
  final refreshToken = prefs.getString("refresh_token");

  if (refreshToken == null) {{
    print("No hay refresh token en SharedPreferences");
    await prefs.remove("token");
    await prefs.remove("refresh_token");

    navigatorKey.currentState?.pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const UserLoginWidget()),
      (route) => false,
    );
    return null;
  }}

  final response = await http.post(
    Uri.parse("$baseURL/auth/refresh/user/"),
    headers: {{"Content-Type": "application/json"}},
    body: jsonEncode({{"refresh_token": refreshToken}}),
  );

  if (response.statusCode == 200) {{
    final data = jsonDecode(response.body);
    final newAccessToken = data["token"];
    final newRefreshToken = data["refresh_token"];

    if (newAccessToken != null) {{
      await prefs.setString("token", newAccessToken);
    }}
    if (newRefreshToken != null) {{
      await prefs.setString("refresh_token", newRefreshToken);
    }}

    print("Token refrescado correctamente");
    return newAccessToken;
  }} else {{
    print("Fallo al refrescar token: ${{response.body}}");
    return null;
  }}
}}

final _defaultClient = Client();

// GET
Future<http.Response> get(Uri url, {{Map<String, String>? headers}}) =>
    _defaultClient.get(url, headers: headers);

// POST
Future<http.Response> post(Uri url,
        {{Map<String, String>? headers, Object? body, Encoding? encoding}}) =>
    _defaultClient.post(url, headers: headers, body: body, encoding: encoding);

// PUT
Future<http.Response> put(Uri url,
        {{Map<String, String>? headers, Object? body, Encoding? encoding}}) =>
    _defaultClient.put(url, headers: headers, body: body, encoding: encoding);

// DELETE
Future<http.Response> delete(Uri url,
        {{Map<String, String>? headers, Object? body, Encoding? encoding}}) =>
    _defaultClient.delete(url, headers: headers, body: body, encoding: encoding);

// PATCH
Future<http.Response> patch(Uri url,
        {{Map<String, String>? headers, Object? body, Encoding? encoding}}) =>
    _defaultClient.patch(url, headers: headers, body: body, encoding: encoding);

// HEAD
Future<http.Response> head(Uri url, {{Map<String, String>? headers}}) =>
    _defaultClient.head(url, headers: headers);
"""

def home_dart(app_name: str, models: List[OpenAPIModel], use_access_rights: bool):
    if use_access_rights:
      laia_import_statements = '\n'.join([f"import 'package:{app_name}/models/{model.__name__.lower()}.dart';" for model in [AccessRight, Role]])
    else:
      laia_import_statements = '\n'.join([f"import 'package:{app_name}/models/{model.__name__.lower()}.dart';" for model in [Role]])
    imports = []
    seen = set()

    for model in models:
        if not model.model_name.startswith("Body_") and not model.model_name.endswith("Update"):
            clean_name = model.model_name.replace('-Input', '').replace('-Output', '')
            if clean_name not in seen:
                seen.add(clean_name)
                imports.append(
                    f"import 'package:{app_name}/models/{clean_name.lower()}.dart';"
                )

    import_statements = '\n'.join(imports)
    return f"""import 'package:{app_name}/config/styles.dart';
import 'package:{app_name}/generic/nav_bar.dart';
import 'package:{app_name}/generic/generic_widgets.dart';
import 'package:{app_name}/screens/gallery_screen.dart';
import 'package:{app_name}/screens/backend_settings_screen.dart';
import 'package:laia_annotations/laia_annotations.dart';
{import_statements}
{laia_import_statements}
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';"""+"""

import 'package:flutter/material.dart';
part 'home.g.dart';

@homeWidget
class Home extends StatefulWidget {
  const Home({super.key});

  @override
  _HomeState createState() => _HomeState();
}

class _HomeState extends State<Home> {
  int _index = 2;

  final items = const [
    NavItem(icon: Icons.photo_library_rounded, label: 'Fotos'),
    NavItem(icon: Icons.fact_check_outlined, label: 'Tasks'),
    NavItem(icon: Icons.home_outlined, label: 'Home'),
    NavItem(icon: Icons.storage_outlined, label: 'Data'),
    NavItem(icon: Icons.add, label: 'Profile'),
  ];

  final demoSections = [
    TaskSection(
      status: TaskStatus.todo,
      items: [
        TaskItem(
          title: 'Review brand guidelines draft',
          dueDate: DateTime(2025, 1, 17),
          tag: 'Work',
          priority: TaskPriority.high,
        ),
        TaskItem(
          title: 'Prepare UI layout for the analytics dashboard',
          dueDate: DateTime(2025, 1, 23),
          tag: 'Work',
          priority: TaskPriority.mid,
        ),
        TaskItem(
          title: 'Prepare UI layout for the analytics dashboard',
          dueDate: DateTime(2025, 1, 18),
          tag: 'Work',
          priority: TaskPriority.low,
        ),
      ],
    ),
    TaskSection(
      status: TaskStatus.inProgress,
      items: [
        TaskItem(
          title: 'Refining mobile wireframes for user testing',
          dueDate: DateTime(2025, 1, 15),
          tag: 'Work',
          priority: TaskPriority.high,
        ),
        TaskItem(
          title: 'Implementing colour updates across the design system',
          dueDate: DateTime(2025, 1, 28),
          tag: 'Work',
          priority: TaskPriority.mid,
        ),
      ],
    ),
    TaskSection(
      status: TaskStatus.done,
      items: [
        TaskItem(
          title: 'Refining mobile wireframes for user testing',
          dueDate: DateTime(2025, 1, 5),
          tag: 'Work',
          priority: TaskPriority.done,
          checked: true,
        ),
        TaskItem(
          title: 'Implementing colour updates across the design system',
          dueDate: DateTime(2025, 1, 8),
          tag: 'Work',
          priority: TaskPriority.done,
          checked: true,
        ),
      ],
    ),
  ];

  final demoBoardTasks = <BoardTask>[
    // To Do
    BoardTask(
      title: 'Review brand guidelines draft',
      status: BoardStatus.todo,
      progress: 10,
      dueDate: DateTime(2025, 1, 17),
      tag: 'Work',
      priority: TaskPriority.high,
      comments: 1,
    ),
    BoardTask(
      title: 'Prepare UI layout for the analytics dashboard',
      status: BoardStatus.todo,
      progress: 30,
      dueDate: DateTime(2025, 1, 23),
      tag: 'Work',
      priority: TaskPriority.mid,
      comments: 0,
    ),
    BoardTask(
      title: 'Prepare UI layout for the analytics dashboard',
      status: BoardStatus.todo,
      progress: 50,
      dueDate: DateTime(2025, 1, 17),
      tag: 'Work',
      priority: TaskPriority.low,
      comments: 0,
    ),

    // In progress
    BoardTask(
      title: 'Refining mobile wireframes for user testing',
      status: BoardStatus.inProgress,
      progress: 50,
      dueDate: DateTime(2025, 1, 15),
      tag: 'Work',
      priority: TaskPriority.mid,
      comments: 5,
    ),
    BoardTask(
      title: 'Implementing colour updates across the design system',
      status: BoardStatus.inProgress,
      progress: 75,
      dueDate: DateTime(2025, 1, 28),
      tag: 'Work',
      priority: TaskPriority.low,
      comments: 2,
    ),

    // Done
    BoardTask(
      title: 'Refining mobile wireframes for user testing',
      status: BoardStatus.done,
      progress: 100,
      dueDate: DateTime(2025, 1, 5),
      tag: 'Work',
      priority: TaskPriority.low,
      comments: 2,
      checked: true,
    ),
    BoardTask(
      title: 'Implementing colour updates across the design system',
      status: BoardStatus.done,
      progress: 100,
      dueDate: DateTime(2025, 1, 8),
      tag: 'Work',
      priority: TaskPriority.low,
      comments: 0,
      checked: true,
    ),
  ];

  @override
  Widget build(BuildContext context) {

    return Scaffold(
      appBar: AppBar(
        automaticallyImplyLeading: false,
        surfaceTintColor: Colors.transparent,
        title: Image.asset('assets/logo_home.png', height: 20),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: ProfileMenuButton(
              avatarUrl: null, // o tu URL
              onViewProfile: () {
                // Navigator.push(...)
              },
              onSettings: () {
                // Navigator.push(...)
              },
              onLogout: () async{
                final prefs= await SharedPreferences.getInstance();
                await prefs.remove("token");
                await prefs.remove("refresh_token");
                Navigator.of(context).pushAndRemoveUntil(
                  MaterialPageRoute(builder: (_) => const UserLoginWidget()),
                  (route) => false,
                );
              },
            ),
          ),
        ],
      ),
      body: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          if (_index == 0)
          Expanded(
            child: const GalleryScreen(),
          ),
          if (_index == 1)
          Expanded(
            child: TasksWidget(sections: demoSections, boardTasks: demoBoardTasks)
          ),
          if (_index == 2)
          Expanded(
            child: AppCardsGrid(
              items: [
                AppCardItem(
                  title: 'Users',
                  icon: const Icon(Icons.people_alt_outlined),
                  onTap: () => Navigator.push(
                    context,
                    PageRouteBuilder(pageBuilder: (_, __, ___) => UserListView()),
                  ),
                ),
                AppCardItem(
                  title: 'Fotos',
                  icon: const Icon(Icons.photo_library_outlined),
                  onTap: () => Navigator.push(
                    context,
                    PageRouteBuilder(
                      pageBuilder: (_, __, ___) => const GalleryScreen(showAppBar: true),
                    ),
                  ),
                ),
                AppCardItem(
                  title: 'Calendar',
                  icon: const Icon(Icons.calendar_month_outlined),
                  onTap: () => debugPrint('Calendar'),
                ),
                AppCardItem(
                  title: 'Projects',
                  icon: const Icon(Icons.folder_open_outlined),
                  onTap: () => debugPrint('Projects'),
                ),
                AppCardItem(
                  title: 'Mailing',
                  icon: const Icon(Icons.mail_outline),
                  onTap: () => debugPrint('Mailing'),
                ),

                AppCardItem(
                  title: 'Tasks',
                  icon: const Icon(Icons.fact_check_outlined),
                  onTap: () => debugPrint('Tasks'),
                ),
                AppCardItem(
                  title: 'Analytics',
                  icon: const Icon(Icons.bar_chart_outlined),
                  onTap: () => debugPrint('Analytics'),
                ),
                AppCardItem(
                  title: 'Data Sources',
                  icon: const Icon(Icons.storage_outlined),
                  onTap: () => setState(() => _index = 3),
                ),
                AppCardItem(
                  title: 'Finance',
                  icon: const Icon(Icons.attach_money_outlined),
                  onTap: () => debugPrint('Finance'),
                ),

                AppCardItem(
                  title: 'AI',
                  icon: const Icon(Icons.auto_awesome_outlined),
                  onTap: () => debugPrint('AI'),
                ),
                AppCardItem(
                  title: 'Chat',
                  icon: const Icon(Icons.chat_bubble_outline),
                  onTap: () => debugPrint('Chat'),
                ),
                AppCardItem(
                  title: 'Dashboard',
                  icon: const Icon(Icons.dashboard_outlined),
                  onTap: () => debugPrint('Dashboard'),
                ),
                AppCardItem(
                  title: 'Reports',
                  icon: const Icon(Icons.description_outlined),
                  onTap: () => debugPrint('Reports'),
                ),

                AppCardItem(
                  title: 'Settings',
                  icon: const Icon(Icons.settings_outlined),
                  onTap: () => Navigator.push(
                    context,
                    PageRouteBuilder(pageBuilder: (_, __, ___) => const BackendSettingsScreen()),
                  ),
                ),
                AppCardItem(
                  title: 'Invoice',
                  icon: const Icon(Icons.receipt_long_outlined),
                  onTap: () => debugPrint('Invoice'),
                ),
                AppCardItem(
                  title: 'Workflow',
                  icon: const Icon(Icons.alt_route_outlined),
                  onTap: () => debugPrint('Workflow'),
                ),
                AppCardItem(
                  title: 'Add',
                  icon: const Icon(Icons.add),
                  onTap: () => debugPrint('Add'),
                ),
              ],
            )
          ),
          if (_index == 3)
          Expanded(
            child: dashboardWidget(context)
          ),
          if (_index == 4)
          Expanded(
            child: Text('Profile View', style: Theme.of(context).textTheme.headlineMedium),
          ),
        ],
      ),
      bottomNavigationBar: LaiaBottomNavBar(items: items, currentIndex: _index, onTap: (i) => setState(() => _index = i))
    );
  }
}
"""

def get_all_sub_dependencies(model_cls, seen_classes=None):
    if seen_classes is None:
        seen_classes = set()
    if not isinstance(model_cls, type):
        return set()
    if isinstance(model_cls, EnumMeta):
        return set()
    if model_cls in seen_classes:
        return set()
    seen_classes.add(model_cls)
    
    dependencies = set()
    annotations = get_inherited_field_annotations(model_cls)
    model_module = sys.modules.get(model_cls.__module__)
    
    for field_name, field_type in annotations.items():
        ref_cls_name = embedded_class_name_from_annotation(field_type)
        if ref_cls_name:
            ref_cls = getattr(model_module, ref_cls_name, None) if model_module else None
            if ref_cls:
                is_pydantic_model = isinstance(ref_cls, type) and issubclass(ref_cls, BaseModel)
                is_enum = isinstance(ref_cls, EnumMeta)
                if is_pydantic_model or is_enum:
                    dependencies.add(ref_cls)
                    if is_pydantic_model:
                        dependencies.update(get_all_sub_dependencies(ref_cls, seen_classes))
    return dependencies

def model_dart(openapiModel: OpenAPIModel=None, app_name: str="", model: Type[BaseModel]=None):
    fields = ""
    fields_constructor = ""
    extra_imports = ""
    inherited_fields = get_inherited_fields(model)
    inherited_field_annotations = get_inherited_field_annotations(model)

    if isinstance(model, EnumMeta):
      print(f"[LAIA Flutter enum] generating standalone enum {model.__name__} -> {model.__name__.lower()}.dart")
      return enum_dart(model, include_import=True)

    # Collect transitive sub-dependencies
    try:
        sub_deps = get_all_sub_dependencies(model)
        for dep in sub_deps:
            if dep == model:
                continue
            dep_name = dep.__name__
            dep_name_clean = dep_name.replace('-Input', '').replace('-Output', '')
            ignored_imports = {
                'type', 'objectid', 'point', 'polygon', 'linestring', 'multipoint',
                'multilinestring', 'multipolygon', 'geometry', 'feature',
                'geometrypoint', 'geometrypolygon', 'geometrylinestring',
                'geometrymultipoint', 'geometrymultilinestring', 'geometrymultipolygon'
            }
            if dep_name_clean.lower() not in ignored_imports:
                imp = f"import 'package:{app_name}/models/{dep_name_clean.lower()}.dart';\n"
                if imp not in extra_imports:
                    extra_imports += imp
    except Exception as e:
        print(f"[LAIA error collecting sub-dependencies] {e}")
    
    if openapiModel:
      frontend_props = openapiModel.get_frontend_properties()
      try:
        raw_fields = openapiModel.extensions['x-frontend-defaultFields']
        filtered_fields = [f for f in raw_fields if str(f).lower() != 'password']
        defaultFields = "defaultFields: " + str(filtered_fields) + ", "
      except KeyError:
        defaultFields = ""
      try:
        raw_detail = openapiModel.extensions['x-frontend-defaultFieldsDetail']
        filtered_detail = [row for row in raw_detail if not any(isinstance(val, str) and val.lower() == 'password' for val in row)]
        defaultFieldsDetail = "defaultFieldsDetail: " + str(filtered_detail) + ", "
      except KeyError:
        defaultFieldsDetail = ""
      try:
        widgetDistributionDetail = "widgetDistributionDetail: " + str(openapiModel.extensions['x-frontend-widgetDistributionDetail']) + ", "
      except KeyError:
        widgetDistributionDetail = ""
      try:
        pageSize = "pageSize: " + str(openapiModel.extensions['x-frontend-pageSize']) + ", "
      except KeyError:
        pageSize = ""
      try:
        widget = "widget: '" + str(openapiModel.extensions['x-frontend-widget']) + "', "
      except KeyError:
        widget = ""
      try:
        raw_tabs = openapiModel.extensions.get('x-frontend-tabs')
        if raw_tabs:
            tab_elements = []
            for tab in raw_tabs:
                label = tab.get('label', '')
                raw_fields_list = tab.get('fields', [])
                fields_dart_parts = []
                flattened_fields = []
                for item in raw_fields_list:
                    if isinstance(item, list):
                        row_cols = [str(x) for x in item]
                        flattened_fields.extend(row_cols)
                        cols_str = ", ".join([f'"{c}"' for c in row_cols])
                        fields_dart_parts.append(f'[{cols_str}]')
                    elif isinstance(item, str):
                        flattened_fields.append(item)
                        fields_dart_parts.append(f'"{item}"')
                fields_str = ", ".join(fields_dart_parts)
                relation = tab.get('relation', '')
                inverse_relation_field = tab.get('inverseRelationField', '')

                if flattened_fields:
                    for f in flattened_fields:
                        prop_info = openapiModel.properties.get(f, {})
                        nicename = (
                            prop_info.get('x_frontend_nicename')
                        )
                        if nicename and (not label or label.lower() == f.lower()):
                            label = nicename
                            break
                if relation and not label:
                    for prop_n, prop_d in openapiModel.properties.items():
                        if prop_d.get('x_frontend_relation') == relation:
                            label = (
                                prop_d.get('x_frontend_nicename')
                                or label
                            )
                            break
                    if not label:
                        label = relation
                if isinstance(inverse_relation_field, list):
                    inverse_relation_field = ", ".join([str(x) for x in inverse_relation_field])
                filters = tab.get('filters') or tab.get('extraFilters')
                
                parts = [f'label: "{label}"']
                if fields_dart_parts:
                    parts.append(f'fields: [{fields_str}]')
                if relation:
                    parts.append(f'relation: "{relation}"')
                    imp = f"import 'package:{app_name}/models/{relation.lower()}.dart';\n"
                    if imp not in extra_imports:
                        extra_imports += imp
                if inverse_relation_field:
                    parts.append(f'inverseRelationField: "{inverse_relation_field}"')
                if filters and isinstance(filters, dict):
                    def _to_dart_val(val):
                        if isinstance(val, bool):
                            return "true" if val else "false"
                        elif isinstance(val, (int, float)):
                            return str(val)
                        elif isinstance(val, str):
                            return f'"{val}"'
                        elif isinstance(val, list):
                            return f"[{', '.join(_to_dart_val(x) for x in val)}]"
                        elif isinstance(val, dict):
                            entries = [f'"{k}": {_to_dart_val(v)}' for k, v in val.items()]
                            return f"{{{', '.join(entries)}}}"
                        return f'"{val}"'
                    filter_entries = [f'"{k}": {_to_dart_val(v)}' for k, v in filters.items()]
                    filters_str = f"{{{', '.join(filter_entries)}}}"
                    parts.append(f'filters: {filters_str}')
                
                tab_elements.append(f'ElementTab({", ".join(parts)})')
            tabs_str = "tabs: [" + ", ".join(tab_elements) + "], "
        else:
            tabs_str = ""
      except Exception as e:
        print(f"[LAIA error parsing x-frontend-tabs] {e}")
        tabs_str = ""
      try:
        raw_format = openapiModel.extensions.get('x_frontend_format')
        format = f"format: '{raw_format}', "
      except Exception as e:
        print(f"[LAIA error parsing x-frontend-format] {e}")
        format = ""
    else:
      frontend_props = {}
      defaultFields = ""
      defaultFieldsDetail = ""
      widgetDistributionDetail = ""
      pageSize = ""
      widget = ""
      tabs_str = ""
    
    for prop_name, prop_type in inherited_fields:
      dart_prop_type = pydantic_to_dart_type(prop_type)
      
      # Determine if the field is excluded from response (needs to be optional in Dart)
      model_config = getattr(model, "model_config", {}) or {}
      json_schema_extra = model_config.get("json_schema_extra", {}) or {}
      excluded_fields = json_schema_extra.get("x-exclude-from-response", []) if isinstance(json_schema_extra, dict) else []
      is_excluded = prop_name in excluded_fields
      if openapiModel:
        prop_yaml = openapiModel.properties.get(prop_name, {})
        if isinstance(prop_yaml, dict) and (prop_yaml.get('x-exclude-from-response') or prop_yaml.get('x_exclude_from_response')):
          is_excluded = True
      
      if is_excluded:
        if not dart_prop_type.endswith('?'):
          dart_prop_type = f"{dart_prop_type}?"
          
      raw_annotation = inherited_field_annotations.get(prop_name)
      enum_cls = enum_class_from_annotation(raw_annotation, model)
      print(
        "[LAIA Flutter model field] "
        f"model={model.__name__} field={prop_name} "
        f"flattened_type={prop_type} dart_type={dart_prop_type} "
        f"raw_annotation={raw_annotation!r} enum={enum_cls.__name__ if enum_cls else None}"
      )
      if enum_cls:
        dart_prop_type = embedded_dart_type(prop_type, enum_cls.__name__)
        imp = f"import 'package:{app_name}/models/{enum_cls.__name__.lower()}.dart';\n"
        if imp not in extra_imports:
          print(f"[LAIA Flutter enum import] {model.__name__}.{prop_name} -> {imp.strip()}")
          extra_imports += imp
      schema_format = None
      if openapiModel:
        prop_yaml_fmt = openapiModel.properties.get(prop_name, {})
        if isinstance(prop_yaml_fmt, dict):
          schema_format = prop_yaml_fmt.get('format')
          if not schema_format and 'anyOf' in prop_yaml_fmt:
            for variant in prop_yaml_fmt['anyOf']:
              if isinstance(variant, dict) and 'format' in variant:
                schema_format = variant['format']
                break

      fields += f"  @Field("
      
      if prop_name in frontend_props:
        frontend_details = frontend_props[prop_name]
        relation = frontend_details.get('relation')
        if relation:
          is_list = 'List[' in str(prop_type) or 'list[' in str(prop_type)
          is_optional = 'Optional[' in str(prop_type) or 'None' in str(prop_type)
          if is_list:
            frontend_details['widget'] = f"{relation}MultiFieldWidget"
            dart_prop_type = 'List<dynamic>?' if is_optional else 'List<dynamic>'
          else:
            frontend_details['widget'] = f"{relation}FieldWidget"
            dart_prop_type = 'dynamic?' if is_optional else 'dynamic'
        if schema_format and 'format' not in frontend_details:
          frontend_details['format'] = schema_format
        for key, value in frontend_details.items():
          if isinstance(value, bool):
            fields += f"{key}: {str(value).lower()}, "
          else:
            fields += f'{key}: "{value}", '
        fields = fields[:-2]
        value_lower = next((value.lower() for key, value in frontend_details.items() if key == "relation"), None)
        if value_lower:
          extra_imports += f"import 'package:{app_name}/models/{value_lower}.dart';\n"
      else:
        if schema_format:
          fields += "fieldName: '{}', format: '{}'".format(prop_name, schema_format)
        else:
          fields += "fieldName: '{}'".format(prop_name)

      if openapiModel:
        prop_yaml = openapiModel.properties.get(prop_name, {})
        ref_cls_name = schema_ref_class_name(prop_yaml)
        ignored_imports = {
            'type', 'objectid', 'point', 'polygon', 'linestring', 'multipoint',
            'multilinestring', 'multipolygon', 'geometry', 'feature',
            'geometrypoint', 'geometrypolygon', 'geometrylinestring',
            'geometrymultipoint', 'geometrymultilinestring', 'geometrymultipolygon'
        }
        if ref_cls_name:
          dart_prop_type = embedded_dart_type(prop_type, ref_cls_name)
          if ref_cls_name.lower() not in ignored_imports:
            imp = f"import 'package:{app_name}/models/{ref_cls_name.lower()}.dart';\n"
            if imp not in extra_imports:
              print(f"[LAIA Flutter schema ref import] {model.__name__}.{prop_name} -> {imp.strip()}")
              extra_imports += imp
        elif isinstance(prop_yaml, dict) and 'enum' in prop_yaml:
          cls_name = embedded_class_name_from_type(prop_type)
          if cls_name:
            dart_prop_type = embedded_dart_type(prop_type, cls_name)
            if cls_name.lower() not in ignored_imports:
              imp = f"import 'package:{app_name}/models/{cls_name.lower()}.dart';\n"
              if imp not in extra_imports:
                print(f"[LAIA Flutter enum import from schema] {model.__name__}.{prop_name} -> {imp.strip()}")
                extra_imports += imp
        if isinstance(prop_yaml, dict) and (prop_yaml.get('x_embedded') or prop_yaml.get('x-embedded')):
          cls_name = embedded_class_name_from_type(prop_type) or embedded_class_name_from_annotation(raw_annotation)
          if cls_name:
            dart_prop_type = embedded_dart_type(prop_type, cls_name)
            if cls_name.lower() not in ignored_imports:
              imp = f"import 'package:{app_name}/models/{cls_name.lower()}.dart';\n"
              if imp not in extra_imports:
                print(f"[LAIA Flutter embedded import] {model.__name__}.{prop_name} -> {imp.strip()}")
                extra_imports += imp

      fields += ")\n"
      fields += f"  final {dart_prop_type} {prop_name};\n"
      if '?' in dart_prop_type:
        fields_constructor += f"    this.{prop_name},\n"
      else:
        fields_constructor += f"    required this.{prop_name},\n"

    if fields_constructor:
      fields_constructor = fields_constructor[:-2]
    
    model_name = model.__name__
    auth = 'false'
    if openapiModel:
      if openapiModel.extensions.get('x-auth'):
        auth = 'true'
        extra_imports += f"import 'package:shared_preferences/shared_preferences.dart';\n"
        extra_imports += f"import 'package:package_info_plus/package_info_plus.dart';\n"

    return f"""import 'package:{app_name}/models/geometry.dart';
import 'package:laia_annotations/laia_annotations.dart';
import 'package:{app_name}/theme/auth_scaffold.dart';
import 'package:{app_name}/theme/theme_app.dart';
import 'package:{app_name}/screens/home.dart';
import 'package:flutter/material.dart';
import 'package:json_annotation/json_annotation.dart';
import 'package:copy_with_extension/copy_with_extension.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:tuple/tuple.dart';
import 'package:{app_name}/config/api.dart';
import 'package:{app_name}/generic/generic_widgets.dart';
import 'package:{app_name}/config/http_client.dart' as http;
import 'package:{app_name}/config/styles.dart';
import 'dart:convert';
import 'dart:typed_data';
import 'package:collection/collection.dart';
import 'package:flutter_typeahead/flutter_typeahead.dart';
{extra_imports}
part '{model_name.lower()}.g.dart';

@JsonSerializable()
@RiverpodGenAnnotation(auth: {auth})
@HomeWidgetElementGenAnnotation()
@ListWidgetGenAnnotation({defaultFields}{pageSize}{widget})
@ElementWidgetGen({defaultFieldsDetail}{widgetDistributionDetail}{tabs_str}auth: {auth})
@CopyWith()
class {model_name} {{
{fields}
  {model_name}({{
{fields_constructor}
  }});

  factory {model_name}.fromJson(Map<String, dynamic> json) => _${model_name}FromJson(json);

  Map<String, dynamic> toJson() => _${model_name}ToJson(this);
}}
"""

def geojson_models_file():
   return """// ignore_for_file: overridden_fields
   
import 'package:json_annotation/json_annotation.dart';
import 'package:copy_with_extension/copy_with_extension.dart';

part 'geometry.g.dart';

@JsonSerializable()
@CopyWith()
class Geometry {
  final String type;
  final dynamic coordinates;

  Geometry({
    required this.type,
    required this.coordinates,
  });

  factory Geometry.fromJson(Map<String, dynamic> json) => _$GeometryFromJson(json);

  Map<String, dynamic> toJson() => _$GeometryToJson(this);
}


@JsonSerializable()
@CopyWith()
class Feature {
  final String type;
  final dynamic properties;
  final dynamic geometry;

  Feature({
    required this.type,
    this.properties,
    required this.geometry
  });

  factory Feature.fromJson(Map<String, dynamic> json) => _$FeatureFromJson(json);

  Map<String, dynamic> toJson() => _$FeatureToJson(this);
}

@JsonSerializable()
@CopyWith()
class GeometryLineString extends Geometry{
  @override
  final List<List<double>> coordinates;

  GeometryLineString({
    required String type,
    required this.coordinates,
  }): super(type: type, coordinates: coordinates);

  factory GeometryLineString.fromJson(Map<String, dynamic> json) => _$GeometryLineStringFromJson(json);

  Map<String, dynamic> toJson() => _$GeometryLineStringToJson(this);
}

@JsonSerializable()
@CopyWith()
class LineString extends Feature {

  LineString({
    required String type,
    dynamic properties,
    required GeometryLineString geometry,
  }) : 
    super(type: type, properties: properties, geometry: geometry);

  factory LineString.fromJson(Map<String, dynamic> json) => _$LineStringFromJson(json);

  Map<String, dynamic> toJson() => _$LineStringToJson(this);
}

@JsonSerializable()
@CopyWith()
class GeometryMultiLineString extends Geometry {
  @override
  final List<List<List<double>>> coordinates;

  GeometryMultiLineString({
    required String type,
    required this.coordinates,
  }): super(type: type, coordinates: coordinates);

  factory GeometryMultiLineString.fromJson(Map<String, dynamic> json) => _$GeometryMultiLineStringFromJson(json);

  Map<String, dynamic> toJson() => _$GeometryMultiLineStringToJson(this);
}

@JsonSerializable()
@CopyWith()
class MultiLineString extends Feature {

  MultiLineString({
    required String type,
    dynamic properties,
    required GeometryMultiLineString geometry,
  }) : 
    super(type: type, properties: properties, geometry: geometry);

  factory MultiLineString.fromJson(Map<String, dynamic> json) => _$MultiLineStringFromJson(json);

  Map<String, dynamic> toJson() => _$MultiLineStringToJson(this);
}

@JsonSerializable()
@CopyWith()
class GeometryMultiPoint extends Geometry {
  @override
  final List<List<double>> coordinates;

  GeometryMultiPoint({
    required String type,
    required this.coordinates,
  }): super(type: type, coordinates: coordinates);

  factory GeometryMultiPoint.fromJson(Map<String, dynamic> json) => _$GeometryMultiPointFromJson(json);

  Map<String, dynamic> toJson() => _$GeometryMultiPointToJson(this);
}

@JsonSerializable()
@CopyWith()
class MultiPoint extends Feature {

  MultiPoint({
    required String type,
    dynamic properties,
    required GeometryMultiPoint geometry,
  }) : 
    super(type: type, properties: properties, geometry: geometry);

  factory MultiPoint.fromJson(Map<String, dynamic> json) => _$MultiPointFromJson(json);

  Map<String, dynamic> toJson() => _$MultiPointToJson(this);
}

@JsonSerializable()
@CopyWith()
class GeometryMultiPolygon extends Geometry{
  @override
  final List<List<List<List<double>>>> coordinates;

  GeometryMultiPolygon({
    required String type,
    required this.coordinates,
  }): super(type: type, coordinates: coordinates);

  factory GeometryMultiPolygon.fromJson(Map<String, dynamic> json) => _$GeometryMultiPolygonFromJson(json);

  Map<String, dynamic> toJson() => _$GeometryMultiPolygonToJson(this);
}

@JsonSerializable()
@CopyWith()
class MultiPolygon extends Feature {

  MultiPolygon({
    required String type,
    dynamic properties,
    required GeometryMultiPolygon geometry,
  }) : 
    super(type: type, properties: properties, geometry: geometry);

  factory MultiPolygon.fromJson(Map<String, dynamic> json) => _$MultiPolygonFromJson(json);

  Map<String, dynamic> toJson() => _$MultiPolygonToJson(this);
}

@JsonSerializable()
@CopyWith()
class GeometryPoint extends Geometry{
  @override
  final List<double> coordinates;

  GeometryPoint({
    required String type,
    required this.coordinates,
  }): super(type: type, coordinates: coordinates);

  factory GeometryPoint.fromJson(Map<String, dynamic> json) => _$GeometryPointFromJson(json);

  Map<String, dynamic> toJson() => _$GeometryPointToJson(this);
}

@JsonSerializable()
@CopyWith()
class Point extends Feature {

  Point({
    required String type,
    dynamic properties,
    required GeometryPoint geometry,
  }) : 
    super(type: type, properties: properties, geometry: geometry);

  factory Point.fromJson(Map<String, dynamic> json) => _$PointFromJson(json);

  Map<String, dynamic> toJson() => _$PointToJson(this);
}

@JsonSerializable()
@CopyWith()
class GeometryPolygon extends Geometry{
  @override
  final List<List<List<double>>> coordinates;

  GeometryPolygon({
    required String type,
    required this.coordinates,
  }): super(type: type, coordinates: coordinates);

  factory GeometryPolygon.fromJson(Map<String, dynamic> json) => _$GeometryPolygonFromJson(json);

  Map<String, dynamic> toJson() => _$GeometryPolygonToJson(this);
}


@JsonSerializable()
@CopyWith()
class Polygon extends Feature {

  Polygon({
    required String type,
    dynamic properties,
    required GeometryPolygon geometry,
  }) : 
    super(type: type, properties: properties, geometry: geometry);

  factory Polygon.fromJson(Map<String, dynamic> json) => _$PolygonFromJson(json);

  Map<String, dynamic> toJson() => _$PolygonToJson(this);
}
"""

def pydantic_to_dart_type(pydantic_type: str):
    dart_type_mapping = {
        'int': 'int',
        'float': 'double',
        'str': 'String',
        'bool': 'bool',
        'datetime': 'DateTime',
        'date': 'DateTime',
        'list': 'List<dynamic>',
        'List': 'List<dynamic>',
        'List[int]': 'List<int>',
        'List[str]': 'List<String>',
        'List[float]': 'List<double>',
        'List[bool]': 'List<bool>',
        'EmailStr': 'String',
        'Dict[str, Any]': 'Map<String, dynamic>',
        'List[Dict[str, Any]]': 'List<Map<String, dynamic>>',
        'LineString': 'LineString',
        'MultiLineString': 'MultiLineString',
        'MultiPoint': 'MultiPoint',
        'MultiPolygon': 'MultiPolygon',
        'Point': 'Point',
        'Polygon': 'Polygon',
        'Optional[int]': 'int?',
        'Optional[str]': 'String?',
        'Optional[bool]': 'bool?',
        'Optional[EmailStr]': 'String?',
        'Optional[float]': 'double?',
        'Optional[datetime]': 'DateTime?',
        'Optional[date]': 'DateTime?',
        'Optional[List]': 'List<dynamic>?',
        'Optional[List[int]]': 'List<int>?',
        'Optional[List[str]]': 'List<String>?',
        'Optional[List[float]]': 'List<double>?',
        'Optional[List[bool]]': 'List<bool>?',
        'Optional[Dict[str, Any]]': 'Map<String, dynamic>?',
        'Optional[List[Dict[str, Any]]]': 'List<Map<String, dynamic>>?',
        'Optional[LineString]': 'LineString?',
        'Optional[MultiLineString]': 'MultiLineString?',
        'Optional[MultiPoint]': 'MultiPoint?',
        'Optional[MultiPolygon]': 'MultiPolygon?',
        'Optional[Point]': 'Point?',
        'Optional[Polygon]': 'Polygon?',
    }

    dart_type = "dynamic?"

    if pydantic_type in dart_type_mapping:
        dart_type = dart_type_mapping[pydantic_type]
    elif hasattr(pydantic_type, "__origin__") and pydantic_type.__origin__ == list:
        inner_type = pydantic_to_dart_type(pydantic_type.__args__[0])
        dart_type = f'List<{inner_type}>'
    else:
        m = re.match(r'^Optional\[List\[(\w+)\]\]$', str(pydantic_type))
        if m:
            dart_type = f'List<{m.group(1)}>?'
        else:
            m = re.match(r'^List\[(\w+)\]$', str(pydantic_type))
            if m:
                dart_type = f'List<{m.group(1)}>'
            else:
                m = re.match(r'^Optional\[(\w+)\]$', str(pydantic_type))
                if m:
                    dart_type = f'{m.group(1)}?'

    return dart_type

def embedded_class_name_from_type(type_str: str):
    primitives = {'str', 'int', 'float', 'bool', 'Any', 'Dict', 'datetime', 'date'}
    type_str = str(type_str).strip().strip("'\"")
    cls_match = (
        re.match(r'Optional\[(?:List|list)\[(\w+)\]\]', type_str) or
        re.match(r'(?:List|list)\[(\w+)\]', type_str) or
        re.match(r'Optional\[(\w+)\]', type_str) or
        re.match(r'^(\w+)$', type_str)
    )
    if not cls_match:
        return None

    cls_name = cls_match.group(1)
    return None if cls_name in primitives else cls_name


def embedded_class_name_from_annotation(annotation):
    if annotation is None:
        return None

    if isinstance(annotation, str):
        return embedded_class_name_from_type(annotation)

    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is Annotated:
        return embedded_class_name_from_annotation(args[0]) if args else None

    if origin is list or origin is List:
        return embedded_class_name_from_annotation(args[0]) if args else None

    if origin is Union and type(None) in args:
        non_none = [arg for arg in args if arg is not type(None)]
        return embedded_class_name_from_annotation(non_none[0]) if non_none else None

    cls_name = getattr(annotation, "__name__", None)
    if cls_name:
        return embedded_class_name_from_type(cls_name)

    return embedded_class_name_from_type(str(annotation))


def embedded_dart_type(type_str: str, cls_name: str):
    type_str = str(type_str).strip().strip("'\"")
    if re.match(r'Optional\[(?:List|list)\[\w+\]\]', type_str) or (
        'Optional' in type_str and ('List[' in type_str or 'list[' in type_str)
    ):
        return f'List<{cls_name}>?'
    if re.match(r'(?:List|list)\[\w+\]', type_str) or 'List[' in type_str or 'list[' in type_str:
        return f'List<{cls_name}>'
    if re.match(r'Optional\[\w+\]', type_str) or 'Optional' in type_str or 'NoneType' in type_str:
        return f'{cls_name}?'
    return cls_name


def schema_ref_class_name(prop_definition):
    if not isinstance(prop_definition, dict):
        return None

    ref = prop_definition.get('$ref')
    if isinstance(ref, str) and ref.startswith('#/components/schemas/'):
        return ref.rsplit('/', 1)[-1]

    items_ref = schema_ref_class_name(prop_definition.get('items'))
    if items_ref:
        return items_ref

    for key in ('anyOf', 'oneOf', 'allOf'):
        for option in prop_definition.get(key, []):
            option_ref = schema_ref_class_name(option)
            if option_ref:
                return option_ref

    return None

def dart_string_literal(value) -> str:
    return str(value).replace("\\", "\\\\").replace("'", "\\'")


def dart_enum_member_name(name: str) -> str:
    keywords = {
        'abstract', 'as', 'assert', 'async', 'await', 'base', 'break', 'case',
        'catch', 'class', 'const', 'continue', 'covariant', 'default',
        'deferred', 'do', 'dynamic', 'else', 'enum', 'export', 'extends',
        'extension', 'external', 'factory', 'false', 'final', 'finally', 'for',
        'function', 'get', 'hide', 'if', 'implements', 'import', 'in',
        'interface', 'is', 'late', 'library', 'mixin', 'new', 'null', 'of',
        'on', 'operator', 'part', 'required', 'rethrow', 'return', 'sealed',
        'set', 'show', 'static', 'super', 'switch', 'sync', 'this', 'throw',
        'true', 'try', 'type', 'typedef', 'var', 'void', 'when', 'with',
        'while', 'yield',
    }
    identifier = re.sub(r'\W+', '_', str(name)).strip('_')
    if not identifier:
        identifier = 'value'
    if identifier[0].isdigit():
        identifier = f'value_{identifier}'
    if identifier in keywords:
        identifier = f'{identifier}_value'
    return identifier


def enum_dart(enum_cls, include_import: bool = False) -> str:
    import_statement = "import 'package:json_annotation/json_annotation.dart';\n\n" if include_import else ""
    members = []
    for member in enum_cls:
        members.append(
            f"  @JsonValue('{dart_string_literal(member.value)}')\n"
            f"  {dart_enum_member_name(member.name)}"
        )
    members_content = ',\n'.join(members)
    return f"""{import_statement}enum {enum_cls.__name__} {{
{members_content}
}}

"""


def enum_class_from_annotation(annotation, model=None):
    if annotation is None:
        return None

    if isinstance(annotation, str):
        cls_name = embedded_class_name_from_type(annotation)
        if not cls_name or model is None:
            return None
        model_module = sys.modules.get(model.__module__)
        enum_cls = getattr(model_module, cls_name, None) if model_module else None
        return enum_cls if isinstance(enum_cls, EnumMeta) else None

    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is Annotated:
        return enum_class_from_annotation(args[0], model)

    if origin is list or origin is List:
        return enum_class_from_annotation(args[0], model) if args else None

    if origin is Union and type(None) in args:
        non_none = [a for a in args if a is not type(None)]
        return enum_class_from_annotation(non_none[0], model) if non_none else None

    return annotation if isinstance(annotation, EnumMeta) else None
    
def flatten_type(t) -> str:
    origin = get_origin(t)
    args = get_args(t)

    if origin is list or origin is List:
        inner = flatten_type(args[0]) if args else "dynamic"
        return f"List[{inner}]"

    if origin is Union and type(None) in args:
        non_none = [a for a in args if a is not type(None)]
        inner = flatten_type(non_none[0]) if non_none else "dynamic"
        return f"Optional[{inner}]"

    if origin is Annotated:
        return flatten_type(args[0])

    if hasattr(t, "__name__") and t.__name__ == "ObjectId":
        return "str"

    if hasattr(t, "__name__"):
        return t.__name__
    return str(t)

def get_inherited_fields(model):
    model_fields = []
    for class_in_hierarchy in model.mro():
        if hasattr(class_in_hierarchy, '__annotations__'):
            for field_name, field_type in class_in_hierarchy.__annotations__.items():
                if not field_name.startswith("_") and field_name not in [f[0] for f in model_fields]:
                    model_fields.append((field_name, flatten_type(field_type)))
    return model_fields


def get_inherited_field_annotations(model):
    model_fields = {}
    for class_in_hierarchy in model.mro():
        if hasattr(class_in_hierarchy, '__annotations__'):
            for field_name, field_type in class_in_hierarchy.__annotations__.items():
                if not field_name.startswith("_") and field_name not in model_fields:
                    model_fields[field_name] = field_type
    return model_fields


def embedded_model_dart(class_name: str, app_name: str, model: Type[BaseModel]) -> str:
    fields = ""
    fields_constructor = ""
    extra_imports = ""
    local_annotations = getattr(model, "__annotations__", {})
    local_fields = [
        (field_name, flatten_type(field_type))
        for field_name, field_type in local_annotations.items()
        if not field_name.startswith("_")
    ]

    for prop_name, prop_type in local_fields:
        dart_prop_type = pydantic_to_dart_type(prop_type)
        fields += f"  final {dart_prop_type} {prop_name};\n"
        if '?' in dart_prop_type:
            fields_constructor += f"    this.{prop_name},\n"
        else:
            fields_constructor += f"    required this.{prop_name},\n"

    # Collect transitive sub-dependencies
    try:
        sub_deps = get_all_sub_dependencies(model)
        for dep in sub_deps:
            if dep == model:
                continue
            dep_name = dep.__name__
            dep_name_clean = dep_name.replace('-Input', '').replace('-Output', '')
            ignored_imports = {
                'type', 'objectid', 'point', 'polygon', 'linestring', 'multipoint',
                'multilinestring', 'multipolygon', 'geometry', 'feature',
                'geometrypoint', 'geometrypolygon', 'geometrylinestring',
                'geometrymultipoint', 'geometrymultilinestring', 'geometrymultipolygon'
            }
            if dep_name_clean.lower() not in ignored_imports:
                imp = f"import 'package:{app_name}/models/{dep_name_clean.lower()}.dart';\n"
                if imp not in extra_imports:
                    extra_imports += imp
    except Exception as e:
        print(f"[LAIA error collecting embedded sub-dependencies] {e}")

    if fields_constructor:
        fields_constructor = fields_constructor[:-2]

    return f"""import 'package:json_annotation/json_annotation.dart';
import 'package:copy_with_extension/copy_with_extension.dart';
{extra_imports}
part '{class_name.lower()}.g.dart';

@JsonSerializable()
@CopyWith()
class {class_name} {{
{fields}
  {class_name}({{
{fields_constructor}
  }});

  factory {class_name}.fromJson(Map<String, dynamic> json) => _${class_name}FromJson(json);

  Map<String, dynamic> toJson() => _${class_name}ToJson(this);
}}
"""


def theme_dart():
    return f"""import 'package:flutter/material.dart';

class AppColors {{
  // Base
  static const Color brand900 = Color(0xFF1B003F);

  // Accents
  static const Color navy = Color(0xFF191970);
  static const Color indigo = Color(0xFF4B0082);
  static const Color brand = Color(0xFF9748FF);
  static const Color blue = Color(0xFF6495ED);

  // Surfaces
  static const Color lavender = Color(0xFFE6E6FA);
  static const Color bg = Color(0xFFF3F4FA);
  static const Color surface = Color(0xFFFDFBFF);

  // Neutrals
  static const Color outline = Color(0xFFD9D9D9);
  static const Color muted = Color(0xFF757575);

  static const Color success = Color(0xFF4CAF50);
  static const Color successBg = Color(0xFFE8F5E9);
  static const Color warning = Color(0xFFFFC107);
  static const Color warningBg = Color(0xFFFFF8E1);
  static const Color error = Color(0xFFF44336);
  static const Color errorBg = Color(0xFFFFEBEE);
}}

class AppTheme {{
  static ThemeData light() {{
    const cs = ColorScheme(
      brightness: Brightness.light,
      primary: AppColors.indigo,
      onPrimary: Colors.white,
      primaryContainer: AppColors.lavender,
      onPrimaryContainer: AppColors.brand900,

      secondary: AppColors.brand,
      onSecondary: Colors.white,
      secondaryContainer: AppColors.lavender,
      onSecondaryContainer: AppColors.brand900,

      tertiary: AppColors.blue,
      onTertiary: Colors.white,
      tertiaryContainer: AppColors.lavender,
      onTertiaryContainer: AppColors.brand900,

      background: AppColors.bg,
      onBackground: AppColors.brand900,

      surface: AppColors.surface,
      onSurface: AppColors.brand900,
      surfaceVariant: AppColors.lavender,
      onSurfaceVariant: AppColors.muted,

      outline: AppColors.outline,
      outlineVariant: AppColors.outline,

      error: Color(0xFFB3261E),
      onError: Colors.white,
      errorContainer: Color(0xFFF9DEDC),
      onErrorContainer: Color(0xFF410E0B),

      inverseSurface: AppColors.brand900,
      onInverseSurface: AppColors.surface,
      inversePrimary: AppColors.indigo,
      shadow: Colors.black,
      scrim: Colors.black,
      surfaceTint: AppColors.indigo,
    );

    final radius = BorderRadius.circular(20);

    return ThemeData(
      useMaterial3: true,
      colorScheme: cs,
      scaffoldBackgroundColor: AppColors.surface,

      // Tipografía: ajusta si tienes PublicSans en tu app
      textTheme: const TextTheme(
        headlineLarge: TextStyle(
          fontSize: 28,
          fontWeight: FontWeight.w600,
          color: AppColors.indigo
        ),
        headlineSmall: TextStyle(
          fontSize: 24,
          fontWeight: FontWeight.w700,
        ),
        titleMedium: TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.w600,
        ),
        bodyMedium: TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.w400,
          color: AppColors.navy
        ),
        bodySmall: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w500,
          color: AppColors.muted
        ),
        labelSmall: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w500,
          color: AppColors.indigo
        ),
      ),

      // Card “flotante” como la imagen
      cardTheme: CardThemeData(
        color: cs.surface,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      ),

      // Inputs redondos, con relleno suave
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        isDense: true,
        hintStyle: const TextStyle(color: AppColors.muted),
        labelStyle: const TextStyle(color: AppColors.muted),
        prefixIconColor: AppColors.muted,
        suffixIconColor: AppColors.muted,
        contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
        border: OutlineInputBorder(
          borderRadius: radius,
          borderSide: BorderSide(color: cs.outline),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: radius,
          borderSide: BorderSide(color: cs.outline),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: radius,
          borderSide: BorderSide(color: cs.primary, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: radius,
          borderSide: BorderSide(color: cs.error),
        ),
      ),

      // AppBar minimal (en login casi ni se usa, pero por si acaso)
      appBarTheme: AppBarTheme(
        backgroundColor: Colors.transparent,
        elevation: 0,
        centerTitle: false,
        foregroundColor: cs.onBackground,
      ),

      dividerTheme: DividerThemeData(color: cs.outline, thickness: 1),

      // Botones “pill”
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: cs.primary,
          foregroundColor: cs.onPrimary,
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(999)),
          textStyle: const TextStyle(fontWeight: FontWeight.w700),
        ),
      ),

      // Por si usas FilledButton (M3)
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: cs.primary,
          foregroundColor: cs.onPrimary,
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(999)),
          textStyle: const TextStyle(fontWeight: FontWeight.w700),
        ),
      ),

      // Outlined
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: cs.primary,
          side: BorderSide(color: cs.primary),
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(999)),
          textStyle: const TextStyle(fontWeight: FontWeight.w700),
        ),
      ),

      // Text buttons / links
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: cs.primary,
          textStyle: const TextStyle(fontWeight: FontWeight.w600),
        ),
      ),

      // Icon buttons (ojo del password, etc.)
      iconButtonTheme: IconButtonThemeData(
        style: IconButton.styleFrom(
          foregroundColor: AppColors.muted,
        ),
      ),
    );
  }}
}}
"""

def auth_scafold_dart():
    return f"""import 'package:flutter/material.dart';
import 'theme_app.dart';

class AuthScaffold extends StatelessWidget {{
  final Widget child;
  final Widget? topLeftBrand;

  const AuthScaffold({{
    super.key,
    required this.child,
    this.topLeftBrand,
  }});

  @override
  Widget build(BuildContext context) {{
    return Scaffold(
      body: Stack(
        children: [
          const Positioned.fill(
            child: DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    AppColors.surface,
                    AppColors.lavender,
                  ],
                ),
              ),
            ),
          ),

          SafeArea(
            child: Padding(
              padding: const EdgeInsets.only(left: 40, top: 40),
              child: Align(
                alignment: Alignment.topLeft,
                child: topLeftBrand ?? const SizedBox.shrink(),
              ),
            ),
          ),

          Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Card(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: child,
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }}
}}
"""

def nav_bar_dart(app_name: str):
    return f"""import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:{app_name}/theme/theme_app.dart';

class NotchedBottomBar extends StatelessWidget {{
  final int currentIndex; 
  final double height;
  final double radius;
  final Widget child;

  const NotchedBottomBar({{
    super.key,
    required this.currentIndex,
    required this.child,
    this.height = 60,
    this.radius = 34,
  }});

  double _xForIndex(double width, int i) {{
    final padding = 16.0;
    final usable = width - padding * 2;
    final slot = usable / 5;
    return padding + slot * (i + 0.5);
  }}

  @override
  Widget build(BuildContext context) {{
    return LayoutBuilder(
      builder: (context, c) {{
        final w = c.maxWidth;
        final notchX = _xForIndex(w, currentIndex);

        return ClipPath(
          clipper: _BarNotchClipper(
            notchCenterX: notchX,
            notchRadius: radius,
          ),
          child: Container(
            height: height,
            decoration: BoxDecoration(
              color: AppColors.lavender,
              borderRadius: BorderRadius.circular(0),
            ),
            child: child,
          ),
        );
      }},
    );
  }}
}}

class _BarNotchClipper extends CustomClipper<Path> {{
  final double notchCenterX;
  final double notchRadius;

  _BarNotchClipper({{
    required this.notchCenterX,
    required this.notchRadius,
  }});

  @override
  Path getClip(Size size) {{
    final r = notchRadius;
    final cx = notchCenterX.clamp(r + 8, size.width - r - 8);

    final valleyDepth = r * 0.85;
    final valleyTop = 0.0;
    final y = valleyTop;

    final left = cx - r;
    final right = cx + r;

    final path = Path();

    path.moveTo(0, 0);

    path.lineTo(left - 14, y);

    path.quadraticBezierTo(left - 6, y, left, y + 8);

    final arcRect = Rect.fromCircle(
      center: Offset(cx, y + 8),
      radius: r,
    );

    path.arcTo(arcRect, math.pi, -math.pi, false);

    path.quadraticBezierTo(right + 6, y, right + 14, y);

    path.lineTo(size.width, y);

    path.lineTo(size.width, size.height);
    path.lineTo(0, size.height);
    path.close();

    return path;
  }}

  @override
  bool shouldReclip(covariant _BarNotchClipper oldClipper) {{
    return oldClipper.notchCenterX != notchCenterX ||
        oldClipper.notchRadius != notchRadius;
  }}
}}

class LaiaBottomNavBar extends StatelessWidget {{
  final List<NavItem> items; // 5
  final int currentIndex;
  final ValueChanged<int> onTap;

  const LaiaBottomNavBar({{
    super.key,
    required this.items,
    required this.currentIndex,
    required this.onTap,
  }}) : assert(items.length == 5);

  @override
  Widget build(BuildContext context) {{
    final cs = Theme.of(context).colorScheme;

    double _xForIndex(double width, int i) {{
      const padding = 16.0;
      final usable = width - padding * 2;
      final slot = usable / 5;
      return padding + slot * (i + 0.5);
    }}

    return SafeArea(
      top: false,
      child: SizedBox(
        height: 104,
        child: Padding(
          padding: EdgeInsets.zero,
          child: LayoutBuilder(
            builder: (context, constraints) {{
              final w = constraints.maxWidth;
              final centerX = _xForIndex(w, currentIndex);
              const bubbleSize = 58.0;
              final bubbleLeft = centerX - bubbleSize / 2;
            return Stack(
              alignment: Alignment.bottomCenter,
              children: [
                AnimatedSwitcher(
                  duration: const Duration(milliseconds: 220),
                  switchInCurve: Curves.easeOut,
                  switchOutCurve: Curves.easeOut,
                  child: NotchedBottomBar(
                    key: ValueKey(currentIndex),
                    currentIndex: currentIndex,
                    height: 62,
                    radius: 32,
                    child: Row(
                      children: List.generate(items.length, (i) {{
                        final selected = i == currentIndex;
                        return Expanded(
                          child: InkResponse(
                            onTap: () => onTap(i),
                            radius: 28,
                            child: Padding(
                              padding: const EdgeInsets.symmetric(vertical: 12),
                              child: Icon(
                                items[i].icon,
                                color: selected
                                    ? Colors.transparent
                                    : AppColors.indigo,
                              ),
                            ),
                          ),
                        );
                      }}),
                    ),
                  ),
                ),
            
                AnimatedPositioned(
                    duration: const Duration(milliseconds: 220),
                    curve: Curves.easeOut,
                    left: bubbleLeft,
                    bottom: 8, 
                    child: Padding(
                      padding: EdgeInsets.zero,
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Container(
                            width: 58,
                            height: 58,
                            decoration: BoxDecoration(
                              color: cs.primary,
                              shape: BoxShape.circle,
                              boxShadow: [
                                BoxShadow(
                                  color: Colors.black.withOpacity(0.08),
                                  blurRadius: 18,
                                  offset: const Offset(0, 8),
                                ),
                              ],
                            ),
                            child: Icon(
                              items[currentIndex].icon,
                              color: Colors.white,
                              size: 26,
                            ),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            items[currentIndex].label,
                            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                  color: AppColors.indigo,
                                  fontWeight: FontWeight.w600,
                                ),
                          ),
                        ],
                      ),
                    ),
                  ),
                
              ],
            );
            }}
          ),
        ),
      ),
    );
  }}
}}


class NavItem {{
  final IconData icon;
  final String label;
  const NavItem({{required this.icon, required this.label}});
}}

"""
