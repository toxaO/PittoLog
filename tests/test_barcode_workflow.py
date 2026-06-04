from __future__ import annotations

from pittolog.db import connect, initialize_database
from pittolog.services.barcode_workflow import BarcodeWorkflow
from pittolog.services.loan_service import LoanService


def make_workflow(tmp_path) -> BarcodeWorkflow:
    connection = connect(tmp_path / "test.sqlite")
    initialize_database(connection)
    service = LoanService(connection)
    service.register_item("ITEM:000001", "プロジェクター")
    service.register_department("DEPT:0001", "総務")
    return BarcodeWorkflow(service)


def test_scan_loan_flow(tmp_path) -> None:
    workflow = make_workflow(tmp_path)

    assert workflow.handle_scan("ITEM:000001").ok
    assert workflow.handle_scan("DEPT:0001").ok
    result = workflow.handle_scan("ACTION:001")

    assert result.ok
    assert result.message == "貸出完了: プロジェクター -> 総務"
    assert result.operation == "貸出"
    assert result.item_name == "プロジェクター"
    assert result.department_name == "総務"
    assert workflow.item_barcode is None
    assert workflow.department_barcode is None


def test_scan_return_flow(tmp_path) -> None:
    workflow = make_workflow(tmp_path)
    workflow.handle_scan("ITEM:000001")
    workflow.handle_scan("DEPT:0001")
    workflow.handle_scan("ACTION:001")

    assert workflow.handle_scan("ITEM:000001").ok
    result = workflow.handle_scan("ACTION+001")

    assert result.ok
    assert result.message == "返却完了: プロジェクター"
    assert result.operation == "返却"
    assert result.item_name == "プロジェクター"
    assert result.department_name == "総務"


def test_loaned_item_enters_return_confirmation(tmp_path) -> None:
    workflow = make_workflow(tmp_path)
    workflow.handle_scan("ITEM:000001")
    workflow.handle_scan("DEPT:0001")
    workflow.handle_scan("ACTION:001")

    result = workflow.handle_scan("ITEM:000001")

    assert result.ok
    assert result.item_name == "プロジェクター"
    assert workflow.action_mode == "return"
    assert "返却する場合は確認" in result.message


def test_department_requires_item_first(tmp_path) -> None:
    workflow = make_workflow(tmp_path)

    result = workflow.handle_scan("DEPT:0001")

    assert not result.ok
    assert "先に物品" in result.message


def test_scan_accepts_plus_separator_from_scanner(tmp_path) -> None:
    workflow = make_workflow(tmp_path)

    assert workflow.handle_scan("ITEM+000001").ok
    assert workflow.handle_scan("DEPT+0001").ok
    result = workflow.handle_scan("ACTION+001")

    assert result.ok
    assert result.message == "貸出完了: プロジェクター -> 総務"


def test_scan_requires_known_prefix(tmp_path) -> None:
    workflow = make_workflow(tmp_path)

    result = workflow.handle_scan("000001")

    assert not result.ok
    assert result.message == "無効なバーコードがスキャンされました。"


def test_unknown_department_barcode_fails_when_scanned(tmp_path) -> None:
    workflow = make_workflow(tmp_path)
    assert workflow.handle_scan("ITEM:000001").ok

    result = workflow.handle_scan("DEPT:9999")

    assert not result.ok
    assert "未登録の部署バーコード" in result.message
    assert workflow.item_barcode == "ITEM:000001"


def test_legacy_loan_and_return_actions_are_rejected(tmp_path) -> None:
    workflow = make_workflow(tmp_path)

    workflow.handle_scan("ITEM:000001")
    workflow.handle_scan("DEPT:0001")
    result = workflow.handle_scan("ACTION:LOAN")

    assert not result.ok
    assert "現在使えません" in result.message
    assert workflow.item_barcode == "ITEM:000001"
    assert workflow.department_barcode == "DEPT:0001"


def test_cancel_accepts_plus_separator_from_scanner(tmp_path) -> None:
    workflow = make_workflow(tmp_path)
    workflow.handle_scan("ITEM:000001")

    result = workflow.handle_scan("ACTION+002")

    assert result.ok
    assert workflow.item_barcode is None


def test_old_confirm_and_cancel_actions_are_rejected(tmp_path) -> None:
    workflow = make_workflow(tmp_path)
    workflow.handle_scan("ITEM:000001")
    result = workflow.handle_scan("ACTION+CANCEL")

    assert not result.ok
    assert workflow.item_barcode == "ITEM:000001"

    workflow.handle_scan("ITEM:000001")
    workflow.handle_scan("DEPT:0001")
    result = workflow.handle_scan("ACTION:CONFIRM")

    assert not result.ok
    assert workflow.item_barcode == "ITEM:000001"
    assert workflow.department_barcode == "DEPT:0001"
