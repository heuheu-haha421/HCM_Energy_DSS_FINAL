import os
from pathlib import Path


class EnvManager:
    DEFAULT_ENV_FILE = Path(__file__).resolve().parent / ".env"

    def __init__(self, env_file_path: Path | None = None):
        self.env_file_path = env_file_path or self.DEFAULT_ENV_FILE

    def load(self, keys: set[str] | None = None):
        if not self._env_file_exists():
            return

        for line in self.env_file_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()

            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()

            if (
                len(value) >= 2
                and value[0] == value[-1]
                and value[0] in {'"', "'"}
            ):
                value = value[1:-1]

            if keys is None or key in keys:
                os.environ[key] = value

    def get_bool(self, key: str, default: bool):
        value = os.environ.get(key)

        if value is None:
            return default

        return value.strip().lower() in {"1", "true", "yes", "on"}

    def get_str(self, key: str, default: str):
        value = os.environ.get(key)

        if value is None:
            return default

        return value.strip()

    def get_int(self, key: str, default: int):
        value = os.environ.get(key)

        if value is None:
            return default

        try:
            parsed = int(value)
        except ValueError:
            return default

        return parsed if parsed > 0 else default

    def set_many(self, values: dict[str, str]):
        for key, value in values.items():
            os.environ[key] = str(value)

        self.save(values)

    def save(self, values: dict[str, str]):
        self._ensure_env_file()

        lines         = self.env_file_path.read_text(encoding="utf-8").splitlines()
        updated_keys  = set()
        updated_lines = []

        for line in lines:
            stripped = line.strip()

            if not stripped or stripped.startswith("#") or "=" not in line:
                updated_lines.append(line)
                continue

            key, _ = line.split("=", 1)
            key = key.strip()

            if key in values:
                updated_lines.append(f"{key}={values[key]}")
                updated_keys.add(key)
            else:
                updated_lines.append(line)

        for key, value in values.items():
            if key not in updated_keys:
                updated_lines.append(f"{key}={value}")

        self.env_file_path.write_text(
            "\n".join(updated_lines) + "\n",
            encoding="utf-8",
        )

    def _env_file_exists(self):
        return self.env_file_path.parent.exists() and self.env_file_path.exists()

    def _ensure_env_file(self):
        self.env_file_path.parent.mkdir(parents=True, exist_ok=True)
        self.env_file_path.touch(exist_ok=True)
