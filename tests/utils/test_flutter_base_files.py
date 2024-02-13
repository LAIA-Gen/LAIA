import pytest
from laiagenlib.utils.flutter_base_files import model_dart
from laiagenlib.models.Model import LaiaBaseModel
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
from laiagenlib.utils.logger import _logger

class User(LaiaBaseModel):
    description: str
    username: Optional[str] = Field(None, description="The user's username")
    email: Optional[EmailStr] = Field(None, description="The user's email address")
    age: Optional[int] = Field(None, description="The user's age")
    is_active: Optional[bool] = Field(
        None, description='Indicates whether the user is active or not'
    )

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
  @Field(fieldName: 'description')
  final String description;
  @Field(fieldName: 'username')
  final String username;
  @Field(fieldName: 'email')
  final String email;
  @Field(fieldName: 'age')
  final int age;
  @Field(fieldName: 'is_active')
  final bool is_active;
  @Field(fieldName: 'id')
  final String id;
  @Field(fieldName: 'name')
  final String name;

  User({
    required this.description,
    required this.username,
    required this.email,
    required this.age,
    required this.is_active,
    required this.id,
    required this.name
  });

  factory User.fromJson(Map<String, dynamic> json) => _$UserFromJson(json);

  Map<String, dynamic> toJson() => _$UserToJson(this);
}
"""
    assert result_content == true_content