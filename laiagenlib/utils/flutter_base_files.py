from pydantic import BaseModel, Field
from typing import List, Optional

def main_dart(app_name:str):
    return f"""import 'package:{app_name}/screens/home.dart';"""+"""
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
      title: 'Flutter Demo',
      theme: ThemeData(
        appBarTheme: const AppBarTheme(
          color:  Color.fromARGB(244, 224, 224, 214),
        ), 
        colorScheme: ColorScheme.fromSwatch(primarySwatch: Colors.brown),
        scaffoldBackgroundColor: const Color.fromARGB(244, 245, 245, 239),
        textTheme: const TextTheme(
          bodyLarge: TextStyle(color: Colors.black),
          bodyMedium: TextStyle(color: Colors.black),
        ),
      ),
      home: Home(),
    );
  }
}
"""

def api_dart():
    return """const String baseURL = 'http://localhost:8000';
//const String baseURL = 'http://10.0.2.2:8000';

// Android emmulator
// const String baseURL = 'http://10.0.2.2:8000';
"""

def styles_dart():
    return """import 'dart:ui';

class Styles {
  static const primaryColor = Color.fromARGB(255, 163, 144, 129);
  static const secondaryColor = Color.fromARGB(255, 196, 209, 208);
}
"""

def generic_dart(app_name:str):
    return f"""import 'package:annotations/annotations.dart';
import 'package:{app_name}/config/styles.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';"""+"""

part 'generic_widgets.g.dart';

@genericWidgets
class GenericWidgets {}
"""

def home_dart(app_name:str, models:list):
    import_statements = '\n'.join([f"import 'package:{app_name}/models/{model.model_name.lower()}.dart';" for model in models])
    return f"""import 'package:annotations/annotations.dart';
{import_statements}
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';"""+"""

part 'home.g.dart';

@homeWidget
class Home extends ConsumerWidget {

  @override
  Widget build(BuildContext context, WidgetRef ref) {

    return Scaffold(
      appBar: AppBar(
        title: const Text('This is your APP :)'),
      ),
      body: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          dashboardWidget(),
        ],
      ),
    );
  }
}
"""

def model_dart(app_name:str, model:BaseModel):
    fields = ""
    fields_constructor = ""
    for prop_name, prop_type in model.__annotations__.items():
        dart_prop_type = pydantic_to_dart_type(prop_type)
        fields += f"final {dart_prop_type} {prop_name};\n"
        fields_constructor += f"required this.{prop_name},\n"

    if fields_constructor:
        fields_constructor = fields_constructor[:-2]

    return f"""import 'package:annotations/annotations.dart';
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
import 'package:flutter_typeahead/flutter_typeahead.dart';

part '{model.model_name.lower()}.g.dart';

@JsonSerializable()
@RiverpodGenAnnotation(baseURL)
@HomeWidgetElementGenAnnotation()
@ListWidgetGenAnnotation()
@elementWidgetGen
@CopyWith()
class {model.model_name} {{
  {fields}

  {model.model_name}({{{fields_constructor}}});

  factory {model.model_name}.fromJson(Map<String, dynamic> json) => _${model.model_name}FromJson(json);

  Map<String, dynamic> toJson() => _${model.model_name}ToJson(this);
}}
"""

def pydantic_to_dart_type(pydantic_type):
    dart_type_mapping = {
        int: 'int',
        float: 'double',
        str: 'String',
        bool: 'bool',
        list: 'List',
    }

    if pydantic_type in dart_type_mapping:
        return dart_type_mapping[pydantic_type]
    elif hasattr(pydantic_type, "__origin__") and pydantic_type.__origin__ == list:
        inner_type = pydantic_to_dart_type(pydantic_type.__args__[0])
        return f'List<{inner_type}>'
    else:
        return 'dynamic'