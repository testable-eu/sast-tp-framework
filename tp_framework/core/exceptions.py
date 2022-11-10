class PatternDoesNotExists(Exception):

    def __init__(self, pattern_id):
        self.pattern_id = pattern_id
        self.message = f"Specified Pattern `{pattern_id}` does not exists"
        super().__init__(self.message)


class InstanceDoesNotExists(Exception):

    def __init__(self, instance_id: int = None, ref_metadata: str = None):
        self.instance_id = instance_id
        self.ref_metadata = ref_metadata
        self.message = "Pattern Instance does not exists"
        if instance_id:
            self.message = f"Specified Pattern Instance `{instance_id}` does not exists"
        if ref_metadata:
            self.message = f"Specified Pattern Instance at `{ref_metadata}` does not exists"
        super().__init__(self.message)


class MeasurementNotFound(Exception):

    def __init__(self, pattern_id):
        self.pattern_id = pattern_id
        self.message = f"Specified measurement `{pattern_id}` does not exists or belong to a non existing pattern"
        super().__init__(self.message)


class LanguageTPLibDoesNotExist(Exception):

    def __init__(self, message="TP Library for specified does not exists"):
        self.message = message
        super().__init__(self.message)


class SastScanFailed(Exception):

    def __init__(self, message=None, tool=None):
        if message:
            self.message = message
        else:
            self.message = f"SAST Scan Failed for: {tool}"
        super().__init__(self.message)


class DiscoveryMethodNotSupported(Exception):

    def __init__(self, message=None, discovery_method=None):
        if message:
            self.message = message
        else:
            self.message = f"Discovery method `{discovery_method}` is not supported"
        super().__init__(self.message)


class PatternValueError(Exception):
    def __init__(self, message=None):
        if message:
            self.message = message
        else:
            self.message = f"Error during Pattern initialization"
        super().__init__(self.message)


class CPGGenerationError(Exception):
    def __init__(self, message="Error while generating CPG for source"):
        self.message = message
        super().__init__(self.message)


class CPGLanguageNotSupported(Exception):
    def __init__(self, language=None):
        if language:
            self.message = f"{language}is not yet supported for CPG generation"
        else:
            self.message = f"Language is not yet supported for CPG generation"
        super().__init__(self.message)


class JoernQueryError(Exception):
    def __init__(self, stderr):
        if stderr:
            self.message = stderr
        else:
            self.message = "Error running Joern query"
        super().__init__(self.message)
