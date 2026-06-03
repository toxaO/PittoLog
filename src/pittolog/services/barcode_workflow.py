from __future__ import annotations

from dataclasses import dataclass

from pittolog.models import ScanResult
from pittolog.services.loan_service import LoanService, normalize_barcode

@dataclass
class BarcodeWorkflow:
    service: LoanService
    item_barcode: str | None = None
    department_barcode: str | None = None
    action_mode: str | None = None

    def reset(self) -> ScanResult:
        self.item_barcode = None
        self.department_barcode = None
        self.action_mode = None
        return ScanResult(True, "入力をキャンセルしました。")

    def fail_and_reset(self, message: str) -> ScanResult:
        self.item_barcode = None
        self.department_barcode = None
        self.action_mode = None
        return ScanResult(False, message)

    def fail(self, message: str) -> ScanResult:
        return ScanResult(False, message, self.item_barcode, self.department_barcode)

    def handle_scan(self, raw_value: str) -> ScanResult:
        barcode = normalize_barcode(raw_value)
        if not barcode:
            return self.fail("空のバーコードです。\nもう一度スキャンしてください。")

        try:
            if barcode == "ACTION:002":
                return self.reset()
            if barcode.startswith("ITEM:"):
                item = self.service.validate_item_barcode(barcode)
                self.item_barcode = barcode
                self.department_barcode = None
                if self.service.item_is_on_loan(barcode):
                    self.action_mode = "return"
                    return ScanResult(True, "貸出中の物品です。\n返却する場合は確認バーコードをスキャンしてください。\nやめる場合はキャンセル用バーコードをスキャンしてください。", barcode, item_name=str(item["name"]))
                self.action_mode = "loan"
                return ScanResult(True, "物品を選択しました。\n貸出先の部署バーコードをスキャンしてください。", barcode, item_name=str(item["name"]))
            if barcode.startswith("DEPT:"):
                if self.item_barcode is None:
                    return self.fail("先に物品バーコードをスキャンしてください。")
                if self.action_mode == "return":
                    return self.fail("返却確認中のため、部署バーコードは使えません。\n確認、またはキャンセルをスキャンしてください。")
                department = self.service.validate_department_barcode(barcode)
                self.department_barcode = barcode
                self.action_mode = "loan"
                return ScanResult(True, "部署を選択しました。\n貸出する場合は確認バーコードをスキャンしてください。\nやめる場合はキャンセル用バーコードをスキャンしてください。", self.item_barcode, barcode, self.service.item_name_for_barcode(self.item_barcode), str(department["name"]))
            if barcode == "ACTION:001":
                return self._confirm()
            if barcode in ("ACTION:LOAN", "ACTION:RETURN"):
                return self.fail("この操作バーコードは現在使えません。\n確認、またはキャンセル用バーコードを使ってください。")
        except ValueError as error:
            return self.fail(f"{error}\n今の画面で必要なバーコードをスキャンしてください。")

        return self.fail(f"読み取った値を処理できません。\nITEM:、DEPT:、ACTION: で始まるバーコードを確認してください。\n今の画面で必要なバーコードをスキャンしてください。\n読み取り値: {barcode}")

    def _confirm(self) -> ScanResult:
        if self.item_barcode is None:
            return self.fail("先に物品バーコードをスキャンしてください。")
        if self.action_mode == "return":
            return self._return()
        if self.department_barcode is None:
            return self.fail("貸出先の部署バーコードがまだ読み取られていません。\n部署コードをスキャンしてください。")
        return self._loan()

    def _loan(self) -> ScanResult:
        if self.item_barcode is None:
            return self.fail("先に物品バーコードをスキャンしてください。")
        if self.department_barcode is None:
            return self.fail("貸出先の部署バーコードがまだ読み取られていません。\n部署コードをスキャンしてください。")
        item_name = self.service.item_name_for_barcode(self.item_barcode)
        department_name = self.service.department_name_for_barcode(self.department_barcode)
        message = self.service.loan_item(self.item_barcode, self.department_barcode)
        self.item_barcode = None
        self.department_barcode = None
        self.action_mode = None
        return ScanResult(True, message, item_name=item_name, department_name=department_name, operation="貸出")

    def _return(self) -> ScanResult:
        if self.item_barcode is None:
            return self.fail("先に物品バーコードをスキャンしてください。")
        item_name = self.service.item_name_for_barcode(self.item_barcode)
        department_name = self.service.open_loan_department_name_for_item_barcode(self.item_barcode)
        message = self.service.return_item(self.item_barcode)
        self.item_barcode = None
        self.department_barcode = None
        self.action_mode = None
        return ScanResult(True, message, item_name=item_name, department_name=department_name, operation="返却")
