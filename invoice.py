import datetime
import os
import platform
import subprocess
from decimal import Decimal
from typing import List, Optional

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from models import Company, InvoiceLine


def create_invoice_excel(
    company: Company,
    invoice_lines: List[InvoiceLine],
    담당자: Optional[str] = None
) -> Optional[str]:
    """
    주어진 회사 정보와 품목들로 거래명세서 Excel 파일을 생성합니다.

    Args:
        company: 거래명세서를 받을 회사 객체.
        invoice_lines: 명세서에 포함될 품목 라인 리스트.
        담당자: (선택) 명세서에 포함될 담당자 이름.

    Returns:
        생성된 Excel 파일의 경로. 실패 시 None.
    """
    wb = Workbook()
    ws = wb.active
    if ws is None: # Should not happen with a new workbook
        return None
    ws.title = "Invoice"

    # --- 스타일 정의 ---
    header_font = Font(name="맑은 고딕", size=18, bold=True)
    title_font = Font(name="맑은 고딕", size=11, bold=True)
    normal_font = Font(name="맑은 고딕", size=10)
    currency_format = "#,##0\"원\""
    total_currency_format = "_(\"₩\"* #,##0_);_(\"₩\"* (#,##0);_(\"₩\"* \"-\"??_);_(@_)" # Excel 기본 통화 형식과 유사하게
    
    thin_border_side = Side(style="thin")
    thin_border = Border(
        left=thin_border_side,
        right=thin_border_side,
        top=thin_border_side,
        bottom=thin_border_side,
    )
    bold_bottom_border = Border(bottom=Side(style="medium"))
    total_border = Border(
        left=thin_border_side,
        right=thin_border_side,
        top=Side(style="medium"),
        bottom=Side(style="medium"),
    )
    
    center_align = Alignment(horizontal="center", vertical="center")
    right_align = Alignment(horizontal="right", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")

    # --- 헤더 섹션 ---
    ws.merge_cells("A1:E1")
    title_cell = ws["A1"]
    title_cell.value = "거 래 명 세 서"
    title_cell.font = header_font
    title_cell.alignment = center_align
    ws.row_dimensions[1].height = 30

    ws["A3"] = "공급받는자:"
    ws["A3"].font = title_font
    ws["B3"] = company.name
    ws["B3"].font = normal_font
    ws["B3"].alignment = left_align
    ws.merge_cells("B3:C3")


    ws["A4"] = "연락처:"
    ws["A4"].font = title_font
    ws["B4"] = company.contact
    ws["B4"].font = normal_font
    ws["B4"].alignment = left_align
    ws.merge_cells("B4:C4")

    current_date = datetime.datetime.now().strftime("%Y년 %m월 %d일")
    ws["D3"] = "발행일:"
    ws["D3"].font = title_font
    ws["D3"].alignment = right_align
    ws["E3"] = current_date
    ws["E3"].font = normal_font
    ws["E3"].alignment = left_align
    
    if 담당자:
        ws["D4"] = "담당자:"
        ws["D4"].font = title_font
        ws["D4"].alignment = right_align
        ws["E4"] = 담당자
        ws["E4"].font = normal_font
        ws["E4"].alignment = left_align

    # --- 테이블 헤더 ---
    table_headers = ["No.", "품목명", "수량", "단가", "금액"]
    header_start_row = 6
    for col_idx, header_text in enumerate(table_headers, start=1):
        cell = ws.cell(row=header_start_row, column=col_idx, value=header_text)
        cell.font = title_font
        cell.alignment = center_align
        cell.border = thin_border
        cell.fill = PatternFill(start_color="E0E0E0", end_color="E0E0E0", fill_type="solid")

    # --- 테이블 내용 ---
    current_row = header_start_row + 1
    total_amount = Decimal("0")

    for idx, line in enumerate(invoice_lines, start=1):
        ws.cell(row=current_row, column=1, value=idx).font = normal_font
        ws.cell(row=current_row, column=1).alignment = center_align
        ws.cell(row=current_row, column=1).border = thin_border
        
        ws.cell(row=current_row, column=2, value=line.item_name).font = normal_font
        ws.cell(row=current_row, column=2).border = thin_border
        
        ws.cell(row=current_row, column=3, value=line.quantity).font = normal_font
        ws.cell(row=current_row, column=3).alignment = right_align
        ws.cell(row=current_row, column=3).border = thin_border
        
        unit_price_cell = ws.cell(row=current_row, column=4, value=line.unit_price)
        unit_price_cell.font = normal_font
        unit_price_cell.number_format = currency_format
        unit_price_cell.alignment = right_align
        unit_price_cell.border = thin_border
        
        line_total_cell = ws.cell(row=current_row, column=5, value=line.line_total)
        line_total_cell.font = normal_font
        line_total_cell.number_format = currency_format
        line_total_cell.alignment = right_align
        line_total_cell.border = thin_border
        
        total_amount += line.line_total
        current_row += 1

    # --- 합계 행 ---
    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=4)
    total_label_cell = ws.cell(row=current_row, column=1, value="총 합계 (VAT 포함)")
    total_label_cell.font = Font(name="맑은 고딕", size=11, bold=True)
    total_label_cell.alignment = center_align
    total_label_cell.border = total_border
    
    total_value_cell = ws.cell(row=current_row, column=5, value=total_amount)
    total_value_cell.font = Font(name="맑은 고딕", size=11, bold=True)
    total_value_cell.number_format = total_currency_format # Excel 기본 통화 형식
    total_value_cell.alignment = right_align
    total_value_cell.border = total_border
    
    # 열 너비 자동 조정 (근사치)
    column_widths = {'A': 5, 'B': 30, 'C': 10, 'D': 15, 'E': 18}
    for col, width in column_widths.items():
        ws.column_dimensions[col].width = width
    
    # --- 파일 저장 ---
    # 파일명: YYYYMMDD_{company_name}_invoice.xlsx
    # 회사명에서 특수문자 제거
    safe_company_name = "".join(c if c.isalnum() or c in " _-" else "" for c in company.name).strip()
    if not safe_company_name: # 회사명이 모두 특수문자였을 경우
        safe_company_name = "invoice"

    filename = f"{datetime.datetime.now().strftime('%Y%m%d')}_{safe_company_name}_invoice.xlsx"
    
    try:
        filepath = os.path.join(os.getcwd(), filename)
        wb.save(filepath)
        print(f"거래명세서가 '{filepath}'에 저장되었습니다.")
        return filepath
    except Exception as e:
        print(f"Excel 파일 저장 중 오류 발생: {e}")
        return None

def open_file_explorer(filepath: str):
    """
    주어진 파일 경로를 파일 탐색기에서 엽니다.
    """
    try:
        if platform.system() == "Windows":
            subprocess.run(['explorer', '/select,', os.path.normpath(filepath)])
        elif platform.system() == "Darwin": # macOS
            subprocess.run(['open', '-R', os.path.normpath(filepath)])
        else: # Linux and other Unix-like
            subprocess.run(['xdg-open', os.path.dirname(os.path.normpath(filepath))])
        print(f"파일 탐색기에서 '{filepath}' 위치를 열었습니다.")
    except Exception as e:
        print(f"파일 탐색기 열기 중 오류 발생: {e}")


if __name__ == '__main__':
    from models import Item # Item 클래스 임포트
    # 테스트용 데이터
    test_company = Company(id="test-co-1", name="테스트 주식회사 (Test Co.)", contact="02-123-4567")
    test_items = [
        InvoiceLine(item=Item(id="item-1", name="고성능 노트북", unit_price=Decimal("1500000.00")), quantity=1),
        InvoiceLine(item=Item(id="item-2", name="무선 마우스 세트", unit_price=Decimal("45000.50")), quantity=5),
        InvoiceLine(item=Item(id="item-3", name="기계식 키보드 (청축)", unit_price=Decimal("120000.00")), quantity=2),
    ]

    # Excel 파일 생성 테스트
    generated_filepath = create_invoice_excel(test_company, test_items, 담당자="김철수")

    if generated_filepath:
        print(f"\n테스트 Excel 파일 생성 완료: {generated_filepath}")
        # 생성된 파일 열기 (선택 사항)
        # open_file_explorer(generated_filepath)
    else:
        print("\n테스트 Excel 파일 생성 실패.")

    # 특수문자 포함 회사명 테스트
    test_company_special_chars = Company(id="test-co-2", name="별표*회사!@#$", contact="특수@문자.com")
    generated_filepath_special = create_invoice_excel(test_company_special_chars, test_items)
    if generated_filepath_special:
        print(f"\n특수문자 회사명 테스트 Excel 파일 생성 완료: {generated_filepath_special}")
    else:
        print("\n특수문자 회사명 테스트 Excel 파일 생성 실패.")
