def patternDoesNotExists(pattern_id):
    return f"Specified Pattern `{pattern_id}` does not exists."


def patternValueError():
    return f"Error during Pattern initialization."


def patternKeyError(e):
    return f"Key {e} was not found in pattern metadata."


def patternJSONDecodeError():
    return f"Pattern json file could not be decoded."


def instanceDoesNotExists(instance_id=None, ref_metadata=None):
    message = "Pattern Instance does not exists."
    if instance_id:
        message = f"Specified Pattern Instance `{instance_id}` does not exists."
    elif ref_metadata:
        message = f"Specified Pattern Instance at `{ref_metadata}` does not exists."
    return message


def patternFolderNotFound(pattern_dir_path):
    return f"`Pattern source folder {pattern_dir_path}` not found or is not a folder."


def patternDefaultJSONNotFound(default_pattern_json):
    return f"`{default_pattern_json}` not found in pattern folder. Please specify explicitly a file containing the pattern metadata."


def measurementNotFound(pattern_id):
    return f"Measurement for pattern `{pattern_id}` not found."


def tpLibDoesNotExist():
    return "TP Library does not exists."


def languageTPLibDoesNotExist():
    return "TP Library for specified language does not exists."


def targetDirDoesNotExist():
    return "The target directory does not exists."


def invalidSastTool(tool):
    return f"SAST tool not found in the SAST yaml configuration: {tool}"


def invalidSastTools():
    return "Invalid SAST tools or none of them could be selected for the task."


def sastScanFailed(tool):
    return f"SAST Scan failed for: {tool}."


def discoveryMethodNotSupported(discovery_method):
    return f"Discovery method `{discovery_method}` is not supported."


def wrongDiscoveryRule(discovery_rule):
    return f"Wrong discovery rule provided: {discovery_rule}."


def cpgGenerationError():
    return "Error while generating CPG for source."


def cpgLanguageNotSupported(language):
    return f"Language `{language}` is not supported for CPG generation."


def discoveryRuleError():
    return "Error running Joern query."


def discoveryRuleParsingResultError():
    return "Error while parsing the result returned by Joern query."


def unexpectedException(e):
    return f"Unexpected exception triggered: {e}."

# Pattern Repair

def measurementResultsDirDoesNotExist():
    return "The directory with the measurements does not exist."


def fileDoesNotExist():
    return "The file you provided for does not exist or is the wrong file type."


def templateDirDoesNotExist(not_exisitng_dir_or_file):
    return f"Your tplib does not have {not_exisitng_dir_or_file}."