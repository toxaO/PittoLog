from __future__ import annotations

from html import escape
from io import BytesIO
import sqlite3
from pathlib import Path

from PIL import ImageOps
from PySide6.QtCore import QDate, QEvent, QTimer, Qt
from PySide6.QtGui import QIntValidator, QPainter, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QDateEdit,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from pittolog.services.barcode_image_service import render_code128_png, safe_filename, write_barcode_png_file, write_barcode_sheet_pdf, write_test_sheet_pdf
from pittolog.services.barcode_workflow import BarcodeWorkflow
from pittolog.services.loan_service import LoanService


TABLE_HEADER_LABELS = {
    "id": "ID",
    "barcode": "バーコード",
    "name": "名前",
    "category": "カテゴリ",
    "active_status": "有効/無効",
    "status": "状態",
    "loan_department": "貸出先",
    "item_barcode": "物品バーコード",
    "item_name": "物品名",
    "department_barcode": "部署バーコード",
    "department_name": "部署名",
    "loaned_at": "貸出日時",
    "event_type": "操作",
    "note": "内容",
    "created_at": "日時",
}


class RoundedComboBox(QComboBox):
    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setPen(Qt.darkGray)
        painter.drawText(self.rect().adjusted(0, 0, -10, 0), Qt.AlignRight | Qt.AlignVCenter, "▼")


class MainWindow(QMainWindow):
    OPERATION_COLOR = "#2f855a"
    OPERATION_BG = "#f3faf6"
    MANAGEMENT_COLOR = "#2563a8"
    MANAGEMENT_BG = "#f4f8ff"

    def __init__(self, service: LoanService, db_path: Path) -> None:
        super().__init__()
        self.service = service
        self.workflow = BarcodeWorkflow(service)
        self.db_path = db_path
        self.setWindowTitle("PittoLog")
        self.resize(1080, 720)
        self.setStyleSheet(
            """
            QWidget {
                font-size: 15px;
            }
            QLineEdit, QComboBox {
                min-height: 32px;
                font-size: 17px;
                border: 1px solid #b8c2cc;
                border-radius: 7px;
                padding: 3px 8px;
                background: white;
            }
            QComboBox::drop-down {
                width: 28px;
                border: none;
                border-top-right-radius: 7px;
                border-bottom-right-radius: 7px;
                background: transparent;
            }
            QComboBox::drop-down:hover {
                background: #eef4fa;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0px;
                height: 0px;
                border: none;
            }
            QPushButton {
                min-height: 34px;
                padding: 5px 12px;
                font-size: 15px;
                border: 1px solid #aeb8c2;
                border-radius: 8px;
                background: #ffffff;
            }
            QPushButton:hover {
                background: #f3f7fb;
            }
            QPushButton:pressed {
                background: #e5edf6;
            }
            QTabBar::tab {
                min-height: 30px;
                padding: 5px 14px;
                border-top-left-radius: 7px;
                border-top-right-radius: 7px;
            }
            QTabWidget#ManagementTabs::pane {
                border: none;
                border-radius: 10px;
                background: #f4f8ff;
            }
            QTabBar#ManagementTabBar::tab:selected {
                background: #2563a8;
                color: white;
                font-weight: 600;
            }
            QTabBar#ManagementTabBar::tab:!selected {
                background: #edf3fb;
            }
            QHeaderView::section {
                min-height: 30px;
                font-size: 14px;
            }
            QFrame#Panel {
                border: none;
                border-radius: 10px;
                background: #fafafa;
            }
            QFrame#Panel[panelRole="scan"] {
                border: 3px solid #16a34a;
            }
            QFrame#Panel[panelRole="error"] {
                background: transparent;
                border: none;
            }
            QFrame#Panel[panelRole="error"][active="true"] {
                background: #fef2f2;
                border: 2px solid #dc2626;
                border-radius: 6px;
            }
            QFrame#FilterGroup {
                background: #ffffff;
                border: 1px solid #d7e0ea;
                border-radius: 10px;
            }
            QFrame#BarcodePanel {
                background: #ffffff;
                border: 1px solid #d7e0ea;
                border-radius: 10px;
            }
            QFrame#BarcodePanel QWidget,
            QFrame#BarcodePanel QLabel {
                background: #ffffff;
            }
            QFrame#BarcodePanel QLineEdit,
            QFrame#BarcodePanel QComboBox,
            QFrame#BarcodePanel QTextEdit {
                background: #ffffff;
            }
            QFrame#Panel[mode="operation"] {
                background: #fbfffc;
            }
            QFrame#Panel[scanReady="true"] {
                background: #ecfdf3;
            }
            QFrame#Panel[scanReady="false"] {
                background: #fdecec;
            }
            QFrame#Panel[scanState="item"] {
                background: #ecfdf3;
            }
            QFrame#Panel[scanState="department"] {
                background: #eff6ff;
            }
            QFrame#Panel[scanState="loan"] {
                background: #eff6ff;
            }
            QFrame#Panel[scanState="return"] {
                background: #fffbeb;
            }
            QFrame#Panel[scanState="confirm"] {
                background: #eff6ff;
            }
            QFrame#Panel[scanState="error"] {
                background: #fef2f2;
            }
            QFrame#Panel[scanState="done"] {
                background: #f0fdf4;
            }
            QFrame#Panel[scanReady="false"][scanState="item"] {
                background: #fff7ed;
            }
            QFrame#Panel[panelRole="scan"][scanReady="false"][scanState="item"] {
                border-color: #d97706;
            }
            QFrame#Panel[panelRole="scan"][scanState="item"] {
                border-color: #16a34a;
            }
            QFrame#Panel[panelRole="scan"][scanState="loan"] {
                border-color: #2563eb;
            }
            QFrame#Panel[panelRole="scan"][scanState="confirm"] {
                border-color: #2563eb;
            }
            QFrame#Panel[panelRole="scan"][scanState="return"] {
                border-color: #d97706;
            }
            QFrame#Panel[panelRole="scan"][scanState="done"] {
                border-color: #16a34a;
            }
            QFrame#Panel[panelRole="scan"][scanState="error"] {
                border-color: #dc2626;
            }
            QLineEdit#ScanInput[ready="true"] {
                border: 3px solid #16a34a;
                background: white;
                font-weight: 700;
                border-radius: 8px;
            }
            QLineEdit#ScanInput[ready="false"] {
                border: 2px solid #d97706;
                background: #fffaf0;
                border-radius: 8px;
            }
            QLabel#ScanMessage {
                font-size: 20px;
                font-weight: 600;
            }
            QLabel#ScanDetail {
                font-size: 16px;
            }
            QLabel#CurrentItemName {
                font-size: 22px;
                font-weight: 700;
                color: #111827;
            }
            QLabel#RecentResult {
                font-size: 18px;
                font-weight: 600;
                color: #1f2937;
            }
            QLabel#ErrorMessage {
                font-size: 17px;
                font-weight: 700;
                color: #991b1b;
            }
            QLabel#PanelTitle {
                font-size: 18px;
                font-weight: 600;
            }
            QLabel#ScanModeTitle {
                font-size: 26px;
                font-weight: 800;
                color: #111827;
            }
            QLabel#ScanModeTitle[scanState="item"] {
                color: #166534;
            }
            QLabel#ScanModeTitle[scanState="loan"],
            QLabel#ScanModeTitle[scanState="confirm"] {
                color: #1d4ed8;
            }
            QLabel#ScanModeTitle[scanState="return"] {
                color: #b45309;
            }
            QLabel#ScanModeTitle[scanState="done"] {
                color: #166534;
            }
            QWidget#OperationPage {
                background: #f3faf6;
                border-radius: 10px;
            }
            QWidget#ManagementPage {
                background: #f4f8ff;
                border-radius: 10px;
            }
            """
        )

        self.scan_input = QLineEdit()
        self.scan_input.setObjectName("ScanInput")
        self.scan_input.returnPressed.connect(self.handle_scan)
        self.scan_input.setPlaceholderText("ここにバーコードが入ります")
        self.scan_input.installEventFilter(self)
        self.scan_frame: QFrame | None = None
        self.scan_error_active = False
        self.last_completed_operation: str | None = None

        self.status_label = QLabel("物品バーコードをスキャンしてください。")
        self.status_label.setObjectName("ScanMessage")
        self.status_label.setTextFormat(Qt.RichText)
        self.status_label.setWordWrap(True)
        self.status_label.setFixedHeight(232)
        self.status_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.current_item_name_label = QLabel("")
        self.current_item_name_label.setObjectName("CurrentItemName")
        self.current_item_name_label.setWordWrap(True)
        self.current_item_name_label.setMinimumHeight(0)
        self.current_item_name_label.setVisible(False)
        self.error_label = QLabel("")
        self.error_label.setObjectName("ErrorMessage")
        self.error_label.setTextFormat(Qt.RichText)
        self.error_label.setWordWrap(True)
        self.recent_operation_label = QLabel("-")
        self.recent_operation_label.setObjectName("RecentResult")
        self.recent_item_label = QLabel("-")
        self.recent_item_label.setObjectName("RecentResult")
        self.recent_item_label.setWordWrap(True)
        self.recent_department_label = QLabel("-")
        self.recent_department_label.setObjectName("RecentResult")
        self.recent_department_label.setWordWrap(True)
        self.pending_scan_reset_version = 0
        self.result_clear_version = 0
        self.scan_message_locked = False
        self.pending_reset_seconds = self.service.get_setting_int("pending_reset_seconds", 30)
        self.result_clear_seconds = self.service.get_setting_int("result_clear_seconds", 30)
        fallback_output_dir = self.service.get_setting("output_dir", str(Path.cwd() / "exports"))
        self.csv_output_dir = self.service.get_setting("csv_output_dir", fallback_output_dir)
        self.png_output_dir = self.service.get_setting("png_output_dir", fallback_output_dir)
        self.pdf_output_dir = self.service.get_setting("pdf_output_dir", fallback_output_dir)
        self.countdown_remaining = 0
        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.countdown_label = QLabel("")
        self.countdown_label.setObjectName("ScanDetail")
        self.countdown_label.setFixedHeight(24)

        self.items_table = QTableWidget()
        self.categories_table = QTableWidget()
        self.departments_table = QTableWidget()
        self.loans_table = QTableWidget()
        self.events_table = QTableWidget()
        self.barcode_target_combo = RoundedComboBox()
        self.barcode_category_combo = RoundedComboBox()
        self.loan_query_input = QLineEdit()
        self.loan_category_filter = RoundedComboBox()
        self.loan_department_filter = RoundedComboBox()
        self.loan_sort_field = RoundedComboBox()
        self.loan_sort_order = RoundedComboBox()
        self.item_query_input = QLineEdit()
        self.item_category_filter = RoundedComboBox()
        self.item_status_filter = RoundedComboBox()
        self.item_active_filter = RoundedComboBox()
        self.item_loan_department_filter = RoundedComboBox()
        self.item_sort_field = RoundedComboBox()
        self.item_sort_order = RoundedComboBox()
        self.event_query_input = QLineEdit()
        self.event_type_filter = RoundedComboBox()
        self.event_department_filter = RoundedComboBox()
        self.event_sort_field = RoundedComboBox()
        self.event_sort_order = RoundedComboBox()
        self.event_date_filter = QCheckBox("期間指定")
        self.event_date_from = QDateEdit()
        self.event_date_to = QDateEdit()
        self.csv_output_dir_input = QLineEdit(self.csv_output_dir)
        self.png_output_dir_input = QLineEdit(self.png_output_dir)
        self.pdf_output_dir_input = QLineEdit(self.pdf_output_dir)
        self.root_tabs = QTabWidget()
        self.root_tabs.setObjectName("RootTabs")
        self.root_tabs.tabBar().setObjectName("RootTabBar")
        self.management_tabs: QTabWidget | None = None
        self.scan_focus_widgets: list[QWidget] = []
        self.root_tabs.currentChanged.connect(self.handle_root_tab_changed)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(self._build_root_tabs())
        self.setCentralWidget(central)
        self.update_mode_style()
        self.refresh_all()

    def _build_scan_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        scan_frame = QFrame()
        self.scan_frame = scan_frame
        scan_frame.setObjectName("Panel")
        scan_frame.setProperty("panelRole", "scan")
        scan_frame.setProperty("mode", "operation")
        scan_frame.setProperty("scanReady", False)
        scan_frame.setFixedHeight(405)
        scan_layout = QVBoxLayout(scan_frame)
        scan_layout.setContentsMargins(14, 10, 14, 10)
        scan_layout.setSpacing(2)
        self.scan_mode_title = QLabel("物品スキャン")
        self.scan_mode_title.setObjectName("ScanModeTitle")
        scan_layout.addWidget(self.scan_mode_title)
        scan_layout.addWidget(self.status_label)
        scan_layout.addWidget(self.current_item_name_label)
        scan_layout.addWidget(self.countdown_label)
        for focus_widget in (scan_frame, self.scan_mode_title, self.status_label, self.countdown_label):
            focus_widget.installEventFilter(self)
            self.scan_focus_widgets.append(focus_widget)

        input_row = QHBoxLayout()
        input_row.setSpacing(8)
        self.scan_input.setMaximumWidth(470)
        input_row.addWidget(self.scan_input, 1)
        confirm_button = QPushButton("確認")
        confirm_button.clicked.connect(self.confirm_scan)
        cancel_button = QPushButton("キャンセル")
        cancel_button.clicked.connect(self.cancel_scan)
        input_row.addWidget(confirm_button)
        input_row.addWidget(cancel_button)
        input_row.addStretch()
        scan_layout.addLayout(input_row)

        error_frame = QFrame()
        self.error_frame = error_frame
        error_frame.setObjectName("Panel")
        error_frame.setProperty("panelRole", "error")
        error_frame.setProperty("active", False)
        error_frame.setFixedHeight(112)
        error_layout = QVBoxLayout(error_frame)
        error_layout.setContentsMargins(12, 10, 12, 10)
        error_layout.addWidget(self.error_label)

        latest_frame = QFrame()
        latest_frame.setObjectName("Panel")
        latest_frame.setProperty("mode", "operation")
        latest_layout = QGridLayout(latest_frame)
        latest_layout.setContentsMargins(14, 12, 14, 12)
        latest_layout.setHorizontalSpacing(12)
        latest_layout.setVerticalSpacing(8)
        latest_title = QLabel("前回処理")
        latest_title.setObjectName("PanelTitle")
        latest_layout.addWidget(latest_title, 0, 0, 1, 2)
        latest_layout.addWidget(QLabel("操作"), 1, 0)
        latest_layout.addWidget(self.recent_operation_label, 1, 1)
        latest_layout.addWidget(QLabel("物品"), 2, 0)
        latest_layout.addWidget(self.recent_item_label, 2, 1)
        latest_layout.addWidget(QLabel("部署"), 3, 0)
        latest_layout.addWidget(self.recent_department_label, 3, 1)
        latest_layout.setColumnStretch(1, 1)

        scan_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        latest_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(scan_frame)
        layout.addWidget(error_frame)
        layout.addWidget(latest_frame)
        layout.addStretch()
        return panel

    def _build_root_tabs(self) -> QTabWidget:
        self.root_tabs.addTab(self._operation_tab(), "貸出・返却")
        self.root_tabs.addTab(self._management_tab(), "登録・設定")
        return self.root_tabs

    def eventFilter(self, watched, event) -> bool:
        if watched is self.scan_input and event.type() in (QEvent.FocusIn, QEvent.FocusOut):
            self.update_scan_ready_indicator()
        if watched in self.scan_focus_widgets and event.type() == QEvent.MouseButtonPress:
            self.scan_input.setFocus()
        return super().eventFilter(watched, event)

    def update_scan_ready_indicator(self) -> None:
        ready = self.root_tabs.currentIndex() == 0 and self.scan_input.hasFocus()
        if not self.scan_message_locked:
            self.status_label.setText(self.scan_message_html(ready=ready))
            self.status_label.setStyleSheet("color: #111827;" if ready else "color: #92400e;")
        self.scan_input.setProperty("ready", ready)
        if self.scan_frame is not None:
            self.scan_frame.setProperty("scanReady", ready)
            state = self.current_scan_state()
            self.scan_frame.setProperty("scanState", state)
            self.update_scan_mode_title(state)
            repolish_widget(self.scan_frame)
        repolish_widget(self.scan_input)

    def current_scan_state(self) -> str:
        if self.workflow.action_mode == "return":
            return "return"
        if self.workflow.item_barcode and self.workflow.department_barcode:
            return "confirm"
        if self.workflow.item_barcode:
            return "loan"
        return "item"

    def show_error_message(self, message: str) -> None:
        self.error_label.setText(html_lines(message))
        self.error_frame.setProperty("active", True)
        repolish_widget(self.error_frame)

    def clear_error_message(self) -> None:
        self.error_label.setText("")
        self.error_frame.setProperty("active", False)
        repolish_widget(self.error_frame)

    def set_scan_state(self, state: str) -> None:
        if self.scan_frame is None:
            return
        self.scan_frame.setProperty("scanState", state)
        self.update_scan_mode_title(state)
        repolish_widget(self.scan_frame)

    def update_scan_mode_title(self, state: str) -> None:
        if state == "done" and self.last_completed_operation:
            title = "キャンセル" if self.last_completed_operation == "キャンセル" else f"{self.last_completed_operation}処理完了"
            self.scan_mode_title.setText(title)
        else:
            self.scan_mode_title.setText(scan_mode_title(state))
        self.scan_mode_title.setProperty("scanState", state)
        repolish_widget(self.scan_mode_title)

    def next_scan_message(self) -> str:
        if self.workflow.action_mode == "return":
            return "返却する場合は確認バーコードをスキャンしてください。\nやめる場合はキャンセル用バーコードをスキャンしてください。"
        if self.workflow.item_barcode and self.workflow.department_barcode:
            return "確認、またはキャンセル用バーコードをスキャンしてください。"
        if self.workflow.item_barcode:
            return "貸出先の部署バーコードをスキャンしてください。"
        return "物品バーコードをスキャンしてください。"

    def scan_message_html(self, ready: bool = True, error: str = "") -> str:
        item_name, department_name = self.current_workflow_names()
        if self.workflow.action_mode == "return":
            return (
                f"{detail_block(('返却物品', item_name or '-'), ('返却元', department_name or '-'))}"
                f"{detail_spacer()}"
                "上記を返却します。<br>"
                f"{strong('確認')}、または{strong('キャンセル')}を<br>"
                "スキャンしてください。"
            )
        if self.workflow.item_barcode and self.workflow.department_barcode:
            return (
                f"{detail_block(('貸出物品', item_name or '-'), ('貸出先', department_name or '-'))}"
                f"{detail_spacer()}"
                "上記で貸出登録します。<br>"
                f"{strong('確認')}、または{strong('キャンセル')}を<br>"
                "スキャンしてください。"
            )
        if self.workflow.item_barcode:
            return (
                "貸出先を登録します。<br>"
                f"{strong('部署コード')}をスキャンしてください。<br><br>"
                "戻る場合はキャンセルを<br>"
                "スキャンしてください。"
            )
        if not ready:
            return "現在スキャンできません。<br>スキャンを開始するにはこのエリアを<br>クリックしてください。"
        return f"貸出・返却する{strong('物品バーコード')}を<br>スキャンしてください。"

    def completion_message_html(self, operation: str, item_name: str, department_name: str) -> str:
        if operation == "返却":
            return (
                f"{detail_block(('返却物品', item_name), ('貸出元', department_name or '-'))}"
                f"{detail_spacer()}"
                "上記で返却登録しました。<br>"
                "次の物品を<br>"
                "スキャン可能です。"
            )
        return (
            f"{detail_block(('貸出物品', item_name), ('貸出先', department_name or '-'))}"
            f"{detail_spacer()}"
            "上記で貸出登録しました。<br>"
            "次の物品を<br>"
            "スキャン可能です。"
        )

    def current_workflow_names(self) -> tuple[str, str]:
        item_name = ""
        department_name = ""
        try:
            if self.workflow.item_barcode:
                item_name = self.service.item_name_for_barcode(self.workflow.item_barcode)
            if self.workflow.department_barcode:
                department_name = self.service.department_name_for_barcode(self.workflow.department_barcode)
            elif self.workflow.action_mode == "return" and self.workflow.item_barcode:
                department_name = self.service.open_loan_department_name_for_item_barcode(self.workflow.item_barcode)
        except ValueError:
            return item_name, department_name
        return item_name, department_name

    def update_mode_style(self) -> None:
        color = self.OPERATION_COLOR if self.root_tabs.currentIndex() == 0 else self.MANAGEMENT_COLOR
        background = self.OPERATION_BG if self.root_tabs.currentIndex() == 0 else self.MANAGEMENT_BG
        self.root_tabs.setStyleSheet(
            f"""
            QTabWidget#RootTabs::pane {{
                border: none;
                border-radius: 10px;
                background: {background};
            }}
            QTabBar#RootTabBar::tab:selected {{
                background: {color};
                color: white;
                font-weight: 700;
            }}
            QTabBar#RootTabBar::tab:!selected {{
                background: #eeeeee;
                color: #202020;
            }}
            """
        )

    def _operation_tab(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("OperationPage")
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        scan_panel = self._build_scan_panel()
        scan_panel.setMinimumWidth(420)
        scan_panel.setMaximumWidth(560)
        layout.addWidget(scan_panel, 3)
        layout.addWidget(self._open_loans_tab(), 5)
        return widget

    def _open_loans_tab(self) -> QWidget:
        widget = self._table_tab(self.loans_table, self.export_loans, show_export_button=False)
        title = QLabel("貸出中物品")
        title.setObjectName("PanelTitle")
        title.setStyleSheet("font-size: 22px; font-weight: 800;")
        self.loan_query_input.setPlaceholderText("貸出日時、物品名、バーコード、部署名で検索")
        self.loan_query_input.returnPressed.connect(self.refresh_open_loans)
        self.loan_category_filter.currentIndexChanged.connect(self.refresh_open_loans)
        self.loan_department_filter.currentIndexChanged.connect(self.refresh_open_loans)
        self.loan_sort_field.addItem("貸出日時", "loaned_at")
        self.loan_sort_field.addItem("物品名", "item_name")
        self.loan_sort_field.addItem("カテゴリ", "category")
        self.loan_sort_field.addItem("物品バーコード", "item_barcode")
        self.loan_sort_field.addItem("部署名", "department_name")
        self.loan_sort_field.currentIndexChanged.connect(self.refresh_open_loans)
        self.loan_sort_order.addItem("降順", True)
        self.loan_sort_order.addItem("昇順", False)
        self.loan_sort_order.currentIndexChanged.connect(self.refresh_open_loans)
        search_button = QPushButton("検索")
        search_button.clicked.connect(self.refresh_open_loans)
        reset_button = QPushButton("初期化")
        reset_button.clicked.connect(self.reset_open_loan_filters)
        export_button = QPushButton("CSV出力")
        export_button.clicked.connect(self.export_loans)
        widget.layout().insertWidget(0, title)
        widget.layout().insertWidget(1, self._open_loan_filter_panel(search_button, reset_button, export_button))
        return widget

    def _open_loan_filter_panel(self, search_button: QPushButton, reset_button: QPushButton, export_button: QPushButton) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        search_group = filter_group()
        search_layout = QGridLayout(search_group)
        search_layout.setContentsMargins(12, 10, 12, 10)
        search_layout.setHorizontalSpacing(8)
        search_layout.addWidget(QLabel("検索"), 0, 0)
        search_layout.addWidget(self.loan_query_input, 0, 1)
        search_layout.addWidget(search_button, 0, 2)
        search_layout.setColumnStretch(1, 1)

        filter_box = filter_group()
        filter_layout = QGridLayout(filter_box)
        filter_layout.setContentsMargins(12, 10, 12, 10)
        filter_layout.setHorizontalSpacing(8)
        filter_layout.addWidget(QLabel("絞り込み"), 0, 0)
        filter_layout.addWidget(QLabel("カテゴリ"), 0, 1)
        filter_layout.addWidget(self.loan_category_filter, 0, 2)
        filter_layout.addWidget(QLabel("部署"), 0, 3)
        filter_layout.addWidget(self.loan_department_filter, 0, 4)
        filter_layout.addWidget(reset_button, 0, 5)
        filter_layout.setColumnStretch(2, 1)
        filter_layout.setColumnStretch(4, 1)

        sort_box = filter_group()
        sort_layout = QGridLayout(sort_box)
        sort_layout.setContentsMargins(12, 10, 12, 10)
        sort_layout.setHorizontalSpacing(8)
        sort_layout.addWidget(QLabel("並び順"), 0, 0)
        sort_layout.addWidget(self.loan_sort_field, 0, 1)
        sort_layout.addWidget(self.loan_sort_order, 0, 2)
        sort_layout.addWidget(export_button, 0, 3)

        layout.addWidget(search_group)
        layout.addWidget(filter_box)
        layout.addWidget(sort_box)
        return panel

    def _management_tab(self) -> QTabWidget:
        tabs = QTabWidget()
        tabs.setObjectName("ManagementTabs")
        tabs.setStyleSheet(tabs.styleSheet() + "QTabWidget#ManagementTabs { background: #f4f8ff; border-radius: 10px; }")
        tabs.tabBar().setObjectName("ManagementTabBar")
        self.management_tabs = tabs
        tabs.addTab(self._items_tab(), "物品")
        tabs.addTab(self._categories_tab(), "カテゴリ")
        tabs.addTab(self._departments_tab(), "部署")
        tabs.addTab(self._events_tab(), "履歴")
        tabs.addTab(self._barcode_tab(), "バーコード発行")
        tabs.addTab(self._settings_tab(), "設定")
        return tabs

    def _items_tab(self) -> QWidget:
        widget = self._table_tab(self.items_table, self.export_items)
        buttons = widget.layout().itemAt(0).layout()
        add_button = QPushButton("物品登録")
        add_button.clicked.connect(self.add_item)
        edit_button = QPushButton("物品登録情報変更")
        edit_button.clicked.connect(self.edit_selected_item)
        import_button = QPushButton("CSV読み込み")
        import_button.clicked.connect(self.import_items_csv)
        issue_button = QPushButton("印刷リストへ追加")
        issue_button.clicked.connect(self.add_selected_items_to_sheet_entries)
        active_button = QPushButton("有効/無効切替")
        active_button.clicked.connect(self.toggle_selected_item_active)
        buttons.insertWidget(0, add_button)
        buttons.insertWidget(1, edit_button)
        buttons.insertWidget(2, import_button)
        buttons.insertWidget(3, issue_button)
        buttons.insertWidget(4, active_button)

        self.item_query_input.setPlaceholderText("ID、物品名、バーコードで検索")
        self.item_query_input.returnPressed.connect(self.refresh_items)
        self.item_category_filter.currentIndexChanged.connect(self.refresh_items)
        self.item_active_filter.addItem("有効", "active")
        self.item_active_filter.addItem("すべて", "")
        self.item_active_filter.addItem("無効", "inactive")
        self.item_active_filter.currentIndexChanged.connect(self.refresh_items)
        self.item_status_filter.addItem("すべて", "")
        self.item_status_filter.addItem("在庫", "在庫")
        self.item_status_filter.addItem("貸出中", "貸出中")
        self.item_status_filter.addItem("登録解除", "登録解除")
        self.item_status_filter.currentIndexChanged.connect(self.refresh_items)
        self.item_loan_department_filter.currentIndexChanged.connect(self.refresh_items)
        self.item_sort_field.addItem("物品名", "name")
        self.item_sort_field.addItem("バーコード", "barcode")
        self.item_sort_field.addItem("カテゴリ", "category")
        self.item_sort_field.addItem("状態", "status")
        self.item_sort_field.currentIndexChanged.connect(self.refresh_items)
        self.item_sort_order.addItem("昇順", False)
        self.item_sort_order.addItem("降順", True)
        self.item_sort_order.currentIndexChanged.connect(self.refresh_items)
        search_button = QPushButton("検索")
        search_button.clicked.connect(self.refresh_items)
        clear_button = QPushButton("初期化")
        clear_button.clicked.connect(self.clear_item_query)
        widget.layout().insertWidget(1, self._items_filter_panel(search_button, clear_button))
        return widget

    def _items_filter_panel(self, search_button: QPushButton, clear_button: QPushButton) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        search_group = filter_group()
        search_layout = QGridLayout(search_group)
        search_layout.setContentsMargins(12, 10, 12, 10)
        search_layout.setHorizontalSpacing(8)
        search_layout.addWidget(QLabel("検索"), 0, 0)
        search_layout.addWidget(self.item_query_input, 0, 1)
        search_layout.addWidget(search_button, 0, 2)
        search_layout.setColumnStretch(1, 1)

        filter_group_frame = filter_group()
        filter_layout = QGridLayout(filter_group_frame)
        filter_layout.setContentsMargins(12, 10, 12, 10)
        filter_layout.setHorizontalSpacing(8)
        filter_layout.setVerticalSpacing(8)
        filter_layout.addWidget(QLabel("絞り込み"), 0, 0)
        filter_layout.addWidget(QLabel("カテゴリ"), 0, 1)
        filter_layout.addWidget(self.item_category_filter, 0, 2)
        filter_layout.addWidget(QLabel("有効/無効"), 0, 3)
        filter_layout.addWidget(self.item_active_filter, 0, 4)
        filter_layout.addWidget(clear_button, 0, 5)
        filter_layout.addWidget(QLabel("状態"), 1, 1)
        filter_layout.addWidget(self.item_status_filter, 1, 2)
        filter_layout.addWidget(QLabel("貸出先"), 1, 3)
        filter_layout.addWidget(self.item_loan_department_filter, 1, 4)
        filter_layout.setColumnStretch(2, 1)
        filter_layout.setColumnStretch(4, 1)

        sort_group = filter_group()
        sort_layout = QGridLayout(sort_group)
        sort_layout.setContentsMargins(12, 10, 12, 10)
        sort_layout.setHorizontalSpacing(8)
        sort_layout.addWidget(QLabel("並び順"), 0, 0)
        sort_layout.addWidget(self.item_sort_field, 0, 1)
        sort_layout.addWidget(self.item_sort_order, 0, 2)

        layout.addWidget(search_group)
        layout.addWidget(filter_group_frame)
        layout.addWidget(sort_group)
        return panel

    def _categories_tab(self) -> QWidget:
        widget = self._table_tab(self.categories_table, self.export_categories)
        buttons = widget.layout().itemAt(0).layout()
        add_button = QPushButton("カテゴリ登録")
        add_button.clicked.connect(self.add_category)
        edit_button = QPushButton("カテゴリ登録情報変更")
        edit_button.clicked.connect(self.edit_selected_category)
        buttons.insertWidget(0, add_button)
        buttons.insertWidget(1, edit_button)
        widget.setMaximumWidth(620)
        return widget

    def _departments_tab(self) -> QWidget:
        widget = self._table_tab(self.departments_table, self.export_departments)
        buttons = widget.layout().itemAt(0).layout()
        add_button = QPushButton("部署登録")
        add_button.clicked.connect(self.add_department)
        edit_button = QPushButton("部署登録情報変更")
        edit_button.clicked.connect(self.edit_selected_department)
        remove_button = QPushButton("登録解除")
        remove_button.clicked.connect(self.deactivate_selected_department)
        buttons.insertWidget(0, add_button)
        buttons.insertWidget(1, edit_button)
        buttons.insertWidget(2, remove_button)
        widget.setMaximumWidth(620)
        return widget

    def _events_tab(self) -> QWidget:
        widget = self._table_tab(self.events_table, self.export_events, show_export_button=False)
        self.event_query_input.setPlaceholderText("日時、操作、物品名、部署名で検索")
        self.event_query_input.returnPressed.connect(self.refresh_events)
        self.event_type_filter.addItem("すべて", "")
        self.event_type_filter.addItem("貸出", "loan")
        self.event_type_filter.addItem("返却", "return")
        self.event_type_filter.currentIndexChanged.connect(self.refresh_events)
        self.event_department_filter.currentIndexChanged.connect(self.refresh_events)
        self.event_sort_field.addItem("日時", "created_at")
        self.event_sort_field.addItem("操作", "event_type")
        self.event_sort_field.addItem("物品名", "item_name")
        self.event_sort_field.addItem("部署名", "department_name")
        self.event_sort_field.currentIndexChanged.connect(self.refresh_events)
        self.event_sort_order.addItem("降順", True)
        self.event_sort_order.addItem("昇順", False)
        self.event_sort_order.currentIndexChanged.connect(self.refresh_events)
        today = QDate.currentDate()
        for date_edit in (self.event_date_from, self.event_date_to):
            date_edit.setCalendarPopup(True)
            date_edit.setDisplayFormat("yyyy-MM-dd")
            date_edit.setDate(today)
            date_edit.dateChanged.connect(lambda _date: self.refresh_events())
            date_edit.setEnabled(False)
        self.event_date_filter.toggled.connect(self.event_date_from.setEnabled)
        self.event_date_filter.toggled.connect(self.event_date_to.setEnabled)
        self.event_date_filter.toggled.connect(lambda _checked: self.refresh_events())

        search_button = QPushButton("検索")
        search_button.clicked.connect(self.refresh_events)
        clear_button = QPushButton("初期化")
        clear_button.clicked.connect(self.clear_event_query)
        export_button = QPushButton("CSV出力")
        export_button.clicked.connect(self.export_events)
        widget.layout().insertWidget(0, self._events_filter_panel(search_button, clear_button, export_button))
        return widget

    def _events_filter_panel(self, search_button: QPushButton, clear_button: QPushButton, export_button: QPushButton) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        search_group = filter_group()
        search_layout = QGridLayout(search_group)
        search_layout.setContentsMargins(12, 10, 12, 10)
        search_layout.setHorizontalSpacing(8)
        search_layout.addWidget(QLabel("検索"), 0, 0)
        search_layout.addWidget(self.event_query_input, 0, 1)
        search_layout.addWidget(search_button, 0, 2)
        search_layout.setColumnStretch(1, 1)

        filter_group_frame = filter_group()
        filter_layout = QGridLayout(filter_group_frame)
        filter_layout.setContentsMargins(12, 10, 12, 10)
        filter_layout.setHorizontalSpacing(8)
        filter_layout.setVerticalSpacing(8)
        filter_layout.addWidget(QLabel("絞り込み"), 0, 0)
        filter_layout.addWidget(QLabel("操作"), 0, 1)
        filter_layout.addWidget(self.event_type_filter, 0, 2)
        filter_layout.addWidget(QLabel("部署"), 0, 3)
        filter_layout.addWidget(self.event_department_filter, 0, 4)
        filter_layout.addWidget(clear_button, 0, 5)
        filter_layout.addWidget(self.event_date_filter, 1, 1)
        filter_layout.addWidget(self.event_date_from, 1, 2)
        filter_layout.addWidget(QLabel("から"), 1, 3)
        filter_layout.addWidget(self.event_date_to, 1, 4)
        filter_layout.addWidget(QLabel("まで"), 1, 5)
        filter_layout.setColumnStretch(2, 1)
        filter_layout.setColumnStretch(4, 1)

        sort_group = filter_group()
        sort_layout = QGridLayout(sort_group)
        sort_layout.setContentsMargins(12, 10, 12, 10)
        sort_layout.setHorizontalSpacing(8)
        sort_layout.addWidget(QLabel("並び順"), 0, 0)
        sort_layout.addWidget(self.event_sort_field, 0, 1)
        sort_layout.addWidget(self.event_sort_order, 0, 2)
        sort_layout.addWidget(export_button, 0, 3)

        layout.addWidget(search_group)
        layout.addWidget(filter_group_frame)
        layout.addWidget(sort_group)
        return panel

    def _settings_tab(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setVerticalSpacing(12)
        self.pending_reset_input = QLineEdit(str(self.pending_reset_seconds))
        self.pending_reset_input.setValidator(QIntValidator(5, 600, self))
        self.pending_reset_input.setMaximumWidth(120)
        self.result_clear_input = QLineEdit(str(self.result_clear_seconds))
        self.result_clear_input.setValidator(QIntValidator(10, 1800, self))
        self.result_clear_input.setMaximumWidth(120)
        csv_output_layout = self.output_dir_row(self.csv_output_dir_input)
        png_output_layout = self.output_dir_row(self.png_output_dir_input)
        pdf_output_layout = self.output_dir_row(self.pdf_output_dir_input)
        save_button = QPushButton("設定を保存")
        save_button.clicked.connect(self.save_timer_settings)
        layout.addRow("CSV出力先フォルダ", csv_output_layout)
        layout.addRow("PNG出力先フォルダ", png_output_layout)
        layout.addRow("PDF出力先フォルダ", pdf_output_layout)
        layout.addRow("読み取り中のリセット時間（秒）", self.pending_reset_input)
        layout.addRow("読み取り結果を表示する時間（秒）", self.result_clear_input)
        layout.addRow(save_button)
        return widget

    def output_dir_row(self, line_edit: QLineEdit) -> QHBoxLayout:
        browse_button = QPushButton("参照")
        browse_button.clicked.connect(lambda: self.browse_output_dir(line_edit))
        row = QHBoxLayout()
        row.addWidget(line_edit, 1)
        row.addWidget(browse_button)
        return row

    def _table_tab(self, table: QTableWidget, export_handler, title: str | None = None, show_export_button: bool = True) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        buttons = QHBoxLayout()
        if title:
            label = QLabel(title)
            label.setStyleSheet("font-size: 17px; font-weight: 600;")
            buttons.addWidget(label)
        if show_export_button:
            export_button = QPushButton("CSV出力")
            export_button.clicked.connect(export_handler)
            buttons.addStretch()
            buttons.addWidget(export_button)
            layout.addLayout(buttons)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setDefaultSectionSize(34)
        layout.addWidget(table)
        return widget

    def _barcode_tab(self) -> QWidget:
        content = QWidget()
        content.setObjectName("BarcodePage")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        self.barcode_kind = RoundedComboBox()
        self.barcode_kind.addItems(["ITEM", "DEPT", "ACTION"])
        self.barcode_width = QLineEdit("0.35")
        self.barcode_height = QLineEdit("18")
        self.barcode_quiet_zone = QLineEdit("4")
        for size_input in (self.barcode_width, self.barcode_height, self.barcode_quiet_zone):
            size_input.setMaximumWidth(90)
            size_input.textChanged.connect(self.update_barcode_preview)
        self.barcode_preview = QLabel()
        self.barcode_preview.setMinimumSize(320, 96)
        self.barcode_preview.setAlignment(Qt.AlignCenter)
        self.barcode_preview.setStyleSheet("background: white; border: 1px solid #c9c9c9;")
        self.barcode_preview_note = QLabel()
        self.barcode_preview_note.setWordWrap(True)
        generate_button = QPushButton("PNG作成")
        generate_button.clicked.connect(self.generate_barcode)

        self.sheet_entries = QTextEdit()
        self.sheet_entries.setMinimumHeight(170)
        self.sheet_entries.setPlaceholderText("物品1,ITEM:000001")
        sheet_button = QPushButton("A4まとめPDF作成")
        sheet_button.clicked.connect(self.generate_barcode_sheet)
        test_sheet_button = QPushButton("テスト用A4 PDF作成")
        test_sheet_button.clicked.connect(self.generate_test_sheet)

        size_frame = QFrame()
        size_frame.setObjectName("BarcodePanel")
        size_frame.setAutoFillBackground(True)
        size_frame.setStyleSheet(barcode_panel_stylesheet())
        size_layout = QHBoxLayout(size_frame)
        size_layout.setContentsMargins(14, 12, 14, 12)
        size_layout.setSpacing(16)
        size_controls = QGridLayout()
        size_controls.setHorizontalSpacing(10)
        size_controls.setVerticalSpacing(8)
        size_title = QLabel("サイズ設定")
        size_title.setObjectName("PanelTitle")
        size_controls.addWidget(size_title, 0, 0, 1, 3)
        size_controls.addWidget(QLabel("長さ mm"), 1, 0)
        size_controls.addWidget(self.barcode_width, 1, 1)
        size_controls.addWidget(QLabel("バーコードの長さ"), 1, 2)
        size_controls.addWidget(QLabel("高さ mm"), 2, 0)
        size_controls.addWidget(self.barcode_height, 2, 1)
        size_controls.addWidget(QLabel("バーコードの高さ"), 2, 2)
        size_controls.addWidget(QLabel("余白 mm"), 3, 0)
        size_controls.addWidget(self.barcode_quiet_zone, 3, 1)
        size_controls.addWidget(QLabel("左右の白い余白"), 3, 2)
        size_controls.setColumnStretch(2, 1)
        preview_layout = QVBoxLayout()
        preview_title = QLabel("プレビュー")
        preview_title.setObjectName("PanelTitle")
        preview_layout.addWidget(preview_title)
        preview_layout.addWidget(self.barcode_preview)
        preview_layout.addWidget(self.barcode_preview_note)
        size_layout.addLayout(size_controls, 2)
        size_layout.addLayout(preview_layout, 3)

        single_frame = QFrame()
        single_frame.setObjectName("BarcodePanel")
        single_frame.setAutoFillBackground(True)
        single_frame.setStyleSheet(barcode_panel_stylesheet())
        single_layout = QFormLayout(single_frame)
        single_layout.setContentsMargins(14, 12, 14, 12)
        single_layout.setVerticalSpacing(8)
        single_title = QLabel("1件ずつPNG")
        single_title.setObjectName("PanelTitle")
        single_layout.addRow(single_title)
        single_layout.addRow("種類", self.barcode_kind)
        self.barcode_category_label = QLabel("カテゴリ")
        single_layout.addRow(self.barcode_category_label, self.barcode_category_combo)
        single_layout.addRow("対象", self.barcode_target_combo)
        single_layout.addRow(generate_button)

        sheet_frame = QFrame()
        sheet_frame.setObjectName("BarcodePanel")
        sheet_frame.setAutoFillBackground(True)
        sheet_frame.setStyleSheet(barcode_panel_stylesheet())
        sheet_layout = QVBoxLayout(sheet_frame)
        sheet_layout.setContentsMargins(14, 12, 14, 12)
        sheet_layout.setSpacing(8)
        sheet_title = QLabel("A4まとめPDF")
        sheet_title.setObjectName("PanelTitle")
        sheet_layout.addWidget(sheet_title)
        sheet_layout.addWidget(QLabel("印刷するバーコード"))
        sheet_layout.addWidget(self.sheet_entries, 1)
        sheet_buttons = QHBoxLayout()
        sheet_buttons.addWidget(sheet_button)
        sheet_buttons.addWidget(test_sheet_button)
        sheet_buttons.addStretch()
        sheet_layout.addLayout(sheet_buttons)

        single_column = QWidget()
        single_column_layout = QVBoxLayout(single_column)
        single_column_layout.setContentsMargins(0, 0, 0, 0)
        single_column_layout.addWidget(single_frame)
        single_column_layout.addStretch()

        sections = QHBoxLayout()
        sections.setSpacing(12)
        sections.addWidget(single_column, 2)
        sections.addWidget(sheet_frame, 3)

        layout.addWidget(size_frame)
        layout.addLayout(sections, 1)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("QScrollArea { background: #f4f8ff; border: none; } QWidget#BarcodePage { background: #f4f8ff; }")
        scroll_area.setWidget(content)
        self.barcode_kind.currentIndexChanged.connect(self.refresh_barcode_targets)
        self.barcode_category_combo.currentIndexChanged.connect(self.refresh_barcode_targets)
        self.barcode_target_combo.currentIndexChanged.connect(self.update_barcode_preview)
        self.refresh_barcode_categories()
        self.refresh_barcode_targets()
        return scroll_area

    def handle_scan(self) -> None:
        value = self.scan_input.text()
        self.scan_input.clear()
        if not value.strip():
            return
        result = self.workflow.handle_scan(value)
        self.scan_error_active = not result.ok
        self.scan_message_locked = True
        self.status_label.setStyleSheet("color: #111827;")
        self.current_item_name_label.setText("")
        if result.ok and result.message == "入力をキャンセルしました。":
            self.show_cancelled_result()
        elif result.operation:
            self.clear_error_message()
            self.last_completed_operation = result.operation
            self.status_label.setText(self.completion_message_html(result.operation, result.item_name or "-", result.department_name or ""))
            self.recent_operation_label.setText(result.operation)
            self.recent_item_label.setText(result.item_name or "-")
            self.recent_department_label.setText(result.department_name or "-")
            self.current_item_name_label.setText("")
        elif result.ok:
            self.clear_error_message()
            self.status_label.setText(self.scan_message_html(ready=True))
        else:
            self.status_label.setText(self.scan_message_html(ready=True))
            self.show_error_message(result.message)
        self.refresh_all()
        self.set_scan_state(self.current_scan_state() if self.workflow.item_barcode or self.workflow.department_barcode else ("done" if result.ok else self.current_scan_state()))
        if self.workflow.item_barcode or self.workflow.department_barcode:
            self.schedule_pending_scan_reset()
        else:
            self.schedule_result_clear()

    def confirm_scan(self) -> None:
        self.scan_input.setText("ACTION:001")
        self.handle_scan()

    def cancel_scan(self) -> None:
        self.workflow.reset()
        self.show_cancelled_result()
        self.scan_input.setFocus()
        self.update_scan_ready_indicator()
        self.schedule_result_clear()

    def show_cancelled_result(self) -> None:
        self.scan_error_active = False
        self.last_completed_operation = "キャンセル"
        self.scan_message_locked = True
        self.status_label.setStyleSheet("color: #111827;")
        self.status_label.setText("処理をキャンセルしました。<br>次の物品を<br>スキャン可能です。")
        self.current_item_name_label.setText("")
        self.clear_error_message()
        self.set_scan_state("done")

    def save_timer_settings(self) -> None:
        try:
            self.pending_reset_seconds = parse_int_range(self.pending_reset_input.text(), "読み取り中のリセット時間", 5, 600)
            self.result_clear_seconds = parse_int_range(self.result_clear_input.text(), "読み取り結果を表示する時間", 10, 1800)
            csv_output_dir = self.parse_output_dir(self.csv_output_dir_input.text(), "CSV出力先フォルダ")
            png_output_dir = self.parse_output_dir(self.png_output_dir_input.text(), "PNG出力先フォルダ")
            pdf_output_dir = self.parse_output_dir(self.pdf_output_dir_input.text(), "PDF出力先フォルダ")
        except ValueError as error:
            QMessageBox.warning(self, "設定保存", str(error))
            return
        except OSError as error:
            QMessageBox.warning(self, "設定保存", f"出力先フォルダを作成できませんでした。\n{error}")
            return
        self.csv_output_dir = str(csv_output_dir)
        self.png_output_dir = str(png_output_dir)
        self.pdf_output_dir = str(pdf_output_dir)
        self.csv_output_dir_input.setText(self.csv_output_dir)
        self.png_output_dir_input.setText(self.png_output_dir)
        self.pdf_output_dir_input.setText(self.pdf_output_dir)
        self.service.set_setting("csv_output_dir", self.csv_output_dir)
        self.service.set_setting("png_output_dir", self.png_output_dir)
        self.service.set_setting("pdf_output_dir", self.pdf_output_dir)
        self.service.set_setting_int("pending_reset_seconds", self.pending_reset_seconds)
        self.service.set_setting_int("result_clear_seconds", self.result_clear_seconds)
        QMessageBox.information(self, "設定保存", "設定を保存しました。")

    def parse_output_dir(self, text: str, label: str) -> Path:
        output_dir_text = text.strip()
        if not output_dir_text:
            raise ValueError(f"{label}を入力してください。")
        output_dir = Path(output_dir_text).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def browse_output_dir(self, line_edit: QLineEdit) -> None:
        directory = QFileDialog.getExistingDirectory(self, "出力先フォルダ", line_edit.text().strip())
        if directory:
            line_edit.setText(directory)

    def schedule_pending_scan_reset(self) -> None:
        self.pending_scan_reset_version += 1
        version = self.pending_scan_reset_version
        self.start_countdown("読み取り中", self.pending_reset_seconds)
        QTimer.singleShot(self.pending_reset_seconds * 1000, lambda: self.reset_pending_scan(version))

    def reset_pending_scan(self, version: int) -> None:
        if version != self.pending_scan_reset_version:
            return
        if not (self.workflow.item_barcode or self.workflow.department_barcode):
            return
        self.workflow.reset()
        self.scan_error_active = False
        self.last_completed_operation = None
        self.current_item_name_label.setText("")
        self.clear_error_message()
        self.scan_message_locked = False
        self.stop_countdown()
        self.update_scan_ready_indicator()

    def schedule_result_clear(self) -> None:
        self.result_clear_version += 1
        version = self.result_clear_version
        self.start_countdown("結果表示", self.result_clear_seconds)
        QTimer.singleShot(self.result_clear_seconds * 1000, lambda: self.clear_result_display(version))

    def clear_result_display(self, version: int) -> None:
        if version != self.result_clear_version:
            return
        self.current_item_name_label.setText("")
        self.scan_error_active = False
        self.last_completed_operation = None
        self.clear_error_message()
        self.scan_message_locked = False
        self.stop_countdown()
        self.update_scan_ready_indicator()

    def start_countdown(self, label: str, seconds: int) -> None:
        self.countdown_label.setText(f"あと {seconds} 秒で初期画面に戻ります。")
        self.countdown_remaining = seconds
        self.countdown_timer.start(1000)

    def update_countdown(self) -> None:
        if self.countdown_remaining <= 1:
            self.countdown_timer.stop()
            return
        self.countdown_remaining -= 1
        self.countdown_label.setText(f"あと {self.countdown_remaining} 秒で初期画面に戻ります。")

    def stop_countdown(self) -> None:
        self.countdown_timer.stop()
        self.countdown_remaining = 0
        self.countdown_label.setText("")

    def add_item(self) -> None:
        dialog = ItemRegistrationDialog(self.service, self)
        if dialog.exec() != QDialog.Accepted:
            return
        name, category_id, barcode = dialog.values()
        self._run_action(lambda: self.service.register_item_with_category(name, category_id, barcode), "物品を登録しました。")

    def edit_selected_item(self) -> None:
        item_id = self._selected_id(self.items_table)
        if item_id is None:
            return
        try:
            item = self.service.get_item(item_id)
        except ValueError as error:
            QMessageBox.warning(self, "エラー", str(error))
            return
        dialog = ItemEditDialog(self.service, item, self)
        if dialog.exec() != QDialog.Accepted:
            return
        name, category_id, barcode = dialog.values()
        self._run_action(lambda: self.service.update_item(item_id, name, category_id, barcode), "物品を変更しました。")

    def add_category(self) -> None:
        name, ok = QInputDialog.getText(self, "カテゴリ登録", "カテゴリ名")
        if not ok:
            return
        self._run_action(lambda: self.service.register_category(name), "カテゴリを登録しました。")

    def edit_selected_category(self) -> None:
        selected = self.categories_table.selectionModel().selectedRows()
        if not selected:
            QMessageBox.warning(self, "選択なし", "行を選択してください。")
            return
        row = selected[0].row()
        category_id = int(self.categories_table.item(row, 0).text())
        current_name = self.categories_table.item(row, 1).text()
        name, ok = QInputDialog.getText(self, "カテゴリ登録情報変更", "カテゴリ名", text=current_name)
        if not ok:
            return
        self._run_action(lambda: self.service.update_category(category_id, name), "カテゴリを変更しました。")

    def import_items_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "物品CSV読み込み", "", "CSV files (*.csv)")
        if not path:
            return
        try:
            count = self.service.import_items_csv(Path(path))
        except (sqlite3.Error, ValueError) as error:
            QMessageBox.warning(self, "CSV読み込み失敗", str(error))
            return
        self.refresh_all()
        QMessageBox.information(self, "CSV読み込み完了", f"{count}件の物品を登録しました。")

    def add_department(self) -> None:
        dialog = DepartmentRegistrationDialog(self.service, self)
        if dialog.exec() != QDialog.Accepted:
            return
        name, barcode = dialog.values()
        self._run_action(lambda: self.service.register_department_with_optional_barcode(name, barcode), "部署を登録しました。")

    def edit_selected_department(self) -> None:
        department_id = self._selected_id(self.departments_table)
        if department_id is None:
            return
        try:
            department = self.service.get_department(department_id)
        except ValueError as error:
            QMessageBox.warning(self, "エラー", str(error))
            return
        dialog = DepartmentEditDialog(department, self)
        if dialog.exec() != QDialog.Accepted:
            return
        name, barcode = dialog.values()
        self._run_action(lambda: self.service.update_department(department_id, name, barcode), "部署を変更しました。")

    def deactivate_selected_item(self) -> None:
        item_id = self._selected_id(self.items_table)
        if item_id is None:
            return
        self._run_action(lambda: self.service.deactivate_item(item_id), "物品を登録解除しました。")

    def toggle_selected_item_active(self) -> None:
        item_id = self._selected_id(self.items_table)
        if item_id is None:
            return
        try:
            item = self.service.get_item(item_id)
        except ValueError as error:
            QMessageBox.warning(self, "エラー", str(error))
            return
        activate = not bool(item["active"])
        message = "物品を有効にしました。" if activate else "物品を無効にしました。"
        self._run_action(lambda: self.service.set_item_active(item_id, activate), message)

    def deactivate_selected_department(self) -> None:
        department_id = self._selected_id(self.departments_table)
        if department_id is None:
            return
        self._run_action(lambda: self.service.deactivate_department(department_id), "部署を登録解除しました。")

    def generate_barcode(self) -> None:
        barcode = self.current_barcode_value()
        if not barcode:
            QMessageBox.warning(self, "入力不足", "値を入力してください。")
            return
        default_path = self.default_output_path("png", f"{safe_filename(barcode)}.png")
        path, _ = QFileDialog.getSaveFileName(self, "バーコードPNGの保存先", str(default_path), "PNG files (*.png)")
        if not path:
            return
        try:
            width, height, quiet_zone = self.barcode_size_values()
            label_text = self.barcode_display_label(barcode)
            written_path = write_barcode_png_file(
                barcode,
                Path(path),
                width,
                height,
                quiet_zone,
                label_text=label_text,
            )
        except ValueError as error:
            QMessageBox.warning(self, "作成失敗", str(error))
            return
        QMessageBox.information(self, "作成完了", f"PNGを作成しました。\n{written_path}")

    def generate_barcode_sheet(self) -> None:
        default_path = self.default_output_path("pdf", "barcodes_a4.pdf")
        path, _ = QFileDialog.getSaveFileName(self, "A4まとめPDFの保存先", str(default_path), "PDF files (*.pdf)")
        if not path:
            return
        try:
            entries = parse_sheet_entries(self.sheet_entries.toPlainText())
            width, height, quiet_zone = self.barcode_size_values()
            written_path = write_barcode_sheet_pdf(
                entries,
                Path(path),
                width,
                height,
                quiet_zone,
            )
        except ValueError as error:
            QMessageBox.warning(self, "作成失敗", str(error))
            return
        QMessageBox.information(self, "作成完了", f"PDFを作成しました。\n{written_path}")

    def add_selected_items_to_sheet_entries(self) -> None:
        item_ids = self._selected_ids(self.items_table)
        if not item_ids:
            QMessageBox.warning(self, "選択なし", "物品を選択してください。")
            return
        try:
            entries = self.service.barcode_entries_for_item_ids(item_ids)
        except ValueError as error:
            QMessageBox.warning(self, "追加失敗", str(error))
            return
        self.append_sheet_entries(entries)
        if self.management_tabs is not None:
            self.management_tabs.setCurrentIndex(4)

    def append_sheet_entries(self, entries: list[tuple[str, str]]) -> None:
        current = self.sheet_entries.toPlainText().rstrip()
        lines = [f"{label},{value}" for label, value in entries]
        text = "\n".join(lines)
        self.sheet_entries.setPlainText(f"{current}\n{text}" if current else text)

    def generate_test_sheet(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "テスト用A4 PDFの保存先",
            str(self.default_output_path("pdf", "pittolog_test_barcodes_a4.pdf")),
            "PDF files (*.pdf)",
        )
        if not path:
            return
        try:
            width, height, quiet_zone = self.barcode_size_values()
            written_path = write_test_sheet_pdf(
                Path(path),
                width,
                height,
                quiet_zone,
            )
        except ValueError as error:
            QMessageBox.warning(self, "作成失敗", str(error))
            return
        QMessageBox.information(self, "作成完了", f"PDFを作成しました。\n{written_path}")

    def barcode_size_values(self) -> tuple[float, float, float]:
        return (
            parse_positive_float(self.barcode_width.text(), "長さ mm"),
            parse_positive_float(self.barcode_height.text(), "高さ mm"),
            parse_positive_float(self.barcode_quiet_zone.text(), "余白 mm"),
        )

    def update_barcode_preview(self) -> None:
        barcode = self.current_barcode_value(default_if_empty=True)
        try:
            width, height, quiet_zone = self.barcode_size_values()
            image = render_code128_png(
                barcode,
                module_width_px=max(1, round(width * 8)),
                height_px=max(80, round(height * 8)),
                quiet_zone_px=max(16, round(quiet_zone * 8)),
                show_text=True,
                append_enter=True,
                label_text=self.barcode_display_label(barcode),
            )
            image = ImageOps.expand(image, border=2, fill="#444444")
        except ValueError as error:
            self.barcode_preview.setPixmap(QPixmap())
            self.barcode_preview.setText(str(error))
            self.barcode_preview_note.setText("")
            return

        buffer = BytesIO()
        image.save(buffer, format="PNG")
        pixmap = QPixmap()
        pixmap.loadFromData(buffer.getvalue(), "PNG")
        self.barcode_preview.setText("")
        self.barcode_preview.setPixmap(pixmap.scaled(330, 92, Qt.KeepAspectRatio, Qt.FastTransformation))
        self.barcode_preview_note.setText(
            f"表示例: {barcode} + Enter / 長さ {width:g}mm、バーコード高さ {height:g}mm、左右余白 {quiet_zone:g}mm"
        )

    def current_barcode_value(self, default_if_empty: bool = False) -> str:
        value = self.barcode_target_combo.currentData()
        if value:
            return str(value)
        if default_if_empty:
            kind = self.barcode_kind.currentText()
            return {"ITEM": "ITEM:000001", "DEPT": "DEPT:0001", "ACTION": "ACTION:001"}.get(kind, "ITEM:000001")
        return ""

    def refresh_barcode_targets(self) -> None:
        kind = self.barcode_kind.currentText()
        self.barcode_category_combo.setVisible(kind == "ITEM")
        self.barcode_category_label.setVisible(kind == "ITEM")
        self.barcode_target_combo.blockSignals(True)
        self.barcode_target_combo.clear()
        category_id = self.barcode_category_combo.currentData() if kind == "ITEM" else None
        for label, value in self.service.barcode_targets(kind, category_id):
            self.barcode_target_combo.addItem(f"{label} / {value}", value)
        self.barcode_target_combo.blockSignals(False)
        self.update_barcode_preview()

    def refresh_barcode_categories(self) -> None:
        current_category_id = self.barcode_category_combo.currentData()
        self.barcode_category_combo.blockSignals(True)
        self.barcode_category_combo.clear()
        self.barcode_category_combo.addItem("すべて", None)
        for category in self.service.list_categories():
            self.barcode_category_combo.addItem(category["name"], category["id"])
            if category["id"] == current_category_id:
                self.barcode_category_combo.setCurrentIndex(self.barcode_category_combo.count() - 1)
        self.barcode_category_combo.blockSignals(False)

    def barcode_display_label(self, barcode: str) -> str:
        try:
            return self.service.barcode_display_label(barcode)
        except ValueError:
            if barcode == "ACTION:001":
                return "確認"
            if barcode == "ACTION:002":
                return "キャンセル"
            return ""

    def handle_root_tab_changed(self, index: int) -> None:
        self.update_mode_style()
        if index == 0:
            self.scan_input.setFocus()
        self.update_scan_ready_indicator()

    def refresh_all(self) -> None:
        self.refresh_item_category_filter()
        self.refresh_loan_category_filter()
        self.refresh_barcode_categories()
        self.refresh_department_filters()
        self.refresh_barcode_targets()
        self.refresh_items()
        self._fill_table(self.categories_table, self.service.list_categories())
        self._fill_table(self.departments_table, self.service.list_departments())
        self.refresh_open_loans()
        self.refresh_events()
        if self.root_tabs.currentIndex() == 0:
            self.scan_input.setFocus()
        self.update_scan_ready_indicator()

    def refresh_items(self) -> None:
        self._fill_table(self.items_table, self.current_item_rows())

    def current_item_rows(self):
        return self.service.list_items(
            query=self.item_query_input.text(),
            sort_by=str(self.item_sort_field.currentData() or "name"),
            sort_desc=bool(self.item_sort_order.currentData()),
            category_id=self.item_category_filter.currentData(),
            status=str(self.item_status_filter.currentData() or ""),
            active_filter=str(self.item_active_filter.currentData() or ""),
            loan_department_id=self.item_loan_department_filter.currentData(),
        )

    def clear_item_query(self) -> None:
        self.item_query_input.clear()
        self.item_category_filter.setCurrentIndex(0)
        self.item_status_filter.setCurrentIndex(0)
        self.item_active_filter.setCurrentIndex(0)
        self.item_loan_department_filter.setCurrentIndex(0)
        self.refresh_items()

    def open_loan_rows(self):
        return self.service.list_open_loans(
            query=self.loan_query_input.text(),
            sort_by=str(self.loan_sort_field.currentData() or "loaned_at"),
            sort_desc=bool(self.loan_sort_order.currentData()),
            department_id=self.loan_department_filter.currentData(),
            category_id=self.loan_category_filter.currentData(),
        )

    def refresh_open_loans(self) -> None:
        self._fill_table(self.loans_table, self.open_loan_rows())
        self.adjust_open_loan_columns()

    def reset_open_loan_filters(self) -> None:
        self.loan_query_input.clear()
        self.loan_category_filter.setCurrentIndex(0)
        self.loan_department_filter.setCurrentIndex(0)
        self.loan_sort_field.setCurrentIndex(0)
        self.loan_sort_order.setCurrentIndex(0)
        self.refresh_open_loans()

    def event_rows(self):
        return self.service.list_events(
            query=self.event_query_input.text(),
            sort_by=str(self.event_sort_field.currentData() or "created_at"),
            sort_desc=bool(self.event_sort_order.currentData()),
            date_from=self.event_date_from.date().toString("yyyy-MM-dd") if self.event_date_filter.isChecked() else "",
            date_to=self.event_date_to.date().toString("yyyy-MM-dd") if self.event_date_filter.isChecked() else "",
            event_type=str(self.event_type_filter.currentData() or ""),
            department_id=self.event_department_filter.currentData(),
        )

    def refresh_events(self) -> None:
        self._fill_table(self.events_table, self.event_rows())

    def clear_event_query(self) -> None:
        self.event_query_input.clear()
        self.event_type_filter.setCurrentIndex(0)
        self.event_department_filter.setCurrentIndex(0)
        self.event_sort_field.setCurrentIndex(0)
        self.event_sort_order.setCurrentIndex(0)
        self.event_date_filter.setChecked(False)
        self.refresh_events()

    def refresh_item_category_filter(self) -> None:
        current_category_id = self.item_category_filter.currentData()
        self.item_category_filter.blockSignals(True)
        self.item_category_filter.clear()
        self.item_category_filter.addItem("すべて", None)
        for category in self.service.list_categories():
            self.item_category_filter.addItem(category["name"], category["id"])
            if category["id"] == current_category_id:
                self.item_category_filter.setCurrentIndex(self.item_category_filter.count() - 1)
        self.item_category_filter.blockSignals(False)

    def refresh_loan_category_filter(self) -> None:
        current_category_id = self.loan_category_filter.currentData()
        self.loan_category_filter.blockSignals(True)
        self.loan_category_filter.clear()
        self.loan_category_filter.addItem("すべて", None)
        for category in self.service.list_categories():
            self.loan_category_filter.addItem(category["name"], category["id"])
            if category["id"] == current_category_id:
                self.loan_category_filter.setCurrentIndex(self.loan_category_filter.count() - 1)
        self.loan_category_filter.blockSignals(False)

    def refresh_department_filters(self) -> None:
        departments = self.service.list_departments()
        for combo in (self.item_loan_department_filter, self.loan_department_filter, self.event_department_filter):
            current_department_id = combo.currentData()
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("すべて", None)
            for department in departments:
                combo.addItem(department["name"], department["id"])
                if department["id"] == current_department_id:
                    combo.setCurrentIndex(combo.count() - 1)
            combo.blockSignals(False)

    def adjust_open_loan_columns(self) -> None:
        if self.loans_table.columnCount() < 5:
            return
        header = self.loans_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        self.loans_table.setColumnWidth(0, 145)
        self.loans_table.setColumnWidth(2, 95)
        self.loans_table.setColumnWidth(3, 125)
        self.loans_table.setColumnWidth(4, 95)
        header.setSectionResizeMode(1, QHeaderView.Stretch)

    def export_items(self) -> None:
        self._export("items.csv", self.current_item_rows())

    def export_categories(self) -> None:
        self._export("categories.csv", self.service.list_categories())

    def export_departments(self) -> None:
        self._export("departments.csv", self.service.list_departments())

    def export_loans(self) -> None:
        self._export("open_loans.csv", self.open_loan_rows())

    def export_events(self) -> None:
        self._export("events.csv", self.event_rows())

    def _export(self, default_name: str, rows) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "CSV出力", str(self.default_output_path("csv", default_name)), "CSV files (*.csv)")
        if not path:
            return
        self.service.export_csv(Path(path), rows)
        QMessageBox.information(self, "CSV出力", "CSVを出力しました。")

    def default_output_path(self, kind: str, filename: str) -> Path:
        output_dirs = {
            "csv": self.csv_output_dir,
            "png": self.png_output_dir,
            "pdf": self.pdf_output_dir,
        }
        output_dir = Path(output_dirs[kind]).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / filename

    def _run_action(self, action, message: str) -> None:
        try:
            action()
        except (sqlite3.Error, ValueError) as error:
            QMessageBox.warning(self, "エラー", str(error))
            return
        self.refresh_all()
        QMessageBox.information(self, "完了", message)

    def _selected_id(self, table: QTableWidget) -> int | None:
        selected = table.selectionModel().selectedRows()
        if not selected:
            QMessageBox.warning(self, "選択なし", "行を選択してください。")
            return None
        return int(table.item(selected[0].row(), 0).text())

    def _selected_ids(self, table: QTableWidget) -> list[int]:
        selected = table.selectionModel().selectedRows()
        return [int(table.item(index.row(), 0).text()) for index in selected]

    def _fill_table(self, table: QTableWidget, rows) -> None:
        table.clear()
        if not rows:
            table.setRowCount(0)
            table.setColumnCount(0)
            return
        headers = list(rows[0].keys())
        table.setColumnCount(len(headers))
        table.setRowCount(len(rows))
        table.setHorizontalHeaderLabels([TABLE_HEADER_LABELS.get(header, header) for header in headers])
        if "id" in headers:
            table.setColumnHidden(headers.index("id"), True)
        if "note" in headers:
            table.setColumnHidden(headers.index("note"), True)
        for row_index, row in enumerate(rows):
            for column_index, header in enumerate(headers):
                value = row[header]
                if value is None and header == "barcode":
                    text = "未登録"
                else:
                    text = "" if value is None else str(value)
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                table.setItem(row_index, column_index, item)


class ItemRegistrationDialog(QDialog):
    def __init__(self, service: LoanService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("物品登録")

        self.name_input = QLineEdit()
        self.category_combo = RoundedComboBox()
        for category in service.list_categories():
            self.category_combo.addItem(category["name"], category["id"])

        self.manual_barcode = QCheckBox("手動でバーコードを指定する")
        self.barcode_input = QLineEdit(service.next_item_barcode())
        self.barcode_input.setEnabled(False)
        self.manual_barcode.toggled.connect(self.barcode_input.setEnabled)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QFormLayout(self)
        layout.addRow("物品名", self.name_input)
        layout.addRow("カテゴリ", self.category_combo)
        layout.addRow("次の自動バーコード", QLabel(service.next_item_barcode()))
        layout.addRow(self.manual_barcode)
        layout.addRow("手動バーコード", self.barcode_input)
        layout.addRow(buttons)

    def accept(self) -> None:
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "入力不足", "物品名を入力してください。")
            return
        if self.category_combo.currentData() is None:
            QMessageBox.warning(self, "入力不足", "先にカテゴリを登録してください。")
            return
        super().accept()

    def values(self) -> tuple[str, int, str]:
        barcode = self.barcode_input.text() if self.manual_barcode.isChecked() else ""
        return self.name_input.text(), int(self.category_combo.currentData()), barcode


class ItemEditDialog(QDialog):
    def __init__(self, service: LoanService, item, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("物品登録情報変更")

        self.name_input = QLineEdit(item["name"])
        self.category_combo = RoundedComboBox()
        for category in service.list_categories():
            self.category_combo.addItem(category["name"], category["id"])
            if category["id"] == item["category_id"]:
                self.category_combo.setCurrentIndex(self.category_combo.count() - 1)

        self.change_barcode = QCheckBox("バーコードも変更する")
        self.barcode_input = QLineEdit(item["barcode"] or "")
        self.barcode_input.setEnabled(False)
        self.change_barcode.toggled.connect(self.barcode_input.setEnabled)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QFormLayout(self)
        layout.addRow("物品名", self.name_input)
        layout.addRow("カテゴリ", self.category_combo)
        layout.addRow(self.change_barcode)
        layout.addRow("バーコード", self.barcode_input)
        layout.addRow(buttons)

    def accept(self) -> None:
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "入力不足", "物品名を入力してください。")
            return
        if self.category_combo.currentData() is None:
            QMessageBox.warning(self, "入力不足", "カテゴリを選択してください。")
            return
        if self.change_barcode.isChecked() and not self.barcode_input.text().strip():
            QMessageBox.warning(self, "入力不足", "バーコードを入力してください。")
            return
        super().accept()

    def values(self) -> tuple[str, int, str | None]:
        barcode = self.barcode_input.text() if self.change_barcode.isChecked() else None
        return self.name_input.text(), int(self.category_combo.currentData()), barcode


def parse_sheet_entries(text: str) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        if "," in line:
            label, value = line.split(",", 1)
        elif "\t" in line:
            label, value = line.split("\t", 1)
        else:
            label = value = line
        label = label.strip()
        value = value.strip().upper()
        if not label or not value:
            raise ValueError(f"{line_number}行目: ラベルとバーコード値を入力してください。")
        entries.append((label, value))
    if not entries:
        raise ValueError("バーコード一覧を入力してください。")
    return entries


def parse_positive_float(text: str, label: str) -> float:
    normalized = text.strip().replace("．", ".")
    if not normalized:
        raise ValueError(f"{label}を入力してください。")
    try:
        value = float(normalized)
    except ValueError as error:
        raise ValueError(f"{label}は数字で入力してください。入力値: {text}") from error
    if value <= 0:
        raise ValueError(f"{label}は0より大きい数字で入力してください。入力値: {text}")
    return value


def parse_int_range(text: str, label: str, minimum: int, maximum: int) -> int:
    normalized = text.strip()
    if not normalized:
        raise ValueError(f"{label}を入力してください。")
    if not normalized.isdigit():
        raise ValueError(f"{label}は数字だけで入力してください。入力値: {text}")
    value = int(normalized)
    if value < minimum or value > maximum:
        raise ValueError(f"{label}は{minimum}から{maximum}の間で入力してください。入力値: {text}")
    return value


def scan_selection_text(item_name: str | None, department_name: str | None) -> str:
    if item_name and department_name:
        return f"{item_name} : {department_name}"
    return item_name or ""


def scan_mode_title(state: str) -> str:
    return {
        "item": "貸出・返却 物品スキャン",
        "loan": "貸出先スキャン",
        "department": "貸出先スキャン",
        "confirm": "貸出確認",
        "return": "返却確認",
        "error": "エラー",
        "done": "物品スキャン",
    }.get(state, "物品スキャン")


def strong(text: str) -> str:
    return f"<strong>{escape(text)}</strong>"


def detail_block(first: tuple[str, str], second: tuple[str, str]) -> str:
    rows = []
    for label, value in (first, second):
        rows.append(
            "<tr>"
            "<td width='120' style='font-size:30px; font-weight:900; padding:0 0 3px 0; white-space:nowrap;'>"
            f"{escape(label)}</td>"
            "<td style='font-size:30px; font-weight:900; padding:0 6px 3px 0;'>:</td>"
            "<td style='font-size:30px; font-weight:900; padding:0 0 3px 0;'>"
            f"{escape(value)}</td>"
            "</tr>"
        )
    return "<table cellspacing='0' cellpadding='0'>" + "".join(rows) + "</table>"


def detail_spacer() -> str:
    return "<span style='font-size:8px;'>&nbsp;</span><br>"


def html_lines(text: str) -> str:
    return "<br>".join(escape(line) for line in text.splitlines())


def repolish_widget(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def filter_group() -> QFrame:
    frame = QFrame()
    frame.setObjectName("FilterGroup")
    return frame


def barcode_panel_stylesheet() -> str:
    return """
        QFrame#BarcodePanel {
            background-color: #ffffff;
            border: 1px solid #d7e0ea;
            border-radius: 10px;
        }
        QFrame#BarcodePanel QLabel,
        QFrame#BarcodePanel QWidget {
            background-color: #ffffff;
        }
        QFrame#BarcodePanel QLineEdit,
        QFrame#BarcodePanel QComboBox,
        QFrame#BarcodePanel QTextEdit {
            background-color: #ffffff;
        }
    """


class DepartmentRegistrationDialog(QDialog):
    def __init__(self, service: LoanService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("部署登録")

        self.name_input = QLineEdit()
        self.manual_barcode = QCheckBox("手動でバーコードを指定する")
        self.barcode_input = QLineEdit(service.next_department_barcode())
        self.barcode_input.setEnabled(False)
        self.manual_barcode.toggled.connect(self.barcode_input.setEnabled)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QFormLayout(self)
        layout.addRow("部署名", self.name_input)
        layout.addRow("次の自動バーコード", QLabel(service.next_department_barcode()))
        layout.addRow(self.manual_barcode)
        layout.addRow("手動バーコード", self.barcode_input)
        layout.addRow(buttons)

    def accept(self) -> None:
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "入力不足", "部署名を入力してください。")
            return
        super().accept()

    def values(self) -> tuple[str, str]:
        barcode = self.barcode_input.text() if self.manual_barcode.isChecked() else ""
        return self.name_input.text(), barcode


class DepartmentEditDialog(QDialog):
    def __init__(self, department, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("部署登録情報変更")

        self.name_input = QLineEdit(department["name"])
        self.change_barcode = QCheckBox("バーコードも変更する")
        self.barcode_input = QLineEdit(department["barcode"] or "")
        self.barcode_input.setEnabled(False)
        self.change_barcode.toggled.connect(self.barcode_input.setEnabled)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QFormLayout(self)
        layout.addRow("部署名", self.name_input)
        layout.addRow(self.change_barcode)
        layout.addRow("バーコード", self.barcode_input)
        layout.addRow(buttons)

    def accept(self) -> None:
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "入力不足", "部署名を入力してください。")
            return
        if self.change_barcode.isChecked() and not self.barcode_input.text().strip():
            QMessageBox.warning(self, "入力不足", "バーコードを入力してください。")
            return
        super().accept()

    def values(self) -> tuple[str, str | None]:
        barcode = self.barcode_input.text() if self.change_barcode.isChecked() else None
        return self.name_input.text(), barcode
