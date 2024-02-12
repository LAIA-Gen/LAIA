import pytest
from laiagenlib.utils.flutter_base_files import model_dart
from laiagenlib.models.Model import LaiaBaseModel
from laiagenlib.utils.logger import _logger

class User(LaiaBaseModel):
    description: str
    age: int

def test_model_dart():
    result_content = model_dart("frontend", User)

    true_content = """import 'package:annotations/annotations.dart';
import 'package:flutter/material.dart';
import 'package:json_annotation/json_annotation.dart';
import 'package:copy_with_extension/copy_with_extension.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:tuple/tuple.dart';
import 'package:frontend/config/api.dart';
import 'package:frontend/generic/generic_widgets.dart';
import 'package:http/http.dart' as http;
import 'package:frontend/config/styles.dart';
import 'dart:convert';
import 'package:flutter_typeahead/flutter_typeahead.dart';

part 'user.g.dart';

@JsonSerializable()
@RiverpodGenAnnotation(baseURL)
@HomeWidgetElementGenAnnotation()
@ListWidgetGenAnnotation()
@elementWidgetGen
@CopyWith()
class User {
  final String description;
  final int age;
  final String id;
  final String name;

  User({
    required this.description,
    required this.age,
    required this.id,
    required this.name
  });

  factory User.fromJson(Map<String, dynamic> json) => _$UserFromJson(json);

  Map<String, dynamic> toJson() => _$UserToJson(this);
}
"""
    assert result_content == true_content