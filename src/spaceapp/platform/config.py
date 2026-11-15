from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from spaceapp.platform.profiles import Profile

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Configuration. The default profile is `jury` (proposal pending confirmation)."""

    model_config = SettingsConfigDict(env_prefix="SPACEAPP_", env_file=".env", extra="ignore")

    profile: Profile = Profile.JURY
    database_url: str = "postgresql+asyncpg://spaceapp:spaceapp@localhost:5433/spaceapp"
    rules_path: Path = ROOT / "rules" / "catalog" / "monitoring.json"
    # Shortens the rule windows (1 real hour) for the demo. 1.0 = the standard values.
    rule_window_scale: float = 1.0
    # Consecutive clean evaluations before resolving an alert.
    alert_hysteresis: int = 3
    # The outbox relay and the simulator start with the application only when requested.
    relay_enabled: bool = False
    simulator_autostart: bool = False
    sim_layout_path: Path = ROOT / "data" / "telemetry" / "sim_layout.json"
    sim_seed: int = 7
    knowledge_catalog_path: Path = ROOT / "data" / "knowledge" / "demo_catalog.json"
    facility_plan_path: Path = ROOT / "data" / "facility" / "plan.json"
    incident_types_path: Path = ROOT / "data" / "facility" / "incident_types.json"
    engagement_templates_path: Path = ROOT / "data" / "engagement" / "templates.json"
    crew_roster_path: Path = ROOT / "data" / "crew" / "roster.json"
