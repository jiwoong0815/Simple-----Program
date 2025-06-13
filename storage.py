import json
import os
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Any
from models import Company, Item

DATA_FILE = "data.json"

def _company_to_dict(company: Company) -> Dict[str, Any]:
    """Company 객체를 JSON 직렬화를 위한 dict로 변환"""
    return {
        "id": company.id,
        "name": company.name,
        "contact": company.contact
    }

def _dict_to_company(data: Dict[str, Any]) -> Company:
    """dict를 Company 객체로 변환"""
    return Company(id=data["id"], name=data["name"], contact=data.get("contact", ""))

def _item_to_dict(item: Item) -> Dict[str, Any]:
    """Item 객체를 JSON 직렬화를 위한 dict로 변환"""
    return {
        "id": item.id,
        "name": item.name,
        "default_unit_price": str(item.default_unit_price),  # Decimal을 문자열로 변환
        "company_prices": {cid: str(price) for cid, price in item.company_prices.items()} # Decimal을 문자열로 변환
    }

def _dict_to_item(data: Dict[str, Any]) -> Item:
    """dict를 Item 객체로 변환"""
    company_prices_data = data.get("company_prices", {})
    company_prices = {}
    for cid, price_str in company_prices_data.items():
        try:
            company_prices[cid] = Decimal(price_str)
        except InvalidOperation:
            print(f"Warning: Invalid price format for company '{cid}' in item '{data.get('name', 'N/A')}'. Skipping this company price.")
            # Optionally, decide how to handle this: skip, use default, or raise error
            # For now, we skip this specific company price.
            continue

    return Item(
        id=data["id"],
        name=data["name"],
        default_unit_price=Decimal(data.get("default_unit_price", "0.00")), # Handle missing default_unit_price
        company_prices=company_prices
    )

def get_initial_data() -> Dict[str, List[Dict[str, Any]]]:
    """초기 더미 데이터를 반환"""
    return {
        "companies": [
            _company_to_dict(Company(name="거래처A", contact="010-1111-2222")),
            _company_to_dict(Company(name="거래처B", contact="sales@company_b.com")),
            _company_to_dict(Company(name="주식회사 헬로월드", contact="02-777-8888")),
        ],
        "items": [
            _item_to_dict(Item(name="프리미엄 키보드", default_unit_price=Decimal("120000"))),
            _item_to_dict(Item(name="고급 마우스", default_unit_price=Decimal("75000"))),
            _item_to_dict(Item(name="27인치 모니터", default_unit_price=Decimal("350000"))),
            _item_to_dict(Item(name="USB-C 허브", default_unit_price=Decimal("45000.50"))),
            _item_to_dict(Item(name="노트북 거치대", default_unit_price=Decimal("25000"))),
        ]
    }

def load_data() -> Dict[str, List[Any]]:
    """
    data.json 파일에서 회사 및 품목 데이터를 로드합니다.
    파일이 없으면 초기 더미 데이터로 생성하고 로드합니다.
    """
    if not os.path.exists(DATA_FILE):
        print(f"'{DATA_FILE}'을 찾을 수 없어 초기 데이터로 생성합니다.")
        save_data([], []) # 빈 리스트로 파일 생성 후 초기 데이터 저장
        initial_content = get_initial_data()
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(initial_content, f, ensure_ascii=False, indent=4)
        
        # 초기 데이터로 companies와 items를 다시 로드
        companies = [_dict_to_company(c_data) for c_data in initial_content["companies"]]
        items = [_dict_to_item(i_data) for i_data in initial_content["items"]]
        return {"companies": companies, "items": items}

    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f) # Can raise JSONDecodeError

            companies_data = data.get("companies", [])
            items_data = data.get("items", [])

            if not isinstance(companies_data, list):
                print(f"Warning: 'companies' in '{DATA_FILE}' is not a list. Will attempt to reset to initial data.")
                raise ValueError("Malformed 'companies' data: not a list.")
            if not isinstance(items_data, list):
                print(f"Warning: 'items' in '{DATA_FILE}' is not a list. Will attempt to reset to initial data.")
                raise ValueError("Malformed 'items' data: not a list.")

            parsed_companies = []
            for c_data in companies_data:
                if not isinstance(c_data, dict):
                    print(f"Warning: Skipping non-dictionary company entry in '{DATA_FILE}': {c_data}")
                    continue
                try:
                    parsed_companies.append(_dict_to_company(c_data))
                except KeyError as ke:
                    print(f"Warning: Skipping company entry with missing key in '{DATA_FILE}': {c_data}. Error: {ke}")
                    continue
            
            parsed_items = []
            for i_data in items_data:
                if not isinstance(i_data, dict):
                    print(f"Warning: Skipping non-dictionary item entry in '{DATA_FILE}': {i_data}")
                    continue
                try:
                    # Ensure 'default_unit_price' exists or handle its absence if necessary
                    if "default_unit_price" not in i_data and "unit_price" in i_data:
                        # Simple backward compatibility: if old "unit_price" exists, use it as "default_unit_price"
                        print(f"Warning: Item '{i_data.get('name', 'N/A')}' uses old 'unit_price' field. Converting to 'default_unit_price'.")
                        i_data["default_unit_price"] = i_data.pop("unit_price")
                    elif "default_unit_price" not in i_data:
                         print(f"Warning: Item '{i_data.get('name', 'N/A')}' missing 'default_unit_price'. Setting to '0.00'.")
                         i_data["default_unit_price"] = "0.00" # Provide a default if missing

                    parsed_items.append(_dict_to_item(i_data))
                except KeyError as ke:
                    # This might catch missing 'id' or 'name' if _dict_to_item expects them strictly
                    print(f"Warning: Skipping item entry with missing critical key in '{DATA_FILE}': {i_data}. Error: {ke}")
                    continue
                except InvalidOperation as ioe: # For Decimal conversion issues (e.g. default_unit_price)
                    print(f"Warning: Skipping item entry with invalid default price in '{DATA_FILE}': {i_data}. Error: {ioe}")
                    continue
            
            return {"companies": parsed_companies, "items": parsed_items}
    except Exception as e: # Catch broader exceptions: JSONDecodeError, FileNotFoundError, ValueError, TypeError, etc.
        print(f"'{DATA_FILE}' 로드 또는 파싱 중 오류 발생 ({type(e).__name__}: {e}). 초기 데이터로 대체합니다.")
        initial_content = get_initial_data()
        # 오류 발생 시에도 초기 데이터로 덮어쓰고 로드
        try:
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(initial_content, f, ensure_ascii=False, indent=4)
            print(f"'{DATA_FILE}'이(가) 초기 데이터로 성공적으로 재작성되었습니다.")
            # Now, load from the newly written initial_content
            companies = [_dict_to_company(c_data) for c_data in initial_content["companies"]]
            items = [_dict_to_item(i_data) for i_data in initial_content["items"]]
            return {"companies": companies, "items": items}
        except Exception as e_fallback:
            print(f"초기 데이터로 대체하는 중 심각한 오류 발생: {e_fallback}. 빈 데이터를 반환합니다.")
            return {"companies": [], "items": []}


def save_data(companies: List[Company], items: List[Item]):
    """
    회사 및 품목 데이터를 data.json 파일에 저장합니다.
    """
    data_to_save = {
        "companies": [_company_to_dict(c) for c in companies],
        "items": [_item_to_dict(i) for i in items]
    }
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)
        print(f"데이터가 '{DATA_FILE}'에 성공적으로 저장되었습니다.")
    except IOError as e:
        print(f"'{DATA_FILE}' 저장 중 오류 발생: {e}")


if __name__ == '__main__':
    # 테스트: 데이터 로드 (파일 없으면 생성)
    loaded_data = load_data()
    print(f"로드된 회사 수: {len(loaded_data['companies'])}")
    for company in loaded_data['companies']:
        print(f"  - {company.name} (ID: {company.id})")
    
    print(f"로드된 품목 수: {len(loaded_data['items'])}")
    for item in loaded_data['items']:
        print(f"  - {item.name} (기본단가: {item.default_unit_price}, ID: {item.id}, 거래처별 가격: {len(item.company_prices)})")

    # 테스트: 데이터 수정 및 저장
    test_company_for_item_price = None
    if loaded_data['companies']:
        loaded_data['companies'][0].name = "수정된 거래처A"
        test_company_for_item_price = loaded_data['companies'][0]

    if loaded_data['items']:
        loaded_data['items'][0].default_unit_price = Decimal("150000.75")
        if test_company_for_item_price:
            loaded_data['items'][0].set_company_price(test_company_for_item_price.id, Decimal("140000.00"))
            print(f"테스트: {loaded_data['items'][0].name}에 대해 {test_company_for_item_price.name} 특별가 설정됨.")


    new_company = Company(name="새로운 회사 XYZ", contact="new@xyz.com")
    loaded_data['companies'].append(new_company)
    
    new_item = Item(name="특별 상품", default_unit_price=Decimal("99900"))
    if test_company_for_item_price: # Give it a company specific price too
        new_item.set_company_price(test_company_for_item_price.id, Decimal("95000"))
    loaded_data['items'].append(new_item)

    save_data(loaded_data['companies'], loaded_data['items'])

    # 다시 로드하여 확인
    reloaded_data = load_data()
    print("\n재로드 후 데이터:")
    print(f"로드된 회사 수: {len(reloaded_data['companies'])}")
    for company in reloaded_data['companies']:
        print(f"  - {company.name} (ID: {company.id})")
    
    print(f"로드된 품목 수: {len(reloaded_data['items'])}")
    for item in reloaded_data['items']:
        print(f"  - {item.name} (기본단가: {item.default_unit_price}, ID: {item.id}, 거래처별 가격: {len(item.company_prices)})")
        if test_company_for_item_price and item.name == "프리미엄 키보드": # Check specific item
             retrieved_price = item.get_price(test_company_for_item_price.id)
             print(f"    {test_company_for_item_price.name} 가격: {retrieved_price}")
             assert retrieved_price == Decimal("140000.00")
        if test_company_for_item_price and item.name == "특별 상품":
            retrieved_price_new_item = item.get_price(test_company_for_item_price.id)
            print(f"    {test_company_for_item_price.name} 가격 (특별 상품): {retrieved_price_new_item}")
            assert retrieved_price_new_item == Decimal("95000")


    # 특정 데이터 확인
    assert any(c.name == "수정된 거래처A" for c in reloaded_data['companies'])
    assert any(i.default_unit_price == Decimal("150000.75") for i in reloaded_data['items'] if i.name == "프리미엄 키보드")
    assert any(c.name == "새로운 회사 XYZ" for c in reloaded_data['companies'])
    assert any(i.name == "특별 상품" and i.default_unit_price == Decimal("99900") for i in reloaded_data['items'])
    print("\n테스트 완료.")
