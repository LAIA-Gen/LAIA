from enum import EnumMeta
from typing import Annotated, Type, List, Union, get_args, get_origin
from pydantic import BaseModel
from .OpenapiModel import OpenAPIModel
from ..AccessRights.AccessRights import AccessRight
from ..LaiaUser.Role import Role
from ...Domain.Shared.Utils.logger import _logger

def main_dart(app_name: str, models: List[OpenAPIModel]):
    auth_models = [model for model in models if model.extensions.get('x-auth')]
    import_statements = '\n'.join([f"import 'package:{app_name}/models/{model.model_name.lower()}.dart';" for model in auth_models])
    auth_screens = ', '.join([f"'{model.model_name}': {model.model_name}LoginWidget()" for model in auth_models])

    file_content = f"""{import_statements}
import 'package:{app_name}/screens/home.dart';"""+f"""
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:{app_name}/theme/theme.dart';"""+"""

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
      home: """+f"""{ "SplashScreen()" if auth_models else "Home()" }"""+""",
    );
  }
}
"""
    if auth_models:
      file_content = file_content + """
class SplashScreen extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AsyncValue<bool> tokenVerificationResult = ref.watch(verifyToken"""+f"""{auth_models[0].model_name}"""+"""Provider);

    return Scaffold(
      body: tokenVerificationResult.when(
        data: (isValid) {
          if (isValid) {
            return Home();
          } else {
            return """+f"""{ ''.join([auth_models[0].model_name, 'LoginWidget();']) if len(auth_models) == 1 else f"DynamicLogInScreen(widgetMap: const {{ {auth_screens} }});"}"""+"""
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
    return """const String baseURL = 'http://localhost:8000';
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
import 'package:{app_name}/theme/theme.dart';
import 'package:{app_name}/config/styles.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_map_arcgis/flutter_map_arcgis.dart';
import 'package:latlong2/latlong.dart';
import 'package:flutter_map/src/layer/polygon_layer/polygon_layer.dart' as flutter_map;
import 'package:{app_name}/models/geometry.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';"""+"""

part 'generic_widgets.g.dart';

@genericWidgets
class GenericWidgets {}
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
    import_statements = '\n'.join([
        f"import 'package:{app_name}/models/{model.model_name.lower()}.dart';"
        for model in models
        if not model.model_name.startswith("Body_")
    ])
    return f"""import 'package:{app_name}/config/styles.dart';
import 'package:{app_name}/generic/nav_bar.dart';
import 'package:{app_name}/generic/generic_widgets.dart';
import 'package:laia_annotations/laia_annotations.dart';
{import_statements}
{laia_import_statements}
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';"""+"""

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
    NavItem(icon: Icons.grid_view_rounded, label: 'Apps'),
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
              onLogout: () {
                // tu logout
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
            child: Text('Apps View', style: Theme.of(context).textTheme.headlineMedium),
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
                  title: 'CRM',
                  icon: const Icon(Icons.settings_outlined),
                  onTap: () => debugPrint('CRM'),
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

def model_dart(openapiModel: OpenAPIModel=None, app_name: str="", model: Type[BaseModel]=None):
    fields = ""
    fields_constructor = ""
    extra_imports = ""
    inherited_fields = get_inherited_fields(model)

    if isinstance(model, EnumMeta):
      members = ',\n  '.join([e.name for e in model])
      return f"""enum {model.__name__} {{
  {members}
}}"""
    
    if openapiModel:
      frontend_props = openapiModel.get_frontend_properties()
      try:
        defaultFields = "defaultFields: " + str(openapiModel.extensions['x-frontend-defaultFields']) + ", "
      except KeyError:
        defaultFields = ""
      try:
        defaultFieldsDetail = "defaultFieldsDetail: " + str(openapiModel.extensions['x-frontend-defaultFieldsDetail']) + ", "
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
    else:
      frontend_props = {}
      defaultFields = ""
      defaultFieldsDetail = ""
      widgetDistributionDetail = ""
      pageSize = ""
      widget = ""
    
    for prop_name, prop_type in inherited_fields:
      dart_prop_type = pydantic_to_dart_type(prop_type)
      fields += f"  @Field("
      
      if prop_name in frontend_props:
        frontend_details = frontend_props[prop_name]
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
        fields += "fieldName: '{}'".format(prop_name)
      
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
        extra_imports += f"import 'package:{app_name}/screens/home.dart';\n"

    return f"""import 'package:{app_name}/models/geometry.dart';
import 'package:laia_annotations/laia_annotations.dart';
import 'package:{app_name}/theme/auth_scaffold.dart';
import 'package:{app_name}/theme/theme.dart';
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
import 'package:collection/collection.dart';
import 'package:flutter_typeahead/flutter_typeahead.dart';
{extra_imports}
part '{model_name.lower()}.g.dart';

@JsonSerializable()
@RiverpodGenAnnotation(auth: {auth})
@HomeWidgetElementGenAnnotation()
@ListWidgetGenAnnotation({defaultFields}{pageSize}{widget})
@ElementWidgetGen({defaultFieldsDetail}{widgetDistributionDetail}auth: {auth})
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

    dart_type = "dynamic"

    if pydantic_type in dart_type_mapping:
        dart_type = dart_type_mapping[pydantic_type]
    elif hasattr(pydantic_type, "__origin__") and pydantic_type.__origin__ == list:
        inner_type = pydantic_to_dart_type(pydantic_type.__args__[0])
        dart_type = f'List<{inner_type}>'
    
    return dart_type
    
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
import 'theme.dart';

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
import 'package:{app_name}/theme/theme.dart';

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