"""
PDF Reader Helper Module
키움증권 API 문서 등 PDF 파일을 읽어서 텍스트로 추출하는 유틸리티
"""

import PyPDF2
from pathlib import Path
from typing import Optional, Dict


def extract_text_from_pdf(
    pdf_path: str,
    start_page: Optional[int] = None,
    end_page: Optional[int] = None
) -> str:
    """
    PDF 파일에서 텍스트를 추출합니다.

    Args:
        pdf_path: PDF 파일 경로
        start_page: 시작 페이지 (0-based index, None이면 처음부터)
        end_page: 종료 페이지 (0-based index, None이면 끝까지)

    Returns:
        추출된 텍스트 문자열
    """
    pdf_file = Path(pdf_path)

    if not pdf_file.exists():
        raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")

    extracted_text = []

    try:
        with open(pdf_file, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            total_pages = len(pdf_reader.pages)

            start = start_page if start_page is not None else 0
            end = end_page if end_page is not None else total_pages

            start = max(0, min(start, total_pages - 1))
            end = max(start + 1, min(end, total_pages))

            print(f"PDF: {pdf_file.name}, 전체: {total_pages}페이지, 추출: {start + 1}~{end}페이지")

            for page_num in range(start, end):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                extracted_text.append(f"\n--- Page {page_num + 1} ---\n{text}")

            return ''.join(extracted_text)

    except Exception as e:
        raise Exception(f"PDF 읽기 오류: {str(e)}")


def extract_pdf_info(pdf_path: str) -> Dict:
    """PDF 파일의 메타데이터 정보를 추출합니다."""
    pdf_file = Path(pdf_path)

    if not pdf_file.exists():
        raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")

    try:
        with open(pdf_file, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            return {
                'file_name': pdf_file.name,
                'total_pages': len(pdf_reader.pages),
                'metadata': pdf_reader.metadata if pdf_reader.metadata else {}
            }
    except Exception as e:
        raise Exception(f"PDF 정보 읽기 오류: {str(e)}")


def save_pdf_text_to_file(
    pdf_path: str,
    output_path: str,
    start_page: Optional[int] = None,
    end_page: Optional[int] = None
) -> None:
    """PDF 텍스트를 추출하여 텍스트 파일로 저장합니다."""
    text = extract_text_from_pdf(pdf_path, start_page, end_page)

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(text)

    print(f"텍스트 파일 저장: {output_path}")
