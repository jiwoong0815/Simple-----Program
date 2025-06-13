import uuid
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass, field
from typing import Optional, Dict

@dataclass
class Company:
    """거래처 회사 정보를 담는 데이터 클래스"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    contact: str = ""  # 전화/이메일 등, 옵션

    def __str__(self):
        return self.name

@dataclass
class Item:
    """품목 정보를 담는 데이터 클래스"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    default_unit_price: Decimal = Decimal("0.00")  # 기본 단가 (VAT 포함, 원 단위)
    company_prices: Dict[str, Decimal] = field(default_factory=dict) # 거래처별 단가: {company_id: price}

    def get_price(self, company_id: Optional[str] = None) -> Decimal:
        """거래처별 단가 또는 기본 단가를 반환합니다."""
        if company_id and company_id in self.company_prices:
            return self.company_prices[company_id]
        return self.default_unit_price

    def set_company_price(self, company_id: str, price: Decimal):
        """거래처별 단가를 설정합니다."""
        self.company_prices[company_id] = price

    def remove_company_price(self, company_id: str):
        """거래처별 단가를 삭제합니다."""
        if company_id in self.company_prices:
            del self.company_prices[company_id]

    def __str__(self):
        price_info = f"기본 단가: {self.default_unit_price.quantize(Decimal('1'), rounding=ROUND_HALF_UP):,}원"
        if self.company_prices:
            price_info += f" (거래처별 단가 {len(self.company_prices)}개 설정됨)"
        return f"{self.name} ({price_info})"

    def get_formatted_price(self, company_id: Optional[str] = None) -> str:
        """지정된 거래처 또는 기본 단가를 '원' 단위 문자열로 포맷하여 반환합니다."""
        price_to_format = self.get_price(company_id)
        return f"{price_to_format.quantize(Decimal('1'), rounding=ROUND_HALF_UP):,}원"

@dataclass
class InvoiceLine:
    """거래명세서의 각 품목 라인을 나타내는 임시 객체"""
    item: Item
    quantity: int
    company_id: Optional[str] = None # 명세서의 거래처 ID, 가격 결정에 사용

    @property
    def item_id(self) -> str:
        return self.item.id

    @property
    def item_name(self) -> str:
        return self.item.name

    @property
    def unit_price(self) -> Decimal:
        """해당 거래처에 맞는 단가를 반환합니다."""
        return self.item.get_price(self.company_id)

    @property
    def line_total(self) -> Decimal:
        return self.unit_price * Decimal(self.quantity)

    def get_formatted_unit_price(self) -> str:
        """단가를 통화 형식 문자열로 반환"""
        return f"{self.unit_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):,.2f}"

    def get_formatted_line_total(self) -> str:
        """금액을 통화 형식 문자열로 반환"""
        return f"{self.line_total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):,.2f}"

if __name__ == '__main__':
    # 테스트용 예시
    company1 = Company(name="테스트 회사 1", contact="02-1234-5678")
    company2 = Company(name="테스트 회사 2", contact="02-9876-5432")

    item1 = Item(name="테스트 품목 A", default_unit_price=Decimal("15000.50"))
    item1.set_company_price(company1.id, Decimal("14000.00")) # 회사1 특별가
    item1.set_company_price(company2.id, Decimal("13500.00")) # 회사2 특별가


    item2 = Item(name="테스트 품목 B", default_unit_price=Decimal("22000"))
    # item2는 회사1에 특별가 없음, 회사2에는 특별가 설정
    item2.set_company_price(company2.id, Decimal("20000.00"))


    print(company1)
    print(company2)
    print("-" * 20)
    print(item1) 
    print(f"  회사1 가격: {item1.get_formatted_price(company1.id)}")
    print(f"  회사2 가격: {item1.get_formatted_price(company2.id)}")
    print(f"  기타 거래처 가격 (기본가): {item1.get_formatted_price()}") 
    print("-" * 20)
    print(item2)
    print(f"  회사1 가격 (기본가): {item2.get_formatted_price(company1.id)}") 
    print(f"  회사2 가격: {item2.get_formatted_price(company2.id)}")
    print("-" * 20)

    # InvoiceLine 테스트
    # 회사1에 대한 명세서 라인
    invoice_line_c1_item1 = InvoiceLine(item=item1, quantity=3, company_id=company1.id)
    print(f"회사1, 품목: {invoice_line_c1_item1.item_name}, 수량: {invoice_line_c1_item1.quantity}, "
          f"단가: {invoice_line_c1_item1.get_formatted_unit_price()}, 금액: {invoice_line_c1_item1.get_formatted_line_total()}")

    # 회사2에 대한 명세서 라인 (item1)
    invoice_line_c2_item1 = InvoiceLine(item=item1, quantity=2, company_id=company2.id)
    print(f"회사2, 품목: {invoice_line_c2_item1.item_name}, 수량: {invoice_line_c2_item1.quantity}, "
          f"단가: {invoice_line_c2_item1.get_formatted_unit_price()}, 금액: {invoice_line_c2_item1.get_formatted_line_total()}")

    # 회사1에 대한 명세서 라인 (item2 - 기본가 적용)
    invoice_line_c1_item2 = InvoiceLine(item=item2, quantity=5, company_id=company1.id)
    print(f"회사1, 품목: {invoice_line_c1_item2.item_name}, 수량: {invoice_line_c1_item2.quantity}, "
          f"단가: {invoice_line_c1_item2.get_formatted_unit_price()}, 금액: {invoice_line_c1_item2.get_formatted_line_total()}")

    # 거래처 지정 없이 (기본가 적용)
    invoice_line_default_item1 = InvoiceLine(item=item1, quantity=1) # company_id=None
    print(f"기본, 품목: {invoice_line_default_item1.item_name}, 수량: {invoice_line_default_item1.quantity}, "
          f"단가: {invoice_line_default_item1.get_formatted_unit_price()}, 금액: {invoice_line_default_item1.get_formatted_line_total()}")
