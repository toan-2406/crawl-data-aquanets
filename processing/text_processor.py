"""
Module xử lý và làm sạch văn bản cho dự án AquaNets
"""

import os
import sys
import json
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
import time
import unicodedata
import uuid

# Thêm thư mục gốc vào đường dẫn import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import (
    PROCESSED_DATA_DIR,
    RAW_DATA_DIR,
    TEXT_PROCESSING_CONFIG,
    detect_language
)

# Thiết lập logging
logger = logging.getLogger(__name__)


class TextProcessor:
    """
    Lớp xử lý văn bản từ nhiều nguồn khác nhau.
    Hỗ trợ:
    - Làm sạch và chuẩn hóa văn bản
    - Phát hiện ngôn ngữ
    - Phân đoạn văn bản
    - Trích xuất thông tin
    - Lưu văn bản đã xử lý
    """
    
    def __init__(self):
        """Khởi tạo bộ xử lý văn bản"""
        # Thư mục lưu trữ
        self.output_dir = PROCESSED_DATA_DIR
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Cấu hình
        self.chunk_size = TEXT_PROCESSING_CONFIG.get("chunk_size", 500)
        self.chunk_overlap = TEXT_PROCESSING_CONFIG.get("chunk_overlap", 100)
        
        # Từ điển thay thế
        self.replacement_dict = {
            # Các ký tự đặc biệt
            '\u200b': '',           # Zero-width space
            '\xa0': ' ',            # Non-breaking space
            '\t': ' ',              # Tab
            '\n\n+': '\n\n',        # Nhiều dòng trống
            r'\.{2,}': '.',         # Nhiều dấu chấm (sửa escape sequence)
            '…': '...',             # Dấu ba chấm liền
            
            # Các mẫu cần chuẩn hóa
            r'(\d+),(\d+)': r'\1.\2',  # Đổi dấu phẩy trong số thành dấu chấm
            r'\s+': ' ',              # Nhiều khoảng trắng thành một
        }
        
        # Mẫu regex cho việc phát hiện và xử lý đoạn văn
        self.paragraph_patterns = {
            # Mẫu phát hiện đoạn văn mới
            'paragraph_break': re.compile(r'\n\s*\n'),
            
            # Mẫu phát hiện tiêu đề
            'heading': re.compile(r'^#+\s+(.+)$|^(.+)\n[=\-]{2,}$', re.MULTILINE),
            
            # Mẫu phát hiện danh sách
            'list_item': re.compile(r'^\s*[-*+]\s+(.+)$|^\s*\d+\.\s+(.+)$', re.MULTILINE),
        }
        
        logger.info("Đã khởi tạo TextProcessor")
    
    def clean_text(self, text: str) -> str:
        """
        Làm sạch và chuẩn hóa văn bản
        
        Args:
            text: Văn bản cần làm sạch
            
        Returns:
            Văn bản đã làm sạch
        """
        if not text:
            return ""
            
        # Chuẩn hóa Unicode
        text = unicodedata.normalize('NFC', text)
        
        # Áp dụng các mẫu thay thế
        for pattern, replacement in self.replacement_dict.items():
            text = re.sub(pattern, replacement, text)
            
        # Xóa khoảng trắng đầu và cuối dòng
        text = text.strip()
        
        # Xóa các dòng trống liên tiếp
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text
    
    def extract_paragraphs(self, text: str) -> List[str]:
        """
        Trích xuất các đoạn văn từ văn bản
        
        Args:
            text: Văn bản đầu vào
            
        Returns:
            Danh sách các đoạn văn
        """
        if not text:
            return []
            
        # Phân tách theo mẫu đoạn văn
        paragraphs = self.paragraph_patterns['paragraph_break'].split(text)
        
        # Loại bỏ các đoạn trống
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        return paragraphs
    
    def chunk_text(self, text: str, chunk_size: Optional[int] = None, 
                  chunk_overlap: Optional[int] = None) -> List[str]:
        """
        Phân đoạn văn bản thành các chunk nhỏ hơn
        
        Args:
            text: Văn bản cần phân đoạn
            chunk_size: Kích thước tối đa của chunk (đơn vị: ký tự)
            chunk_overlap: Kích thước phần chồng lấp giữa các chunk
            
        Returns:
            Danh sách các chunk
        """
        if not text:
            return []
            
        # Sử dụng giá trị mặc định nếu không được chỉ định
        chunk_size = chunk_size or self.chunk_size
        chunk_overlap = chunk_overlap or self.chunk_overlap
        
        # Trích xuất đoạn văn
        paragraphs = self.extract_paragraphs(text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for paragraph in paragraphs:
            # Nếu đoạn văn dài hơn chunk_size, cắt thành nhiều phần
            if len(paragraph) > chunk_size:
                # Nếu current_chunk không trống, thêm vào chunks
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_length = 0
                
                # Phân đoạn văn dài thành nhiều chunk
                words = paragraph.split(' ')
                temp_chunk = []
                temp_length = 0
                
                for word in words:
                    if temp_length + len(word) + 1 <= chunk_size:
                        temp_chunk.append(word)
                        temp_length += len(word) + 1
                    else:
                        chunks.append(' '.join(temp_chunk))
                        
                        # Lấy phần chồng lấp từ chunk trước
                        overlap_words = temp_chunk[-min(len(temp_chunk), chunk_overlap//10):]
                        temp_chunk = overlap_words + [word]
                        temp_length = sum(len(w) + 1 for w in temp_chunk)
                
                # Thêm phần còn lại
                if temp_chunk:
                    chunks.append(' '.join(temp_chunk))
                
            elif current_length + len(paragraph) + 2 <= chunk_size:
                # Nếu đoạn văn có thể thêm vào chunk hiện tại
                current_chunk.append(paragraph)
                current_length += len(paragraph) + 2  # +2 cho '\n\n'
            else:
                # Nếu đoạn văn không thể thêm vào chunk hiện tại
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [paragraph]
                current_length = len(paragraph)
        
        # Thêm chunk cuối cùng nếu còn
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks
    
    def process_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Xử lý một tài liệu từ dữ liệu thô
        
        Args:
            document: Tài liệu thô (từ crawler)
            
        Returns:
            Tài liệu đã xử lý
        """
        if not document:
            logger.warning("Không thể xử lý tài liệu trống")
            return {}
            
        # Tạo bản sao để tránh thay đổi dữ liệu gốc
        processed_doc = document.copy()
        
        # Thêm ID nếu chưa có
        if "id" not in processed_doc:
            processed_doc["id"] = str(uuid.uuid4())
            
        # Phát hiện ngôn ngữ nếu chưa có
        if "language" not in processed_doc:
            content = processed_doc.get("content", processed_doc.get("title", ""))
            processed_doc["language"] = detect_language(content)
            
        # Làm sạch tiêu đề
        if "title" in processed_doc:
            processed_doc["title"] = self.clean_text(processed_doc["title"])
            
        # Làm sạch tóm tắt
        if "summary" in processed_doc and processed_doc["summary"]:
            processed_doc["summary"] = self.clean_text(processed_doc["summary"])
            
        # Làm sạch nội dung
        if "content" in processed_doc and processed_doc["content"]:
            processed_doc["content"] = self.clean_text(processed_doc["content"])
            
            # Phân đoạn nội dung
            chunks = self.chunk_text(processed_doc["content"])
            processed_doc["chunks"] = chunks
            
            # Tạo metadata cho mỗi chunk
            chunk_metadata = []
            for i, chunk in enumerate(chunks):
                # Tạo ID cho chunk
                chunk_id = f"{processed_doc['id']}_chunk_{i}"
                
                # Phát hiện ngôn ngữ cho chunk
                chunk_language = detect_language(chunk)
                
                # Tạo metadata
                metadata = {
                    "chunk_id": chunk_id,
                    "index": i,
                    "text": chunk,
                    "language": chunk_language,
                    "length": len(chunk),
                    "source_id": processed_doc["id"],
                    "source_title": processed_doc.get("title", ""),
                    "source_url": processed_doc.get("url", ""),
                }
                
                chunk_metadata.append(metadata)
            
            processed_doc["chunk_metadata"] = chunk_metadata
            
        # Trích xuất các thực thể (nếu cần)
        # processed_doc["entities"] = self.extract_entities(processed_doc.get("content", ""))
            
        # Thêm thời gian xử lý
        processed_doc["processed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        return processed_doc
    
    def process_and_save(self, document: Dict[str, Any]) -> Optional[str]:
        """
        Xử lý một tài liệu và lưu vào thư mục đã xử lý
        
        Args:
            document: Tài liệu thô (từ crawler)
            
        Returns:
            Đường dẫn đến file đã lưu hoặc None nếu thất bại
        """
        try:
            # Xử lý tài liệu
            processed_doc = self.process_document(document)
            
            if not processed_doc:
                return None
                
            # Tạo tên file
            doc_id = processed_doc.get("id", str(uuid.uuid4()))
            source = processed_doc.get("source", "").replace("/", "-")
            
            if source:
                filename = f"{source}_{doc_id}.json"
            else:
                filename = f"{doc_id}.json"
                
            # Lưu file
            filepath = os.path.join(self.output_dir, filename)
            
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(processed_doc, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Đã xử lý và lưu tài liệu vào {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Lỗi khi xử lý và lưu tài liệu: {str(e)}")
            return None
    
    def process_all_from_directory(self, source_dir: Optional[str] = None,
                               limit: Optional[int] = None) -> List[str]:
        """
        Xử lý tất cả tài liệu trong thư mục
        
        Args:
            source_dir: Thư mục chứa dữ liệu thô (mặc định: RAW_DATA_DIR)
            limit: Giới hạn số lượng tài liệu cần xử lý
            
        Returns:
            Danh sách đường dẫn đến các file đã xử lý
        """
        source_dir = source_dir or RAW_DATA_DIR
        processed_files = []
        
        try:
            # Lấy danh sách file JSON trong thư mục nguồn
            json_files = [f for f in os.listdir(source_dir) if f.endswith('.json')]
            logger.info(f"Tìm thấy {len(json_files)} file JSON trong {source_dir}")
            
            # Giới hạn số lượng file nếu cần
            if limit and limit > 0:
                json_files = json_files[:limit]
                
            # Xử lý từng file
            for i, filename in enumerate(json_files):
                try:
                    # Đọc tài liệu
                    filepath = os.path.join(source_dir, filename)
                    with open(filepath, "r", encoding="utf-8") as f:
                        document = json.load(f)
                        
                    # Xử lý và lưu
                    processed_file = self.process_and_save(document)
                    
                    if processed_file:
                        processed_files.append(processed_file)
                        
                    logger.info(f"Đã xử lý {i+1}/{len(json_files)} tài liệu")
                    
                except Exception as e:
                    logger.error(f"Lỗi khi xử lý file {filename}: {str(e)}")
                    continue
                    
            logger.info(f"Hoàn thành xử lý {len(processed_files)}/{len(json_files)} tài liệu")
            return processed_files
            
        except Exception as e:
            logger.error(f"Lỗi khi xử lý từ thư mục {source_dir}: {str(e)}")
            return processed_files
            
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Trích xuất các thực thể từ văn bản (yêu cầu thư viện NLP)
        
        Args:
            text: Văn bản cần trích xuất
            
        Returns:
            Dict các loại thực thể và giá trị
        """
        # Đây là triển khai đơn giản sử dụng regex pattern
        # Một triển khai thực tế nên sử dụng thư viện NLP như spaCy
        
        entities = {
            "species": [],       # Các loài tôm
            "diseases": [],      # Bệnh tôm
            "chemicals": [],     # Hóa chất, thuốc
            "parameters": [],    # Thông số kỹ thuật (nhiệt độ, pH,...)
            "locations": [],     # Địa điểm
            "techniques": [],    # Kỹ thuật nuôi
        }
        
        # Mẫu regex cho từng loại thực thể
        patterns = {
            "species": [
                r"tôm\s+(sú|thẻ|càng\s+xanh|hùm|he|chân\s+trắng)",
                r"penaeus\s+monodon",
                r"litopenaeus\s+vannamei",
                r"macrobrachium\s+rosenbergii"
            ],
            "diseases": [
                r"(bệnh|hội\s+chứng)\s+(đốm\s+trắng|đầu\s+vàng|hoại\s+tử\s+gan\s+tụy|EMS|WSSV|đỏ\s+thân|phân\s+trắng|mềm\s+vỏ|đen\s+mang)",
                r"(white\s+spot|early\s+mortality|hepatopancreatic\s+necrosis)\s+syndrome",
                r"vibrio(\s+\w+)?"
            ],
            "chemicals": [
                r"(chlorine|iodine|formalin|CuSO4|BKC)",
                r"(vôi|thuốc\s+tím|xanh\s+methylene)",
                r"kháng\s+sinh(\s+\w+)?"
            ],
            "parameters": [
                r"(\d+[.,]?\d*)\s*(°C|độ|pH|ppt|mg/l|ppm)",
                r"(nhiệt\s+độ|pH|độ\s+mặn|oxy|DO|NH3|NH4|NO2|NO3|H2S)\s*[:=]?\s*(\d+[.,]?\d*)"
            ],
            "locations": [
                r"(tỉnh|thành\s+phố|huyện|xã)\s+([A-ZÀ-Ỹ][a-zà-ỹ]*\s*)+",
                r"([A-ZÀ-Ỹ][a-zà-ỹ]*\s*)+(tỉnh|thành\s+phố)"
            ],
            "techniques": [
                r"nuôi\s+(thâm\s+canh|bán\s+thâm\s+canh|quảng\s+canh|siêu\s+thâm\s+canh)",
                r"(biofloc|RAS|tuần\s+hoàn|lót\s+bạt)",
                r"(xử\s+lý|cải\s+tạo)\s+(nước|ao|đáy)",
                r"(cho\s+ăn|thức\s+ăn)\s+tôm"
            ]
        }
        
        # Trích xuất thực thể
        for entity_type, regex_patterns in patterns.items():
            for pattern in regex_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                
                # Xử lý kết quả tìm kiếm
                if matches:
                    if isinstance(matches[0], tuple):  # Nếu regex có nhiều nhóm
                        for match_group in matches:
                            # Lấy nhóm đầu tiên không rỗng
                            entity = next((group for group in match_group if group), None)
                            if entity and entity not in entities[entity_type]:
                                entities[entity_type].append(entity)
                    else:  # Nếu regex chỉ có một nhóm
                        for match in matches:
                            if match and match not in entities[entity_type]:
                                entities[entity_type].append(match)
        
        return entities


if __name__ == "__main__":
    # Cấu hình logging khi chạy trực tiếp
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Khởi tạo bộ xử lý văn bản
    processor = TextProcessor()
    
    # Xử lý tất cả tài liệu trong thư mục raw_data
    processed_files = processor.process_all_from_directory(limit=5)  # Giới hạn 5 file khi chạy thử
    
    print(f"Đã xử lý {len(processed_files)} tài liệu")