import pytest
from unittest.mock import patch

from core.repair.pattern_repair import PatternRepair
from qualitytests.qualitytests_utils import join_resources_path, create_pattern, create_instance2

class TestPatternRepair:
    template_json_dict = {
            "name": "Pattern Name",
            "description": "",
            "family": "code_pattern_LANG",
            "tags": ["sast", "LANG"],
            "instances": [
                "./IID_instance_ID_pattern_name/IID_instance_ID_pattern_name.json"
            ],
            "version": "v0.draft"
        }
    def _get_pattern_repair(self) -> PatternRepair:
        test_pattern = create_pattern()
        with patch("pathlib.Path.is_file") as is_file_mock, \
            patch("core.utils.read_json") as read_json_mock:
            is_file_mock.return_value = True
            read_json_mock.return_value = TestPatternRepair.template_json_dict

            repair_tool = PatternRepair(test_pattern)

        read_json_mock.assert_called()
        is_file_mock.assert_called()
        return repair_tool            

    def test_complete_instances_no_new_instance0(self):
        test_repair_tool = self._get_pattern_repair()
        base_path = test_repair_tool.to_repair.path
        instance_path = test_repair_tool.to_repair.instances[0].path
        with patch("core.utils.list_directories") as listdir_mock, \
            patch("core.utils.get_json_file") as get_json_file_mock, \
            patch("core.instance.Instance.init_from_json_path") as instance_mock, \
            patch("core.instance.Instance.set_new_instance_path") as i_set_instance_path_mock:

            listdir_mock.return_value = [instance_path]
            test_repair_tool._complete_instances()
        listdir_mock.assert_called_once_with(base_path)
        get_json_file_mock.assert_not_called()
        instance_mock.assert_not_called()
        i_set_instance_path_mock.assert_not_called()

    def test_complete_instances_no_new_instance1(self):
        test_repair_tool = self._get_pattern_repair()
        base_path = test_repair_tool.to_repair.path
        instance_path = test_repair_tool.to_repair.instances[0].path
        with patch("core.utils.list_directories") as listdir_mock, \
            patch("core.utils.get_json_file") as get_json_file_mock, \
            patch("core.instance.Instance.init_from_json_path") as instance_mock, \
            patch("core.instance.Instance.set_new_instance_path") as i_set_instance_path_mock:

            listdir_mock.return_value = [instance_path, base_path / "docs"]
            get_json_file_mock.return_value = None

            test_repair_tool._complete_instances()
        listdir_mock.assert_called_once_with(base_path)
        get_json_file_mock.assert_called_once()
        instance_mock.assert_not_called()
        i_set_instance_path_mock.assert_not_called()
    
    def test_complete_instances_one_new_instance1(self):
        sample_tp_lib = join_resources_path("sample_patlib")
        test_repair_tool = self._get_pattern_repair()
        test_instance = create_instance2()
        base_path = test_repair_tool.to_repair.path
        instance_path = test_repair_tool.to_repair.instances[0].path
        with patch("core.utils.list_directories") as listdir_mock, \
            patch("core.utils.get_json_file") as get_json_file_mock, \
            patch("core.instance.Instance.init_from_json_path") as instance_mock, \
            patch("core.instance.Instance.set_new_instance_path") as i_set_instance_path_mock:

            listdir_mock.return_value = [instance_path, base_path / "2_instance_test_instance"]
            get_json_file_mock.return_value = "some_path"
            instance_mock.return_value = test_instance

            test_repair_tool._complete_instances()
        listdir_mock.assert_called_once_with(base_path)
        get_json_file_mock.assert_called_once()
        instance_mock.assert_called_once_with("some_path", 1, "JS", sample_tp_lib)
        i_set_instance_path_mock.assert_called_once_with(sample_tp_lib / "JS" / "2_uri" / "1_instance_1_unset_element_array")

    def test_repair_name(self):
        test_repair_tool = self._get_pattern_repair()
        test_repair_tool.to_repair.name = "Test"
        test_repair_tool._repair_name()
        assert "Unset Element Array" == test_repair_tool.to_repair.name
    
    repair_description_testcases = [
                                    ((True, ""), (True, ""), True, False, False),
                                    ((True, "Some description in file"), (True, ""), False, False, False),
                                    ((False, "Short description in JSON"), (False, ""), False, False, False),
                                    ((False, "A"*141), (False, ""), False, True, True),
                                    ((False, "A"*140), (False, ""), False, False, False),
                                    ((False, "Same description"), (False, "Same description"), False, True, False)
                                    ]

    @pytest.mark.parametrize("pattern_description_ret, instance_description_ret, should_warn, should_info, should_open", repair_description_testcases)
    def test_repair_description(self, pattern_description_ret, instance_description_ret, should_warn, should_info, should_open):
        test_repair_tool = self._get_pattern_repair()

        with patch("core.pattern.Pattern.get_description") as get_pattern_description_mock, \
            patch("core.instance.Instance.get_description") as get_instance_description_mock, \
            patch("core.repair.pattern_repair.logger.warn") as warn_logger, \
            patch("core.repair.pattern_repair.logger.info") as info_logger, \
            patch("pathlib.Path.mkdir") as mkdir_mock, \
            patch("builtins.open") as open_mock:

            get_pattern_description_mock.return_value = pattern_description_ret
            get_instance_description_mock.return_value = instance_description_ret

            test_repair_tool._repair_description()
        get_pattern_description_mock.assert_called_once()
        get_instance_description_mock.assert_called() if not should_warn else get_instance_description_mock.assert_not_called()
        open_mock.assert_called_once() if should_open else open_mock.assert_not_called()
        mkdir_mock.assert_called_once() if should_open else mkdir_mock.assert_not_called()
        warn_logger.assert_called_once() if should_warn else warn_logger.assert_not_called()
        info_logger.assert_called() if should_info else info_logger.assert_not_called()

    def test_repair_tags(self):
        test_repair_tool = self._get_pattern_repair()
        
        test_repair_tool.to_repair.tags = []
        test_repair_tool._repair_tags()
        assert ["JS", "sast"] == test_repair_tool.to_repair.tags

        test_repair_tool.to_repair.tags = ["sast", "LANG"]
        test_repair_tool._repair_tags()
        assert ["JS", "sast"] == test_repair_tool.to_repair.tags

        test_repair_tool.to_repair.tags = ["sast", "js"]
        test_repair_tool._repair_tags()
        assert ["JS", "sast"] == test_repair_tool.to_repair.tags

        test_repair_tool.to_repair.tags = ["sast", "JS"]
        test_repair_tool._repair_tags()
        assert ["JS", "sast"] == test_repair_tool.to_repair.tags

        test_repair_tool.to_repair.tags = ["sast", "Js"]
        test_repair_tool._repair_tags()
        assert ["JS", "sast"] == test_repair_tool.to_repair.tags
