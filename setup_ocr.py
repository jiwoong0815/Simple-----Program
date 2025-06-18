# setup_ocr.py - OCR 환경 설정 스크립트
import os
import sys
import subprocess
import platform
from pathlib import Path

class OCRSetup:
    """OCR 환경 설정을 위한 헬퍼 클래스"""
    
    @staticmethod
    def install_packages():
        """필요한 Python 패키지 설치"""
        packages = [
            "easyocr>=1.7.0",
            "opencv-python>=4.8.0", 
            "Pillow>=10.0.0",
            "pytesseract>=0.3.10"
        ]
        
        print("OCR 관련 패키지를 설치합니다...")
        for package in packages:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                print(f"✓ {package} 설치 완료")
            except subprocess.CalledProcessError as e:
                print(f"✗ {package} 설치 실패: {e}")
                return False
        return True
    
    @staticmethod
    def check_tesseract():
        """Tesseract OCR 설치 확인"""
        try:
            import pytesseract
            # Tesseract 실행 테스트
            version = pytesseract.get_tesseract_version()
            print(f"✓ Tesseract OCR 발견됨: v{version}")
            return True
        except Exception as e:
            print(f"✗ Tesseract OCR 설치 필요: {e}")
            OCRSetup.print_tesseract_install_guide()
            return False
    
    @staticmethod
    def print_tesseract_install_guide():
        """Tesseract 설치 가이드 출력"""
        system = platform.system()
        
        if system == "Windows":
            print("\n=== Windows Tesseract 설치 가이드 ===")
            print("1. https://github.com/UB-Mannheim/tesseract/wiki 방문")
            print("2. Windows installer 다운로드")
            print("3. 설치 시 'Additional language data' 에서 Korean 선택")
            print("4. 환경변수 PATH에 설치 경로 추가 (예: C:\\Program Files\\Tesseract-OCR)")
            print("5. 또는 코드에서 pytesseract.pytesseract.tesseract_cmd 설정")
            
        elif system == "Darwin":  # macOS
            print("\n=== macOS Tesseract 설치 가이드 ===")
            print("1. Homebrew 설치: /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
            print("2. Tesseract 설치: brew install tesseract")
            print("3. 한국어 언어팩: brew install tesseract-lang")
            
        elif system == "Linux":
            print("\n=== Linux Tesseract 설치 가이드 ===")
            print("Ubuntu/Debian:")
            print("  sudo apt-get update")
            print("  sudo apt-get install tesseract-ocr tesseract-ocr-kor")
            print("\nCentOS/RHEL:")
            print("  sudo yum install tesseract tesseract-langpack-kor")
    
    @staticmethod
    def test_ocr():
        """OCR 기능 테스트"""
        try:
            import cv2
            import numpy as np
            from PIL import Image, ImageDraw, ImageFont
            import easyocr
            
            print("\nOCR 기능 테스트 중...")
            
            # 테스트 이미지 생성
            img = Image.new('RGB', (300, 100), color='white')
            draw = ImageDraw.Draw(img)
            
            # 한글 텍스트 추가 (기본 폰트 사용)
            test_text = "티타늄 스크류 3개"
            draw.text((10, 30), test_text, fill='black')
            
            # numpy 배열로 변환
            img_array = np.array(img)
            
            # EasyOCR 테스트
            reader = easyocr.Reader(['ko', 'en'], gpu=False)
            results = reader.readtext(img_array)
            
            if results:
                detected_text = results[0][1] if results else ""
                print(f"✓ EasyOCR 테스트 성공: '{detected_text}'")
                return True
            else:
                print("✗ EasyOCR 테스트 실패: 텍스트를 인식하지 못함")
                return False
                
        except Exception as e:
            print(f"✗ OCR 테스트 실패: {e}")
            return False
    
    @staticmethod
    def setup_all():
        """전체 OCR 환경 설정"""
        print("=== OCR 환경 설정 시작 ===\n")
        
        # 1. 패키지 설치
        if not OCRSetup.install_packages():
            print("패키지 설치 실패. 수동으로 설치해주세요.")
            return False
        
        print("\n" + "="*50)
        
        # 2. Tesseract 확인
        tesseract_ok = OCRSetup.check_tesseract()
        
        print("\n" + "="*50)
        
        # 3. OCR 테스트 (Tesseract가 있는 경우만)
        if tesseract_ok:
            test_ok = OCRSetup.test_ocr()
            if test_ok:
                print("\n✓ OCR 환경 설정 완료!")
                print("이제 '영수증 업로드' 기능을 사용할 수 있습니다.")
                return True
        
        print("\n⚠ OCR 환경 설정이 완전하지 않습니다.")
        print("Tesseract OCR을 설치한 후 다시 테스트해주세요.")
        return False