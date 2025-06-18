import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, Menu, simpledialog
import os
import uuid
import datetime
from typing import List, Optional, Dict, Any
from decimal import Decimal, InvalidOperation

from models import Company, Item, InvoiceLine, PriceTier, PriceProfile
import storage
import invoice

def get_bundle_dir():
    """Return the base directory for bundled files, or the script's directory."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    else:
        return os.path.dirname(os.path.abspath(__file__))

class App(tk.Tk):
    """메인 애플리케이션 GUI 클래스"""

    def __init__(self):
        super().__init__()
        self.title("거래명세서 자동 작성 툴")
        self.geometry("1100x750")

        self.companies: List[Company] = storage.load_companies()
        self.price_profiles: List[PriceProfile] = storage.load_price_profiles()
        self.product_master_items: List[Item] = []

        bundle_dir = get_bundle_dir()
        bundled_product_master_path = os.path.join(bundle_dir, "데이터파일", storage.DEFAULT_PRODUCT_MASTER_FILE_BASENAME)

        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            if os.path.exists(bundled_product_master_path):
                self.product_master_file_path: str = bundled_product_master_path
            else:
                self.product_master_file_path: str = ""
                print(f"경고: 번들된 애플리케이션의 제품 마스터 파일 '{bundled_product_master_path}'을(를) 찾을 수 없습니다.")
        else:
            path_in_data_folder_script_dir = os.path.join(bundle_dir, "데이터파일", storage.DEFAULT_PRODUCT_MASTER_FILE_BASENAME)
            path_in_script_dir = os.path.join(bundle_dir, storage.DEFAULT_PRODUCT_MASTER_FILE_BASENAME)
            path_in_downloads = ""
            try:
                path_in_downloads = os.path.expanduser(f"~/Downloads/{storage.DEFAULT_PRODUCT_MASTER_FILE_BASENAME}")
            except Exception:
                pass

            if os.path.exists(path_in_data_folder_script_dir):
                self.product_master_file_path: str = path_in_data_folder_script_dir
            elif os.path.exists(path_in_script_dir):
                self.product_master_file_path: str = path_in_script_dir
            elif path_in_downloads and os.path.exists(path_in_downloads):
                 self.product_master_file_path: str = path_in_downloads
            else:
                self.product_master_file_path: str = ""

        self._load_product_master_data()

        self.current_invoice_lines: List[InvoiceLine] = []
        self.selected_company_for_invoice: Optional[Company] = None
        self.invoice_담당자_var = tk.StringVar() 
        self.invoice_date_var = tk.StringVar(value=datetime.date.today().strftime("%Y-%m-%d"))

        self._create_main_menu()
        self.notebook = ttk.Notebook(self)
        self.invoice_tab = ttk.Frame(self.notebook)
        self.company_management_tab = ttk.Frame(self.notebook)
        self.price_profile_management_tab = ttk.Frame(self.notebook)
        self.product_viewer_tab = ttk.Frame(self.notebook) 
        self.notebook.add(self.invoice_tab, text="거래명세서 작성")
        self.notebook.add(self.company_management_tab, text="거래처 관리")
        self.notebook.add(self.price_profile_management_tab, text="단가 프로파일 관리")
        self.notebook.add(self.product_viewer_tab, text="제품 마스터 조회") 
        self._create_invoice_tab() 
        self._create_company_management_tab()
        self._create_price_profile_management_tab()
        self._create_product_viewer_tab() 
        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)
        self._refresh_company_listbox_invoice_tab()
        self._refresh_company_management_listbox()
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _create_main_menu(self):
        menubar = Menu(self)
        self.config(menu=menubar)
        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="파일", menu=file_menu)
        file_menu.add_command(label="제품 마스터 파일 선택...", command=self._select_product_master_file)
        file_menu.add_command(label="제품 마스터 새로고침", command=self._refresh_product_master_data)
        file_menu.add_separator()
        file_menu.add_command(label="종료", command=self._on_closing)

    def _select_product_master_file(self):
        initial_dir = os.path.dirname(self.product_master_file_path) if self.product_master_file_path and os.path.exists(os.path.dirname(self.product_master_file_path)) else os.getcwd()
        initial_file = os.path.basename(self.product_master_file_path) if self.product_master_file_path else storage.DEFAULT_PRODUCT_MASTER_FILE_BASENAME
        filepath = filedialog.askopenfilename(
            title="제품 마스터 JSON 파일 선택",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
            initialfile=initial_file,
            initialdir=initial_dir
        )
        if filepath:
            self.product_master_file_path = filepath
            self._load_product_master_data()
            messagebox.showinfo("성공", f"제품 마스터 파일이 '{filepath}'로 설정되었습니다.\n데이터를 새로고침합니다.")

    def _load_product_master_data(self, file_path: Optional[str] = None):
        path_to_load = file_path if file_path else self.product_master_file_path
        if not path_to_load or not os.path.exists(path_to_load):
            if path_to_load: print(f"정보: 제품 마스터 파일을 찾을 수 없습니다: {path_to_load}.")
            else: print(f"정보: 제품 마스터 파일 경로가 설정되지 않았습니다.")
            self.product_master_items = []
        else:
            self.product_master_items = storage.load_product_master(path_to_load)
        
        if hasattr(self, 'invoice_item_listbox'): self._refresh_item_listbox_invoice_tab() 
        if hasattr(self, 'product_viewer_tree'): self._refresh_product_viewer_listbox()

    def _refresh_product_master_data(self):
        self._load_product_master_data()
        messagebox.showinfo("정보", "제품 마스터 데이터를 새로고침했습니다.")

    def _on_closing(self):
        if messagebox.askokcancel("종료 확인", "프로그램을 종료하시겠습니까? 변경사항이 저장됩니다."):
            storage.save_companies(self.companies)
            storage.save_price_profiles(self.price_profiles)
            self.destroy()

    def _create_invoice_tab(self):
        tab = self.invoice_tab
        top_frame = ttk.Frame(tab)
        top_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(top_frame, text="거래처 선택:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.invoice_company_combo = ttk.Combobox(top_frame, state="readonly", width=30)
        self.invoice_company_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.invoice_company_combo.bind("<<ComboboxSelected>>", self._on_invoice_company_selected)
        self.invoice_company_combo.bind("<FocusOut>", lambda e: self.invoice_company_combo.selection_clear())
        ttk.Label(top_frame, text="담당자 (선택):").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.담당자_entry = ttk.Entry(top_frame, textvariable=self.invoice_담당자_var, width=20)
        self.담당자_entry.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        ttk.Label(top_frame, text="명세서 날짜:").grid(row=0, column=4, padx=5, pady=5, sticky="w")
        self.invoice_date_entry = ttk.Entry(top_frame, textvariable=self.invoice_date_var, width=12)
        self.invoice_date_entry.grid(row=0, column=5, padx=5, pady=5, sticky="w")

        item_selection_frame = ttk.LabelFrame(tab, text="품목 선택 및 추가")
        item_selection_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(item_selection_frame, text="품목 검색:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.invoice_item_search_var = tk.StringVar()
        self.invoice_item_search_var.trace_add("write", self._filter_invoice_items)
        ttk.Entry(item_selection_frame, textvariable=self.invoice_item_search_var, width=40).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.invoice_item_listbox = tk.Listbox(item_selection_frame, height=8, exportselection=False, width=70)
        self.invoice_item_listbox.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
        self.invoice_item_listbox.bind("<Double-1>", self._on_invoice_item_listbox_double_click)
        item_scrollbar_y = ttk.Scrollbar(item_selection_frame, orient="vertical", command=self.invoice_item_listbox.yview)
        item_scrollbar_y.grid(row=1, column=2, sticky="ns")
        self.invoice_item_listbox.config(yscrollcommand=item_scrollbar_y.set)
        item_scrollbar_x = ttk.Scrollbar(item_selection_frame, orient="horizontal", command=self.invoice_item_listbox.xview)
        item_scrollbar_x.grid(row=2, column=0, columnspan=2, sticky="ew")
        self.invoice_item_listbox.config(xscrollcommand=item_scrollbar_x.set)
        ttk.Label(item_selection_frame, text="수량:").grid(row=0, column=3, padx=5, pady=5, sticky="w")
        self.invoice_item_quantity_spinbox = ttk.Spinbox(item_selection_frame, from_=1, to=9999, width=8)
        self.invoice_item_quantity_spinbox.set(1)
        self.invoice_item_quantity_spinbox.grid(row=0, column=4, padx=5, pady=5)
        ttk.Button(item_selection_frame, text="품목 추가", command=self._add_item_to_invoice).grid(row=1, column=3, columnspan=2, padx=5, pady=10, sticky="ew")
        item_selection_frame.grid_columnconfigure(1, weight=1)

        invoice_table_frame = ttk.LabelFrame(tab, text="거래명세서 품목")
        invoice_table_frame.pack(expand=True, fill="both", padx=5, pady=5)
        columns = ("lot", "model_name", "product_name", "spec", "qty", "unit_price", "supply_amount", "vat", "insurance_price", "treatment_code", "udi_di")
        self.invoice_tree = ttk.Treeview(invoice_table_frame, columns=columns, show="headings", height=10)
        header_texts = ["LOT", "모델명", "제품명", "규격", "납품수량", "단가", "공급가액", "부가세", "보험수가", "치료재료코드", "UDI-DI"]
        col_widths = [100, 120, 180, 100, 70, 90, 90, 90, 90, 100, 150]
        col_anchors = ['w', 'w', 'w', 'w', 'e', 'e', 'e', 'e', 'e', 'w', 'w']
        for i, col_id in enumerate(columns):
            is_numeric = col_id in ["qty", "unit_price", "supply_amount", "vat", "insurance_price"]
            self.invoice_tree.heading(col_id, text=header_texts[i], command=lambda c=col_id, n=is_numeric: self._sort_invoice_tree_column(c, n))
            self.invoice_tree.column(col_id, width=col_widths[i], anchor=col_anchors[i], stretch=tk.NO)
        tree_scrollbar_y = ttk.Scrollbar(invoice_table_frame, orient="vertical", command=self.invoice_tree.yview)
        self.invoice_tree.configure(yscrollcommand=tree_scrollbar_y.set)
        tree_scrollbar_y.pack(side="right", fill="y")
        tree_scrollbar_x = ttk.Scrollbar(invoice_table_frame, orient="horizontal", command=self.invoice_tree.xview)
        self.invoice_tree.configure(xscrollcommand=tree_scrollbar_x.set)
        tree_scrollbar_x.pack(side="bottom", fill="x")
        self.invoice_tree.pack(side="left", fill="both", expand=True)
        self.invoice_tree.bind("<Double-1>", self._on_invoice_item_double_click_for_edit)

        bottom_frame = ttk.Frame(tab)
        bottom_frame.pack(fill="x", padx=5, pady=10)
        self.invoice_total_sum_label = ttk.Label(bottom_frame, text="총계: 0 원", font=("Arial", 10, "bold"))
        self.invoice_total_sum_label.pack(side="left", padx=5)
        ttk.Button(bottom_frame, text="선택 품목 삭제", command=self._remove_item_from_invoice).pack(side="right", padx=5)
        ttk.Button(bottom_frame, text="명세서 초기화", command=self._clear_invoice).pack(side="right", padx=5)
        ttk.Button(bottom_frame, text="엑셀 생성", command=self._generate_excel_invoice).pack(side="right", padx=10, ipady=5)

    def _refresh_company_listbox_invoice_tab(self):
        company_display_names = []
        for company in sorted(self.companies, key=lambda c: c.name):
            display_name = str(company.name)
            if company.custom_price_profile_id:
                profile = next((p for p in self.price_profiles if p.id == company.custom_price_profile_id), None)
                if profile:
                    display_name = f"{company.name} (단가: {profile.name})"
                else: 
                    display_name = f"{company.name} (단가: {str(company.price_tier)})" 
            else:
                display_name = f"{company.name} (단가: {str(company.price_tier)})"
            company_display_names.append(display_name)
            
        self.invoice_company_combo['values'] = company_display_names
        if company_display_names:
            current_selection_text = self.invoice_company_combo.get()
            if current_selection_text in company_display_names:
                self.invoice_company_combo.set(current_selection_text)
            else:
                self.invoice_company_combo.current(0)
            self._on_invoice_company_selected(None) 
        else:
            self.invoice_company_combo.set('')
            self.selected_company_for_invoice = None
            self._refresh_item_listbox_invoice_tab()

    def _on_invoice_company_selected(self, event):
        selected_display_str_from_combo = self.invoice_company_combo.get()
        if not selected_display_str_from_combo:
            self.selected_company_for_invoice = None
        else:
            company_name_part = selected_display_str_from_combo.split(" (단가:")[0]
            self.selected_company_for_invoice = next((c for c in self.companies if c.name == company_name_part), None)
        
        self._refresh_item_listbox_invoice_tab()

    def _refresh_item_listbox_invoice_tab(self, filter_text=""):
        self.invoice_item_listbox.delete(0, tk.END)
        search_term = self.invoice_item_search_var.get().lower() if filter_text == "" else filter_text.lower()
        current_company = self.selected_company_for_invoice
        current_price_profile: Optional[PriceProfile] = None
        if current_company and current_company.custom_price_profile_id:
            current_price_profile = next((p for p in self.price_profiles if p.id == current_company.custom_price_profile_id), None)

        unique_representative_items: Dict[tuple, Item] = {}
        for item_obj in self.product_master_items:
            passes_search = False
            if not search_term or any(st in s.lower() for s in [item_obj.lot, item_obj.model_name, item_obj.product_name, item_obj.spec] for st in search_term.split() if st):
                passes_search = True
            if passes_search:
                item_key = (item_obj.model_name, item_obj.product_name, item_obj.spec, item_obj.treatment_code, item_obj.udi_di)
                if item_key not in unique_representative_items: unique_representative_items[item_key] = item_obj
        
        if not hasattr(self, 'invoice_tab_display_to_item_map'): self.invoice_tab_display_to_item_map: Dict[str, Item] = {}
        self.invoice_tab_display_to_item_map.clear()
        display_strings_for_listbox = []

        for rep_item_obj in unique_representative_items.values():
            display_text = f"{rep_item_obj.product_name} ({rep_item_obj.model_name} / {rep_item_obj.spec})"
            unit_price: Optional[Decimal] = None; price_source = ""
            if current_price_profile:
                model_name_normalized = storage.normalize_text(rep_item_obj.model_name)
                product_name_normalized = storage.normalize_text(rep_item_obj.product_name)
                spec_normalized = storage.normalize_text(rep_item_obj.spec)
                item_profile_key_str = storage.ITEM_KEY_SEPARATOR.join([model_name_normalized, product_name_normalized, spec_normalized])
                if item_profile_key_str in current_price_profile.item_prices:
                    unit_price = current_price_profile.item_prices[item_profile_key_str]
                    price_source = f" ({current_price_profile.name})"
            
            if unit_price is None and current_company:
                unit_price = rep_item_obj.get_price_for_tier(current_company.price_tier)
                if unit_price is not None: 
                    if not price_source:
                         price_source = f" ({str(current_company.price_tier)})"
            
            display_text += f" (단가: {unit_price:,.0f}{price_source})" if unit_price is not None else " (단가: N/A)"
            display_strings_for_listbox.append(display_text)
            self.invoice_tab_display_to_item_map[display_text] = rep_item_obj
        
        for text_to_display in sorted(display_strings_for_listbox): self.invoice_item_listbox.insert(tk.END, text_to_display)
        if self.invoice_item_listbox.size() > 0:
            self.invoice_item_listbox.selection_set(0)
    
    def _filter_invoice_items(self, *args): self._refresh_item_listbox_invoice_tab(self.invoice_item_search_var.get())

    def _on_invoice_item_listbox_double_click(self, event):
        self._add_item_to_invoice()

    def _add_item_to_invoice(self):
        selected_indices = self.invoice_item_listbox.curselection()
        if not selected_indices: messagebox.showwarning("품목 미선택", "추가할 품목을 리스트에서 선택해주세요."); return
        selected_item_display_name = self.invoice_item_listbox.get(selected_indices[0])
        representative_item_obj = self.invoice_tab_display_to_item_map.get(selected_item_display_name)
        if not representative_item_obj: messagebox.showerror("오류", "선택된 품목에 대한 내부 참조를 찾을 수 없습니다."); return
        
        candidate_items = [item for item in self.product_master_items if item.model_name == representative_item_obj.model_name and item.product_name == representative_item_obj.product_name and item.spec == representative_item_obj.spec and item.treatment_code == representative_item_obj.treatment_code and item.udi_di == representative_item_obj.udi_di]
        if not candidate_items: messagebox.showerror("오류", "선택된 품목에 해당하는 제품 마스터 정보를 찾을 수 없습니다 (후보 없음)."); return
        selected_item_obj = sorted(candidate_items, key=lambda i: i.lot)[0]

        if not self.selected_company_for_invoice: messagebox.showwarning("거래처 미선택", "먼저 거래처를 선택해주세요."); return
        
        unit_price: Optional[Decimal] = None
        current_price_profile: Optional[PriceProfile] = None
        if self.selected_company_for_invoice.custom_price_profile_id:
            current_price_profile = next((p for p in self.price_profiles if p.id == self.selected_company_for_invoice.custom_price_profile_id), None)
        
        if current_price_profile:
            model_name_normalized = storage.normalize_text(selected_item_obj.model_name)
            product_name_normalized = storage.normalize_text(selected_item_obj.product_name)
            spec_normalized = storage.normalize_text(selected_item_obj.spec)
            item_profile_key_str = storage.ITEM_KEY_SEPARATOR.join([model_name_normalized, product_name_normalized, spec_normalized])
            if item_profile_key_str in current_price_profile.item_prices:
                unit_price = current_price_profile.item_prices[item_profile_key_str]
        
        if unit_price is None:
            unit_price = selected_item_obj.get_price_for_tier(self.selected_company_for_invoice.price_tier)

        if unit_price is None: 
            messagebox.showwarning("단가 정보 없음", f"선택된 품목 '{selected_item_obj.product_name}'에 대해 거래처 '{self.selected_company_for_invoice.name}'의 단가 정보를 찾을 수 없습니다.\n(커스텀 프로파일 및 기본 등급 모두 확인됨)\n품목을 추가할 수 없습니다."); return
        try:
            quantity = int(self.invoice_item_quantity_spinbox.get())
            if quantity <= 0: messagebox.showwarning("수량 오류", "수량은 0보다 커야 합니다."); return
        except ValueError: messagebox.showwarning("수량 오류", "수량은 숫자로 입력해야 합니다."); return

        existing_line: Optional[InvoiceLine] = next((line for line in self.current_invoice_lines if line.item.lot == selected_item_obj.lot), None)
        if existing_line:
            if messagebox.askyesno("품목 중복", f"'{selected_item_obj.product_name}' (LOT: {selected_item_obj.lot}) 품목이 이미 명세서에 존재합니다. 수량을 합치시겠습니까?"): existing_line.qty += quantity
            else: return 
        else: self.current_invoice_lines.append(InvoiceLine(item=selected_item_obj, qty=quantity, unit_price=unit_price))
        self._refresh_invoice_tree(); self._update_invoice_total_sum()

    def _remove_item_from_invoice(self):
        selected_tree_items_iids = self.invoice_tree.selection() 
        if not selected_tree_items_iids: messagebox.showwarning("품목 미선택", "삭제할 품목을 테이블에서 선택해주세요."); return
        for item_lot in selected_tree_items_iids:
            line_to_remove = next((line for line in self.current_invoice_lines if line.item.lot == item_lot), None)
            if line_to_remove: self.current_invoice_lines.remove(line_to_remove)
        self._refresh_invoice_tree(); self._update_invoice_total_sum()

    def _clear_invoice(self):
        if messagebox.askyesno("초기화 확인", "정말로 현재 명세서 내용을 모두 지우시겠습니까?"):
            self.current_invoice_lines.clear(); self._refresh_invoice_tree(); self._update_invoice_total_sum()
            self.invoice_담당자_var.set(""); self.invoice_date_var.set(datetime.date.today().strftime("%Y-%m-%d"))

    def _refresh_invoice_tree(self):
        for i in self.invoice_tree.get_children(): self.invoice_tree.delete(i)
        for line in self.current_invoice_lines:
            insurance_price_display = f"{line.insurance_price:,.0f}" if line.insurance_price is not None else ""
            values = (line.lot, line.model_name, line.product_name, line.spec, line.qty, f"{line.unit_price:,.0f}", f"{line.supply_amount:,.0f}", f"{line.vat:,.0f}", insurance_price_display, line.treatment_code, line.udi_di)
            self.invoice_tree.insert("", tk.END, values=values, iid=line.item.lot)

    def _update_invoice_total_sum(self):
        total_supply = sum(line.supply_amount for line in self.current_invoice_lines)
        total_vat_sum = sum(line.vat for line in self.current_invoice_lines)
        grand_total = total_supply + total_vat_sum
        self.invoice_total_sum_label.config(text=f"공급가액 합계: {total_supply:,.0f} 원, 부가세 합계: {total_vat_sum:,.0f} 원,  총계: {grand_total:,.0f} 원")

    def _generate_excel_invoice(self):
        if not self.selected_company_for_invoice: messagebox.showwarning("회사 미선택", "명세서를 발행할 거래처를 선택해주세요."); return
        if not self.current_invoice_lines: messagebox.showwarning("품목 없음", "명세서에 추가된 품목이 없습니다."); return
        try: date_str = self.invoice_date_var.get(); invoice_dt = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError: messagebox.showerror("날짜 오류", "명세서 날짜 형식이 잘못되었습니다. (YYYY-MM-DD)"); return
        filepath = invoice.create_invoice_excel(company=self.selected_company_for_invoice, invoice_lines=self.current_invoice_lines, invoice_date=invoice_dt)
        if filepath:
            msg = f"거래명세서가 성공적으로 생성되었습니다:\n{filepath}"
            if messagebox.askyesno("성공", f"{msg}\n\n생성된 명세서 파일이 있는 폴더를 여시겠습니까?"): invoice.open_file_explorer(filepath)
            self._clear_invoice() 
        else: messagebox.showerror("실패", "거래명세서 생성에 실패했습니다.")

    def _on_invoice_item_double_click_for_edit(self, event):
        if hasattr(self, '_invoice_qty_edit_entry') and self._invoice_qty_edit_entry:
            self._invoice_qty_edit_entry.destroy()
            self._invoice_qty_edit_entry = None
        tree = event.widget
        region = tree.identify_region(event.x, event.y)
        if region != "cell": return
        column_id_str = tree.identify_column(event.x)
        item_iid = tree.focus()
        if not item_iid: return
        if column_id_str != "#5": return
        line_to_edit = next((line for line in self.current_invoice_lines if line.item.lot == item_iid), None)
        if not line_to_edit: return
        x, y, width, height = tree.bbox(item_iid, column_id_str)
        entry_var = tk.StringVar(value=str(line_to_edit.qty))
        entry = ttk.Entry(tree, textvariable=entry_var, width=width//7)
        entry.place(x=x, y=y, width=width, height=height, anchor='nw')
        entry.focus_set()
        entry.select_range(0, tk.END)
        self._invoice_qty_edit_entry = entry
        self._invoice_qty_edit_line = line_to_edit
        entry.bind("<Return>", self._save_invoice_qty_edit)
        entry.bind("<FocusOut>", self._save_invoice_qty_edit)
        entry.bind("<Escape>", lambda e: self._invoice_qty_edit_entry.destroy() if hasattr(self, '_invoice_qty_edit_entry') and self._invoice_qty_edit_entry else None)

    def _save_invoice_qty_edit(self, event):
        if not hasattr(self, '_invoice_qty_edit_entry') or not self._invoice_qty_edit_entry: return
        entry = self._invoice_qty_edit_entry
        new_qty_str = entry.get().strip()
        line_to_edit = self._invoice_qty_edit_line
        entry.destroy()
        self._invoice_qty_edit_entry = None
        if not new_qty_str:
            messagebox.showwarning("입력 오류", "수량을 입력해주세요.", parent=self)
            self._refresh_invoice_tree(); self._update_invoice_total_sum()
            return
        try:
            new_qty = int(new_qty_str)
            if new_qty <= 0:
                messagebox.showwarning("수량 오류", "수량은 0보다 커야 합니다.", parent=self)
                self._refresh_invoice_tree(); self._update_invoice_total_sum()
                return
            line_to_edit.qty = new_qty
            self._refresh_invoice_tree(); self._update_invoice_total_sum()
            if self.invoice_tree.exists(line_to_edit.item.lot):
                self.invoice_tree.selection_set(line_to_edit.item.lot)
                self.invoice_tree.focus(line_to_edit.item.lot)
                self.invoice_tree.see(line_to_edit.item.lot)
        except ValueError:
            messagebox.showwarning("수량 오류", "수량은 숫자로 입력해야 합니다.", parent=self)
            self._refresh_invoice_tree(); self._update_invoice_total_sum()
        except Exception as e:
            messagebox.showerror("저장 오류", f"수량 저장 중 오류 발생: {e}", parent=self)
            self._refresh_invoice_tree(); self._update_invoice_total_sum()

    def _sort_invoice_tree_column(self, col, is_numeric):
        try:
            data = [(self.invoice_tree.set(child, col), child) for child in self.invoice_tree.get_children('')]
            def convert(value_str):
                if is_numeric:
                    try: return float(value_str.replace(",", ""))
                    except ValueError: return 0 
                return value_str.lower() 
            if not hasattr(self, '_last_sort_invoice_col') or self._last_sort_invoice_col != col: self._last_sort_invoice_col = col; self._last_sort_invoice_reverse = False
            else: self._last_sort_invoice_reverse = not self._last_sort_invoice_reverse
            current_reverse = self._last_sort_invoice_reverse
            data.sort(key=lambda t: convert(t[0]), reverse=current_reverse)
            for index, (val, child) in enumerate(data): self.invoice_tree.move(child, '', index)
        except Exception as e: print(f"Treeview 정렬 중 오류: {e}")

    def _create_company_management_tab(self):
        tab = self.company_management_tab
        list_frame = ttk.LabelFrame(tab, text="거래처 목록"); list_frame.pack(side="left", fill="y", padx=10, pady=10)
        self.company_listbox = tk.Listbox(list_frame, exportselection=False, width=35, height=25); self.company_listbox.pack(side="left", fill="y")
        company_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.company_listbox.yview); company_scrollbar.pack(side="right", fill="y")
        self.company_listbox.config(yscrollcommand=company_scrollbar.set)
        self.company_listbox.bind("<<ListboxSelect>>", self._on_company_selected_management)
        details_frame = ttk.LabelFrame(tab, text="거래처 정보"); details_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        ttk.Label(details_frame, text="회사명:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.company_name_var = tk.StringVar()
        self.company_name_entry = ttk.Entry(details_frame, textvariable=self.company_name_var, width=40); self.company_name_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Label(details_frame, text="연락처:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.company_contact_var = tk.StringVar()
        self.company_contact_entry = ttk.Entry(details_frame, textvariable=self.company_contact_var, width=40); self.company_contact_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        ttk.Label(details_frame, text="가격 등급:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.company_price_tier_var = tk.StringVar()
        self.company_price_tier_combo = ttk.Combobox(details_frame, textvariable=self.company_price_tier_var, state="readonly", width=38)
        self.company_price_tier_combo.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self._update_company_price_tier_combo_values() 
        self.company_id_var = tk.StringVar() 
        buttons_frame = ttk.Frame(details_frame); buttons_frame.grid(row=5, column=0, columnspan=2, pady=20)
        ttk.Button(buttons_frame, text="새로 입력", command=self._clear_company_fields).pack(side="left", padx=5)
        ttk.Button(buttons_frame, text="추가", command=self._add_company).pack(side="left", padx=5)
        ttk.Button(buttons_frame, text="수정", command=self._update_company).pack(side="left", padx=5)
        ttk.Button(buttons_frame, text="삭제", command=self._delete_company).pack(side="left", padx=5)
        details_frame.grid_columnconfigure(1, weight=1)

    def _refresh_company_management_listbox(self):
        self.company_listbox.delete(0, tk.END)
        sorted_companies = sorted(self.companies, key=lambda comp: comp.name)
        for company in sorted_companies:
            display_name = str(company.name)
            if company.custom_price_profile_id:
                profile = next((p for p in self.price_profiles if p.id == company.custom_price_profile_id), None)
                if profile:
                    display_name = f"{company.name} (단가: {profile.name})"
                else: 
                    display_name = f"{company.name} (단가: 커스텀)"
            else:
                display_name = f"{company.name} (단가: {str(company.price_tier)})"
            self.company_listbox.insert(tk.END, display_name)
        self._clear_company_fields()
        self._update_company_price_tier_combo_values()

    def _on_company_selected_management(self, event):
        selected_indices = self.company_listbox.curselection()
        if not selected_indices: self._clear_company_fields(); return
        selected_display_str_from_listbox = self.company_listbox.get(selected_indices[0])
        company_name_part = selected_display_str_from_listbox.split(" (단가:")[0]
        company = next((c for c in self.companies if c.name == company_name_part), None)
        if company:
            self.company_id_var.set(company.id); self.company_name_var.set(company.name)
            self.company_contact_var.set(company.contact or "")
            if company.custom_price_profile_id:
                selected_profile = next((p for p in self.price_profiles if p.id == company.custom_price_profile_id), None)
                self.company_price_tier_var.set(selected_profile.name if selected_profile else str(PriceTier.CUSTOM)) 
            else:
                self.company_price_tier_var.set(str(company.price_tier)) 
        else: self._clear_company_fields()

    def _clear_company_fields(self):
        self.company_id_var.set(""); self.company_name_var.set(""); self.company_contact_var.set("")
        if hasattr(self, 'company_price_tier_combo') and self.company_price_tier_combo['values']:
             standard_tiers = [str(tier) for tier in PriceTier if tier != PriceTier.CUSTOM]
             default_tier_to_set = str(PriceTier.A)
             if default_tier_to_set in self.company_price_tier_combo['values']:
                 self.company_price_tier_var.set(default_tier_to_set)
             elif self.company_price_tier_combo['values']: 
                 self.company_price_tier_var.set(self.company_price_tier_combo['values'][0])
             else: 
                 self.company_price_tier_var.set("")
        else:
            self.company_price_tier_var.set("")
        if hasattr(self, 'company_listbox'): self.company_listbox.selection_clear(0, tk.END)
        if hasattr(self, 'company_name_entry'): self.company_name_entry.focus()

    def _update_company_price_tier_combo_values(self): 
        standard_tier_names = [str(tier) for tier in PriceTier if tier != PriceTier.CUSTOM]
        custom_profile_names = [p.name for p in sorted(self.price_profiles, key=lambda x: x.name)]
        combined_values = standard_tier_names + custom_profile_names
        if hasattr(self, 'company_price_tier_combo'):
            current_val = self.company_price_tier_var.get()
            self.company_price_tier_combo['values'] = combined_values
            if current_val in combined_values:
                self.company_price_tier_var.set(current_val)
            elif combined_values: 
                default_tier = str(PriceTier.A)
                if default_tier in combined_values: self.company_price_tier_var.set(default_tier)
                else: self.company_price_tier_var.set(combined_values[0])
            else: 
                self.company_price_tier_var.set("")
    
    def _add_company(self):
        name = self.company_name_var.get().strip()
        contact = self.company_contact_var.get().strip() or None
        selected_tier_or_profile_name = self.company_price_tier_var.get()
        if not name: messagebox.showwarning("입력 오류", "회사명은 필수 항목입니다."); return
        if not selected_tier_or_profile_name: messagebox.showwarning("입력 오류", "가격 등급 또는 프로파일을 선택해주세요."); return
        final_price_tier: Optional[PriceTier] = None
        final_custom_profile_id: Optional[str] = None
        standard_tier = next((tier for tier in PriceTier if str(tier) == selected_tier_or_profile_name and tier != PriceTier.CUSTOM), None)
        if standard_tier:
            final_price_tier = standard_tier
            final_custom_profile_id = None
        else: 
            custom_profile = next((p for p in self.price_profiles if p.name == selected_tier_or_profile_name), None)
            if custom_profile:
                final_price_tier = PriceTier.CUSTOM 
                final_custom_profile_id = custom_profile.id
            else:
                messagebox.showerror("오류", f"선택된 가격 설정 '{selected_tier_or_profile_name}'을(를) 찾을 수 없습니다."); return
        if any(c.name.lower() == name.lower() for c in self.companies): 
            messagebox.showwarning("중복 오류", f"이미 '{name}' 이름의 회사가 존재합니다."); return
        new_company = Company(name=name, contact=contact, price_tier=final_price_tier, custom_price_profile_id=final_custom_profile_id)
        self.companies.append(new_company)
        storage.save_companies(self.companies) 
        self._refresh_company_management_listbox()
        self._refresh_company_listbox_invoice_tab() 
        messagebox.showinfo("성공", f"'{name}' 회사가 추가되었습니다.")
        self._clear_company_fields()

    def _update_company(self):
        selected_id = self.company_id_var.get()
        if not selected_id: messagebox.showwarning("선택 오류", "수정할 회사를 목록에서 선택해주세요."); return
        name = self.company_name_var.get().strip()
        contact = self.company_contact_var.get().strip() or None
        selected_tier_or_profile_name = self.company_price_tier_var.get()
        if not name: messagebox.showwarning("입력 오류", "회사명은 필수 항목입니다."); return
        if not selected_tier_or_profile_name: messagebox.showwarning("입력 오류", "가격 등급 또는 프로파일을 선택해주세요."); return
        final_price_tier: Optional[PriceTier] = None
        final_custom_profile_id: Optional[str] = None
        standard_tier = next((tier for tier in PriceTier if str(tier) == selected_tier_or_profile_name and tier != PriceTier.CUSTOM), None)
        if standard_tier:
            final_price_tier = standard_tier
            final_custom_profile_id = None
        else: 
            custom_profile = next((p for p in self.price_profiles if p.name == selected_tier_or_profile_name), None)
            if custom_profile:
                final_price_tier = PriceTier.CUSTOM
                final_custom_profile_id = custom_profile.id
            else:
                messagebox.showerror("오류", f"선택된 가격 설정 '{selected_tier_or_profile_name}'을(를) 찾을 수 없습니다."); return
        company_to_update = next((c for c in self.companies if c.id == selected_id), None)
        if not company_to_update: messagebox.showerror("오류", "수정할 회사를 찾을 수 없습니다."); return
        if (company_to_update.name.lower() != name.lower() and any(c.name.lower() == name.lower() and c.id != selected_id for c in self.companies)):
            messagebox.showwarning("중복 오류", f"이미 '{name}' 이름의 다른 회사가 존재합니다."); return
        company_to_update.name = name
        company_to_update.contact = contact
        company_to_update.price_tier = final_price_tier
        company_to_update.custom_price_profile_id = final_custom_profile_id
        storage.save_companies(self.companies)
        self._refresh_company_management_listbox()
        self._refresh_company_listbox_invoice_tab()
        messagebox.showinfo("성공", f"'{name}' 회사 정보가 수정되었습니다.")
        self._clear_company_fields()

    def _delete_company(self):
        selected_id = self.company_id_var.get()
        if not selected_id: messagebox.showwarning("선택 오류", "삭제할 회사를 목록에서 선택해주세요."); return
        company_to_delete = next((c for c in self.companies if c.id == selected_id), None)
        if not company_to_delete: messagebox.showerror("오류", "삭제할 회사를 찾을 수 없습니다."); return
        if messagebox.askyesno("삭제 확인", f"정말로 '{company_to_delete.name}' 회사를 삭제하시겠습니까?"):
            self.companies.remove(company_to_delete); storage.save_companies(self.companies)
            self._refresh_company_management_listbox(); self._refresh_company_listbox_invoice_tab()
            messagebox.showinfo("성공", f"'{company_to_delete.name}' 회사가 삭제되었습니다."); self._clear_company_fields()

    def _create_product_viewer_tab(self):
        tab = self.product_viewer_tab; search_frame = ttk.Frame(tab); search_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(search_frame, text="검색 (LOT, 모델명, 제품명, 규격):").pack(side="left", padx=5)
        self.product_viewer_search_var = tk.StringVar(); self.product_viewer_search_var.trace_add("write", lambda *args: self._refresh_product_viewer_listbox())
        ttk.Entry(search_frame, textvariable=self.product_viewer_search_var, width=50).pack(side="left", fill="x", expand=True, padx=5)
        tree_frame = ttk.Frame(tab); tree_frame.pack(expand=True, fill="both", padx=5, pady=5)
        cols = ("lot", "model_name", "product_name", "spec", "treatment_code", "udi_di", "price_purchase", "price_a", "price_b", "price_dealer", "price_medical")
        header_texts = ["LOT", "모델명", "제품명", "규격", "치료재료코드", "UDI-DI", "매입가", "A단가", "B단가", "대리점가", "치료재료가"]
        col_widths = [100, 120, 180, 100, 100, 150, 80, 80, 80, 80, 80]
        self.product_viewer_tree = ttk.Treeview(tree_frame, columns=cols, show="headings")
        for i, col_id in enumerate(cols):
            self.product_viewer_tree.heading(col_id, text=header_texts[i], command=lambda c=col_id: self._sort_product_viewer_column(c))
            self.product_viewer_tree.column(col_id, width=col_widths[i], anchor='w', stretch=tk.NO)
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.product_viewer_tree.yview); hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.product_viewer_tree.xview)
        self.product_viewer_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set); vsb.pack(side="right", fill="y"); hsb.pack(side="bottom", fill="x"); self.product_viewer_tree.pack(expand=True, fill="both")
        self._refresh_product_viewer_listbox()

    def _refresh_product_viewer_listbox(self):
        if not hasattr(self, 'product_viewer_tree'): return
        for i in self.product_viewer_tree.get_children(): self.product_viewer_tree.delete(i)
        search_term = self.product_viewer_search_var.get().lower()
        filtered_items = [item for item in self.product_master_items if not search_term or any(search_term in s.lower() for s in [item.lot, item.model_name, item.product_name, item.spec])]
        sorted_items_for_display = sorted(filtered_items, key=lambda item: item.product_name)
        for item in sorted_items_for_display:
            values = (item.lot, item.model_name, item.product_name, item.spec, item.treatment_code, item.udi_di, f"{item.prices.get(PriceTier.PURCHASE.value, ''):,.0f}", f"{item.prices.get(PriceTier.A.value, ''):,.0f}", f"{item.prices.get(PriceTier.B.value, ''):,.0f}", f"{item.prices.get(PriceTier.DEALER.value, ''):,.0f}", f"{item.prices.get(PriceTier.MEDICAL.value, ''):,.0f}")
            self.product_viewer_tree.insert("", tk.END, values=values, iid=str(uuid.uuid4()))

    def _sort_product_viewer_column(self, col):
        try:
            data = [(self.product_viewer_tree.set(child, col), child) for child in self.product_viewer_tree.get_children('')]
            is_numeric_col = col.startswith("price_")
            def convert(value_str):
                if is_numeric_col:
                    try: return float(value_str.replace(",", "")) if value_str else -1
                    except ValueError: return -1 
                return value_str.lower() 
            if not hasattr(self, '_last_sort_viewer_col') or self._last_sort_viewer_col != col: self._last_sort_viewer_col = col; self._last_sort_viewer_reverse = False
            else: self._last_sort_viewer_reverse = not self._last_sort_viewer_reverse
            current_reverse = self._last_sort_viewer_reverse
            data.sort(key=lambda t: convert(t[0]), reverse=current_reverse)
            for index, (val, child) in enumerate(data): self.product_viewer_tree.move(child, '', index)
        except Exception as e: print(f"Product Viewer Treeview 정렬 중 오류: {e}")

    def _create_price_profile_management_tab(self):
        tab = self.price_profile_management_tab
        profile_list_frame = ttk.LabelFrame(tab, text="단가 프로파일 목록"); profile_list_frame.pack(side="left", fill="y", padx=10, pady=10)
        self.price_profile_listbox = tk.Listbox(profile_list_frame, exportselection=False, width=30, height=20); self.price_profile_listbox.pack(side="top", fill="y", expand=True)
        self.price_profile_listbox.bind("<<ListboxSelect>>", self._on_price_profile_selected)
        profile_buttons_frame = ttk.Frame(profile_list_frame); profile_buttons_frame.pack(side="bottom", fill="x", pady=5)
        ttk.Button(profile_buttons_frame, text="새 프로파일", command=self._add_new_price_profile).pack(side="left", padx=2, pady=2)
        ttk.Button(profile_buttons_frame, text="이름 변경", command=self._rename_price_profile).pack(side="left", padx=2, pady=2)
        ttk.Button(profile_buttons_frame, text="삭제", command=self._delete_price_profile).pack(side="left", padx=2, pady=2)
        self.profile_edit_frame = ttk.LabelFrame(tab, text="선택된 프로파일 상세"); self.profile_edit_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        self._setup_profile_edit_frame_widgets()
        self._refresh_price_profile_listbox(); self._clear_price_profile_details_view()

    def _setup_profile_edit_frame_widgets(self):
        for widget in self.profile_edit_frame.winfo_children(): widget.destroy()
        self.selected_profile_name_var = tk.StringVar()
        ttk.Label(self.profile_edit_frame, text="선택된 프로파일 이름:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(self.profile_edit_frame, textvariable=self.selected_profile_name_var, state="readonly", width=40).grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        item_prices_frame = ttk.LabelFrame(self.profile_edit_frame, text="프로파일 내 품목별 단가"); item_prices_frame.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=5, pady=5)
        self.profile_edit_frame.grid_rowconfigure(1, weight=1); self.profile_edit_frame.grid_columnconfigure(1, weight=1)
        item_price_cols = ("item_desc", "custom_price"); item_price_headers = ["품목 (모델명/제품명/규격)", "사용자 지정 단가"]; item_price_widths = [400, 100]
        self.profile_item_prices_tree = ttk.Treeview(item_prices_frame, columns=item_price_cols, show="headings", height=15)
        for i, col_id in enumerate(item_price_cols):
            self.profile_item_prices_tree.heading(col_id, text=item_price_headers[i])
            self.profile_item_prices_tree.column(col_id, width=item_price_widths[i], anchor='w' if i == 0 else 'e')
        
        self.profile_item_prices_tree.bind("<Double-1>", self._on_profile_price_double_click)

        tree_scroll_y = ttk.Scrollbar(item_prices_frame, orient="vertical", command=self.profile_item_prices_tree.yview); self.profile_item_prices_tree.configure(yscrollcommand=tree_scroll_y.set)
        self.profile_item_prices_tree.pack(side="left", fill="both", expand=True); tree_scroll_y.pack(side="right", fill="y")
        item_buttons_frame = ttk.Frame(self.profile_edit_frame); item_buttons_frame.grid(row=2, column=0, columnspan=3, pady=5)
        ttk.Button(item_buttons_frame, text="품목 단가 추가/수정", command=self._add_or_edit_profile_item_price).pack(side="left", padx=5)
        ttk.Button(item_buttons_frame, text="품목 단가 삭제", command=self._remove_profile_item_price).pack(side="left", padx=5)

    def _on_profile_price_double_click(self, event):
        if hasattr(self, '_profile_price_edit_entry') and self._profile_price_edit_entry:
            self._profile_price_edit_entry.destroy()
            self._profile_price_edit_entry = None
        tree = event.widget
        region = tree.identify_region(event.x, event.y)
        if region != "cell": return
        column_id = tree.identify_column(event.x)
        item_iid = tree.focus() 
        if not item_iid or column_id != "#2": return
        x, y, width, height = tree.bbox(item_iid, column_id)
        current_values = tree.item(item_iid, "values")
        if not current_values or len(current_values) < 2: return
        selected_profile_name = self.selected_profile_name_var.get()
        profile = next((p for p in self.price_profiles if p.name == selected_profile_name), None)
        if not profile: return
        if item_iid not in profile.item_prices:
            print(f"Warning: Item key '{item_iid}' not found in profile '{profile.name}' for editing.")
            return
        original_price_decimal = profile.item_prices[item_iid]
        entry_var = tk.StringVar(value=str(original_price_decimal))
        entry = ttk.Entry(tree, textvariable=entry_var, width=width//7)
        entry.place(x=x, y=y, width=width, height=height, anchor='nw')
        entry.focus_set()
        entry.select_range(0, tk.END)
        self._profile_price_edit_entry = entry
        self._profile_price_edit_item_iid = item_iid
        self._profile_price_edit_profile = profile
        entry.bind("<Return>", self._save_profile_price_edit)
        entry.bind("<FocusOut>", self._save_profile_price_edit)
        entry.bind("<Escape>", lambda e: self._profile_price_edit_entry.destroy() if hasattr(self, '_profile_price_edit_entry') and self._profile_price_edit_entry else None)

    def _save_profile_price_edit(self, event):
        if not hasattr(self, '_profile_price_edit_entry') or not self._profile_price_edit_entry: return
        entry = self._profile_price_edit_entry
        new_price_str = entry.get().strip()
        item_iid = self._profile_price_edit_item_iid 
        profile = self._profile_price_edit_profile
        entry.destroy()
        self._profile_price_edit_entry = None
        if not new_price_str:
            messagebox.showwarning("입력 오류", "단가를 입력해주세요.", parent=self)
            self._refresh_profile_item_prices_tree(profile)
            return
        try:
            new_price_decimal = Decimal(new_price_str)
            if new_price_decimal < Decimal("0"):
                messagebox.showwarning("가격 오류", "단가는 0보다 크거나 같아야 합니다.", parent=self)
                self._refresh_profile_item_prices_tree(profile)
                return
            profile.item_prices[item_iid] = new_price_decimal
            storage.save_price_profiles(self.price_profiles)
            self._refresh_profile_item_prices_tree(profile)
            if self.price_profile_listbox.curselection():
                selected_profile_name_in_list = self.price_profile_listbox.get(self.price_profile_listbox.curselection()[0])
                if selected_profile_name_in_list == profile.name:
                    if self.profile_item_prices_tree.exists(item_iid):
                         self.profile_item_prices_tree.selection_set(item_iid)
                         self.profile_item_prices_tree.focus(item_iid)
                         self.profile_item_prices_tree.see(item_iid)
        except InvalidOperation:
            messagebox.showwarning("가격 오류", "유효한 숫자 형식으로 단가를 입력해주세요 (예: 123.45).", parent=self)
            self._refresh_profile_item_prices_tree(profile)
        except Exception as e:
            messagebox.showerror("저장 오류", f"단가 저장 중 오류 발생: {e}", parent=self)
            self._refresh_profile_item_prices_tree(profile)

    def _refresh_price_profile_listbox(self):
        if not hasattr(self, 'price_profile_listbox'): return
        current_selection_index = self.price_profile_listbox.curselection(); current_selected_name = None
        if current_selection_index: current_selected_name = self.price_profile_listbox.get(current_selection_index[0])
        self.price_profile_listbox.delete(0, tk.END)
        sorted_profiles = sorted(self.price_profiles, key=lambda p: p.name); new_selection_index = -1
        for i, profile in enumerate(sorted_profiles):
            self.price_profile_listbox.insert(tk.END, profile.name)
            if profile.name == current_selected_name: new_selection_index = i
        if new_selection_index != -1: self.price_profile_listbox.selection_set(new_selection_index); self.price_profile_listbox.see(new_selection_index)
        else: self._clear_price_profile_details_view()
        self._update_company_price_tier_combo_values()

    def _add_new_price_profile(self):
        profile_name = simpledialog.askstring("새 단가 프로파일", "새 프로파일 이름을 입력하세요:", parent=self)
        if profile_name:
            profile_name = profile_name.strip()
            if not profile_name: messagebox.showwarning("입력 오류", "프로파일 이름은 비워둘 수 없습니다.", parent=self); return
            if any(p.name.lower() == profile_name.lower() for p in self.price_profiles): messagebox.showwarning("중복 오류", f"이미 '{profile_name}' 이름의 프로파일이 존재합니다.", parent=self); return
            
            new_profile = PriceProfile(name=profile_name)
            if not self.product_master_items:
                self._load_product_master_data() 

            for item_obj in self.product_master_items:
                dealer_price = item_obj.prices.get(PriceTier.DEALER.value)
                if dealer_price is not None:
                    item_key_tuple = (storage.normalize_text(item_obj.model_name), storage.normalize_text(item_obj.product_name), storage.normalize_text(item_obj.spec))
                    item_key_str = storage.ITEM_KEY_SEPARATOR.join(item_key_tuple)
                    new_profile.item_prices[item_key_str] = dealer_price
            
            self.price_profiles.append(new_profile)
            storage.save_price_profiles(self.price_profiles)
            self._refresh_price_profile_listbox()
            newly_added_profile_selected = False
            for i, p_name in enumerate(self.price_profile_listbox.get(0, tk.END)):
                if p_name == profile_name:
                    self.price_profile_listbox.selection_set(i)
                    self.price_profile_listbox.see(i)
                    self._on_price_profile_selected(None) 
                    newly_added_profile_selected = True
                    break
            if not newly_added_profile_selected and self.price_profile_listbox.size() > 0:
                self.price_profile_listbox.selection_set(0) 
                self._on_price_profile_selected(None)

            messagebox.showinfo("성공", f"'{profile_name}' 프로파일이 추가되고 기본 단가로 채워졌습니다.", parent=self)
            self._update_company_price_tier_combo_values() 
    
    def _rename_price_profile(self):
        selected_indices = self.price_profile_listbox.curselection()
        if not selected_indices: messagebox.showwarning("프로파일 미선택", "이름을 변경할 프로파일을 목록에서 선택해주세요.", parent=self); return
        selected_profile_name = self.price_profile_listbox.get(selected_indices[0])
        profile_to_rename = next((p for p in self.price_profiles if p.name == selected_profile_name), None)
        if not profile_to_rename: messagebox.showerror("오류", "선택된 프로파일을 찾을 수 없습니다.", parent=self); return
        new_name = simpledialog.askstring("프로파일 이름 변경", "새 프로파일 이름을 입력하세요:", initialvalue=profile_to_rename.name, parent=self)
        if new_name:
            new_name = new_name.strip()
            if not new_name: messagebox.showwarning("입력 오류", "프로파일 이름은 비워둘 수 없습니다.", parent=self); return
            if new_name.lower() != profile_to_rename.name.lower() and any(p.name.lower() == new_name.lower() for p in self.price_profiles): messagebox.showwarning("중복 오류", f"이미 '{new_name}' 이름의 프로파일이 존재합니다.", parent=self); return
            profile_to_rename.name = new_name
            storage.save_price_profiles(self.price_profiles)
            self._refresh_price_profile_listbox()
            for i, p_name in enumerate(self.price_profile_listbox.get(0, tk.END)):
                if p_name == new_name: 
                    self.price_profile_listbox.selection_set(i)
                    self.price_profile_listbox.see(i)
                    self._on_price_profile_selected(None)
                    break
            messagebox.showinfo("성공", f"프로파일 이름이 '{new_name}'(으)로 변경되었습니다.", parent=self)
            self._update_company_price_tier_combo_values()

    def _delete_price_profile(self):
        selected_indices = self.price_profile_listbox.curselection()
        if not selected_indices: messagebox.showwarning("프로파일 미선택", "삭제할 프로파일을 목록에서 선택해주세요.", parent=self); return
        selected_profile_name = self.price_profile_listbox.get(selected_indices[0])
        profile_to_delete = next((p for p in self.price_profiles if p.name == selected_profile_name), None)
        if not profile_to_delete: messagebox.showerror("오류", "선택된 프로파일을 찾을 수 없습니다.", parent=self); return
        if messagebox.askyesno("삭제 확인", f"정말로 '{profile_to_delete.name}' 프로파일을 삭제하시겠습니까?\n이 프로파일을 사용하는 모든 거래처에서 연결이 해제됩니다.", parent=self):
            for company in self.companies:
                if company.custom_price_profile_id == profile_to_delete.id: company.custom_price_profile_id = None
            storage.save_companies(self.companies)
            self.price_profiles.remove(profile_to_delete)
            storage.save_price_profiles(self.price_profiles)
            self._refresh_price_profile_listbox()
            self._refresh_company_management_listbox()
            self._refresh_company_listbox_invoice_tab()
            messagebox.showinfo("성공", f"'{profile_to_delete.name}' 프로파일이 삭제되었습니다.", parent=self)
            self._clear_price_profile_details_view()
            self._update_company_price_tier_combo_values()

    def _clear_price_profile_details_view(self):
        if hasattr(self, 'selected_profile_name_var'): self.selected_profile_name_var.set("")
        if hasattr(self, 'profile_item_prices_tree'):
            for i in self.profile_item_prices_tree.get_children(): self.profile_item_prices_tree.delete(i)

    def _on_price_profile_selected(self, event):
        if not hasattr(self, 'price_profile_listbox'): return
        selected_indices = self.price_profile_listbox.curselection()
        if not selected_indices: self._clear_price_profile_details_view(); return
        selected_profile_name = self.price_profile_listbox.get(selected_indices[0])
        profile = next((p for p in self.price_profiles if p.name == selected_profile_name), None)
        if profile: 
            self.selected_profile_name_var.set(profile.name)
            self._refresh_profile_item_prices_tree(profile)
        else: self._clear_price_profile_details_view()

    def _refresh_profile_item_prices_tree(self, profile: PriceProfile):
        if not hasattr(self, 'profile_item_prices_tree'): return
        for i in self.profile_item_prices_tree.get_children(): self.profile_item_prices_tree.delete(i)
        
        sorted_item_str_keys = sorted(
            profile.item_prices.keys(),
            key=lambda k_str: (
                k_str.split(storage.ITEM_KEY_SEPARATOR)[1], 
                k_str.split(storage.ITEM_KEY_SEPARATOR)[0], 
                k_str.split(storage.ITEM_KEY_SEPARATOR)[2]
            )
        )

        for item_key_str in sorted_item_str_keys:
            price = profile.item_prices[item_key_str]
            key_parts = item_key_str.split(storage.ITEM_KEY_SEPARATOR)
            m, p, s = key_parts[0], key_parts[1], key_parts[2]
            
            master_item_ref = next((it for it in self.product_master_items if storage.normalize_text(it.model_name) == m and storage.normalize_text(it.product_name) == p and storage.normalize_text(it.spec) == s), None)
            item_desc_display = f"{p} ({m} / {s})" 
            if master_item_ref: 
                item_desc_display = f"{master_item_ref.product_name} ({master_item_ref.model_name} / {master_item_ref.spec})"
            
            self.profile_item_prices_tree.insert("", tk.END, iid=item_key_str, values=(item_desc_display, f"{price:,.2f}"))

    def _add_or_edit_profile_item_price(self):
        selected_profile_indices = self.price_profile_listbox.curselection()
        if not selected_profile_indices: messagebox.showwarning("프로파일 미선택", "단가를 추가/수정할 프로파일을 선택해주세요.", parent=self); return
        selected_profile_name = self.price_profile_listbox.get(selected_profile_indices[0])
        profile = next((p for p in self.price_profiles if p.name == selected_profile_name), None)
        if not profile: messagebox.showerror("오류", "선택된 프로파일을 찾을 수 없습니다.", parent=self); return
        
        selected_item_price_iid = self.profile_item_prices_tree.focus() 
        existing_item_key_str: Optional[str] = None
        initial_price_str = ""
        
        if selected_item_price_iid: 
            existing_item_key_str = selected_item_price_iid 
            if existing_item_key_str in profile.item_prices:
                initial_price_str = str(profile.item_prices[existing_item_key_str])
            else: 
                print(f"Warning: Tree IID (string key) '{existing_item_key_str}' not found in profile prices for editing. Profile items: {profile.item_prices}")
        
        dialog = EditProfileItemPriceDialog(self, self.product_master_items, profile_name=profile.name, existing_item_key_str=existing_item_key_str, initial_price_str=initial_price_str)
        if dialog.result:
            item_key_str_from_dialog, new_price_decimal = dialog.result
            profile.item_prices[item_key_str_from_dialog] = new_price_decimal
            storage.save_price_profiles(self.price_profiles)
            self._refresh_profile_item_prices_tree(profile)
            messagebox.showinfo("성공", "프로파일 품목 단가가 저장되었습니다.", parent=self)

    def _remove_profile_item_price(self):
        selected_profile_indices = self.price_profile_listbox.curselection()
        if not selected_profile_indices: messagebox.showwarning("프로파일 미선택", "단가를 삭제할 프로파일을 선택해주세요.", parent=self); return
        selected_profile_name = self.price_profile_listbox.get(selected_indices[0])
        profile = next((p for p in self.price_profiles if p.name == selected_profile_name), None)
        if not profile: messagebox.showerror("오류", "선택된 프로파일을 찾을 수 없습니다.", parent=self); return
        
        selected_item_price_iid = self.profile_item_prices_tree.focus() 
        if not selected_item_price_iid: messagebox.showwarning("품목 미선택", "프로파일에서 삭제할 품목 단가를 선택해주세요.", parent=self); return
        
        item_key_to_remove_str = selected_item_price_iid

        if item_key_to_remove_str in profile.item_prices:
            item_values = self.profile_item_prices_tree.item(selected_item_price_iid, "values")
            item_display_name = item_values[0] if item_values else item_key_to_remove_str
            
            if messagebox.askyesno("삭제 확인", f"'{profile.name}' 프로파일에서\n'{item_display_name}' 품목의 단가를 삭제하시겠습니까?", parent=self):
                del profile.item_prices[item_key_to_remove_str]
                storage.save_price_profiles(self.price_profiles)
                self._refresh_profile_item_prices_tree(profile)
                messagebox.showinfo("성공", "프로파일 품목 단가가 삭제되었습니다.", parent=self)
        else:
            messagebox.showerror("오류", f"선택된 품목 단가 키 '{item_key_to_remove_str}'을(를) 프로파일에서 찾을 수 없습니다.", parent=self)

# --- Custom Dialog for Editing Profile Item Price ---
class EditProfileItemPriceDialog(simpledialog.Dialog):
    def __init__(self, parent, product_master_items: List[Item], profile_name: str,
                 existing_item_key_str: Optional[str] = None,
                 initial_price_str: str = ""):
        self.product_master_items = product_master_items
        self.profile_name = profile_name
        self.existing_item_key_str = existing_item_key_str 
        self.initial_price_str = initial_price_str
        self.selected_item_key_str: Optional[str] = None 
        self.new_price_var = tk.StringVar(value=initial_price_str)
        self.result: Optional[tuple[str, Decimal]] = None 
        self.item_search_var = tk.StringVar()
        self.item_listbox: Optional[tk.Listbox] = None
        self.dialog_item_map: Dict[str, tuple[str, str, str]] = {} 
        super().__init__(parent, title=f"'{profile_name}' 프로파일 단가 설정")

    def body(self, master):
        top_controls_frame = ttk.Frame(master)
        top_controls_frame.pack(fill="x", padx=10, pady=(10,0))
        ttk.Label(top_controls_frame, text="품목:").pack(side="left", padx=(0,5))
        if self.existing_item_key_str: 
            key_parts = self.existing_item_key_str.split(storage.ITEM_KEY_SEPARATOR)
            item_desc = "알 수 없는 품목"
            if len(key_parts) == 3:
                m, p, s = key_parts[0], key_parts[1], key_parts[2]
                master_item_ref = next((it for it in self.product_master_items if storage.normalize_text(it.model_name) == m and storage.normalize_text(it.product_name) == p and storage.normalize_text(it.spec) == s), None)
                item_desc = f"{master_item_ref.product_name} ({m}/{s})" if master_item_ref else f"{p} ({m}/{s})"
            ttk.Label(top_controls_frame, text=item_desc, width=40, anchor="w").pack(side="left", fill="x", expand=True)
            self.selected_item_key_str = self.existing_item_key_str 
        else: 
            search_entry = ttk.Entry(top_controls_frame, textvariable=self.item_search_var, width=30)
            search_entry.pack(side="left", fill="x", expand=True)
            search_entry.bind("<KeyRelease>", self._filter_dialog_items)
            listbox_frame = ttk.Frame(master)
            listbox_frame.pack(fill="both", expand=True, padx=10, pady=5)
            self.item_listbox = tk.Listbox(listbox_frame, exportselection=False, height=7)
            list_scrollbar_y = ttk.Scrollbar(listbox_frame, orient="vertical", command=self.item_listbox.yview)
            self.item_listbox.configure(yscrollcommand=list_scrollbar_y.set)
            list_scrollbar_y.pack(side="right", fill="y")
            self.item_listbox.pack(side="left", fill="both", expand=True)
            self._populate_dialog_item_listbox()
        price_frame = ttk.Frame(master)
        price_frame.pack(fill="x", padx=10, pady=(5,10))
        ttk.Label(price_frame, text="사용자 지정 단가:").pack(side="left", padx=(0,5))
        self.price_entry_widget = ttk.Entry(price_frame, textvariable=self.new_price_var, width=15)
        self.price_entry_widget.pack(side="left")
        if not self.existing_item_key_str and self.item_listbox:
            return self.item_listbox 
        return self.price_entry_widget

    def _populate_dialog_item_listbox(self, filter_text=""):
        if not self.item_listbox: return
        self.item_listbox.delete(0, tk.END)
        self.dialog_item_map.clear()
        search_term = filter_text.lower()
        unique_item_keys_in_listbox = set()
        for item_obj in self.product_master_items:
            item_tuple_key_for_dialog = (storage.normalize_text(item_obj.model_name), storage.normalize_text(item_obj.product_name), storage.normalize_text(item_obj.spec))
            item_str_key_for_dialog = storage.ITEM_KEY_SEPARATOR.join(item_tuple_key_for_dialog)
            if item_str_key_for_dialog in unique_item_keys_in_listbox: continue
            display_text = f"{item_obj.product_name} ({item_obj.model_name} / {item_obj.spec})"
            passes_search = not search_term or any(st in s.lower() for s in [item_obj.model_name, item_obj.product_name, item_obj.spec, display_text] for st in search_term.split() if st)
            if passes_search:
                self.item_listbox.insert(tk.END, display_text)
                self.dialog_item_map[display_text] = item_tuple_key_for_dialog
                unique_item_keys_in_listbox.add(item_str_key_for_dialog)
        if self.item_listbox.size() > 0: self.item_listbox.selection_set(0)

    def _filter_dialog_items(self, event=None):
        if self.item_listbox: self._populate_dialog_item_listbox(self.item_search_var.get())

    def buttonbox(self):
        box = ttk.Frame(self)
        ttk.Button(box, text="확인", width=10, command=self.ok, default=tk.ACTIVE).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(box, text="취소", width=10, command=self.cancel).pack(side=tk.LEFT, padx=5, pady=5)
        self.bind("<Return>", self.ok); self.bind("<Escape>", self.cancel)
        box.pack(pady=5)

    def validate(self):
        if not self.existing_item_key_str: 
            if not self.item_listbox or not self.item_listbox.curselection():
                messagebox.showwarning("품목 미선택", "프로파일에 추가할 품목을 선택해주세요.", parent=self); return False
        price_str = self.new_price_var.get().strip()
        if not price_str: 
            messagebox.showwarning("가격 오류", "단가를 입력해주세요.", parent=self); return False
        try:
            price_decimal = Decimal(price_str)
            if price_decimal < Decimal("0"): 
                messagebox.showwarning("가격 오류", "단가는 0보다 크거나 같아야 합니다.", parent=self); return False
        except InvalidOperation: 
            messagebox.showwarning("가격 오류", "유효한 숫자 형식으로 단가를 입력해주세요 (예: 123.45).", parent=self); return False
        return True

    def apply(self):
        item_key_tuple_to_return: Optional[tuple[str,str,str]] = None
        if not self.existing_item_key_str: 
            if self.item_listbox and self.item_listbox.curselection():
                selected_display_name = self.item_listbox.get(self.item_listbox.curselection()[0])
                item_key_tuple_to_return = self.dialog_item_map.get(selected_display_name)
        else: 
            key_parts = self.existing_item_key_str.split(storage.ITEM_KEY_SEPARATOR)
            if len(key_parts) == 3: 
                item_key_tuple_to_return = (storage.normalize_text(key_parts[0]), storage.normalize_text(key_parts[1]), storage.normalize_text(key_parts[2]))
        if not item_key_tuple_to_return: 
            messagebox.showerror("오류", "품목 키를 결정할 수 없습니다.", parent=self); self.result = None; return
        self.selected_item_key_str = storage.ITEM_KEY_SEPARATOR.join(item_key_tuple_to_return) # Removed map(str, ...) as parts are already strings
        self.result = (self.selected_item_key_str, Decimal(self.new_price_var.get().strip()))

def main():
    app = None
    try:
        app = App()
        app.update_idletasks(); app.update(); app.mainloop()
    except Exception as e:
        print("--------------------------------------------------")
        print(f"애플리케이션 실행 중 오류 발생: {e}")
        print("--------------------------------------------------")
        import traceback
        traceback.print_exc()
        print("--------------------------------------------------")
        if app:
            try: app.destroy()
            except: pass
        import sys
        sys.exit(1)

if __name__ == "__main__":
    main()
