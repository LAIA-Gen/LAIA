from pydantic import BaseModel
from laiagenlib.Domain.Openapi import FlutterBaseFiles
from .Stub.StubOpenAPIModelBuilder import StubOpenAPIModelBuilder

def test_main_dart():
    app_name = "your_package_name"
    expected_result = f"""import 'package:{app_name}/screens/home.dart';"""+"""
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
          color:  Color.fromARGB(255, 255, 255, 255),
        ), 
        colorScheme: ColorScheme.fromSwatch(primarySwatch: Colors.brown),
        scaffoldBackgroundColor: const Color.fromARGB(244, 255, 255, 255),
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
    assert FlutterBaseFiles.main_dart(app_name) == expected_result

def test_api_dart():
    expected_result = """const String baseURL = 'http://localhost:8000';
//const String baseURL = 'http://10.0.2.2:8000';

// Android emmulator
// const String baseURL = 'http://10.0.2.2:8000';
"""
    assert FlutterBaseFiles.api_dart() == expected_result

def test_styles_dart():
    expected_result = """import 'dart:ui';

class Styles {
  static const primaryColor = Color.fromARGB(255, 210, 223, 224);
  static const secondaryColor = Color.fromARGB(255, 236, 243, 242);
  static const buttonPrimaryColor = Color.fromARGB(255, 210, 223, 224);
  static const buttonPrimaryColorHover = Color.fromARGB(255, 165, 194, 191);
  static const dashboardBlock = Color.fromARGB(255, 196, 209, 208);
}
"""
    assert FlutterBaseFiles.styles_dart() == expected_result

def test_generic_dart():
    app_name = "your_package_name"
    expected_result = f"""import 'package:laia_annotations/laia_annotations.dart';
import 'package:{app_name}/config/styles.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';"""+"""

part 'generic_widgets.g.dart';

@genericWidgets
class GenericWidgets {}
"""
    assert FlutterBaseFiles.generic_dart(app_name) == expected_result

def test_home_dart():
    app_name = "your_package_name"
    models = [
        StubOpenAPIModelBuilder("Model1").build(),
        StubOpenAPIModelBuilder("Model2").build(),
    ]

    expected_import_statements = '\n'.join([f"import 'package:{app_name}/models/{model.model_name.lower()}.dart';" for model in models])

    expected_dart_code = f"""import 'package:laia_annotations/laia_annotations.dart';
{expected_import_statements}
import 'package:{app_name}/models/accessright.dart';
import 'package:{app_name}/models/role.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

part 'home.g.dart';

@homeWidget
class Home extends StatefulWidget {{
  const Home({{super.key}});

  @override
  _HomeState createState() => _HomeState();
}}

class _HomeState extends State<Home> {{
  int _selectedIndex = 0;

  void _onItemTapped(int index) {{
    setState(() {{
      _selectedIndex = index;
    }});
  }}

  @override
  Widget build(BuildContext context) {{

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
  }}
}}
"""
    assert FlutterBaseFiles.home_dart(app_name=app_name, models=models) == expected_dart_code

# TODO    
def test_model_dart():
    pass
    
def test_pydantic_to_dart_type():
    assert FlutterBaseFiles.pydantic_to_dart_type('int') == 'int'
    assert FlutterBaseFiles.pydantic_to_dart_type('float') == 'double'
    assert FlutterBaseFiles.pydantic_to_dart_type('str') == 'String'
    assert FlutterBaseFiles.pydantic_to_dart_type('bool') == 'bool'

    assert FlutterBaseFiles.pydantic_to_dart_type('Optional[int]') == 'int?'
    assert FlutterBaseFiles.pydantic_to_dart_type('Optional[str]') == 'String?'
    assert FlutterBaseFiles.pydantic_to_dart_type('Optional[bool]') == 'bool?'
    assert FlutterBaseFiles.pydantic_to_dart_type('Optional[float]') == 'double?'

    assert FlutterBaseFiles.pydantic_to_dart_type('EmailStr') == 'String'
    assert FlutterBaseFiles.pydantic_to_dart_type('Optional[EmailStr]') == 'String?'

    assert FlutterBaseFiles.pydantic_to_dart_type('list') == 'List<dynamic>'
    assert FlutterBaseFiles.pydantic_to_dart_type('List') == 'List<dynamic>'
    assert FlutterBaseFiles.pydantic_to_dart_type('List[int]') == 'List<int>'
    assert FlutterBaseFiles.pydantic_to_dart_type('List[str]') == 'List<String>'
    assert FlutterBaseFiles.pydantic_to_dart_type('List[float]') == 'List<double>'
    assert FlutterBaseFiles.pydantic_to_dart_type('List[bool]') == 'List<bool>'

    assert FlutterBaseFiles.pydantic_to_dart_type('List[List[int]]') == 'dynamic'
    assert FlutterBaseFiles.pydantic_to_dart_type('List[List[str]]') == 'dynamic'

    assert FlutterBaseFiles.pydantic_to_dart_type('other') == 'dynamic'
    assert FlutterBaseFiles.pydantic_to_dart_type('Optional[other]') == 'dynamic'

class ParentModel(BaseModel):
    parent_field: str

class ChildModel(ParentModel):
    child_field: int

class GrandChildModel(ChildModel):
    grandchild_field: float
    
# TODO
def test_get_inherited_fields():
    pass