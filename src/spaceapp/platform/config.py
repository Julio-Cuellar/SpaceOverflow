from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from spaceapp.platform.profiles import Profile

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Configuración. El perfil por defecto es `jurado` (propuesta pendiente de confirmar)."""

    model_config = SettingsConfigDict(env_prefix="SPACEAPP_", env_file=".env", extra="ignore")

    profile: Profile = Profile.JURADO
    database_url: str = "postgresql+asyncpg://spaceapp:spaceapp@localhost:5433/spaceapp"
    rules_path: Path = ROOT / "rules" / "catalog" / "monitoring.json"
    # Acorta las ventanas de las reglas (1 h real) para la demostración. 1.0 = valores de la norma.
    rule_window_scale: float = 1.0
    # Evaluaciones limpias seguidas antes de resolver una alerta.
    alert_hysteresis: int = 3
    # El relay del outbox y el simulador arrancan con la aplicación solo si se piden.
    relay_enabled: bool = False
    simulator_autostart: bool = False
    sim_layout_path: Path = ROOT / "data" / "telemetry" / "sim_layout.json"
    sim_seed: int = 7
    knowledge_catalog_path: Path = ROOT / "data" / "knowledge" / "demo_catalog.json"
