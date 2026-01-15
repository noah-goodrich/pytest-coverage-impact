from typing import Any
from ..interface.telemetry import ProjectTelemetry


class SensoriaContainer:
    def __init__(self):
        self._singletons = {}
        self.register_telemetry(project_name="SENSORIA", color="blue", welcome_msg="Orbital Sensors Active")

    def register_telemetry(self, project_name: str, color: str, welcome_msg: str):
        telemetry = ProjectTelemetry(project_name, color, welcome_msg)
        self.register_singleton("TelemetryPort", telemetry)

    def register_singleton(self, key: str, instance: Any):
        self._singletons[key] = instance

    def get(self, key: str) -> Any:
        if key in self._singletons:
            return self._singletons[key]
        raise ValueError(f"Dependency '{key}' not registered.")
