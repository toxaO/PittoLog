from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

from pittolog.db import prepare_database
from pittolog.services.loan_service import LoanService
from pittolog.ui.main_window import MainWindow


def run_app(db_path: Path) -> int:
    app = QApplication([])
    connection = prepare_database(db_path)
    window = MainWindow(LoanService(connection), db_path)
    window.show()
    return app.exec()
