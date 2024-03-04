from core import errors


class AddPatternError(Exception):
    def __init__(self, message: str) -> None:
        self.message = errors.addPatternFailed(message)
        super().__init__()

class PatternDoesNotExists(Exception):
    def __init__(self, pattern_id):
        self.pattern_id = pattern_id
        self.message = errors.patternDoesNotExists(pattern_id)
        super().__init__(self.message)


class PatternInvalid(Exception):
    def __init__(self, message: str) -> None:
        self.message = errors.patternInvalidError(message)
        super().__init__(self.message)


class PatternRepairError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


class InstanceDoesNotExists(Exception):
    def __init__(self, instance_id: int = None, ref_metadata: str = None):
        self.instance_id = instance_id
        self.ref_metadata = ref_metadata
        self.message = errors.instanceDoesNotExists(instance_id, ref_metadata)
        super().__init__(self.message)


class InstanceInvalid(Exception):
    def __init__(self, message: str) -> None:
        self.message = errors.instanceInvalidError(message)
        super().__init__(self.message)


class MeasurementNotFound(Exception):
    def __init__(self, pattern_id):
        self.pattern_id = pattern_id
        self.message = errors.measurementNotFound(pattern_id)
        super().__init__(self.message)


class TPLibDoesNotExist(Exception):
    def __init__(self, message=errors.tpLibDoesNotExist()):
        self.message = message
        super().__init__(self.message)


class LanguageTPLibDoesNotExist(Exception):
    def __init__(self, message=errors.languageTPLibDoesNotExist()):
        self.message = message
        super().__init__(self.message)


class TargetDirDoesNotExist(Exception):
    def __init__(self, message=errors.targetDirDoesNotExist()):
        self.message = message
        super().__init__(self.message)


class DiscoveryMethodNotSupported(Exception):
    def __init__(self, message=None, discovery_method=None):
        if message:
            self.message = message
        elif discovery_method:
            self.message = errors.discoveryMethodNotSupported(discovery_method)
        else:
            self.message("")
        super().__init__(self.message)


class CPGGenerationError(Exception):
    def __init__(self, message=errors.cpgGenerationError()):
        self.message = message
        super().__init__(self.message)


class CPGLanguageNotSupported(Exception):
    def __init__(self, language=None):
        self.message = errors.cpgLanguageNotSupported(language)
        super().__init__(self.message)


class DiscoveryRuleError(Exception):
    def __init__(self, stderr=None):
        if stderr:
            self.message = stderr
        else:
            self.message = errors.discoveryRuleError()
        super().__init__(self.message)


class DiscoveryRuleParsingResultError(Exception):
    def __init__(self, stderr=None):
        if stderr:
            self.message = stderr
        else:
            self.message = errors.discoveryRuleParsingResultError()
        super().__init__(self.message)

# Pattern Repair

class MeasurementResultsDoNotExist(Exception):
    def __init__(self, message=errors.measurementResultsDirDoesNotExist()):
        self.message = message
        super().__init__(self.message)


class MeasurementInvalid(Exception):
    def __init__(self, message) -> None:
        self.message = message
        super().__init__(self.message)


class TemplateDoesNotExist(Exception):
    def __init__(self, message=errors.templateDirDoesNotExist('template')) -> None:
        self.message = message
        super().__init__(self.message)

