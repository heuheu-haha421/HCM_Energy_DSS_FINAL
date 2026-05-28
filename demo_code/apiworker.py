from PyQt5.QtCore import QThread, pyqtSignal
import requests

BASE_URL = "http://127.0.0.1:8000"


def get_backend_message(response):
    try:
        data = response.json()
    except ValueError:
        return response.text or f"HTTP {response.status_code}"

    for key in ("error", "message", "detail"):
        value = data.get(key)
        if isinstance(value, str) and value:
            return value
        if isinstance(value, list) and value:
            first = value[0]
            if isinstance(first, dict):
                return first.get("msg") or str(first)
            return str(first)
        if isinstance(value, dict) and value:
            return value.get("msg") or str(value)

    return f"HTTP {response.status_code}"


class ApiWorker(QThread):
    success = pyqtSignal(str)
    error   = pyqtSignal(str)

    def __init__(self, payload, token):
        super().__init__()
        self.payload = payload
        self.token   = token

    def run(self):
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            res     = requests.post(
                f"{BASE_URL}/api/v1/data/energy-data",
                json    = self.payload,
                headers = headers,
            )

            # ===== SUCCESS =====
            if res.status_code == 200:
                try:
                    data = res.json()
                    msg  = data.get("message", "Success")
                    self.success.emit(msg)
                except Exception:
                    self.success.emit("Success (no JSON)")
                return

            # ===== ERROR (400, etc.) =====
            self.error.emit(get_backend_message(res))

        except Exception as e:
            self.error.emit(f"Request failed: {str(e)}")
