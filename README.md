# AquaNets - Hệ thống Crawl Dữ liệu Nuôi Tôm

Hệ thống thu thập, xử lý và tạo embedding cho dữ liệu về nuôi tôm từ nhiều nguồn khác nhau. Dữ liệu này có thể được sử dụng để xây dựng các hệ thống RAG (Retrieval-Augmented Generation) chuyên biệt về lĩnh vực nuôi tôm.

## Tính năng chính

- **Thu thập dữ liệu từ nhiều nguồn**:
  - Trang web chuyên ngành: ThuySanVietNam.com
  - Nguồn học thuật: Google Scholar, CORE.ac.uk
  - Hỗ trợ mở rộng thêm các nguồn khác

- **Xử lý văn bản thông minh**:
  - Làm sạch và chuẩn hóa văn bản
  - Phát hiện ngôn ngữ
  - Phân đoạn văn bản thành chunks phù hợp

- **Tạo embedding và lưu trữ vector**:
  - Sử dụng mô hình Sentence Transformers
  - Hỗ trợ nhiều loại mô hình embedding khác nhau
  - Lưu trữ trong vector database (FAISS hoặc ChromaDB)

- **Pipeline hoàn chỉnh từ crawl đến vector database**:
  - Quy trình tự động từ thu thập đến lưu trữ
  - Hỗ trợ chạy từng bước riêng lẻ
  - Ghi log đầy đủ

## Cài đặt

### Yêu cầu

- Python 3.8+
- Các thư viện trong file `requirements.txt`

### Cài đặt các thư viện

```bash
pip install -r requirements.txt
```

## Cấu trúc thư mục

```
crawl_data_aquanets/
├── config/             # Cấu hình hệ thống
├── crawlers/           # Các crawler cho từng nguồn dữ liệu
├── models/             # Mô hình embedding và xử lý
├── processing/         # Xử lý văn bản
├── scripts/            # Script chạy pipeline
├── storage/            # Lưu trữ vector database
├── data/               # Thư mục chứa dữ liệu
│   ├── raw/            # Dữ liệu thô từ crawler
│   ├── processed/      # Dữ liệu đã xử lý
│   └── embeddings/     # Dữ liệu đã tạo embedding
├── logs/               # Log hệ thống
└── README.md           # Hướng dẫn sử dụng
```

## Sử dụng

### Chạy toàn bộ pipeline

```bash
python scripts/run_pipeline.py --all --max-articles 100
```

### Chạy từng bước riêng lẻ

```bash
# Chỉ chạy bước crawl dữ liệu
python scripts/run_pipeline.py --crawl --max-articles 50

# Chỉ chạy bước xử lý văn bản
python scripts/run_pipeline.py --process --limit 30

# Chỉ chạy bước tạo embedding
python scripts/run_pipeline.py --embed --limit 30

# Chỉ chạy bước lưu vào vector database
python scripts/run_pipeline.py --store
```

### Tham số dòng lệnh

- `--all`: Chạy toàn bộ pipeline
- `--crawl`: Chỉ chạy bước crawl dữ liệu
- `--process`: Chỉ chạy bước xử lý văn bản
- `--embed`: Chỉ chạy bước tạo embedding
- `--store`: Chỉ chạy bước lưu vào vector database
- `--max-articles <số>`: Số lượng bài viết tối đa cho mỗi crawler
- `--limit <số>`: Giới hạn số tài liệu xử lý (cho các bước riêng lẻ)
- `--log-level <level>`: Mức độ log (DEBUG, INFO, WARNING, ERROR)

## Mở rộng

### Thêm crawler mới

1. Tạo một lớp mới kế thừa từ `BaseCrawler` trong thư mục `crawlers/`
2. Triển khai các phương thức cần thiết
3. Thêm crawler vào file `run_pipeline.py`

### Thay đổi mô hình embedding

Chỉnh sửa cấu hình trong `config/config.py` để sử dụng mô hình embedding khác:

```python
RAG_CONFIG = {
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",  # Thay đổi mô hình ở đây
    "embedding_dim": 384,
    "use_gpu": False,
    # ...
}
```

## Ví dụ kết quả

Sau khi chạy pipeline, bạn sẽ có:

1. Dữ liệu thô trong thư mục `data/raw/`
2. Dữ liệu đã xử lý trong thư mục `data/processed/`
3. Dữ liệu đã tạo embedding trong thư mục `data/embeddings/`
4. Vector database trong thư mục `data/embeddings/vector_db/`

## Truy vấn dữ liệu

Bạn có thể truy vấn dữ liệu đã lưu trong vector database:

```python
from storage.vector_db import VectorDatabase
from models.embedding_manager import EmbeddingManager

# Tạo đối tượng vector database
db = VectorDatabase()

# Tạo embedding cho câu truy vấn
embedding_manager = EmbeddingManager()
query = "Các bệnh thường gặp ở tôm thẻ chân trắng"
query_embedding = embedding_manager.get_embedding(query)

# Truy vấn vector database
results = db.query(query_embedding, top_k=5)

# Hiển thị kết quả
for i, result in enumerate(results):
    print(f"Kết quả {i+1}: {result['text'][:100]}...")
    print(f"Điểm số: {result['score']}")
    print(f"URL: {result['metadata'].get('url', 'N/A')}")
    print()
```

## Giấy phép

Dự án này được phân phối dưới giấy phép MIT.

## Liên hệ

Nếu có câu hỏi hoặc đóng góp, vui lòng liên hệ qua issue tracker trên GitHub.