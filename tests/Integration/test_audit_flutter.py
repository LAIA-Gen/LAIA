from types import SimpleNamespace
from laiagenlib.Domain.Openapi.AuditFlutter import install_audit_screens
from laiagenlib.Domain.Openapi.FlutterBaseFiles import home_dart


def test_generated_home_installs_protected_navigation_and_is_repeatable(tmp_path):
    home = home_dart('frontend', [SimpleNamespace(model_name='User')], False)
    result = install_audit_screens(tmp_path, 'frontend', ['AuditLog', 'LoginEvent'], home)
    assert result.count('const AuditNavigation()') == 1
    assert 'if (_index == 2 || _index == 3)' in result
    assert 'screens/audit_navigation.dart' in result
    assert 'AuditLog' in (tmp_path / 'audit_navigation.dart').read_text()
    assert 'LoginEvent' in (tmp_path / 'audit_navigation.dart').read_text()
    assert install_audit_screens(tmp_path, 'frontend', ['AuditLog', 'LoginEvent'], result) == result


def test_projects_without_audit_models_are_unchanged(tmp_path):
    assert install_audit_screens(tmp_path, 'frontend', [], 'custom home') == 'custom home'
    assert not list(tmp_path.iterdir())


def test_custom_home_content_and_single_model_are_preserved(tmp_path):
    home = "// custom header\nchildren: [if (_index == 0) CustomWidget()],"
    result = install_audit_screens(tmp_path, 'my_app', ['LoginEvent'], home)
    assert 'CustomWidget()' in result and '// custom header' in result
    navigation = (tmp_path / 'audit_navigation.dart').read_text()
    assert 'package:my_app/config/api.dart' in navigation
    assert 'models: const ["LoginEvent"]' in navigation
