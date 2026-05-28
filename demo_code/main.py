import sys
import requests
from PyQt5.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QFormLayout,
    QLineEdit, QDateEdit, QDoubleSpinBox, QLabel, QPushButton, QToolButton
)
from PyQt5.QtCore import QDate
from apiworker import ApiWorker

BASE_URL       = "http://127.0.0.1:8000"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


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


class EnergyInputWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.access_token = None

        self.setWindowTitle("Energy Input")
        self.resize(700, 320)

        main_layout = QHBoxLayout()

        # ===== LEFT (INPUT) =====
        left_layout = QFormLayout()

        self.username_display = QLineEdit(ADMIN_USERNAME)
        self.username_display.setReadOnly(True)
        left_layout.addRow("Username:", self.username_display)

        self.password = QLineEdit(ADMIN_PASSWORD)
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setReadOnly(True)
        self.btn_toggle_password = QToolButton()
        self.btn_toggle_password.setText("Show")
        self.btn_toggle_password.setCheckable(True)

        password_layout = QHBoxLayout()
        password_layout.addWidget(self.password)
        password_layout.addWidget(self.btn_toggle_password)
        left_layout.addRow("Password:", password_layout)

        self.btn_login = QPushButton("Login")
        left_layout.addRow(self.btn_login)

        self.login_status_label = QLabel("Not logged in")
        self.login_status_label.setWordWrap(True)
        self.login_status_label.setStyleSheet("color: gray;")
        left_layout.addRow(self.login_status_label)

        self.input_date = QDateEdit()
        self.input_date.setCalendarPopup(True)
        self.input_date.setDate(QDate.currentDate())
        left_layout.addRow("Select Date:", self.input_date)

        self.pmax = QDoubleSpinBox()
        self.pmax.setMaximum(1e9)
        left_layout.addRow("Pmax:", self.pmax)

        self.pmin = QDoubleSpinBox()
        self.pmin.setMaximum(1e9)
        left_layout.addRow("Pmin:", self.pmin)

        self.total_load = QDoubleSpinBox()
        self.total_load.setMaximum(1e12)
        left_layout.addRow("Total Load (kWh):", self.total_load)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: gray;")
        left_layout.addRow(self.status_label)
        
        # ===== RIGHT (OUTPUT) =====
        right_layout = QFormLayout()

        self.week_display = QLineEdit()
        self.week_display.setReadOnly(True)
        right_layout.addRow("Week:", self.week_display)

        self.start_display = QLineEdit()
        self.start_display.setReadOnly(True)
        right_layout.addRow("Start (Mon):", self.start_display)

        self.end_display = QLineEdit()
        self.end_display.setReadOnly(True)
        right_layout.addRow("End (Sun):", self.end_display)

        # ===== BUTTON =====
        self.btn_submit = QPushButton("Submit")
        left_layout.addRow(self.btn_submit)

        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)

        self.setLayout(main_layout)

        # connect
        self.btn_login.clicked.connect(self.handle_login)
        self.btn_toggle_password.clicked.connect(self.toggle_password_visibility)
        self.input_date.dateChanged.connect(self.update_week_info)
        self.btn_submit.clicked.connect(self.handle_submit)

        self.update_week_info()

    def toggle_password_visibility(self):
        if self.btn_toggle_password.isChecked():
            self.password.setEchoMode(QLineEdit.Normal)
            self.btn_toggle_password.setText("Hide")
        else:
            self.password.setEchoMode(QLineEdit.Password)
            self.btn_toggle_password.setText("Show")

    def handle_login(self):
        username = ADMIN_USERNAME
        password = ADMIN_PASSWORD

        if not username or not password:
            self.update_login_status("Missing username or password", success=False)
            return

        self.btn_login.setEnabled(False)
        self.update_login_status("Logging in...", success=None)

        try:
            res = requests.post(
                f"{BASE_URL}/api/v1/auth/login",
                json    = {"username": username, "password": password},
                timeout = 10,
            )

            if res.status_code != 200:
                self.access_token = None
                self.update_login_status(get_backend_message(res), success=False)
                return

            data  = res.json().get("data") or {}
            token = data.get("access_token")
            role  = data.get("role", "")

            if not token:
                self.access_token = None
                self.update_login_status("Login response missing access token", success=False)
                return

            self.access_token = token
            suffix            = f" ({role})" if role else ""
            self.update_login_status(f"Logged in{suffix}", success=True)

        except Exception as e:
            self.access_token = None
            self.update_login_status(f"Login failed: {str(e)}", success=False)
        finally:
            self.btn_login.setEnabled(True)

    def update_week_info(self):
        selected = self.input_date.date()

        # tìm Monday của tuần
        day_of_week = selected.dayOfWeek()               # Mon=1
        monday      = selected.addDays(1 - day_of_week)
        sunday      = monday.addDays(6)

        # format hiển thị
        self.start_display.setText(monday.toString("yyyy-MM-dd"))
        self.end_display.setText(sunday.toString("yyyy-MM-dd"))

        # week ISO
        py_date = monday.toPyDate()
        iso_year, iso_week, _ = py_date.isocalendar()
        self.week_display.setText(f"{iso_week:02d}/{iso_year}")

    def handle_submit(self):
        if not self.access_token:
            self.update_status("Please login first", success=False)
            return

        week       = self.week_display.text()
        start_date = self.start_display.text()
        end_date   = self.end_display.text()

        if not week or not start_date or not end_date:
            self.update_status("Missing data", success=False)
            return

        payload = {
            "data": [
                {
                    "week"          : week,
                    "start_date"    : start_date,
                    "end_date"      : end_date,
                    "total_load_kwh": self.total_load.value(),
                    "pmax_mw"       : self.pmax.value(),
                    "pmin_mw"       : self.pmin.value()
                }
            ]
        }

        # disable nút để tránh spam
        self.btn_submit.setEnabled(False)
        self.update_status("Sending...", success=None)

        self.worker = ApiWorker(payload, self.access_token)
        self.worker.success.connect(self.on_success)
        self.worker.error.connect(self.on_error)
        self.worker.start()
        
    def on_success(self, msg):
        self.update_status(msg, success=True)
        self.btn_submit.setEnabled(True)


    def on_error(self, msg):
        self.update_status(msg, success=False)
        self.btn_submit.setEnabled(True)


    def update_status(self, msg, success=True):
        if success is True:
            self.status_label.setStyleSheet("color: green;")
        elif success is False:
            self.status_label.setStyleSheet("color: red;")
        else:
            self.status_label.setStyleSheet("color: gray;")

        self.status_label.setText(msg)

    def update_login_status(self, msg, success=True):
        if success is True:
            self.login_status_label.setStyleSheet("color: green;")
        elif success is False:
            self.login_status_label.setStyleSheet("color: red;")
        else:
            self.login_status_label.setStyleSheet("color: gray;")

        self.login_status_label.setText(msg)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EnergyInputWidget()
    window.show()
    sys.exit(app.exec_())
