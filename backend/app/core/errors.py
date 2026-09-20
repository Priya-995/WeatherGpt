class WeatherGPTError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 500):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class UpstreamError(WeatherGPTError):
    def __init__(self, service: str, status_code: int = 502, message: str = ""):
        msg = message or f"Upstream service '{service}' failed with status {status_code}"
        super().__init__(code="UPSTREAM_ERROR", message=msg, status_code=502)
        self.service = service
        self.upstream_status = status_code
