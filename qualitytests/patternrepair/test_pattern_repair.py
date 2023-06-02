import pytest
import os
import shutil
from pathlib import Path

from pattern_repair.pattern_repair import PatternRepair
from pattern_repair.PHP.instance_repair_php import InstanceRepairPHP

from qualitytests.qualitytests_utils import join_resources_path

@pytest.fixture(autouse=True)
def run_around_tests():
    # Code that will run before the test
    path_to_test_pattern = join_resources_path("sample_patlib/PHP/5_pattern_to_repair")
    path_to_save = join_resources_path("sample_patlib/PHP/5_pattern_to_repair_copy")
    # copy the directory, to save it
    shutil.copytree(path_to_test_pattern, path_to_save)

    # A test function will be run at this point
    yield

    # Code that will run after the test
    # restore the saved pattern
    shutil.rmtree(path_to_test_pattern)
    os.rename(path_to_save, path_to_test_pattern)
    assert os.path.exists(path_to_test_pattern)

class TestPatternRepair:
    def test_repair_test_pattern_assert_files_exist(self):
        path_to_test_pattern = join_resources_path("sample_patlib/PHP/5_pattern_to_repair")
        instance_path = path_to_test_pattern / "1_instance_5_pattern_to_repair"
        assert os.path.exists(instance_path)

        PatternRepair(path_to_test_pattern, "PHP", join_resources_path("sample_patlib")).repair(True)

        expected_pattern_json = path_to_test_pattern / "5_pattern_to_repair.json"
        assert expected_pattern_json.is_file()
        expected_instance_json = instance_path / "1_instance_5_pattern_to_repair.json"
        assert expected_instance_json.is_file()
        expected_instance_php = instance_path / "1_instance_5_pattern_to_repair.php"
        assert expected_instance_php.is_file()
        expected_instance_bash = instance_path / "1_instance_5_pattern_to_repair.bash"
        assert expected_instance_bash.is_file()
        expected_instance_sc = instance_path / "1_instance_5_pattern_to_repair.sc"
        assert expected_instance_sc.is_file()
        expected_docs_dir = path_to_test_pattern / "docs"
        assert expected_docs_dir.is_dir()
        expected_description = expected_docs_dir / "description.md"
        assert expected_description.is_file()
        expected_README_file = path_to_test_pattern / "README.md"
        assert expected_README_file.is_file()
    
    def test_finding_source_and_sink_line(self):
        path_to_test_pattern = join_resources_path("sample_patlib/PHP/5_pattern_to_repair")
        instance_repair = InstanceRepairPHP("PHP", path_to_test_pattern, "", join_resources_path("sample_pathlib"))

        path_to_php_file = path_to_test_pattern / "1_instance_5_pattern_to_repair" / "test.php"

        source, sink = instance_repair._get_source_and_sink_for_file(path_to_php_file)
        assert 2 == source
        assert 3 == sink