import sys
import subprocess
from pathlib import Path
from typing import Dict
from unittest.mock import patch
import shutil

pyexe = sys.executable
print("-- Python executable: {}".format(pyexe))
pr = subprocess.Popen([pyexe, "--version"], shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
(output, errdata) = pr.communicate()
print("-- Python version: {}".format(output.decode("utf-8").strip()))

resource_path = "resources"
cpg_binary_rel_path = "sample_joern/cpg_binary.bin"

example_instance_dict = {
        "description": "Some description",
        "code": {
            "path": "<code_path>",
            "injection_skeleton_broken": True
        },
        "discovery": {
            "rule": "<rule_path>",
            "method": "joern",
            "rule_accuracy": "Perfect",
            "notes": "Some notes"
        },
        "remediation": {
            "notes": "./docs/remediation_notes.md",
            "transformation": None,
            "modeling_rule": None
        },
        "compile": {
            "binary": "",
            "dependencies": None,
            "instruction": None
        },
        "expectation": {
            "type": "xss",
            "sink_file": "<sink_path>",
            "sink_line": 5,
            "source_file": "<source_path>",
            "source_line": 9,
            "expectation": True
        },
        "properties": {
            "category": "S0",
            "feature_vs_internal_api": "FEATURE",
            "input_sanitizer": False,
            "source_and_sink": False,
            "negative_test_case": False
        }
    }

example_pattern_dict = {
        "name": "Test Pattern",
        "description": "./docs/description.md",
        "family": "test_pattern",
        "tags": ["sast", "language"],
        "instances": [
            "./1_instance_1_test_pattern/1_instance_1_test_pattern.json"
        ],
        "version": "v0.draft"
    }

def join_resources_path(relativepath):
    dirname = Path(__file__).parent.resolve()
    return dirname / resource_path / relativepath


def create_mock_cpg(dst_file: Path):
    sample_cpg_binary: Path = join_resources_path(cpg_binary_rel_path)
    shutil.copy(sample_cpg_binary, dst_file)


def in_logfile(logfile: Path, target: str, lastNlines: int = None):
    if not lastNlines:
        lastNlines = 0
    with open(logfile, 'r') as lfile:
        for l in (lfile.readlines() [-lastNlines:]):
            if target in l:
                return True
    return False


def get_path_after_string_from_output(target: str, captured_out_lines: list[str]):
    path = None
    for l in captured_out_lines:
        if target in l:
            path = Path(l.split(target)[1])
    return path


def get_result_output_dir(captured_out_lines, targ="results available here: "):
    ## assume stdout comprises "results available here: OUTPUT_DIR"
    return get_path_after_string_from_output(targ, captured_out_lines)


def get_logfile_path(captured_out_lines, targ="log file available here: "):
    ## assume stdout comprises "log file available here: LOG_PATH"
    return get_path_after_string_from_output(targ, captured_out_lines)


def init_test(init, language="PHP"):
    init["language"] = language
    init["tools"] = [
        {"name": "dummyTool", "version": "1"},
        {"name": "dummyTool", "version": "2"},
        {"name": "anotherDummyTool", "version": "1.2"}
    ]
    temp_meas = "../temp/measure/sample_patlib"
    init["tp_lib_path"] = join_resources_path(temp_meas).resolve()
    try:
        shutil.copytree(join_resources_path("sample_patlib"), init["tp_lib_path"])
    except Exception as e:
        pass
        # assert False, f"stop your tests will fail {e}"
    init["patterns"] = [1,2,3]


def mocked_tools_interfaces(tool_name: str, tool_version: str) -> Dict:
    if tool_name == "dummyTool" and tool_version == "2":
        return {
            "supported_languages": ["PHP", "JS", "JAVA"],
            "tool_interface": "qualitytests.core.sast_test.SastTestException"
        }
    else:
        return {
            "supported_languages": ["PHP", "JS", "JAVA"],
            "tool_interface": "qualitytests.core.sast_test.SastTest"
        }


def init_measure_test(init, mocker, language="PHP", exception=True):
    init_test(init, language=language)
    if exception:
        mocker.patch("core.utils.load_sast_specific_config", side_effect=mocked_tools_interfaces)
    else:
        mocked_tool_interface: Dict = {
            "supported_languages": [language],
            "tool_interface": "qualitytests.core.sast_test.SastTest"
        }
        mocker.patch("core.utils.load_sast_specific_config", return_value=mocked_tool_interface)


def init_sastreport_test(init, mocker):
    init_test(init)
    # mocked_tool_interface: Dict = {
    #     "supported_languages": ["PHP"],
    #     "tool_interface": "qualitytests.core.sast_test.SastTest"
    # }
    # mocker.patch("core.utils.load_sast_specific_config", return_value=mocked_tool_interface)

def create_instance():
    from core.instance import Instance
    sample_tp_lib = join_resources_path("sample_patlib")
    with patch('pathlib.Path.is_file') as is_file_mock, \
        patch("pathlib.Path.is_dir") as is_dir_mock:
                
        is_file_mock.return_value = True
        # read_json_mock.return_value = example_instance_dict
        json_path = sample_tp_lib / "JS" / "1_unset_element_array" / "1_instance_1_unset_element_array" / "1_instance_1_unset_element_array.json"
        test_instance = Instance.init_from_json_path(json_path, 1, "js", sample_tp_lib)

    # read_json_mock.assert_called_once()
    is_file_mock.assert_called()
    is_dir_mock.assert_called()
    return test_instance


def create_instance2():
    from core.instance import Instance
    sample_tp_lib = join_resources_path("sample_patlib")
    with patch('pathlib.Path.is_file') as is_file_mock, \
        patch("pathlib.Path.is_dir") as is_dir_mock:
                
        is_file_mock.return_value = True
        # read_json_mock.return_value = example_instance_dict
        json_path = sample_tp_lib / "JS" / "2_uri" / "1_instance_2_uri" / "1_instance_2_uri.json"
        test_instance = Instance.init_from_json_path(json_path, 1, "js", sample_tp_lib)

    # read_json_mock.assert_called_once()
    is_file_mock.assert_called()
    is_dir_mock.assert_called()
    return test_instance


def create_instance_php():
    from core.instance import Instance
    sample_tp_lib = join_resources_path("sample_patlib")
    with patch('pathlib.Path.is_file') as is_file_mock, \
        patch("pathlib.Path.is_dir") as is_dir_mock:
                
        is_file_mock.return_value = True
        # read_json_mock.return_value = example_instance_dict
        json_path = sample_tp_lib / "PHP" / "1_static_variables" / "1_instance_1_static_variables" / "1_instance_1_static_variables.json"
        test_instance = Instance.init_from_json_path(json_path, 1, "php", sample_tp_lib)

    # read_json_mock.assert_called_once()
    is_file_mock.assert_called()
    is_dir_mock.assert_called()
    return test_instance

def create_pattern():
    from core.pattern import Pattern
    sample_tp_lib = join_resources_path("sample_patlib")
    test_instance = create_instance()
    with patch('core.utils.read_json') as read_json_mock, \
        patch('pathlib.Path.is_file') as is_file_mock, \
        patch("pathlib.Path.is_dir") as is_dir_mock, \
        patch("core.pattern.isinstance") as isinstance_mock, \
        patch('core.instance.Instance.init_from_json_path') as instance_init_mock:

        is_dir_mock.return_value = True
        is_file_mock.return_value = True
        isinstance_mock.return_value = True
        read_json_mock.return_value = example_pattern_dict
        instance_init_mock.return_value = test_instance
        test_pattern = Pattern.init_from_id_and_language(1, "JS", sample_tp_lib)
    
    read_json_mock.assert_called_once()
    is_file_mock.assert_called()
    is_dir_mock.assert_called()
    isinstance_mock.assert_called()
    instance_init_mock.assert_called_once()
    return test_pattern
