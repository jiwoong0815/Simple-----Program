# config_ocr.py - OCR 설정 관리
import json
import os
from typing import Dict, Any, Optional

class OCRConfig:
    """OCR 설정 관리 클래스"""
    
    DEFAULT_CONFIG = {
        "tesseract_cmd": "",  # Tesseract 실행 파일 경로 (Windows에서 필요할 수 있음)
        "easyocr_gpu": False,  # GPU 사용 여부
        "confidence_threshold": 0.3,  # 최소 신뢰도
        "similarity_threshold": 0.7,  # 제품 매칭 최소 유사도
        "auto_select_threshold": 0.8,  # 자동 선택 신뢰도 임계값
        "image_preprocessing": {
            "contrast_enhance": 1.5,
            "sharpness_enhance": 1.2,
            "median_blur_kernel": 3,
            "adaptive_threshold_block_size": 11,
            "adaptive_threshold_c": 2
        }
    }
    
    def __init__(self, config_file: str = "ocr_config.json"):
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """설정 파일 로드"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                # 기본 설정과 병합
                config = self.DEFAULT_CONFIG.copy()
                config.update(loaded_config)
                return config
            except Exception as e:
                print(f"설정 파일 로드 실패: {e}. 기본 설정을 사용합니다.")
        
        return self.DEFAULT_CONFIG.copy()
    
    def save_config(self):
        """설정 파일 저장"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"설정 파일 저장 실패: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """설정값 가져오기"""
        keys = key.split('.')
        value = self.config
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any):
        """설정값 설정"""
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
    
    def configure_tesseract(self, tesseract_path: Optional[str] = None):
        """Tesseract 경로 설정"""
        if tesseract_path:
            self.set("tesseract_cmd", tesseract_path)
            self.save_config()
            
            # pytesseract에 경로 설정
            try:
                import pytesseract
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
                print(f"Tesseract 경로 설정됨: {tesseract_path}")
            except ImportError:
                print("pytesseract를 먼저 설치해주세요.")