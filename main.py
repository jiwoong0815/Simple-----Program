import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from decimal import Decimal, InvalidOperation
from typing import List, Optional, Dict, Any
import uuid # For new item/company IDs if not handled by models default_factory

from models import Company, Item, InvoiceLine
import storage
import invoice

class App(tk.Tk):
    """메인 애플리케이션 GUI 클래스"""

    def __init__(self):
        super().__init__()
        self.title("거래명세서 생성 툴")
        self.geometry("900x700") # 창 크기 조정

        # # 데이터 로드 - COMMENT OUT FOR NOW
        # self.data = storage.load_data()
        # self.companies: List[Company] = [] # self.data["companies"]
        # self.items: List[Item] = [] # self.data["items"]
        
        # # 현재 작성 중인 명세서 라인들
        # self.current_invoice_lines: List[InvoiceLine] = []
        # self.selected_company_for_invoice: Optional[Company] = None
        # self.담당자_entry_var = tk.StringVar()


        # Notebook (탭) 생성
        self.notebook = ttk.Notebook(self)
        
        # 탭 생성 (Simplified)
        self.invoice_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.invoice_tab, text="거래명세서 작성")
        ttk.Label(self.invoice_tab, text="Test Label in Invoice Tab").pack(padx=20, pady=20)

        # # COMMENT OUT OTHER TABS AND THEIR CREATION
        # self.company_management_tab = ttk.Frame(self.notebook)
        # self.item_management_tab = ttk.Frame(self.notebook)
        # self.notebook.add(self.company_management_tab, text="거래처 관리")
        # self.notebook.add(self.item_management_tab, text="품목 관리")

        # # 각 탭 UI 구성 - COMMENT OUT ORIGINAL CALLS
        # # self._create_invoice_tab() # Simplified above
        # # self._create_company_management_tab()
        # # self._create_item_management_tab()

        # Notebook을 모든 내용이 구성된 후 pack
        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)

        # # 초기 데이터 표시 - COMMENT OUT REFRESH CALLS
        # self._refresh_company_listbox_invoice_tab()
        # self._refresh_item_listbox_invoice_tab()
        # self._refresh_company_management_listbox()
        # self._refresh_item_management_listbox()
        
        # # 창 닫기 시 데이터 저장 - COMMENT OUT PROTOCOL HANDLER FOR NOW
        # self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _on_closing(self):
        """창 닫기 시 데이터 저장 확인"""
        if messagebox.askokcancel("종료 확인", "프로그램을 종료하시겠습니까? 변경사항이 저장됩니다."):
            storage.save_data(self.companies, self.items)
            self.destroy()

    # --- 거래명세서 작성 탭 ---
    def _create_invoice_tab(self):
        """거래명세서 작성 탭의 UI를 생성합니다."""
        tab = self.invoice_tab
        
        # 상단 프레임: 회사 선택, 품목 선택, 수량 입력
        top_frame = ttk.Frame(tab)
        top_frame.pack(fill="x", padx=5, pady=5)

        # 회사 선택
        ttk.Label(top_frame, text="거래처 선택:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.invoice_company_combo = ttk.Combobox(top_frame, state="readonly", width=30)
        self.invoice_company_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.invoice_company_combo.bind("<<ComboboxSelected>>", self._on_invoice_company_selected)
        
        ttk.Label(top_frame, text="담당자 (선택):").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.담당자_entry = ttk.Entry(top_frame, textvariable=self.담당자_entry_var, width=20)
        self.담당자_entry.grid(row=0, column=3, padx=5, pady=5, sticky="ew")


        # 품목 검색 및 선택
        item_selection_frame = ttk.LabelFrame(tab, text="품목 선택 및 추가")
        item_selection_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(item_selection_frame, text="품목 검색:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.invoice_item_search_var = tk.StringVar()
        self.invoice_item_search_var.trace_add("write", self._filter_invoice_items)
        ttk.Entry(item_selection_frame, textvariable=self.invoice_item_search_var, width=30).grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.invoice_item_listbox = tk.Listbox(item_selection_frame, height=6, exportselection=False, width=50)
        self.invoice_item_listbox.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        item_scrollbar = ttk.Scrollbar(item_selection_frame, orient="vertical", command=self.invoice_item_listbox.yview)
        item_scrollbar.grid(row=1, column=2, sticky="ns")
        self.invoice_item_listbox.config(yscrollcommand=item_scrollbar.set)

        ttk.Label(item_selection_frame, text="수량:").grid(row=0, column=3, padx=5, pady=5, sticky="w")
        self.invoice_item_quantity_spinbox = ttk.Spinbox(item_selection_frame, from_=1, to=9999, width=8)
        self.invoice_item_quantity_spinbox.set(1)
        self.invoice_item_quantity_spinbox.grid(row=0, column=4, padx=5, pady=5)
        
        ttk.Button(item_selection_frame, text="품목 추가", command=self._add_item_to_invoice).grid(row=1, column=3, columnspan=2, padx=5, pady=10, sticky="ew")

        item_selection_frame.grid_columnconfigure(1, weight=1) # 검색창과 리스트박스 확장

        # 명세서 품목 테이블 (Treeview)
        invoice_table_frame = ttk.LabelFrame(tab, text="거래명세서 품목")
        invoice_table_frame.pack(expand=True, fill="both", padx=5, pady=5)

        columns = ("item_name", "quantity", "unit_price", "line_total")
        self.invoice_tree = ttk.Treeview(invoice_table_frame, columns=columns, show="headings", height=10)
        
        self.invoice_tree.heading("item_name", text="품목명")
        self.invoice_tree.heading("quantity", text="수량")
        self.invoice_tree.heading("unit_price", text="단가")
        self.invoice_tree.heading("line_total", text="금액")

        self.invoice_tree.column("item_name", width=250, anchor="w")
        self.invoice_tree.column("quantity", width=80, anchor="e")
        self.invoice_tree.column("unit_price", width=120, anchor="e")
        self.invoice_tree.column("line_total", width=120, anchor="e")
        
        tree_scrollbar = ttk.Scrollbar(invoice_table_frame, orient="vertical", command=self.invoice_tree.yview)
        self.invoice_tree.configure(yscrollcommand=tree_scrollbar.set)
        
        self.invoice_tree.pack(side="left", fill="both", expand=True)
        tree_scrollbar.pack(side="right", fill="y")

        # 총합계 및 버튼 프레임
        bottom_frame = ttk.Frame(tab)
        bottom_frame.pack(fill="x", padx=5, pady=10)

        ttk.Label(bottom_frame, text="총 합계:", font=("Arial", 12, "bold")).pack(side="left", padx=5)
        self.invoice_total_sum_label = ttk.Label(bottom_frame, text="0 원", font=("Arial", 12, "bold"))
        self.invoice_total_sum_label.pack(side="left", padx=5)
        
        ttk.Button(bottom_frame, text="선택 품목 삭제", command=self._remove_item_from_invoice).pack(side="right", padx=5)
        ttk.Button(bottom_frame, text="명세서 초기화", command=self._clear_invoice).pack(side="right", padx=5)
        ttk.Button(bottom_frame, text="엑셀 생성 및 열기", command=self._generate_excel_invoice).pack(side="right", padx=10, ipady=5)


    def _refresh_company_listbox_invoice_tab(self):
        """인보이스 탭의 회사 콤보박스를 새로고침합니다."""
        self.invoice_company_combo['values'] = [c.name for c in self.companies]
        if self.companies:
            self.invoice_company_combo.current(0)
        else:
            self.invoice_company_combo.set('')
        self._on_invoice_company_selected(None) # 첫번째 회사 자동 선택 또는 초기화


    def _on_invoice_company_selected(self, event):
        """회사 콤보박스에서 회사 선택 시 호출됩니다."""
        selected_name = self.invoice_company_combo.get()
        self.selected_company_for_invoice = next((c for c in self.companies if c.name == selected_name), None)
        # 회사 선택이 변경되면, 해당 회사의 가격을 반영하여 품목 목록을 새로고침
        self._refresh_item_listbox_invoice_tab(self.invoice_item_search_var.get())
        # 선택된 회사가 변경되면, 현재 명세서 품목들의 단가가 달라질 수 있으므로, 명세서 트리도 새로고침
        # 주의: 이 경우 이미 추가된 품목의 단가가 동적으로 변경됩니다.
        # 만약 추가 시점의 단가를 고정하고 싶다면, InvoiceLine에 단가를 직접 저장해야 합니다.
        # 현재 모델(InvoiceLine.unit_price property)은 동적으로 가져오므로, Treeview 새로고침만으로 충분합니다.
        self._refresh_invoice_tree() 
        self._update_invoice_total_sum()


    def _refresh_item_listbox_invoice_tab(self, filter_text=""):
        """인보이스 탭의 품목 리스트박스를 새로고침합니다 (검색 필터링 포함)."""
        self.invoice_item_listbox.delete(0, tk.END)
        filter_text = filter_text.lower()
        
        current_company_id = self.selected_company_for_invoice.id if self.selected_company_for_invoice else None
        
        # 품목 이름순으로 정렬
        sorted_items = sorted(self.items, key=lambda item: item.name)

        for item in sorted_items:
            if filter_text in item.name.lower():
                # 선택된 회사의 ID를 전달하여 해당 회사의 가격을 표시
                display_price = item.get_formatted_price(current_company_id)
                self.invoice_item_listbox.insert(tk.END, f"{item.name} ({display_price})")
    
    def _filter_invoice_items(self, *args):
        """품목 검색창 내용 변경 시 필터링 수행"""
        search_term = self.invoice_item_search_var.get()
        self._refresh_item_listbox_invoice_tab(search_term)

    def _add_item_to_invoice(self):
        """선택된 품목을 명세서 테이블에 추가합니다."""
        selected_indices = self.invoice_item_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("품목 미선택", "추가할 품목을 리스트에서 선택해주세요.")
            return
        
        selected_item_display_name = self.invoice_item_listbox.get(selected_indices[0])
        # display name에서 실제 Item 객체 찾기 (이름과 가격으로 구분)
        # 예: "프리미엄 키보드 (120,000원)" -> 가격 포맷이 변경되었으므로 주의
        # 가격 부분은 괄호 안의 마지막 요소임. " (단가:" 문자열이 더 이상 없을 수 있음.
        # "아이템 이름 (가격)" 형식으로 가정
        
        parts = selected_item_display_name.rsplit(" (", 1)
        item_name_part = parts[0]
        # 가격 부분은 "가격)" 형태이므로, 마지막 ')' 제거 필요
        # displayed_price_str_in_list = parts[1][:-1] if len(parts) > 1 else ""


        selected_item: Optional[Item] = None
        current_company_id_for_match = self.selected_company_for_invoice.id if self.selected_company_for_invoice else None

        for item_obj in self.items:
            # 이름이 일치하고, 현재 선택된 회사에 대한 포맷된 가격이 리스트박스의 표시와 일치하는지 확인
            expected_display_format = f"{item_obj.name} ({item_obj.get_formatted_price(current_company_id_for_match)})"
            if item_obj.name == item_name_part and selected_item_display_name == expected_display_format:
                selected_item = item_obj
                break
        
        if not selected_item:
            # 디버깅을 위해 추가 정보 표시
            # print(f"선택된 표시 이름: {selected_item_display_name}")
            # print(f"추출된 품목명: {item_name_part}")
            # print(f"현재 선택된 회사 ID: {current_company_id_for_match}")
            # for item_obj in self.items:
            #     if item_obj.name == item_name_part:
            #         print(f"  검토 품목: {item_obj.name}, 예상 표시: {item_obj.name} ({item_obj.get_formatted_price(current_company_id_for_match)})")
            messagebox.showerror("오류", "선택된 품목 정보를 정확히 찾을 수 없습니다. 목록이 최신 상태인지 확인하세요.")
            return

        try:
            quantity_str = self.invoice_item_quantity_spinbox.get()
            if not quantity_str: # Spinbox가 비어있을 경우
                 messagebox.showwarning("수량 오류", "수량을 입력해주세요.")
                 return
            quantity = int(quantity_str)
            if quantity <= 0:
                messagebox.showwarning("수량 오류", "수량은 0보다 커야 합니다.")
                return
        except ValueError:
            messagebox.showwarning("수량 오류", "수량은 숫자로 입력해야 합니다.")
            return

        # 중복 품목 확인 (선택: 합치거나, 새로 추가하거나, 막거나) - 여기서는 새로 추가
        # 이미 추가된 품목인지 확인 (ID 기준)
        for line in self.current_invoice_lines:
            if line.item_id == selected_item.id:
                if messagebox.askyesno("품목 중복", f"'{selected_item.name}' 품목이 이미 존재합니다. 수량을 합치시겠습니까?"):
                    line.quantity += quantity
                    self._refresh_invoice_tree()
                    self._update_invoice_total_sum()
                    return
                # '아니오'를 선택하면 새 라인으로 추가하지 않고 그냥 넘어감 (요구사항에 따라 변경 가능)
                # 또는 중복 추가를 허용하고 싶다면 이 블록을 제거
                # 여기서는 중복 추가를 막고, 수량 합치기 옵션만 제공
                return

        company_id_for_invoice_line = self.selected_company_for_invoice.id if self.selected_company_for_invoice else None
        invoice_line = InvoiceLine(item=selected_item, quantity=quantity, company_id=company_id_for_invoice_line)
        self.current_invoice_lines.append(invoice_line)
        self._refresh_invoice_tree()
        self._update_invoice_total_sum()

    def _remove_item_from_invoice(self):
        """명세서 테이블에서 선택된 품목을 제거합니다."""
        selected_tree_items = self.invoice_tree.selection()
        if not selected_tree_items:
            messagebox.showwarning("품목 미선택", "삭제할 품목을 테이블에서 선택해주세요.")
            return

        items_to_remove_from_current_invoice = []
        for tree_item_iid in selected_tree_items: # tree_item_iid는 Item.id 값임
            # current_invoice_lines에서 해당 item_id를 가진 InvoiceLine 객체를 찾음
            line_to_remove = next((line for line in self.current_invoice_lines if line.item.id == tree_item_iid), None)
            if line_to_remove:
                items_to_remove_from_current_invoice.append(line_to_remove)
        
        if not items_to_remove_from_current_invoice:
             # 이론적으로 이 경우는 발생하지 않아야 함 (Treeview iid와 Item.id가 동기화되므로)
            messagebox.showerror("오류", "삭제할 품목을 명세서 데이터에서 찾지 못했습니다.")
            return

        for item_line in items_to_remove_from_current_invoice:
            self.current_invoice_lines.remove(item_line)
            # Treeview에서는 이미 해당 iid로 삭제됨 (Treeview.selection()이 iid를 반환하므로)
            # self.invoice_tree.delete(item_line.item.id) # _refresh_invoice_tree에서 처리

        self._refresh_invoice_tree() # Treeview 전체 새로고침
        self._update_invoice_total_sum()

    def _clear_invoice(self):
        """현재 작성 중인 명세서 내용을 모두 지웁니다."""
        if messagebox.askyesno("초기화 확인", "정말로 현재 명세서 내용을 모두 지우시겠습니까?"):
            self.current_invoice_lines.clear()
            self._refresh_invoice_tree()
            self._update_invoice_total_sum()
            self.담당자_entry_var.set("") # 담당자 필드도 초기화

    def _refresh_invoice_tree(self):
        """명세서 품목 테이블(Treeview)을 새로고침합니다."""
        # 기존 항목 모두 삭제
        for i in self.invoice_tree.get_children():
            self.invoice_tree.delete(i)
        
        # 현재 명세서 라인들로 채우기
        for line in self.current_invoice_lines:
            # Treeview에 표시될 값들
            # InvoiceLine의 unit_price는 이미 company_id를 고려함
            values = (
                line.item_name,
                line.quantity,
                line.get_formatted_unit_price(), # InvoiceLine의 단가 사용 (거래처별 가격 반영)
                line.get_formatted_line_total()  # InvoiceLine의 금액 사용
            )
            # 각 품목은 명세서에 한 번만 나타나므로 item.id를 iid로 사용 가능
            # 하지만, 만약 동일 품목을 다른 조건으로 여러번 추가하는 시나리오가 있다면 iid 전략 수정 필요
            # 현재는 품목 중복 시 수량 합치기이므로 item.id 사용 가능
            if self.invoice_tree.exists(line.item.id): # 이미 해당 iid가 존재하면 (이론상 _add_item_to_invoice에서 처리됨)
                # 기존 항목 업데이트 또는 다른 iid 사용 (예: uuid.uuid4())
                # 여기서는 _add_item_to_invoice에서 중복을 관리하므로, 이 경우는 거의 발생 안 함
                self.invoice_tree.item(line.item.id, values=values)
            else:
                self.invoice_tree.insert("", tk.END, values=values, iid=line.item.id)


    def _update_invoice_total_sum(self):
        """명세서 총 합계를 계산하고 레이블을 업데이트합니다."""
        # InvoiceLine.line_total은 이미 company_id를 고려한 unit_price를 사용함
        total_sum = sum(line.line_total for line in self.current_invoice_lines)
        self.invoice_total_sum_label.config(text=f"{total_sum:,.0f} 원")


    def _generate_excel_invoice(self):
        """거래명세서 Excel 파일을 생성합니다."""
        if not self.selected_company_for_invoice:
            messagebox.showwarning("회사 미선택", "명세서를 발행할 거래처를 선택해주세요.")
            return
        
        if not self.current_invoice_lines:
            messagebox.showwarning("품목 없음", "명세서에 추가된 품목이 없습니다.")
            return

        담당자 = self.담당자_entry_var.get() or None # 빈 문자열이면 None

        filepath = invoice.create_invoice_excel(
            self.selected_company_for_invoice,
            self.current_invoice_lines,
            담당자=담당자
        )

        if filepath:
            messagebox.showinfo("성공", f"거래명세서가 성공적으로 생성되었습니다:\n{filepath}")
            if messagebox.askyesno("파일 열기", "생성된 명세서 파일이 있는 폴더를 여시겠습니까?"):
                invoice.open_file_explorer(filepath)
            self._clear_invoice() # 성공 시 명세서 초기화
        else:
            messagebox.showerror("실패", "거래명세서 생성에 실패했습니다.")

    # --- 거래처 관리 탭 ---
    def _create_company_management_tab(self):
        """거래처 관리 탭의 UI를 생성합니다."""
        tab = self.company_management_tab
        
        # 왼쪽: 회사 목록
        list_frame = ttk.LabelFrame(tab, text="거래처 목록")
        list_frame.pack(side="left", fill="y", padx=10, pady=10)

        self.company_listbox = tk.Listbox(list_frame, exportselection=False, width=30, height=20)
        self.company_listbox.pack(side="left", fill="y")
        company_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.company_listbox.yview)
        company_scrollbar.pack(side="right", fill="y")
        self.company_listbox.config(yscrollcommand=company_scrollbar.set)
        self.company_listbox.bind("<<ListboxSelect>>", self._on_company_selected_management)

        # 오른쪽: 회사 정보 입력/수정
        details_frame = ttk.LabelFrame(tab, text="거래처 정보")
        details_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        ttk.Label(details_frame, text="회사명:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.company_name_var = tk.StringVar()
        self.company_name_entry = ttk.Entry(details_frame, textvariable=self.company_name_var, width=40)
        self.company_name_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(details_frame, text="연락처:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.company_contact_var = tk.StringVar()
        self.company_contact_entry = ttk.Entry(details_frame, textvariable=self.company_contact_var, width=40)
        self.company_contact_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        # ID (숨김 또는 읽기 전용)
        self.company_id_var = tk.StringVar() # 실제 ID 저장용
        # ttk.Label(details_frame, text="ID:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        # ttk.Label(details_frame, textvariable=self.company_id_var).grid(row=2, column=1, padx=5, pady=5, sticky="w")


        buttons_frame = ttk.Frame(details_frame)
        buttons_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        ttk.Button(buttons_frame, text="새로 입력", command=self._clear_company_fields).pack(side="left", padx=5)
        ttk.Button(buttons_frame, text="추가", command=self._add_company).pack(side="left", padx=5)
        ttk.Button(buttons_frame, text="수정", command=self._update_company).pack(side="left", padx=5)
        ttk.Button(buttons_frame, text="삭제", command=self._delete_company).pack(side="left", padx=5)
        
        details_frame.grid_columnconfigure(1, weight=1)

    def _refresh_company_management_listbox(self):
        """거래처 관리 탭의 리스트박스를 새로고침합니다."""
        self.company_listbox.delete(0, tk.END)
        # 회사 이름순으로 정렬
        sorted_companies = sorted(self.companies, key=lambda comp: comp.name)
        for company in sorted_companies:
            self.company_listbox.insert(tk.END, company.name)
        self._clear_company_fields() # 선택 해제 및 필드 초기화

    def _on_company_selected_management(self, event):
        """거래처 관리 리스트박스에서 회사 선택 시 호출됩니다."""
        selected_indices = self.company_listbox.curselection()
        if not selected_indices:
            self._clear_company_fields()
            return
        
        selected_company_name = self.company_listbox.get(selected_indices[0])
        # 이름으로 회사 객체 찾기 (이름이 유니크하다고 가정)
        company = next((c for c in self.companies if c.name == selected_company_name), None)

        if company:
            self.company_id_var.set(company.id)
            self.company_name_var.set(company.name)
            self.company_contact_var.set(company.contact)
        else: # 혹시 모를 불일치 상황
            self._clear_company_fields()


    def _clear_company_fields(self):
        """거래처 정보 입력 필드를 초기화합니다."""
        self.company_id_var.set("") # 새 회사 추가 시 ID는 자동 생성됨
        self.company_name_var.set("")
        self.company_contact_var.set("")
        self.company_listbox.selection_clear(0, tk.END) # 리스트박스 선택 해제
        self.company_name_entry.focus()


    def _add_company(self):
        """새 거래처를 추가합니다."""
        name = self.company_name_var.get().strip()
        contact = self.company_contact_var.get().strip()

        if not name:
            messagebox.showwarning("입력 오류", "회사명은 필수 항목입니다.")
            return
        
        # 중복 회사명 체크
        if any(c.name.lower() == name.lower() for c in self.companies):
            messagebox.showwarning("중복 오류", f"이미 '{name}' 이름의 회사가 존재합니다.")
            return

        new_company = Company(name=name, contact=contact) # ID는 자동 생성
        self.companies.append(new_company)
        storage.save_data(self.companies, self.items) # 즉시 저장
        self._refresh_company_management_listbox()
        self._refresh_company_listbox_invoice_tab() # 인보이스 탭 콤보박스도 업데이트
        messagebox.showinfo("성공", f"'{name}' 회사가 추가되었습니다.")
        self._clear_company_fields()

    def _update_company(self):
        """선택된 거래처 정보를 수정합니다."""
        selected_id = self.company_id_var.get()
        if not selected_id:
            messagebox.showwarning("선택 오류", "수정할 회사를 목록에서 선택해주세요.")
            return

        name = self.company_name_var.get().strip()
        contact = self.company_contact_var.get().strip()

        if not name:
            messagebox.showwarning("입력 오류", "회사명은 필수 항목입니다.")
            return

        company_to_update = next((c for c in self.companies if c.id == selected_id), None)
        if not company_to_update:
            messagebox.showerror("오류", "수정할 회사를 찾을 수 없습니다.")
            return
            
        # 이름 변경 시 중복 체크 (자기 자신 제외)
        if (company_to_update.name.lower() != name.lower() and
            any(c.name.lower() == name.lower() and c.id != selected_id for c in self.companies)):
            messagebox.showwarning("중복 오류", f"이미 '{name}' 이름의 다른 회사가 존재합니다.")
            return

        company_to_update.name = name
        company_to_update.contact = contact
        storage.save_data(self.companies, self.items)
        self._refresh_company_management_listbox()
        self._refresh_company_listbox_invoice_tab()
        messagebox.showinfo("성공", f"'{name}' 회사 정보가 수정되었습니다.")
        self._clear_company_fields()


    def _delete_company(self):
        """선택된 거래처를 삭제합니다."""
        selected_id = self.company_id_var.get()
        if not selected_id:
            messagebox.showwarning("선택 오류", "삭제할 회사를 목록에서 선택해주세요.")
            return
        
        company_to_delete = next((c for c in self.companies if c.id == selected_id), None)
        if not company_to_delete:
            messagebox.showerror("오류", "삭제할 회사를 찾을 수 없습니다.")
            return

        if messagebox.askyesno("삭제 확인", f"정말로 '{company_to_delete.name}' 회사를 삭제하시겠습니까?"):
            self.companies.remove(company_to_delete)
            storage.save_data(self.companies, self.items)
            self._refresh_company_management_listbox()
            self._refresh_company_listbox_invoice_tab()
            messagebox.showinfo("성공", f"'{company_to_delete.name}' 회사가 삭제되었습니다.")
            self._clear_company_fields()

    # --- 품목 관리 탭 ---
    def _create_item_management_tab(self):
        """품목 관리 탭의 UI를 생성합니다."""
        tab = self.item_management_tab
        
        # 왼쪽: 품목 목록
        list_frame = ttk.LabelFrame(tab, text="품목 목록 (이름순 정렬)")
        list_frame.pack(side="left", fill="y", padx=10, pady=10)

        # 품목 검색 필드
        ttk.Label(list_frame, text="검색:").pack(side="top", anchor="w", padx=5, pady=(5,0))
        self.item_search_var_management = tk.StringVar()
        self.item_search_var_management.trace_add("write", self._filter_management_items)
        ttk.Entry(list_frame, textvariable=self.item_search_var_management, width=28).pack(side="top", fill="x", padx=5, pady=(0,5))

        self.item_listbox = tk.Listbox(list_frame, exportselection=False, width=30, height=18) # 높이 조정
        self.item_listbox.pack(side="left", fill="y")
        item_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.item_listbox.yview)
        item_scrollbar.pack(side="right", fill="y")
        self.item_listbox.config(yscrollcommand=item_scrollbar.set)
        self.item_listbox.bind("<<ListboxSelect>>", self._on_item_selected_management)

        # 오른쪽: 품목 정보 입력/수정
        details_frame = ttk.LabelFrame(tab, text="품목 정보")
        details_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        ttk.Label(details_frame, text="품목명:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.item_name_var = tk.StringVar()
        self.item_name_entry = ttk.Entry(details_frame, textvariable=self.item_name_var, width=40)
        self.item_name_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(details_frame, text="단가 (VAT 포함, 원):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.item_price_var = tk.StringVar()
        self.item_price_entry = ttk.Entry(details_frame, textvariable=self.item_price_var, width=40)
        self.item_price_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        self.item_id_var = tk.StringVar() # 실제 ID 저장용

        buttons_frame = ttk.Frame(details_frame)
        buttons_frame.grid(row=2, column=0, columnspan=2, pady=10) # Adjusted row and pady
        
        ttk.Button(buttons_frame, text="새로 입력", command=self._clear_item_fields).pack(side="left", padx=5)
        ttk.Button(buttons_frame, text="추가", command=self._add_item).pack(side="left", padx=5)
        ttk.Button(buttons_frame, text="수정 (기본정보)", command=self._update_item).pack(side="left", padx=5) # Clarified button
        ttk.Button(buttons_frame, text="삭제 (품목 전체)", command=self._delete_item).pack(side="left", padx=5) # Clarified button
        
        details_frame.grid_columnconfigure(1, weight=1)

        # --- 거래처별 단가 설정 프레임 ---
        company_price_frame = ttk.LabelFrame(details_frame, text="거래처별 단가 설정")
        company_price_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=5, pady=(10,5)) # Use row 3
        company_price_frame.grid_columnconfigure(1, weight=1) # Allow company combobox to expand

        ttk.Label(company_price_frame, text="거래처:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.item_company_price_company_combo = ttk.Combobox(company_price_frame, state="readonly", width=30) # Increased width
        self.item_company_price_company_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.item_company_price_company_combo.bind("<<ComboboxSelected>>", self._on_company_selected_for_item_price_setting)

        ttk.Label(company_price_frame, text="거래처별 단가:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.item_company_price_var = tk.StringVar()
        self.item_company_price_entry = ttk.Entry(company_price_frame, textvariable=self.item_company_price_var, width=15)
        self.item_company_price_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        company_price_buttons_frame = ttk.Frame(company_price_frame)
        company_price_buttons_frame.grid(row=1, column=2, padx=5, pady=5, sticky="e")

        ttk.Button(company_price_buttons_frame, text="설정/수정", command=self._set_or_update_company_item_price).pack(side="left", padx=2)
        ttk.Button(company_price_buttons_frame, text="삭제", command=self._remove_company_item_price).pack(side="left", padx=2)
        
        self.company_specific_prices_listbox = tk.Listbox(company_price_frame, height=4, exportselection=False) # Adjusted height
        self.company_specific_prices_listbox.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky="ew")
        csp_scrollbar = ttk.Scrollbar(company_price_frame, orient="vertical", command=self.company_specific_prices_listbox.yview)
        csp_scrollbar.grid(row=2, column=3, sticky="ns", padx=(0,5), pady=5)
        self.company_specific_prices_listbox.config(yscrollcommand=csp_scrollbar.set)
        self.company_specific_prices_listbox.bind("<<ListboxSelect>>", self._on_company_specific_price_selected_in_list)

    def _refresh_item_management_listbox(self, filter_text=""):
        """품목 관리 탭의 리스트박스를 새로고침합니다 (검색 필터링 포함)."""
        self.item_listbox.delete(0, tk.END)
        filter_text = filter_text.lower()
        
        # 품목 이름순으로 정렬
        sorted_items = sorted(self.items, key=lambda item: item.name)

        for item in sorted_items:
            if filter_text in item.name.lower(): # 이름으로만 검색
                # 품목 관리 탭에서는 항상 기본 단가를 표시
                self.item_listbox.insert(tk.END, f"{item.name} ({item.get_formatted_price(company_id=None)})")
        
        if not filter_text: # 필터가 없을 때만 필드 클리어 (선택 유지 위함)
             self._clear_item_fields()


    def _filter_management_items(self, *args):
        """품목 관리 탭의 검색창 내용 변경 시 필터링 수행"""
        search_term = self.item_search_var_management.get()
        self._refresh_item_management_listbox(search_term)


    def _on_item_selected_management(self, event):
        """품목 관리 리스트박스에서 품목 선택 시 호출됩니다."""
        selected_indices = self.item_listbox.curselection()
        if not selected_indices:
            self._clear_item_fields()
            return
        
        selected_item_display_name = self.item_listbox.get(selected_indices[0])
        # display name에서 실제 Item 객체 찾기
        # "아이템 이름 (기본가격)" 형식으로 가정
        parts = selected_item_display_name.rsplit(" (", 1)
        item_name_part = parts[0]
        
        item: Optional[Item] = None
        for item_obj in self.items:
            # 품목 관리 탭에서는 기본 가격으로 비교
            expected_display_format = f"{item_obj.name} ({item_obj.get_formatted_price(company_id=None)})"
            if item_obj.name == item_name_part and selected_item_display_name == expected_display_format:
                item = item_obj
                break
        
        if item:
            self.item_id_var.set(item.id)
            self.item_name_var.set(item.name)
            # 품목 관리 탭에서는 default_unit_price를 편집
            self.item_price_var.set(f"{item.default_unit_price:.2f}") # 소수점 2자리까지 표시
            
            # 거래처별 단가 섹션 업데이트
            self._populate_company_combo_for_item_pricing()
            self._refresh_company_specific_prices_listbox()
            self.item_company_price_var.set("") # 거래처별 단가 입력 필드 초기화
            if self.companies:
                self.item_company_price_company_combo.current(0) # 첫번째 회사 선택 (또는 비워두기)
                self._on_company_selected_for_item_price_setting(None) # 선택된 회사에 대한 가격 로드 시도
            else:
                self.item_company_price_company_combo.set("")
            # Ensure the listbox selection doesn't persist unwantedly
            self.company_specific_prices_listbox.selection_clear(0, tk.END)


        else:
            self._clear_item_fields() # 전체 초기화 (거래처별 가격 섹션 포함)

    def _clear_item_fields(self):
        """품목 정보 입력 필드를 초기화합니다."""
        self.item_id_var.set("")
        self.item_name_var.set("")
        self.item_price_var.set("")
        self.item_listbox.selection_clear(0, tk.END)
        self.item_name_entry.focus()

        # 거래처별 단가 섹션도 초기화
        self.item_company_price_company_combo.set("")
        if hasattr(self, 'item_company_price_company_combo'): # Check if widget exists
            self.item_company_price_company_combo['values'] = []
        self.item_company_price_var.set("")
        if hasattr(self, 'company_specific_prices_listbox'): # Check if widget exists
            self.company_specific_prices_listbox.delete(0, tk.END)


    def _populate_company_combo_for_item_pricing(self):
        """거래처별 단가 설정의 회사 콤보박스를 채웁니다."""
        company_names = [c.name for c in sorted(self.companies, key=lambda comp: comp.name)]
        self.item_company_price_company_combo['values'] = company_names
        if company_names:
            self.item_company_price_company_combo.current(0) # 첫번째 회사 자동 선택
        else:
            self.item_company_price_company_combo.set("")

    def _refresh_company_specific_prices_listbox(self):
        """선택된 품목의 거래처별 단가 목록을 새로고침합니다."""
        self.company_specific_prices_listbox.delete(0, tk.END)
        selected_item_id = self.item_id_var.get()
        if not selected_item_id:
            return

        item = next((i for i in self.items if i.id == selected_item_id), None)
        if not item:
            return

        # 회사 이름으로 정렬하여 표시
        sorted_company_ids = sorted(item.company_prices.keys(), key=lambda cid: next((c.name for c in self.companies if c.id == cid), "알 수 없는 회사"))

        for company_id in sorted_company_ids:
            price = item.company_prices[company_id]
            company = next((c for c in self.companies if c.id == company_id), None)
            company_name = company.name if company else f"ID:{company_id[:8]}..." # Show partial ID if name not found
            self.company_specific_prices_listbox.insert(tk.END, f"{company_name}: {price:,.2f} 원") # Store company_id with item? No, use name for display.
            
    def _on_company_selected_for_item_price_setting(self, event):
        """거래처별 단가 설정에서 회사가 선택되었을 때 호출됩니다."""
        selected_item_id = self.item_id_var.get()
        selected_company_name = self.item_company_price_company_combo.get()

        if not selected_item_id or not selected_company_name:
            self.item_company_price_var.set("")
            return

        item = next((i for i in self.items if i.id == selected_item_id), None)
        company = next((c for c in self.companies if c.name == selected_company_name), None)

        if item and company:
            if company.id in item.company_prices:
                self.item_company_price_var.set(f"{item.company_prices[company.id]:.2f}")
            else:
                self.item_company_price_var.set("") # 해당 거래처 가격 없음
        else:
            self.item_company_price_var.set("")
        # When company combo changes, clear selection in the listbox of specific prices
        # to avoid confusion, as the price entry now reflects the combo, not the listbox selection.
        self.company_specific_prices_listbox.selection_clear(0, tk.END)


    def _on_company_specific_price_selected_in_list(self, event):
        """거래처별 단가 리스트박스에서 항목 선택 시 호출됩니다."""
        selected_indices = self.company_specific_prices_listbox.curselection()
        if not selected_indices:
            return

        selected_text = self.company_specific_prices_listbox.get(selected_indices[0])
        # "회사명: 가격 원" 형식에서 회사명과 가격 추출
        try:
            company_name_part, price_part_full = selected_text.split(":", 1)
            company_name = company_name_part.strip()
            
            # 가격 부분에서 숫자만 추출 (쉼표와 ' 원' 제거)
            price_str = price_part_full.strip().replace(" 원", "").replace(",", "")
            
            self.item_company_price_company_combo.set(company_name)
            self.item_company_price_var.set(Decimal(price_str).quantize(Decimal("0.01"))) # Ensure .2f format
        except ValueError:
            messagebox.showerror("오류", "선택된 거래처별 단가 형식이 잘못되었습니다.")
            self.item_company_price_company_combo.set("")
            self.item_company_price_var.set("")
        except Exception as e:
            print(f"Error parsing selected company specific price: {e}")
            self.item_company_price_company_combo.set("")
            self.item_company_price_var.set("")


    def _set_or_update_company_item_price(self):
        """선택된 품목에 대해 선택된 거래처의 특별 단가를 설정/수정합니다."""
        selected_item_id = self.item_id_var.get()
        if not selected_item_id:
            messagebox.showwarning("품목 미선택", "먼저 품목 목록에서 품목을 선택해주세요.")
            return

        selected_company_name = self.item_company_price_company_combo.get()
        if not selected_company_name:
            messagebox.showwarning("거래처 미선택", "단가를 설정할 거래처를 선택해주세요.")
            return
            
        price_str = self.item_company_price_var.get().strip()
        if not price_str:
            messagebox.showwarning("단가 미입력", "거래처별 단가를 입력해주세요.")
            return

        try:
            price = Decimal(price_str).quantize(Decimal("0.01"))
            if price < Decimal("0"):
                messagebox.showwarning("입력 오류", "단가는 0 이상이어야 합니다.")
                return
        except InvalidOperation:
            messagebox.showwarning("입력 오류", "단가는 숫자로 입력해야 합니다. (예: 12500.75)")
            return

        item = next((i for i in self.items if i.id == selected_item_id), None)
        company = next((c for c in self.companies if c.name == selected_company_name), None)

        if not item or not company:
            messagebox.showerror("오류", "품목 또는 거래처 정보를 찾을 수 없습니다.")
            return

        item.set_company_price(company.id, price)
        storage.save_data(self.companies, self.items) # 변경사항 저장
        self._refresh_company_specific_prices_listbox() # 목록 새로고침
        self._refresh_item_listbox_invoice_tab() # 명세서 작성 탭의 품목 목록도 갱신 (가격 변경 가능성)
        messagebox.showinfo("성공", f"'{item.name}' 품목에 대한 '{company.name}'의 단가가 {price:,.2f} 원으로 설정/수정되었습니다.")


    def _remove_company_item_price(self):
        """선택된 품목에 대해 선택된 거래처의 특별 단가를 삭제합니다."""
        selected_item_id = self.item_id_var.get()
        if not selected_item_id:
            messagebox.showwarning("품목 미선택", "먼저 품목 목록에서 품목을 선택해주세요.")
            return

        # 거래처 선택은 콤보박스 또는 리스트박스에서 가져올 수 있음
        # 여기서는 콤보박스에서 선택된 거래처를 기준으로 삭제
        selected_company_name_in_combo = self.item_company_price_company_combo.get()
        
        # 또는, 리스트박스에서 선택된 항목을 기준으로 삭제할 수도 있음
        # selected_csp_indices = self.company_specific_prices_listbox.curselection()
        # company_to_remove_name = None
        # if selected_csp_indices:
        #    selected_csp_text = self.company_specific_prices_listbox.get(selected_csp_indices[0])
        #    company_to_remove_name = selected_csp_text.split(":")[0].strip()

        if not selected_company_name_in_combo: # 콤보박스에 아무것도 선택되지 않았으면
            messagebox.showwarning("거래처 미선택", "삭제할 거래처별 단가의 거래처를 선택하거나, 아래 목록에서 해당 항목을 선택 후 다시 시도해주세요.")
            return

        item = next((i for i in self.items if i.id == selected_item_id), None)
        company_to_remove = next((c for c in self.companies if c.name == selected_company_name_in_combo), None)

        if not item or not company_to_remove:
            messagebox.showerror("오류", "품목 또는 거래처 정보를 찾을 수 없습니다.")
            return

        if company_to_remove.id not in item.company_prices:
            messagebox.showwarning("단가 없음", f"'{item.name}' 품목에 대해 '{company_to_remove.name}'의 특별 단가가 설정되어 있지 않습니다.")
            return

        if messagebox.askyesno("삭제 확인", f"'{item.name}' 품목에 대한 '{company_to_remove.name}'의 특별 단가를 삭제하시겠습니까?"):
            item.remove_company_price(company_to_remove.id)
            storage.save_data(self.companies, self.items)
            self._refresh_company_specific_prices_listbox()
            self.item_company_price_var.set("") # 단가 입력 필드 초기화
            self._refresh_item_listbox_invoice_tab() # 명세서 작성 탭의 품목 목록도 갱신
            messagebox.showinfo("성공", f"'{item.name}' 품목에 대한 '{company_to_remove.name}'의 특별 단가가 삭제되었습니다.")


    def _add_item(self):
        """새 품목을 추가합니다."""
        name = self.item_name_var.get().strip()
        price_str = self.item_price_var.get().strip()

        if not name:
            messagebox.showwarning("입력 오류", "품목명은 필수 항목입니다.")
            return
        if not price_str:
            messagebox.showwarning("입력 오류", "단가는 필수 항목입니다.")
            return

        try:
            price = Decimal(price_str)
            if price < Decimal("0"):
                messagebox.showwarning("입력 오류", "단가는 0 이상이어야 합니다.")
                return
            # 소수점 2자리로 반올림 (Decimal 기본 설정이 ROUND_HALF_EVEN일 수 있으므로 명시)
            price = price.quantize(Decimal("0.01")) 
        except InvalidOperation:
            messagebox.showwarning("입력 오류", "단가는 숫자로 입력해야 합니다. (예: 15000.50)")
            return
        
        # 중복 품목명 체크 (이름만으로 체크, 단가가 달라도 중복으로 간주)
        if any(i.name.lower() == name.lower() for i in self.items):
            messagebox.showwarning("중복 오류", f"이미 '{name}' 이름의 품목이 존재합니다.")
            return

        new_item = Item(name=name, default_unit_price=price) # ID는 자동 생성, default_unit_price 사용
        self.items.append(new_item)
        storage.save_data(self.companies, self.items)
        self._refresh_item_management_listbox()
        self._refresh_item_listbox_invoice_tab() # 인보이스 탭 리스트박스도 업데이트
        messagebox.showinfo("성공", f"'{name}' 품목이 추가되었습니다.")
        self._clear_item_fields()

    def _update_item(self):
        """선택된 품목 정보를 수정합니다."""
        selected_id = self.item_id_var.get()
        if not selected_id:
            messagebox.showwarning("선택 오류", "수정할 품목을 목록에서 선택해주세요.")
            return

        name = self.item_name_var.get().strip()
        price_str = self.item_price_var.get().strip()

        if not name:
            messagebox.showwarning("입력 오류", "품목명은 필수 항목입니다.")
            return
        if not price_str:
            messagebox.showwarning("입력 오류", "단가는 필수 항목입니다.")
            return

        try:
            price = Decimal(price_str).quantize(Decimal("0.01"))
            if price < Decimal("0"):
                messagebox.showwarning("입력 오류", "단가는 0 이상이어야 합니다.")
                return
        except InvalidOperation:
            messagebox.showwarning("입력 오류", "단가는 숫자로 입력해야 합니다.")
            return

        item_to_update = next((i for i in self.items if i.id == selected_id), None)
        if not item_to_update:
            messagebox.showerror("오류", "수정할 품목을 찾을 수 없습니다.")
            return
            
        # 이름 변경 시 중복 체크 (자기 자신 제외)
        if (item_to_update.name.lower() != name.lower() and
            any(i.name.lower() == name.lower() and i.id != selected_id for i in self.items)):
            messagebox.showwarning("중복 오류", f"이미 '{name}' 이름의 다른 품목이 존재합니다.")
            return

        item_to_update.name = name
        item_to_update.default_unit_price = price # default_unit_price 사용
        storage.save_data(self.companies, self.items)
        self._refresh_item_management_listbox()
        self._refresh_item_listbox_invoice_tab()
        messagebox.showinfo("성공", f"'{name}' 품목 정보가 수정되었습니다.")
        self._clear_item_fields()

    def _delete_item(self):
        """선택된 품목을 삭제합니다."""
        selected_id = self.item_id_var.get()
        if not selected_id:
            messagebox.showwarning("선택 오류", "삭제할 품목을 목록에서 선택해주세요.")
            return
        
        item_to_delete = next((i for i in self.items if i.id == selected_id), None)
        if not item_to_delete:
            messagebox.showerror("오류", "삭제할 품목을 찾을 수 없습니다.")
            return

        if messagebox.askyesno("삭제 확인", f"정말로 '{item_to_delete.name}' 품목을 삭제하시겠습니까?"):
            self.items.remove(item_to_delete)
            storage.save_data(self.companies, self.items)
            self._refresh_item_management_listbox()
            self._refresh_item_listbox_invoice_tab()
            messagebox.showinfo("성공", f"'{item_to_delete.name}' 품목이 삭제되었습니다.")
            self._clear_item_fields()


def main():
    """애플리케이션 실행 진입점"""
    app = None  # Initialize app to None
    try:
        app = App()
        app.update_idletasks()  # Process pending idle tasks (like geometry management)
        app.update()  # Force an update of the display
        app.mainloop()
    except Exception as e:
        print("--------------------------------------------------")
        print(f"AN ERROR OCCURRED: {e}")
        print("--------------------------------------------------")
        import traceback
        traceback.print_exc()
        print("--------------------------------------------------")
        # If app was initialized, still try to destroy it if possible, or exit
        if app:
            try:
                app.destroy()
            except:
                pass
        import sys
        sys.exit(1) # Exit with an error code

if __name__ == "__main__":
    main()
