"""
Cấu hình cho dự án Crawl Data Aquanets
"""

import os
from pathlib import Path
import logging
from typing import Optional

# Đường dẫn cơ bản
BASE_DIR = Path(__file__).parent.parent.absolute()
DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_DATA_DIR = os.path.join(DATA_DIR, "raw")
PROCESSED_DATA_DIR = os.path.join(DATA_DIR, "processed")
EMBEDDINGS_DIR = os.path.join(DATA_DIR, "embeddings")

# Tạo thư mục nếu chưa tồn tại
os.makedirs(RAW_DATA_DIR, exist_ok=True)
os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
os.makedirs(EMBEDDINGS_DIR, exist_ok=True)

# Hàm phát hiện ngôn ngữ
def detect_language(text: str) -> str:
    """
    Phát hiện ngôn ngữ của văn bản
    
    Args:
        text: Văn bản cần phát hiện ngôn ngữ
        
    Returns:
        Mã ngôn ngữ ('vi' hoặc 'en' hoặc 'unknown')
    """
    try:
        from langdetect import detect
        
        # Nếu văn bản quá ngắn, không thể phát hiện chính xác
        if len(text) < 20:
            # Danh sách từ đặc trưng tiếng Việt
            vietnamese_words = [
                "của", "và", "trong", "đến", "với", "các", "được", "có", "là", "để",
                "tôm", "nuôi", "trồng", "thuỷ", "hải", "sản", "bệnh", "con", "giống"
            ]
            text_lower = text.lower()
            vi_count = sum(1 for word in vietnamese_words if word in text_lower)
            return "vi" if vi_count >= 1 else "en"
        
        # Phát hiện ngôn ngữ
        lang = detect(text)
        
        # Ánh xạ mã ngôn ngữ
        if lang == "vi":
            return "vi"
        else:
            return "en"  # Mặc định là tiếng Anh cho các ngôn ngữ khác
            
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Lỗi khi phát hiện ngôn ngữ: {str(e)}")
        return "unknown"

# Cấu hình crawl
CRAWL_SETTINGS = {
    "USER_AGENTS": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
    ],
    "DELAY_BETWEEN_REQUESTS": 2,  # seconds
    "MAX_RETRIES": 3,
    "TIMEOUT": 30,  # seconds
    "HEADERS": {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
    },
    "RESPECT_ROBOTS_TXT": True,
    "PROXY_ROTATION": False,  # Set to True if using proxies
    "PROXIES": [],  # Add proxies if needed
}

# Nguồn dữ liệu
DATA_SOURCES = {
    "official_websites": [
        {"name": "Bộ Nông nghiệp và Phát triển Nông thôn", "url": "https://www.mard.gov.vn", "language": "vi"},
        {"name": "Tổng cục Thủy sản", "url": "https://tcts.gov.vn", "language": "vi"},
        {"name": "Viện Nghiên cứu Nuôi trồng Thủy sản", "url": "http://www.ria1.org", "language": "vi"},
        {"name": "FAO Aquaculture", "url": "https://www.fao.org/fishery/en/aquaculture", "language": "en"},
        {"name": "VASEP", "url": "http://vasep.com.vn", "language": "vi"},
    ],
    "specialized_websites": [
        {"name": "Thủy sản Việt Nam", "url": "https://thuysanvietnam.com.vn", "language": "vi"},
        {"name": "Người nuôi tôm", "url": "https://nguoinuoitom.vn", "language": "vi"},
        {"name": "Thủy sản Online", "url": "https://thuysanonline.vn", "language": "vi"},
        {"name": "Aquaculture Asia Pacific", "url": "https://www.aquaasiapac.com", "language": "en"},
        {"name": "The Fish Site", "url": "https://thefishsite.com", "language": "en"},
    ],
    "forums": [
        {"name": "Facebook Groups", "url": None, "language": "vi"},
        {"name": "Reddit Aquaculture", "url": "https://www.reddit.com/r/aquaculture/", "language": "en"},
    ],
    "academic": [
        {"name": "Google Scholar", "url": "https://scholar.google.com", "language": "en"},
        {"name": "ScienceDirect", "url": "https://www.sciencedirect.com", "language": "en"},
        {"name": "ResearchGate", "url": "https://www.researchgate.net", "language": "en"},
    ]
}

# Cấu hình database
DB_CONFIG = {
    "mongodb": {
        "host": "localhost",
        "port": 27017,
        "db_name": "aquanets",
        "collections": {
            "raw_data": "raw_data",
            "processed_data": "processed_data",
            "metadata": "metadata",
        }
    },
    "postgres": {
        "host": "localhost",
        "port": 5432,
        "db_name": "aquanets",
        "user": "postgres",
        "password": "postgres",
    },
    "vector_db": {
        "type": "milvus",  # milvus, pinecone, qdrant
        "host": "localhost",
        "port": 19530,
        "collection": "aquanets_embeddings",
    }
}

# Cấu hình xử lý văn bản
TEXT_PROCESSING = {
    "chunk_size": 512,
    "chunk_overlap": 50,
    "embedding_model": "paraphrase-multilingual-MiniLM-L12-v2",
    "language_detection": True,
    "enable_translation": True,
    "source_languages": ["vi", "en"],
    "target_language": "vi",
    "languages": ["vi", "en"],
    "translate": False
}

# Đổi tên để sử dụng trong các module xử lý
TEXT_PROCESSING_CONFIG = {
    "chunk_size": 512,
    "chunk_overlap": 50,
    "language_detection": True,
    "enable_translation": False,
    "clean_html": True,
    "remove_urls": True,
    "remove_emails": True,
    "remove_special_chars": False,
    "normalize_unicode": True,
    "replacement_patterns": {
        r"\u200b": "",            # Zero-width space
        r"\xa0": " ",             # Non-breaking space
        r"\t": " ",               # Tab
        r"\n\n+": "\n\n",         # Nhiều dòng trống
        r"\.{2,}": ".",           # Nhiều dấu chấm
        r"…": "...",              # Dấu ba chấm liền
        r"(\d+),(\d+)": r"\1.\2", # Đổi dấu phẩy trong số thành dấu chấm
        r"\s+": " ",              # Nhiều khoảng trắng thành một
    }
}

# Cấu hình NLP
NLP_CONFIG = {
    "models": {
        "ner": "vi_spacy_model",  # Pretrained NER model for Vietnamese
        "classification": "vi_text_classification",
        "summarization": "vi_summarization",
    },
    "entity_types": [
        "SHRIMP_SPECIES",
        "DISEASE",
        "CHEMICAL",
        "TECHNIQUE",
        "EQUIPMENT",
        "LOCATION",
        "MEASUREMENT",
    ],
    "use_ner": False
}

# Cấu hình RAG
RAG_CONFIG = {
    "embedding_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "embedding_dim": 384,
    "use_gpu": False,
    "llm_model": "gpt-3.5-turbo",
    "top_k": 5,
    "score_threshold": 0.7,
    "max_tokens": 2000,
}

# Cấu hình vector database
VECTOR_DB_CONFIG = {
    "type": "faiss",  # faiss, chroma
    "collection_name": "shrimp_aquaculture",
    "persist_directory": os.path.join(EMBEDDINGS_DIR, "vector_db"),
    "distance_metric": "cosine",
}

# Cấu hình logging
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "standard",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.FileHandler",
            "level": "DEBUG",
            "formatter": "standard",
            "filename": os.path.join(BASE_DIR, "logs", "aquanets.log"),
            "mode": "a",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": True
        },
    }
}

# Thiết lập logging
def set_up_logging(level=logging.INFO):
    """
    Thiết lập logging
    
    Args:
        level: Mức độ logging (mặc định: INFO)
    """
    # Tạo thư mục logs nếu chưa tồn tại
    logs_dir = os.path.join(BASE_DIR, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Cấu hình logging
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),  # Log ra console
            logging.FileHandler(os.path.join(logs_dir, "aquanets.log")),  # Log ra file
        ]
    )