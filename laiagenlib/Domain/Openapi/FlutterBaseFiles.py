from typing import Type, List
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
import 'package:{app_name}/screens/home.dart';"""+"""
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

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
      theme: ThemeData(
        appBarTheme: const AppBarTheme(
          color:  Color.fromARGB(255, 255, 255, 255),
        ), 
        colorScheme: ColorScheme.fromSwatch(primarySwatch: Colors.brown),
        scaffoldBackgroundColor: const Color.fromARGB(244, 255, 255, 255),
        textTheme: const TextTheme(
          bodyLarge: TextStyle(color: Colors.black),
          bodyMedium: TextStyle(color: Colors.black),
        ),
      ),
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
import 'package:{app_name}/config/styles.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_map_arcgis/flutter_map_arcgis.dart';
import 'package:latlong2/latlong.dart';
import 'package:flutter_map/src/layer/polygon_layer/polygon_layer.dart' as flutter_map;
import 'package:{app_name}/models/geometry.dart';"""+"""

part 'generic_widgets.g.dart';

@genericWidgets
class GenericWidgets {}
"""

def home_dart(app_name: str, models: List[OpenAPIModel]):
    laia_import_statements = '\n'.join([f"import 'package:{app_name}/models/{model.__name__.lower()}.dart';" for model in [AccessRight, Role]])
    import_statements = '\n'.join([f"import 'package:{app_name}/models/{model.model_name.lower()}.dart';" for model in models])
    return f"""import 'package:{app_name}/config/styles.dart';
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
  int _selectedIndex = 0;

  void _onItemTapped(int index) {
    setState(() {
      _selectedIndex = index;
    });
  }

  @override
  Widget build(BuildContext context) {

    return Scaffold(
      appBar: AppBar(
        title: const Text('LAIA'),
        centerTitle: true,
      ),
      body: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Expanded(
            child: dashboardWidget(context),
          ),
        ],
      ),
      bottomNavigationBar: BottomNavigationBar(
        backgroundColor: Colors.white,
        items: const <BottomNavigationBarItem>[
          BottomNavigationBarItem(
            icon: Icon(Icons.favorite_outline_sharp),
            label: 'Favorites',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.home_outlined),
            label: 'Home',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.person_outline_outlined),
            label: 'Profile',
          ),
        ],
        currentIndex: _selectedIndex,
        selectedItemColor: const Color.fromARGB(255, 0, 0, 0),
        onTap: _onItemTapped,
      ),
    );
  }
}
"""

def model_dart(openapiModel: OpenAPIModel=None, app_name: str="", model: Type[BaseModel]=None):
    fields = ""
    fields_constructor = ""
    extra_imports = ""
    inherited_fields = get_inherited_fields(model)
    
    if openapiModel:
      frontend_props = openapiModel.get_frontend_properties()
      try:
        defaultFields = "defaultFields: " + str(openapiModel.extensions['x-frontend-defaultFields']) + ", "
      except KeyError:
        defaultFields = ""
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
import 'package:flutter/material.dart';
import 'package:json_annotation/json_annotation.dart';
import 'package:copy_with_extension/copy_with_extension.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:tuple/tuple.dart';
import 'package:{app_name}/config/api.dart';
import 'package:{app_name}/generic/generic_widgets.dart';
import 'package:http/http.dart' as http;
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
@ElementWidgetGen(auth: {auth})
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
    
def get_inherited_fields(model: Type[BaseModel]):
    model_fields = []
    for class_in_hierarchy in model.mro():
        if hasattr(class_in_hierarchy, '__annotations__'):
            for field_name, field_type in class_in_hierarchy.__annotations__.items():
                if not field_name.startswith("_") and field_name not in [field[0] for field in model_fields]:
                    if hasattr(field_type, '__args__') and len(field_type.__args__) > 0:
                        unwrapped_type = field_type.__args__[0]
                        if hasattr(unwrapped_type, '__name__'):
                            model_fields.append((field_name, unwrapped_type.__name__))
                        else:
                            model_fields.append((field_name, str(unwrapped_type)))
                    else:
                        model_fields.append((field_name, getattr(field_type, '__name__', str(field_type))))
    return model_fields