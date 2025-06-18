# receipt_ocr.py
import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
import re
import difflib
from decimal import Decimal
from PIL import Image, ImageEnhance
import io
import base64
# receipt_ocr.py 파일 상단에 추가
from config_ocr import OCRConfig

class ReceiptOCRProcessor:
    def __init__(self, product_master_items: List[Item], config_file: str = "ocr_config.json"):
        self.product_master_items = product_master_items
        self.config = OCRConfig(config_file)
        self.easyocr_reader = None
        
        # Tesseract 경로 설정
        tesseract_cmd = self.config.get("tesseract_cmd")
        if tesseract_cmd and PYTESSERACT_AVAILABLE:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        
        # OCR 엔진 초기화
        if EASYOCR_AVAILABLE:
            try:
                gpu_enabled = self.config.get("easyocr_gpu", False)
                self.easyocr_reader = easyocr.Reader(['ko', 'en'], gpu=gpu_enabled)
                print(f"EasyOCR 초기화 완료 (GPU: {gpu_enabled})")
            except Exception as e:
                print(f"EasyOCR 초기화 실패: {e}")
                self.easyocr_reader = None
        
        self._build_product_search_index()
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    print("Warning: EasyOCR not available. Install with: pip install easyocr")

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False
    print("Warning: Pytesseract not available. Install with: pip install pytesseract")

from models import Item, InvoiceLine
from difflib import SequenceMatcher

class ReceiptOCRProcessor:
    """영수증 이미지에서 텍스트를 추출하고 품목을 매칭하는 클래스"""
    
    def __init__(self, product_master_items: List[Item]):
        self.product_master_items = product_master_items
        self.easyocr_reader = None
        
        # OCR 엔진 초기화
        if EASYOCR_AVAILABLE:
            try:
                # 한국어와 영어 지원
                self.easyocr_reader = easyocr.Reader(['ko', 'en'], gpu=False)
                print("EasyOCR 초기화 완료 (한국어, 영어)")
            except Exception as e:
                print(f"EasyOCR 초기화 실패: {e}")
                self.easyocr_reader = None
        
        # 제품 검색을 위한 인덱스 생성
        self._build_product_search_index()
    
    def _build_product_search_index(self):
        """제품 검색을 위한 인덱스 구축"""
        self.product_search_terms = {}
        
        for item in self.product_master_items:
            # 검색 키워드들 생성
            search_terms = [
                item.product_name,
                item.model_name,
                item.spec,
                f"{item.product_name} {item.model_name}",
                f"{item.model_name} {item.spec}"
            ]
            
            # 공백과 특수문자 제거한 버전도 추가
            for term in search_terms.copy():
                clean_term = re.sub(r'[^\w가-힣]', '', term)
                if clean_term and clean_term not in search_terms:
                    search_terms.append(clean_term)
            
            # 각 검색어를 키로 하여 아이템 매핑
            for term in search_terms:
                if term.strip():
                    term_lower = term.lower().strip()
                    if term_lower not in self.product_search_terms:
                        self.product_search_terms[term_lower] = []
                    self.product_search_terms[term_lower].append(item)
    
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """이미지 전처리 (OCR 정확도 향상을 위해)"""
        # PIL Image로 변환하여 향상 적용
        if len(image.shape) == 3:
            pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        else:
            pil_image = Image.fromarray(image)
        
        # 대비 향상
        enhancer = ImageEnhance.Contrast(pil_image)
        pil_image = enhancer.enhance(1.5)
        
        # 선명도 향상
        enhancer = ImageEnhance.Sharpness(pil_image)
        pil_image = enhancer.enhance(1.2)
        
        # 다시 OpenCV 형태로 변환
        if pil_image.mode == 'RGB':
            image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        else:
            image = np.array(pil_image)
        
        # 그레이스케일 변환
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # 노이즈 제거
        denoised = cv2.medianBlur(gray, 3)
        
        # 적응적 이진화
        binary = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # 모폴로지 연산으로 텍스트 개선
        kernel = np.ones((1, 1), np.uint8)
        processed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        return processed
    
    def extract_text_easyocr(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """EasyOCR을 사용한 텍스트 추출"""
        if not self.easyocr_reader:
            return []
        
        try:
            results = self.easyocr_reader.readtext(image)
            extracted_data = []
            
            for bbox, text, confidence in results:
                if confidence > 0.3:  # 신뢰도 임계값
                    # bbox는 4개의 좌표 점
                    x_coords = [point[0] for point in bbox]
                    y_coords = [point[1] for point in bbox]
                    
                    extracted_data.append({
                        'text': text.strip(),
                        'confidence': confidence,
                        'bbox': {
                            'x': min(x_coords),
                            'y': min(y_coords),
                            'width': max(x_coords) - min(x_coords),
                            'height': max(y_coords) - min(y_coords)
                        }
                    })
            
            return extracted_data
        except Exception as e:
            print(f"EasyOCR 텍스트 추출 실패: {e}")
            return []
    
    def extract_text_tesseract(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Tesseract를 사용한 텍스트 추출"""
        if not PYTESSERACT_AVAILABLE:
            return []
        
        try:
            # Tesseract 설정 (한국어 지원)
            config = '--psm 6 -l kor+eng'
            
            # 텍스트와 좌표 정보 추출
            data = pytesseract.image_to_data(image, config=config, output_type=pytesseract.Output.DICT)
            
            extracted_data = []
            n_boxes = len(data['text'])
            
            for i in range(n_boxes):
                text = data['text'][i].strip()
                confidence = float(data['conf'][i])
                
                if text and confidence > 30:  # 신뢰도 임계값
                    extracted_data.append({
                        'text': text,
                        'confidence': confidence / 100.0,  # 0-1 범위로 정규화
                        'bbox': {
                            'x': data['left'][i],
                            'y': data['top'][i],
                            'width': data['width'][i],
                            'height': data['height'][i]
                        }
                    })
            
            return extracted_data
        except Exception as e:
            print(f"Tesseract 텍스트 추출 실패: {e}")
            return []
    
    def extract_all_text(self, image_path: str) -> List[Dict[str, Any]]:
        """모든 사용 가능한 OCR 엔진으로 텍스트 추출"""
        # 이미지 로드
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"이미지를 로드할 수 없습니다: {image_path}")
        
        # 이미지 전처리
        processed_image = self.preprocess_image(image)
        
        all_results = []
        
        # EasyOCR 결과
        easyocr_results = self.extract_text_easyocr(processed_image)
        for result in easyocr_results:
            result['engine'] = 'easyocr'
            all_results.append(result)
        
        # Tesseract 결과
        tesseract_results = self.extract_text_tesseract(processed_image)
        for result in tesseract_results:
            result['engine'] = 'tesseract'
            all_results.append(result)
        
        # 결과를 신뢰도 순으로 정렬
        all_results.sort(key=lambda x: x['confidence'], reverse=True)
        
        return all_results
    
    def parse_receipt_items(self, ocr_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """OCR 결과에서 품목명과 수량 추출"""
        parsed_items = []
        
        # 텍스트를 y좌표 순으로 정렬 (위에서 아래로)
        sorted_results = sorted(ocr_results, key=lambda x: x['bbox']['y'])
        
        for i, result in enumerate(sorted_results):
            text = result['text']
            
            # 수량 패턴 매칭 (숫자만 있는 경우, "수량: 3", "3개", "x3" 등)
            quantity_patterns = [
                r'(\d+)개',
                r'(\d+)EA',
                r'수량[\s:]*(\d+)',
                r'x\s*(\d+)',
                r'X\s*(\d+)',
                r'^\s*(\d+)\s*$'  # 숫자만 있는 경우
            ]
            
            quantity = None
            for pattern in quantity_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        quantity = int(match.group(1))
                        break
                    except ValueError:
                        continue
            
            # 품목명으로 추정되는 텍스트 (수량이 아니고 충분히 긴 텍스트)
            if not quantity and len(text) > 2 and not text.isdigit():
                # 인근의 텍스트에서 수량 찾기
                nearby_quantity = self._find_nearby_quantity(result, sorted_results)
                
                parsed_items.append({
                    'text': text,
                    'quantity': nearby_quantity or 1,  # 기본값 1
                    'confidence': result['confidence'],
                    'bbox': result['bbox']
                })
        
        return parsed_items
    
    def _find_nearby_quantity(self, item_result: Dict[str, Any], all_results: List[Dict[str, Any]]) -> Optional[int]:
        """주어진 아이템 근처에서 수량 찾기"""
        item_bbox = item_result['bbox']
        item_center_y = item_bbox['y'] + item_bbox['height'] / 2
        
        # 같은 줄이나 인근 줄에서 수량 찾기
        for result in all_results:
            if result == item_result:
                continue
            
            other_bbox = result['bbox']
            other_center_y = other_bbox['y'] + other_bbox['height'] / 2
            
            # Y 좌표 차이가 작은 경우 (같은 줄 또는 인근)
            if abs(item_center_y - other_center_y) < 50:
                text = result['text']
                
                # 수량 패턴 확인
                quantity_patterns = [
                    r'(\d+)개',
                    r'(\d+)EA',
                    r'x\s*(\d+)',
                    r'X\s*(\d+)',
                    r'^\s*(\d+)\s*$'
                ]
                
                for pattern in quantity_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        try:
                            return int(match.group(1))
                        except ValueError:
                            continue
        
        return None
    
    def match_products(self, parsed_items: List[Dict[str, Any]]) -> List[Tuple[Item, int, float]]:
        """추출된 품목명을 제품 마스터와 매칭"""
        matched_products = []
        
        for parsed_item in parsed_items:
            item_text = parsed_item['text']
            quantity = parsed_item['quantity']
            confidence = parsed_item['confidence']
            
            # 제품 매칭 시도
            best_match = self._find_best_product_match(item_text)
            
            if best_match:
                item, similarity = best_match
                # 전체 신뢰도 = OCR 신뢰도 × 매칭 유사도
                total_confidence = confidence * similarity
                matched_products.append((item, quantity, total_confidence))
        
        return matched_products
    
    def _find_best_product_match(self, text: str) -> Optional[Tuple[Item, float]]:
        """텍스트와 가장 유사한 제품 찾기"""
        text_clean = re.sub(r'[^\w가-힣]', '', text.lower())
        best_match = None
        best_similarity = 0.0
        
        # 정확한 매칭 시도
        if text_clean in self.product_search_terms:
            items = self.product_search_terms[text_clean]
            if items:
                return items[0], 1.0
        
        # 유사도 기반 매칭
        for search_term, items in self.product_search_terms.items():
            # 텍스트가 검색어에 포함되거나 그 반대인 경우
            if text_clean in search_term or search_term in text_clean:
                similarity = max(
                    len(text_clean) / len(search_term) if search_term else 0,
                    len(search_term) / len(text_clean) if text_clean else 0
                )
                if similarity > best_similarity and similarity > 0.6:
                    best_similarity = similarity
                    best_match = (items[0], similarity)
            
            # SequenceMatcher를 이용한 유사도 계산
            similarity = SequenceMatcher(None, text_clean, search_term).ratio()
            if similarity > best_similarity and similarity > 0.7:
                best_similarity = similarity
                best_match = (items[0], similarity)
        
        return best_match
    
    def process_receipt_image(self, image_path: str) -> Tuple[List[Tuple[Item, int, float]], List[Dict[str, Any]]]:
        """영수증 이미지를 처리하여 매칭된 제품 목록 반환"""
        try:
            # 1. OCR로 텍스트 추출
            print(f"영수증 이미지 처리 시작: {image_path}")
            ocr_results = self.extract_all_text(image_path)
            print(f"OCR 결과: {len(ocr_results)}개 텍스트 추출됨")
            
            # 2. 품목과 수량 파싱
            parsed_items = self.parse_receipt_items(ocr_results)
            print(f"파싱된 품목: {len(parsed_items)}개")
            
            # 3. 제품 마스터와 매칭
            matched_products = self.match_products(parsed_items)
            print(f"매칭된 제품: {len(matched_products)}개")
            
            return matched_products, ocr_results
            
        except Exception as e:
            print(f"영수증 처리 중 오류 발생: {e}")
            return [], []

# 사용 예제 및 테스트
if __name__ == "__main__":
    # 테스트용 더미 데이터
    from models import Item, PriceTier
    from decimal import Decimal
    
    test_items = [
        Item(
            lot="LOT001",
            model_name="스크류-A1",
            product_name="티타늄 스크류",
            spec="3.5mm",
            treatment_code="C001",
            udi_di=123456789,
            prices={PriceTier.A.value: Decimal("150000")}
        ),
        Item(
            lot="LOT002",
            model_name="플레이트-B2",
            product_name="정형외과 플레이트",
            spec="5홀",
            treatment_code="C002",
            udi_di=987654321,
            prices={PriceTier.A.value: Decimal("320000")}
        )
    ]
    
    processor = ReceiptOCRProcessor(test_items)
    
    # 가상의 OCR 결과로 테스트
    mock_ocr_results = [
        {
            'text': '티타늄 스크류',
            'confidence': 0.9,
            'bbox': {'x': 10, 'y': 50, 'width': 100, 'height': 20}
        },
        {
            'text': '3',
            'confidence': 0.85,
            'bbox': {'x': 120, 'y': 50, 'width': 20, 'height': 20}
        },
        {
            'text': '플레이트',
            'confidence': 0.8,
            'bbox': {'x': 10, 'y': 80, 'width': 80, 'height': 20}
        },
        {
            'text': '2개',
            'confidence': 0.9,
            'bbox': {'x': 100, 'y': 80, 'width': 30, 'height': 20}
        }
    ]
    
    parsed_items = processor.parse_receipt_items(mock_ocr_results)
    matched_products = processor.match_products(parsed_items)
    
    print("매칭 결과:")
    for item, quantity, confidence in matched_products:
        print(f"- {item.product_name} ({item.model_name}): 수량 {quantity}, 신뢰도 {confidence:.2f}")