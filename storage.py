import json
import os
import sys # Added sys
import shutil # Added shutil
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Any, Optional, Tuple # Added Tuple
from models import Company, Item, PriceTier, PriceProfile # Added PriceProfile

COMPANY_DATA_FILE = "data.json"
PRICE_PROFILES_FILE = "price_profiles.json" # New file for price profiles
ITEM_KEY_SEPARATOR = "|" # For converting tuple keys to string
# The actual default path for product master will be handled by the main application,
# possibly pointing to a bundled file or a user-configurable path.
# For now, this constant can represent a typical name.
DEFAULT_PRODUCT_MASTER_FILE_BASENAME = "item_data.json" # Updated to use the correct filename

USER_DATA_DIR_NAME = ".LohasInvoiceTool"

def get_bundle_dir():
    """Return the base directory for bundled files, or the script's directory."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    else:
        return os.path.dirname(os.path.abspath(__file__))

def get_user_data_path(filename: str) -> str:
    """Gets the full path to a file in the user-specific data directory."""
    user_data_dir = os.path.join(os.path.expanduser("~"), USER_DATA_DIR_NAME)
    if not os.path.exists(user_data_dir):
        try:
            os.makedirs(user_data_dir)
        except OSError as e:
            print(f"Error creating user data directory '{user_data_dir}': {e}")
            # Fallback to CWD if user dir creation fails, though not ideal
            return os.path.join(os.getcwd(), filename) 
    return os.path.join(user_data_dir, filename)

# --- Company Data Persistence (data.json) ---

def _company_to_dict(company: Company) -> Dict[str, Any]:
    """Company 객체를 JSON 직렬화를 위한 dict로 변환"""
    return {
        "id": company.id,
        "name": company.name,
        "price_tier": company.price_tier.name,  # Enum의 이름 (e.g., "A")을 저장
        "contact": company.contact,
        "custom_price_profile_id": company.custom_price_profile_id
    }

def _dict_to_company(data: Dict[str, Any]) -> Company:
    """dict를 Company 객체로 변환"""
    try:
        price_tier_name = data.get("price_tier", PriceTier.A.name) # 기본값 A
        price_tier = PriceTier[price_tier_name]
    except KeyError:
        print(f"Warning: Invalid price_tier name '{data.get('price_tier')}' for company '{data.get('name', 'N/A')}'. Defaulting to {PriceTier.A.name}.")
        price_tier = PriceTier.A
        
    return Company(
        id=data.get("id", ""), # ID가 없는 경우에 대한 처리 추가 (uuid로 자동생성되므로 문제는 없으나 방어적)
        name=data["name"],
        price_tier=price_tier,
        contact=data.get("contact"),
        custom_price_profile_id=data.get("custom_price_profile_id")
    )

def get_initial_companies() -> List[Company]:
    """초기 더미 회사 데이터를 반환 (다른 price_tier 적용)"""
    return [
        Company(name="샘플 병원 (A단가)", price_tier=PriceTier.A, contact="02-123-0001"),
        Company(name="샘플 대리점 (일반가)", price_tier=PriceTier.DEALER, contact="031-456-0002"),
    ]

def load_companies() -> List[Company]:
    """
    Loads company data from the user-specific data directory.
    If not found, creates initial data and saves it there.
    """
    user_file_path = get_user_data_path(COMPANY_DATA_FILE)

    if not os.path.exists(user_file_path):
        print(f"'{user_file_path}'을 찾을 수 없어 초기 데이터로 생성합니다.")
        initial_companies = get_initial_companies()
        # Save_companies will now save to the user_file_path
        save_companies(initial_companies) 
        return initial_companies

    try:
        with open(user_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

            # 이전 data.json은 {"companies": [...], "items": [...]} 구조였을 수 있음
            # 새 구조는 그냥 [...] 리스트 형태 또는 {"companies": [...]}
            companies_data_list: Optional[List[Dict[str, Any]]] = None
            if isinstance(data, list): # 최상위가 리스트인 경우 (새로운 단순 형식)
                 companies_data_list = data
            elif isinstance(data, dict) and "companies" in data: # 이전 형식 호환
                 companies_data_list = data.get("companies")
            else: # 알 수 없는 형식
                print(f"Warning: '{user_file_path}' has an unexpected format. Attempting to reset.")
                raise ValueError("Malformed company data: unknown format.")


            if not isinstance(companies_data_list, list):
                print(f"Warning: Company data in '{user_file_path}' is not a list. Will attempt to reset to initial data.")
                raise ValueError("Malformed company data: not a list.")

            parsed_companies = []
            for c_data in companies_data_list:
                if not isinstance(c_data, dict):
                    print(f"Warning: Skipping non-dictionary company entry in '{user_file_path}': {c_data}")
                    continue
                try:
                    # 필수 필드 확인 (예: name)
                    if "name" not in c_data:
                        print(f"Warning: Skipping company entry with missing 'name' in '{user_file_path}': {c_data}")
                        continue
                    parsed_companies.append(_dict_to_company(c_data))
                except KeyError as ke:
                    print(f"Warning: Skipping company entry with missing key in '{user_file_path}': {c_data}. Error: {ke}")
                    continue
            
            return parsed_companies
            
    except Exception as e: # Catch broader exceptions
        print(f"'{user_file_path}' 로드 또는 파싱 중 오류 발생 ({type(e).__name__}: {e}). 초기 데이터로 대체합니다.")
        initial_companies = get_initial_companies()
        try:
            save_companies(initial_companies) # 오류 발생 시 초기 데이터로 덮어쓰고 로드
            print(f"'{COMPANY_DATA_FILE}'이(가) 초기 데이터로 성공적으로 재작성되었습니다.")
            return initial_companies
        except Exception as e_fallback:
            print(f"초기 데이터로 대체하는 중 심각한 오류 발생: {e_fallback}. 빈 리스트를 반환합니다.")
            return []


def save_companies(companies: List[Company]):
    """
    회사 데이터를 사용자별 데이터 디렉토리의 COMPANY_DATA_FILE (data.json) 파일에 저장합니다.
    최상위가 리스트인 단순한 형태로 저장합니다.
    """
    user_file_path = get_user_data_path(COMPANY_DATA_FILE)
    data_to_save = [_company_to_dict(c) for c in companies]
    try:
        os.makedirs(os.path.dirname(user_file_path), exist_ok=True)
        with open(user_file_path, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)
        print(f"회사 데이터가 '{user_file_path}'에 성공적으로 저장되었습니다.")
    except IOError as e:
        print(f"'{user_file_path}' 저장 중 오류 발생: {e}")
    except Exception as e_general:
        print(f"회사 데이터 저장 중 일반 오류 발생 ({user_file_path}): {e_general}")

# --- Price Profile Data Persistence (price_profiles.json) ---

def _price_profile_to_dict(profile: PriceProfile) -> Dict[str, Any]:
    """PriceProfile 객체를 JSON 직렬화를 위한 dict로 변환"""
    # Convert tuple keys in item_prices to string keys
    string_key_item_prices = {
        ITEM_KEY_SEPARATOR.join(k): str(v) for k, v in profile.item_prices.items()
    }
    return {
        "id": profile.id,
        "name": profile.name,
        "item_prices": string_key_item_prices
    }

def _dict_to_price_profile(data: Dict[str, Any]) -> PriceProfile:
    """dict를 PriceProfile 객체로 변환"""
    # Convert string keys back to tuple keys and Decimal values
    parsed_item_prices: Dict[tuple[str, str, str], Decimal] = {}
    raw_item_prices = data.get("item_prices", {})
    if isinstance(raw_item_prices, dict):
        for str_key, str_val in raw_item_prices.items():
            try:
                key_parts = tuple(str_key.split(ITEM_KEY_SEPARATOR))
                if len(key_parts) == 3: # Expecting (model_name, product_name, spec)
                    parsed_item_prices[key_parts] = Decimal(str_val)
                else:
                    print(f"Warning: Skipping malformed item price key '{str_key}' in profile '{data.get('name', 'N/A')}'.")
            except (InvalidOperation, ValueError) as e:
                print(f"Warning: Skipping invalid price value '{str_val}' for key '{str_key}' in profile '{data.get('name', 'N/A')}'. Error: {e}")
    
    return PriceProfile(
        id=data.get("id", ""),
        name=data["name"],
        item_prices=parsed_item_prices
    )

def load_price_profiles() -> List[PriceProfile]:
    """Loads price profiles. Tries user data dir, then bundled file, then empty."""
    user_file_path = get_user_data_path(PRICE_PROFILES_FILE)
    
    path_to_load_from = None

    if os.path.exists(user_file_path):
        path_to_load_from = user_file_path
        # print(f"Loading price profiles from user path: {user_file_path}")
    else:
        # Try to load from bundle if it exists and copy to user dir for future use
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            bundle_dir = get_bundle_dir()
            bundled_file_path = os.path.join(bundle_dir, PRICE_PROFILES_FILE) # PRICE_PROFILES_FILE is "price_profiles.json"
            if os.path.exists(bundled_file_path):
                # print(f"Loading price profiles from bundled path: {bundled_file_path} and copying to user dir.")
                try:
                    os.makedirs(os.path.dirname(user_file_path), exist_ok=True)
                    shutil.copy2(bundled_file_path, user_file_path)
                    path_to_load_from = user_file_path # Load from the new copy in user dir
                except Exception as e_copy:
                    print(f"Error copying bundled price profiles to user dir: {e_copy}. Will try to load directly from bundle.")
                    path_to_load_from = bundled_file_path # Fallback to loading directly from bundle
            # else: print(f"Bundled price profiles file not found at {bundled_file_path}")
        # else: print("Not running bundled, and no user price profiles file found.")

    if not path_to_load_from:
        # print(f"No price profiles file found at user path or in bundle. Returning empty list.")
        return []

    try:
        with open(path_to_load_from, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            print(f"Warning: Data in '{path_to_load_from}' is not a list. Returning empty list.")
            return []

        profiles = []
        for p_data in data:
            if not isinstance(p_data, dict) or "name" not in p_data:
                print(f"Warning: Skipping invalid profile entry in '{path_to_load_from}': {p_data}")
                continue
            try:
                profiles.append(_dict_to_price_profile(p_data))
            except Exception as e:
                print(f"Warning: Error parsing profile entry '{p_data.get('name', 'N/A')}' in '{path_to_load_from}'. Error: {e}")
        return profiles
    except Exception as e:
        print(f"Error loading or parsing '{path_to_load_from}' ({type(e).__name__}: {e}). Returning empty list.")
        return []

def save_price_profiles(profiles: List[PriceProfile]):
    """Saves price profiles to the user-specific data directory."""
    user_file_path = get_user_data_path(PRICE_PROFILES_FILE)
    data_to_save = [_price_profile_to_dict(p) for p in profiles]
    try:
        os.makedirs(os.path.dirname(user_file_path), exist_ok=True)
        with open(user_file_path, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)
        print(f"가격 프로파일 데이터가 '{user_file_path}'에 성공적으로 저장되었습니다.")
    except IOError as e:
        print(f"'{user_file_path}' 저장 중 오류 발생: {e}")
    except Exception as e_general: # Catch other potential errors like makedirs failing
        print(f"가격 프로파일 저장 중 일반 오류 발생 ({user_file_path}): {e_general}")

# --- Product Master Data Loading (External JSON) ---

# JSON 키와 Item.prices의 키 매핑
# JSON의 "매입단가 (VAT 포함)" 같은 키를 PriceTier.PURCHASE.value ("purchase_price")로 매핑
JSON_PRICE_KEY_TO_MODEL_PRICE_KEY = {
    "매입단가                  (VAT 포함)": PriceTier.PURCHASE.value, # 원본 JSON의 공백 포함 키
    "A단가": PriceTier.A.value,
    "B단가": PriceTier.B.value,
    "일반대리점가": PriceTier.DEALER.value,
    "치료재료단가": PriceTier.MEDICAL.value,
}
# 필수 컬럼 정의 (가격 외)
REQUIRED_ITEM_COLUMNS = ["LOT", "모델명", "제품명", "규격", "치료재료코드", "UDI-DI(필수입력)"]


def load_product_master(json_file_path: str) -> List[Item]:
    """
    지정된 경로의 제품 마스터 JSON 파일에서 모든 시트의 품목 데이터를 로드하여
    단일 Item 리스트로 반환합니다.
    """
    if not os.path.exists(json_file_path):
        print(f"오류: 제품 마스터 파일 '{json_file_path}'을(를) 찾을 수 없습니다.")
        return []

    all_items: List[Item] = []
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data_by_sheet = json.load(f) # 최상위는 시트명을 키로 하는 딕셔너리

        if not isinstance(data_by_sheet, dict):
            print(f"오류: '{json_file_path}'의 최상위 구조가 딕셔너리(시트별)가 아닙니다.")
            return []

        # Process only the specified sheet
        target_sheet_name = "코딩데이터용(2024.01.04)"
        sheet_items_data = data_by_sheet.get(target_sheet_name)

        if not isinstance(sheet_items_data, list):
            print(f"Warning: 시트 '{target_sheet_name}'의 데이터가 리스트 형태가 아니거나 찾을 수 없습니다. 건너뜁니다.")
            if sheet_items_data is None:
                print(f"오류: 대상 시트 '{target_sheet_name}'을(를) 파일 '{json_file_path}'에서 찾을 수 없습니다.")
                print(f"정보: 파일 '{json_file_path}'에서 사용 가능한 시트 이름: {list(data_by_sheet.keys())}")
                return []
            else: # It exists but is not a list
                print(f"Warning: 시트 '{target_sheet_name}'의 데이터가 리스트 형태가 아닙니다. 실제 타입: {type(sheet_items_data)}")
                return []
        
        if not sheet_items_data: # Check if the list is empty
            print(f"정보: 대상 시트 '{target_sheet_name}'은(는) 비어 있습니다 (0개 항목).")
            # No further processing needed if the sheet is empty
        else:
            print(f"정보: 대상 시트 '{target_sheet_name}'에서 {len(sheet_items_data)}개의 원시 항목을 찾았습니다. 상세 처리 시작...")

        for item_data_dict in sheet_items_data:
            if not isinstance(item_data_dict, dict):
                print(f"Warning: 시트 '{target_sheet_name}'에 딕셔너리가 아닌 품목 데이터가 있습니다. 건너뜁니다: {item_data_dict}")
                continue
            
            # 필수 컬럼 존재 여부 확인 - This check should be outside the above if, and before the try block.
            missing_cols = [col for col in REQUIRED_ITEM_COLUMNS if col not in item_data_dict or item_data_dict[col] is None]
            if missing_cols:
                lot_info = item_data_dict.get('LOT', 'N/A') # Try to get LOT for better logging, even if it might be one of the missing ones.
                # If LOT itself is missing, it will appear in missing_cols.
                # Construct a more informative log for the item being skipped.
                item_identifier_for_log = f"LOT '{lot_info}'" if 'LOT' not in missing_cols else f"항목 '{item_data_dict}'"
                print(f"Warning: {item_identifier_for_log} 품목 데이터에 필수 컬럼이 누락되었습니다: {missing_cols}. 건너뜁니다.")
                continue

            try:
                prices: Dict[str, Decimal] = {}
                for json_key, model_key in JSON_PRICE_KEY_TO_MODEL_PRICE_KEY.items():
                    raw_price = item_data_dict.get(json_key)
                    if raw_price is not None: # null이나 누락이 아닐 경우
                        try:
                            prices[model_key] = Decimal(str(raw_price)) # 문자열로 변환 후 Decimal로
                        except InvalidOperation:
                            lot_info = item_data_dict.get('LOT', 'N/A')
                            print(f"Warning: LOT '{lot_info}' 품목의 '{json_key}' 가격 형식이 잘못되었습니다: '{raw_price}'. 이 가격은 제외됩니다.")
                    # else: 가격이 null이거나 누락된 경우, 해당 가격은 포함되지 않음
                
                raw_udi_di = str(item_data_dict.get("UDI-DI(필수입력)", "")).strip()
                parsed_udi_di: Optional[int] = None
                if raw_udi_di:
                    try:
                        # Attempt to convert to float first to catch "123.0" then to int
                        parsed_udi_di = int(float(raw_udi_di))
                    except ValueError:
                        lot_info = item_data_dict.get('LOT', 'N/A')
                        print(f"Warning: LOT '{lot_info}' 품목의 UDI-DI '{raw_udi_di}'는 유효한 정수가 아닙니다. UDI-DI를 비워둡니다.")

                item_obj = Item(
                    lot=str(item_data_dict["LOT"]),
                    model_name=str(item_data_dict["모델명"]),
                    product_name=str(item_data_dict["제품명"]).lstrip(','),
                    spec=str(item_data_dict["규격"]),
                    treatment_code=str(item_data_dict["치료재료코드"]),
                    udi_di=parsed_udi_di,
                    prices=prices
                )
                all_items.append(item_obj)
            except KeyError as ke:
                lot_info = item_data_dict.get('LOT', 'N/A')
                print(f"Warning: LOT '{lot_info}' 품목 데이터 처리 중 필수 키 오류: {ke}. 건너뜁니다.")
            except Exception as e_item: # 개별 아이템 파싱 오류
                lot_info = item_data_dict.get('LOT', 'N/A')
                print(f"Warning: LOT '{lot_info}' 품목 데이터 처리 중 오류 발생 ({type(e_item).__name__}: {e_item}). 건너뜁니다.")
        
        print(f"제품 마스터에서 총 {len(all_items)}개의 품목을 로드했습니다.")
        return all_items

    except FileNotFoundError:
        print(f"오류: 제품 마스터 파일 '{json_file_path}'을(를) 찾을 수 없습니다.")
        return []
    except json.JSONDecodeError:
        print(f"오류: 제품 마스터 파일 '{json_file_path}'이(가) 유효한 JSON 형식이 아닙니다.")
        return []
    except Exception as e:
        print(f"제품 마스터 파일 '{json_file_path}' 로드 중 예기치 않은 오류 발생: {e}")
        return []


if __name__ == '__main__':
    # --- 회사 데이터 테스트 ---
    print("--- 회사 데이터 테스트 ---")
    # 초기 회사 로드 (파일 없으면 생성)
    companies = load_companies()
    print(f"로드된 회사 수: {len(companies)}")
    for company in companies:
        print(f"  - {company.name} (ID: {company.id}, 등급: {company.price_tier.name})")

    # 회사 수정 및 추가 테스트
    if companies:
        companies[0].name = "수정된 회사명"
        companies[0].price_tier = PriceTier.B
    
    new_company = Company(name="신규 테스트 회사", price_tier=PriceTier.MEDICAL, contact="070-777-7777")
    companies.append(new_company)
    save_companies(companies)

    # 다시 로드하여 확인
    reloaded_companies = load_companies()
    print("\n재로드 후 회사 데이터:")
    assert any(c.name == "수정된 회사명" and c.price_tier == PriceTier.B for c in reloaded_companies)
    assert any(c.name == "신규 테스트 회사" for c in reloaded_companies)
    for company in reloaded_companies:
        print(f"  - {company.name} (ID: {company.id}, 등급: {company.price_tier.name}, 연락처: {company.contact})")
    print("회사 데이터 테스트 완료.\n")

    # --- 제품 마스터 로드 테스트 ---
    print("--- 제품 마스터 로드 테스트 ---")
    # 테스트용 더미 JSON 파일 생성
    dummy_master_file = "dummy_product_master.json"
    dummy_data = {
        "Sheet1": [
            {
                "LOT": "DUMMY_LOT_001", "모델명": "D-MOD-01", "제품명": "더미 제품 A", "규격": "Large",
                "치료재료코드": "D0000001", "UDI-DI(필수입력)": "1234567890123", # 정수형 UDI
                "매입단가                  (VAT 포함)": 100.0, "A단가": 120.0, "B단가": 110.0,
                "일반대리점가": 130.0, "치료재료단가": 150.0
            },
            {
                "LOT": "DUMMY_LOT_002", "모델명": "D-MOD-02", "제품명": "더미 제품 B", "규격": "Small",
                "치료재료코드": "D0000002", "UDI-DI(필수입력)": "9876543210987.0", # 정수 변환 가능한 실수형 UDI
                "A단가": 220.0, "치료재료단가": None # 치료재료단가가 null인 경우
            }
        ],
        "Sheet2": [
            {
                "LOT": "DUMMY_LOT_003", "모델명": "D-MOD-03", "제품명": "더미 제품 C", "규격": "Medium",
                "치료재료코드": "D0000003", "UDI-DI(필수입력)": "INVALID_UDI", # 잘못된 UDI
                "매입단가                  (VAT 포함)": 300.0, "A단가": "잘못된가격형식", "B단가": 310.0
            },
            { # 필수 컬럼 누락 케이스
                "LOT": "DUMMY_LOT_004", "모델명": "D-MOD-04", # "제품명" 누락
                "규격": "Tiny", "치료재료코드": "D0000004", "UDI-DI(필수입력)": "111222333",
                "A단가": 420.0
            }
        ]
    }
    with open(dummy_master_file, 'w', encoding='utf-8') as f:
        json.dump(dummy_data, f, ensure_ascii=False, indent=4)

    loaded_items = load_product_master(dummy_master_file)
    print(f"\n로드된 제품 마스터 품목 수: {len(loaded_items)}")
    assert len(loaded_items) == 2 # DUMMY_LOT_001, DUMMY_LOT_002 (003은 가격오류, 004는 필수컬럼 누락으로 제외)
    
    for item in loaded_items:
        print(f"  - LOT: {item.lot}, 제품명: {item.product_name}, 모델명: {item.model_name}")
        print(f"    가격: {item.prices}")
        if item.lot == "DUMMY_LOT_001":
            assert item.prices[PriceTier.A.value] == Decimal("120.0")
            assert item.prices[PriceTier.MEDICAL.value] == Decimal("150.0")
        if item.lot == "DUMMY_LOT_002":
            assert PriceTier.MEDICAL.value not in item.prices # null이었으므로 제외됨
            assert item.prices[PriceTier.A.value] == Decimal("220.0")

    # 존재하지 않는 파일 테스트
    print("\n존재하지 않는 파일 로드 시도:")
    load_product_master("non_existent_file.json")

    # 잘못된 JSON 형식 파일 테스트
    invalid_json_file = "invalid_master.json"
    with open(invalid_json_file, 'w', encoding='utf-8') as f:
        f.write("{not_json_content: ")
    print("\n잘못된 JSON 형식 파일 로드 시도:")
    load_product_master(invalid_json_file)

    # 테스트 후 더미 파일 삭제
    if os.path.exists(dummy_master_file):
        os.remove(dummy_master_file)
    if os.path.exists(invalid_json_file):
        os.remove(invalid_json_file)
        
    print("\n제품 마스터 로드 테스트 완료.")

    # --- 가격 프로파일 테스트 ---
    print("\n--- 가격 프로파일 테스트 ---")
    # 초기 프로파일 로드 (파일 없으면 빈 리스트)
    price_profiles = load_price_profiles()
    print(f"로드된 가격 프로파일 수: {len(price_profiles)}")

    # 새 프로파일 생성 및 아이템 가격 추가
    profile1 = PriceProfile(name="VIP 고객 단가")
    item_key1 = ("D-MOD-01", "더미 제품 A", "Large") # (model_name, product_name, spec)
    profile1.item_prices[item_key1] = Decimal("115.0") # VIP 가격
    
    profile2 = PriceProfile(name="여름 할인 프로모션")
    item_key2 = ("D-MOD-02", "더미 제품 B", "Small")
    profile2.item_prices[item_key2] = Decimal("200.0")
    profile2.item_prices[item_key1] = Decimal("118.0") # 여름 할인에도 더미 제품 A 포함

    profiles_to_save = [profile1, profile2]
    save_price_profiles(profiles_to_save)

    # 다시 로드하여 확인
    reloaded_profiles = load_price_profiles()
    print(f"\n재로드 후 가격 프로파일 수: {len(reloaded_profiles)}")
    assert len(reloaded_profiles) == 2
    
    for rp in reloaded_profiles:
        print(f"  - 프로파일명: {rp.name} (ID: {rp.id})")
        for item_k, price_v in rp.item_prices.items():
            print(f"    - 품목키: {item_k}, 가격: {price_v}")
        if rp.name == "VIP 고객 단가":
            assert rp.item_prices[item_key1] == Decimal("115.0")
        if rp.name == "여름 할인 프로모션":
            assert rp.item_prices[item_key2] == Decimal("200.0")
            assert rp.item_prices[item_key1] == Decimal("118.0")
            
    # 회사 데이터에 custom_price_profile_id 적용 테스트
    if reloaded_companies and reloaded_profiles:
        reloaded_companies[0].custom_price_profile_id = reloaded_profiles[0].id # 첫번째 회사에 첫번째 프로파일 적용
        save_companies(reloaded_companies)
        
        final_companies = load_companies()
        assert final_companies[0].custom_price_profile_id == reloaded_profiles[0].id
        print(f"\n회사 '{final_companies[0].name}'에 프로파일 ID '{final_companies[0].custom_price_profile_id}' 적용됨.")

    # 테스트 후 가격 프로파일 파일 삭제 (선택적)
    if os.path.exists(PRICE_PROFILES_FILE):
        os.remove(PRICE_PROFILES_FILE)
        print(f"'{PRICE_PROFILES_FILE}' 삭제 완료.")
        
    print("\n가격 프로파일 테스트 완료.")
