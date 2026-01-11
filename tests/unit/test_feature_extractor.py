"""Unit tests for feature extractor module"""

import ast


from pytest_coverage_impact.ml.feature_extractor import FeatureExtractor


def test_extract_features_basic():
    """Test extracting features from a simple function"""
    code = """
def simple_func():
    return 42
"""
    tree = ast.parse(code)
    func_node = tree.body[0]

    features = FeatureExtractor.extract_features(func_node)

    assert "lines_of_code" in features
    assert "num_statements" in features
    assert "cyclomatic_complexity" in features
    assert "num_parameters" in features
    assert features["num_parameters"] == 0.0


def test_extract_features_with_parameters():
    """Test extracting features from function with parameters"""
    code = """
def func_with_params(x, y, z=10):
    return x + y + z
"""
    tree = ast.parse(code)
    func_node = tree.body[0]

    features = FeatureExtractor.extract_features(func_node)

    assert features["num_parameters"] == 3.0


def test_extract_features_variadic_args():
    """Test extracting features with variadic arguments"""
    code = """
def func_with_args(*args, **kwargs):
    return len(args)
"""
    tree = ast.parse(code)
    func_node = tree.body[0]

    features = FeatureExtractor.extract_features(func_node)

    assert features["has_variadic_args"] == 1.0


def test_extract_features_no_variadic_args():
    """Test extracting features without variadic arguments"""
    code = """
def func(x):
    return x
"""
    tree = ast.parse(code)
    func_node = tree.body[0]

    features = FeatureExtractor.extract_features(func_node)

    assert features["has_variadic_args"] == 0.0


def test_extract_features_with_branches():
    """Test extracting features with control flow"""
    code = """
def func_with_branches(x):
    if x > 0:
        return 1
    elif x < 0:
        return -1
    else:
        return 0
"""
    tree = ast.parse(code)
    func_node = tree.body[0]

    features = FeatureExtractor.extract_features(func_node)

    assert features["num_branches"] > 0
    assert features["cyclomatic_complexity"] > 1.0


def test_extract_features_with_loops():
    """Test extracting features with loops"""
    code = """
def func_with_loops(items):
    result = []
    for item in items:
        while item > 0:
            result.append(item)
            item -= 1
    return result
"""
    tree = ast.parse(code)
    func_node = tree.body[0]

    features = FeatureExtractor.extract_features(func_node)

    assert features["num_loops"] == 2.0


def test_extract_features_with_exceptions():
    """Test extracting features with exception handling"""
    code = """
def func_with_exceptions():
    try:
        risky_op()
    except ValueError:
        pass
    except KeyError:
        pass
"""
    tree = ast.parse(code)
    func_node = tree.body[0]

    features = FeatureExtractor.extract_features(func_node)

    assert features["num_exceptions"] == 2.0


def test_extract_features_with_returns():
    """Test extracting features with multiple returns"""
    code = """
def func_with_returns(x):
    if x > 0:
        return 1
    return 0
"""
    tree = ast.parse(code)
    func_node = tree.body[0]

    features = FeatureExtractor.extract_features(func_node)

    assert features["num_returns"] == 2.0


def test_extract_features_function_calls():
    """Test extracting function call features"""
    code = """
def func_with_calls():
    x = helper_func()
    y = obj.method()
    return helper_func()
"""
    tree = ast.parse(code)
    func_node = tree.body[0]

    features = FeatureExtractor.extract_features(func_node)

    assert features["num_function_calls"] > 0


def test_extract_features_async_function():
    """Test extracting features from async function"""
    code = """
async def async_func():
    await some_coro()
    return 42
"""
    tree = ast.parse(code)
    func_node = tree.body[0]

    features = FeatureExtractor.extract_features(func_node)

    assert features["is_async"] == 1.0


def test_extract_features_not_async():
    """Test that regular function is not marked as async"""
    code = """
def regular_func():
    return 42
"""
    tree = ast.parse(code)
    func_node = tree.body[0]

    features = FeatureExtractor.extract_features(func_node)

    assert features["is_async"] == 0.0


def test_extract_features_with_module_tree():
    """Test extracting features with module tree context"""
    module_code = """
class MyClass:
    def method(self):
        return 42
"""
    func_code = """
def standalone_func():
    return 1
"""
    module_tree = ast.parse(module_code)
    func_tree = ast.parse(func_code)
    func_node = func_tree.body[0]

    features = FeatureExtractor.extract_features(func_node, module_tree=module_tree)

    assert features["is_method"] == 0.0  # Not a method


def test_extract_features_method():
    """Test extracting features from a method"""
    code = """
class MyClass:
    def my_method(self):
        return 42
"""
    tree = ast.parse(code)
    class_node = tree.body[0]
    func_node = class_node.body[0]

    features = FeatureExtractor.extract_features(func_node, module_tree=tree)

    assert features["is_method"] == 1.0


def test_extract_features_filesystem_usage():
    """Test detecting filesystem usage"""
    code = """
def func_with_filesystem():
    with open("file.txt", encoding="utf-8") as f:
        return f.read()
"""
    tree = ast.parse(code)
    func_node = tree.body[0]

    features = FeatureExtractor.extract_features(func_node, file_path="module.py")

    assert features["uses_filesystem"] == 1.0


def test_extract_features_no_filesystem_usage():
    """Test that filesystem usage is not detected when not present"""
    code = """
def func_no_filesystem():
    return 42
"""
    tree = ast.parse(code)
    func_node = tree.body[0]

    features = FeatureExtractor.extract_features(func_node, file_path="module.py")

    assert features["uses_filesystem"] == 0.0


def test_extract_features_filesystem_no_file_path():
    """Test that filesystem detection defaults to 0 when no file_path"""
    code = """
def func_with_filesystem():
    with open("file.txt", encoding="utf-8") as f:
        return f.read()
"""
    tree = ast.parse(code)
    func_node = tree.body[0]

    features = FeatureExtractor.extract_features(func_node)

    assert features["uses_filesystem"] == 0.0


def test_extract_features_network_usage():
    """Test detecting network usage"""
    code = """
def func_with_network():
    response = requests.get("http://example.com")
    return response.text
"""
    tree = ast.parse(code)
    func_node = tree.body[0]

    features = FeatureExtractor.extract_features(func_node, file_path="module.py")

    assert features["uses_network"] == 1.0


def test_extract_features_snowflake_usage():
    """Test detecting Snowflake usage"""
    code = """
def func_with_snowflake():
    session = snowflake_connector()
    snowpark_session()
    return session
"""
    tree = ast.parse(code)
    func_node = tree.body[0]

    features = FeatureExtractor.extract_features(func_node, file_path="module.py")

    assert features["uses_snowflake"] == 1.0


def test_count_lines():
    """Test counting lines in function"""
    code = """
def multi_line_func():
    x = 1
    y = 2
    z = x + y
    return z
"""
    tree = ast.parse(code)
    func_node = tree.body[0]

    lines = FeatureExtractor.count_lines(func_node)

    assert lines >= 4.0


def test_count_lines_empty_body():
    """Test counting lines with empty body"""
    code = """
def empty_func():
    pass
"""
    tree = ast.parse(code)
    func_node = tree.body[0]

    lines = FeatureExtractor.count_lines(func_node)

    assert lines >= 1.0


def test_count_statements():
    """Test counting statements"""
    code = """
def func_with_statements():
    x = 1
    y = 2
    z = x + y
    return z
"""
    tree = ast.parse(code)
    func_node = tree.body[0]

    statements = FeatureExtractor.count_statements(func_node)

    assert statements >= 3.0


def test_cyclomatic_complexity():
    """Test cyclomatic complexity calculation"""
    code = """
def complex_func(x, y):
    if x > 0:
        if y > 0:
            return 1
    elif x < 0:
        return -1
    return 0
"""
    tree = ast.parse(code)
    func_node = tree.body[0]

    complexity = FeatureExtractor.cyclomatic_complexity(func_node)

    assert complexity >= 3.0  # Base + 2 ifs + 1 elif


def test_count_branches():
    """Test counting branches"""
    code = """
def func_with_branches(x):
    if x > 0:
        pass
    elif x == 0:
        pass
    else:
        pass
"""
    tree = ast.parse(code)
    func_node = tree.body[0]

    branches = FeatureExtractor.count_branches(func_node)

    assert branches > 0


def test_count_loops():
    """Test counting loops"""
    code = """
def func_with_loops(items):
    for item in items:
        while True:
            break
"""
    tree = ast.parse(code)
    func_node = tree.body[0]

    loops = FeatureExtractor.count_loops(func_node)

    assert loops == 2.0


def test_count_exceptions():
    """Test counting exception handlers"""
    code = """
def func_with_exceptions():
    try:
        pass
    except ValueError:
        pass
    except KeyError:
        pass
"""
    tree = ast.parse(code)
    func_node = tree.body[0]

    exceptions = FeatureExtractor.count_exceptions(func_node)

    assert exceptions == 2.0


def test_count_returns():
    """Test counting return statements"""
    code = """
def func_with_returns(x):
    if x > 0:
        return 1
    return 0
"""
    tree = ast.parse(code)
    func_node = tree.body[0]

    returns = FeatureExtractor.count_returns(func_node)

    assert returns == 2.0


def test_extract_function_calls():
    """Test extracting function calls"""
    code = """
def func_with_calls():
    x = helper()
    y = obj.method()
    return helper()
"""
    tree = ast.parse(code)
    func_node = tree.body[0]

    calls = FeatureExtractor.extract_function_calls(func_node)

    assert len(calls) >= 2  # helper() and obj.method()


def test_is_method_with_class():
    """Test detecting method in class"""
    code = """
class MyClass:
    def my_method(self):
        pass
"""
    tree = ast.parse(code)
    class_node = tree.body[0]
    func_node = class_node.body[0]

    is_method = FeatureExtractor.is_method(func_node, tree)

    assert is_method == 1.0


def test_is_method_standalone():
    """Test that standalone function is not a method"""
    code = """
def standalone_func():
    pass
"""
    tree = ast.parse(code)
    func_node = tree.body[0]

    is_method = FeatureExtractor.is_method(func_node, tree)

    assert is_method == 0.0


def test_detect_filesystem_usage():
    """Test filesystem usage detection"""
    code = """
def func():
    with open("file.txt", encoding="utf-8") as f:
        data = f.read()
    return Path("dir")
"""
    tree = ast.parse(code)
    func_node = tree.body[0]

    uses_fs = FeatureExtractor.detect_filesystem_usage(func_node)

    assert uses_fs == 1.0


def test_detect_network_usage():
    """Test network usage detection"""
    code = """
def func():
    response = requests.get("http://example.com")
    urllib.urlopen("http://test.com")
"""
    tree = ast.parse(code)
    func_node = tree.body[0]

    uses_net = FeatureExtractor.detect_network_usage(func_node)

    assert uses_net == 1.0


def test_detect_snowflake_usage():
    """Test Snowflake usage detection"""
    code = """
def func():
    session = snowflake_connector()
    snowpark_session()
"""
    tree = ast.parse(code)
    func_node = tree.body[0]

    uses_sf = FeatureExtractor.detect_snowflake_usage(func_node)

    assert uses_sf == 1.0
