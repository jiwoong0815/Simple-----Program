import uuid
import enum
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass, field
from typing import Optional, Dict, List

class PriceTier(enum.Enum):
    """가격 등급을 나타내는 열거형"""
    PURCHASE = "purchase_price"  # 매입단가 (VAT 포함)
    A = "price_A"                # A단가
    B = "price_B"                # B단가
    DEALER = "price_dealer"      # 일반대리점가
    MEDICAL = "price_medical"    # 치료재료단가
    ETC = "price_etc"            # 기타단가
    CUSTOM = "price_custom"      # 사용자 지정 단가 프로파일

    def __str__(self):
        # UI 표시에 사용될 수 있는 한글 이름 반환
        if self == PriceTier.PURCHASE:
            return "매입단가"
        elif self == PriceTier.A:
            return "A단가"
        elif self == PriceTier.B:
            return "B단가"
        elif self == PriceTier.DEALER:
            return "일반대리점가"
        elif self == PriceTier.MEDICAL:
            return "치료재료단가"
        elif self == PriceTier.ETC:
            return "기타단가"
        return self.name

@dataclass
class Company:
    """거래처 회사 정보를 담는 데이터 클래스"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    price_tier: PriceTier = PriceTier.A  # 기본값으로 A단가 설정
    contact: Optional[str] = None       # 전화/이메일 등
    custom_price_profile_id: Optional[str] = None # ID of the applied PriceProfile

    def __str__(self):
        # UI에 표시될 때, custom_price_profile_id를 기반으로 실제 프로파일 이름을 가져와야 함.
        # 여기서는 간단히 ID 존재 여부만 표시하거나, 기본 등급만 표시.
        # 실제 프로파일 이름 표시는 UI 로직에서 처리하는 것이 더 적합할 수 있음.
        tier_display = str(self.price_tier)
        if self.custom_price_profile_id:
            tier_display = "커스텀" # 실제 프로파일 이름은 UI에서 조회하여 표시
        return f"{self.name} (단가: {tier_display})"

@dataclass
class PriceProfile:
    """사용자 정의 단가 프로파일을 나타내는 데이터 클래스"""
    name: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    # Key: Tuple (model_name, product_name, spec) to uniquely identify an item type.
    # Value: Decimal price for that item in this profile.
    # JSON 저장을 위해 튜플 키를 문자열로 변환해야 할 수 있음 (예: "model|product|spec").
    item_prices: Dict[str, Decimal] = field(default_factory=dict) # 키는 "모델명|제품명|규격" 형태의 문자열

    def __str__(self):
        return self.name

@dataclass
class Item:
    """
    제품 마스터에서 로드된 품목 정보를 담는 데이터 클래스.
    이 객체는 애플리케이션 내에서 직접 수정되지 않고, 마스터 파일 재로드를 통해 갱신됩니다.
    """
    lot: str
    model_name: str  # 모델명
    product_name: str  # 제품명
    spec: str  # 규격
    treatment_code: str  # 치료재료코드
    udi_di: Optional[int]  # UDI-DI(필수입력)
    prices: Dict[str, Decimal] = field(default_factory=dict)  # 예: {'purchase_price': Decimal('100.00'), 'price_A': Decimal('120.00')}

    def get_price_for_tier(self, tier: PriceTier) -> Optional[Decimal]:
        """지정된 가격 등급에 해당하는 단가를 반환합니다."""
        return self.prices.get(tier.value)

    def __str__(self):
        return f"{self.product_name} ({self.model_name} / {self.spec}) - LOT: {self.lot}"

@dataclass
class InvoiceLine:
    """거래명세서의 각 품목 라인을 나타내는 데이터 클래스"""
    item: Item  # 원본 Item 객체 참조
    qty: int
    unit_price: Decimal  # 이 라인에 적용된 실제 단가 (회사 등급에 따라 결정됨)

    @property
    def supply_amount(self) -> Decimal:
        """공급가액 (수량 * 단가)"""
        return (self.qty * self.unit_price).quantize(Decimal("0"), rounding=ROUND_HALF_UP) # 소수점 없이 반올림

    @property
    def vat(self) -> Decimal:
        """부가세 (공급가액 * 0.1, 1원 단위 반올림)"""
        # 먼저 정확한 부가세를 계산한 후, 최종적으로 반올림
        exact_vat = self.supply_amount * Decimal("0.1")
        return exact_vat.quantize(Decimal("0"), rounding=ROUND_HALF_UP) # 1원 단위로 반올림 (소수점 0자리)

    # Excel 및 UI 표시에 필요한 Item의 속성들을 쉽게 접근할 수 있도록 property 추가
    @property
    def lot(self) -> str:
        return self.item.lot

    @property
    def model_name(self) -> str:
        return self.item.model_name

    @property
    def product_name(self) -> str:
        return self.item.product_name

    @property
    def spec(self) -> str:
        return self.item.spec

    @property
    def treatment_code(self) -> str:
        return self.item.treatment_code

    @property
    def udi_di(self) -> Optional[int]:
        return self.item.udi_di
    
    @property
    def insurance_price(self) -> Optional[Decimal]:
        """보험수가 (치료재료단가와 동일하다고 가정)"""
        return self.item.prices.get(PriceTier.MEDICAL.value)

@dataclass
class InvoiceRecord:
    """생성된 거래명세서 기록을 담는 데이터 클래스"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    invoice_date: str = "" # "YYYY-MM-DD"
    company_name: str = ""
    invoice_lines: List[InvoiceLine] = field(default_factory=list)
    total_amount: Decimal = Decimal("0")
    created_at: str = "" # ISO 8601 format

if __name__ == '__main__':
    # 테스트용 예시
    company1 = Company(name="테스트 병원 A", price_tier=PriceTier.A, contact="02-111-1111")
    company2 = Company(name="일반 대리점 B", price_tier=PriceTier.DEALER, contact="031-222-2222")
    company3 = Company(name="국립 병원 C", price_tier=PriceTier.MEDICAL, contact="042-333-3333")

    print(company1)
    print(company2)
    print(company3)
    print("-" * 20)

    # Item 객체 생성 (JSON에서 로드되었다고 가정)
    item_data_1 = {
        "lot": "LOT001", "model_name": "MODEL-X1", "product_name": "스마트 인공관절",
        "spec": "Size M, Type A", "treatment_code": "C1234567", "udi_di": 8801111222201,
        "prices": {
            PriceTier.PURCHASE.value: Decimal("1000000"),
            PriceTier.A.value: Decimal("1200000"),
            PriceTier.B.value: Decimal("1150000"),
            PriceTier.DEALER.value: Decimal("1300000"),
            PriceTier.MEDICAL.value: Decimal("1500000") # 치료재료단가 (보험수가로 사용될 수 있음)
        }
    }
    item1 = Item(**item_data_1)

    item_data_2 = {
        "lot": "LOT002", "model_name": "MODEL-Y2", "product_name": "고정 플레이트",
        "spec": "Titanium, 5H", "treatment_code": "C7654321", "udi_di": 8801111222202,
        "prices": {
            PriceTier.PURCHASE.value: Decimal("50000"),
            PriceTier.A.value: Decimal("60000"),
            PriceTier.B.value: Decimal("58000"),
            PriceTier.DEALER.value: Decimal("65000"),
            # PriceTier.MEDICAL.value: Decimal("70000") # 이 항목은 치료재료단가가 없을 수 있음
        }
    }
    item2 = Item(**item_data_2)

    print(item1)
    print(f"  A단가: {item1.get_price_for_tier(PriceTier.A)}")
    print(f"  보험수가 (치료재료단가): {item1.prices.get(PriceTier.MEDICAL.value)}")
    print(item2)
    print(f"  A단가: {item2.get_price_for_tier(PriceTier.A)}")
    print(f"  보험수가 (치료재료단가): {item2.prices.get(PriceTier.MEDICAL.value)}") # None이 될 수 있음
    print("-" * 20)

    # InvoiceLine 테스트
    # 회사1 (A단가 적용)에 대한 명세서 라인
    price_for_item1_company1 = item1.get_price_for_tier(company1.price_tier)
    if price_for_item1_company1 is None:
        raise ValueError(f"{item1.product_name}에 대해 {company1.price_tier} 단가 정보가 없습니다.")

    invoice_line1 = InvoiceLine(item=item1, qty=2, unit_price=price_for_item1_company1)
    print(f"명세라인1: {invoice_line1.product_name}, 수량: {invoice_line1.qty}, 단가: {invoice_line1.unit_price:,.0f}, "
          f"공급가액: {invoice_line1.supply_amount:,.0f}, 부가세: {invoice_line1.vat:,.0f}, "
          f"보험수가: {invoice_line1.insurance_price if invoice_line1.insurance_price else 'N/A'}")

    # 회사2 (일반대리점가 적용)에 대한 명세서 라인
    price_for_item2_company2 = item2.get_price_for_tier(company2.price_tier)
    if price_for_item2_company2 is None:
        # 이 경우, 단가 정책을 결정해야 함 (예: 기본 단가 사용 또는 오류)
        # 여기서는 간단히 0으로 처리하거나, 해당 품목을 추가할 수 없도록 처리
        print(f"경고: {item2.product_name}에 대해 {company2.price_tier} 단가 정보가 없습니다. 해당 품목은 추가할 수 없습니다.")
        # 실제 애플리케이션에서는 이 품목을 명세서에 추가하지 못하게 하거나, 사용자에게 알림
    else:
        invoice_line2 = InvoiceLine(item=item2, qty=10, unit_price=price_for_item2_company2)
        print(f"명세라인2: {invoice_line2.product_name}, 수량: {invoice_line2.qty}, 단가: {invoice_line2.unit_price:,.0f}, "
              f"공급가액: {invoice_line2.supply_amount:,.0f}, 부가세: {invoice_line2.vat:,.0f}, "
              f"보험수가: {invoice_line2.insurance_price if invoice_line2.insurance_price else 'N/A'}")

    # VAT 계산 테스트 (공급가액이 소수점을 발생시키는 경우)
    # 예: 단가 12345, 수량 1 -> 공급가액 12345, VAT 1234.5 -> 1235
    # 예: 단가 123.4, 수량 10 -> unit_price는 Decimal('123.4')로 저장됨
    # supply_amount = 1234, vat = 123.4 -> 123
    test_item_vat = Item(
        lot="VAT001", model_name="VAT-Test", product_name="VAT 계산 테스트품", spec="N/A",
        treatment_code="N/A", udi_di=None, # UDI-DI can be None
        prices={PriceTier.A.value: Decimal("123.4")}
    )
    price_for_vat_test = test_item_vat.get_price_for_tier(PriceTier.A)
    assert price_for_vat_test is not None
    
    invoice_line_vat_test1 = InvoiceLine(item=test_item_vat, qty=10, unit_price=price_for_vat_test) # 공급가액 1234
    print(f"VAT 테스트1: 단가 {invoice_line_vat_test1.unit_price}, 공급가액 {invoice_line_vat_test1.supply_amount}, VAT {invoice_line_vat_test1.vat}")
    assert invoice_line_vat_test1.supply_amount == Decimal("1234")
    assert invoice_line_vat_test1.vat == Decimal("123") # 123.4 -> 123 (ROUND_HALF_UP 이지만, 0.5 미만이므로 내림)

    test_item_vat2 = Item(
        lot="VAT002", model_name="VAT-Test2", product_name="VAT 계산 테스트품2", spec="N/A",
        treatment_code="N/A", udi_di=None, # UDI-DI can be None
        prices={PriceTier.A.value: Decimal("123.5")}
    )
    price_for_vat_test2 = test_item_vat2.get_price_for_tier(PriceTier.A)
    assert price_for_vat_test2 is not None
    invoice_line_vat_test2 = InvoiceLine(item=test_item_vat2, qty=10, unit_price=price_for_vat_test2) # 공급가액 1235
    print(f"VAT 테스트2: 단가 {invoice_line_vat_test2.unit_price}, 공급가액 {invoice_line_vat_test2.supply_amount}, VAT {invoice_line_vat_test2.vat}")
    assert invoice_line_vat_test2.supply_amount == Decimal("1235")
    assert invoice_line_vat_test2.vat == Decimal("124") # 123.5 -> 124 (ROUND_HALF_UP)

    test_item_vat3 = Item(
        lot="VAT003", model_name="VAT-Test3", product_name="VAT 계산 테스트품3", spec="N/A",
        treatment_code="N/A", udi_di=None, # UDI-DI can be None
        prices={PriceTier.A.value: Decimal("550")} # 공급가액 550, VAT 55
    )
    price_for_vat_test3 = test_item_vat3.get_price_for_tier(PriceTier.A)
    assert price_for_vat_test3 is not None
    invoice_line_vat_test3 = InvoiceLine(item=test_item_vat3, qty=1, unit_price=price_for_vat_test3)
    print(f"VAT 테스트3: 단가 {invoice_line_vat_test3.unit_price}, 공급가액 {invoice_line_vat_test3.supply_amount}, VAT {invoice_line_vat_test3.vat}")
    assert invoice_line_vat_test3.supply_amount == Decimal("550")
    assert invoice_line_vat_test3.vat == Decimal("55")

    print("\n모델 테스트 완료.")
