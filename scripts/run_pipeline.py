#!/usr/bin/env python3
"""
Script chạy toàn bộ pipeline từ crawl dữ liệu đến tạo embedding và lưu vào vector database
"""

import os
import sys
import argparse
import logging
import time
from typing import List, Dict, Any, Optional
import json
from pathlib import Path

# Thêm thư mục gốc vào đường dẫn import
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
sys.path.append(root_dir)

# Import các module cần thiết
from crawlers.thuysanvietnam_crawler import ThuySanVietNamCrawler
from crawlers.academic_crawler import AcademicCrawler
from processing.text_processor import TextProcessor
from models.embedding_manager import EmbeddingManager
from storage.vector_db import VectorDatabase
from config.config import (
    RAW_DATA_DIR,
    PROCESSED_DATA_DIR,
    EMBEDDINGS_DIR,
    set_up_logging
)

# Thiết lập logging
logger = logging.getLogger(__name__)


def setup_environment():
    """Chuẩn bị môi trường làm việc, tạo thư mục cần thiết"""
    dirs = [RAW_DATA_DIR, PROCESSED_DATA_DIR, EMBEDDINGS_DIR]
    for dir_path in dirs:
        os.makedirs(dir_path, exist_ok=True)
        logger.info(f"Đảm bảo thư mục tồn tại: {dir_path}")


def run_crawlers(max_articles: int = 100):
    """
    Chạy các crawler để thu thập dữ liệu
    
    Args:
        max_articles: Số lượng bài viết tối đa mỗi crawler
        
    Returns:
        Số lượng tài liệu đã crawl
    """
    crawled_count = 0
    
    # Crawler cho thuysanvietnam.com
    try:
        logger.info("Bắt đầu crawl từ thuysanvietnam.com")
        crawler = ThuySanVietNamCrawler()
        thuysanvietnam_results = crawler.crawl(max_articles=max_articles)
        crawled_count += len(thuysanvietnam_results)
        logger.info(f"Đã crawl {len(thuysanvietnam_results)} bài viết từ thuysanvietnam.com")
        
        # Hiển thị một vài ví dụ
        if thuysanvietnam_results:
            for i, article in enumerate(thuysanvietnam_results[:3]):
                logger.info(f"Bài viết {i+1}: {article.get('title', 'Không có tiêu đề')}")
                
    except Exception as e:
        logger.error(f"Lỗi khi crawl từ thuysanvietnam.com: {str(e)}")
    
    # Crawler cho các nguồn học thuật
    try:
        logger.info("Bắt đầu crawl từ các nguồn học thuật")
        academic_crawler = AcademicCrawler()
        academic_results = academic_crawler.crawl(max_articles_per_source=max_articles // 2)  # Lấy một nửa số bài từ nguồn học thuật
        crawled_count += len(academic_results)
        logger.info(f"Đã crawl {len(academic_results)} tài liệu từ các nguồn học thuật")
        
        # Hiển thị một vài ví dụ
        if academic_results:
            for i, article in enumerate(academic_results[:3]):
                logger.info(f"Tài liệu học thuật {i+1}: {article.get('title', 'Không có tiêu đề')}")
                
    except Exception as e:
        logger.error(f"Lỗi khi crawl từ các nguồn học thuật: {str(e)}")
    
    logger.info(f"Đã hoàn thành crawl, tổng cộng {crawled_count} tài liệu")
    return crawled_count


def process_raw_data(limit: Optional[int] = None):
    """
    Xử lý dữ liệu thô thành các đoạn văn bản
    
    Args:
        limit: Giới hạn số tài liệu cần xử lý
        
    Returns:
        Danh sách đường dẫn đến các file đã xử lý
    """
    logger.info("Bắt đầu xử lý dữ liệu thô")
    
    processor = TextProcessor()
    processed_files = processor.process_all_from_directory(limit=limit)
    
    logger.info(f"Đã xử lý và lưu {len(processed_files)} tài liệu")
    return processed_files


def create_embeddings(limit: Optional[int] = None):
    """
    Tạo embedding cho dữ liệu đã xử lý
    
    Args:
        limit: Giới hạn số tài liệu cần tạo embedding
        
    Returns:
        Danh sách đường dẫn đến các file embedding
    """
    logger.info("Bắt đầu tạo embedding cho dữ liệu đã xử lý")
    
    embedding_manager = EmbeddingManager()
    embedded_files = embedding_manager.process_all_from_directory(limit=limit)
    
    logger.info(f"Đã tạo embedding và lưu {len(embedded_files)} tài liệu")
    return embedded_files


def store_in_vector_db():
    """
    Lưu trữ embedding vào vector database
    
    Returns:
        Số lượng tài liệu đã lưu vào vector database
    """
    logger.info("Bắt đầu lưu trữ embedding vào vector database")
    
    vector_db = VectorDatabase()
    count = vector_db.import_embeddings_from_directory()
    
    logger.info(f"Đã lưu trữ {count} tài liệu vào vector database")
    return count


def run_full_pipeline(max_articles: int = 100):
    """
    Chạy toàn bộ quy trình từ crawl dữ liệu đến lưu trữ vector
    
    Args:
        max_articles: Số lượng bài viết tối đa cho mỗi crawler
        
    Returns:
        Tổng quan về quy trình và số lượng tài liệu đã xử lý
    """
    logger.info("Bắt đầu chạy toàn bộ pipeline")
    
    start_time = time.time()
    
    # Chuẩn bị môi trường
    setup_environment()
    
    # Chạy crawl
    crawled_count = run_crawlers(max_articles=max_articles)
    
    # Xử lý văn bản
    processed_files = process_raw_data()
    
    # Tạo embedding
    embedded_files = create_embeddings()
    
    # Lưu vào vector database
    stored_count = store_in_vector_db()
    
    # Tổng kết
    elapsed_time = time.time() - start_time
    
    summary = {
        "crawled_count": crawled_count,
        "processed_count": len(processed_files),
        "embedded_count": len(embedded_files),
        "stored_count": stored_count,
        "elapsed_time": elapsed_time
    }
    
    logger.info("Kết quả chạy pipeline:")
    logger.info(f"- Số tài liệu đã crawl: {summary['crawled_count']}")
    logger.info(f"- Số tài liệu đã xử lý: {summary['processed_count']}")
    logger.info(f"- Số tài liệu đã tạo embedding: {summary['embedded_count']}")
    logger.info(f"- Số tài liệu đã lưu vào vector database: {summary['stored_count']}")
    logger.info(f"- Thời gian chạy: {elapsed_time:.2f} giây")
    
    return summary


def main():
    """Hàm chính để chạy script từ dòng lệnh"""
    parser = argparse.ArgumentParser(description="Chạy pipeline xử lý dữ liệu cho dự án AquaNets")
    
    # Các tham số
    parser.add_argument("--all", action="store_true", help="Chạy tất cả các bước trong pipeline")
    parser.add_argument("--crawl", action="store_true", help="Chỉ chạy bước crawl dữ liệu")
    parser.add_argument("--process", action="store_true", help="Chỉ chạy bước xử lý văn bản")
    parser.add_argument("--embed", action="store_true", help="Chỉ chạy bước tạo embedding")
    parser.add_argument("--store", action="store_true", help="Chỉ chạy bước lưu vào vector database")
    parser.add_argument("--max-articles", type=int, default=100, help="Số lượng bài viết tối đa cho mỗi crawler")
    parser.add_argument("--limit", type=int, help="Giới hạn số tài liệu xử lý (cho các bước riêng lẻ)")
    parser.add_argument("--log-level", type=str, default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                      help="Mức độ log (mặc định: INFO)")
    
    args = parser.parse_args()
    
    # Thiết lập logging
    log_level = getattr(logging, args.log_level)
    set_up_logging(log_level)
    
    # Khởi chạy các bước theo tham số
    if args.all or not any([args.crawl, args.process, args.embed, args.store]):
        # Nếu không có tham số hoặc có --all, chạy toàn bộ pipeline
        run_full_pipeline(max_articles=args.max_articles)
    else:
        # Chạy từng bước riêng lẻ
        if args.crawl:
            run_crawlers(max_articles=args.max_articles)
            
        if args.process:
            process_raw_data(limit=args.limit)
            
        if args.embed:
            create_embeddings(limit=args.limit)
            
        if args.store:
            store_in_vector_db()
    
    logger.info("Đã hoàn thành thực thi pipeline")


if __name__ == "__main__":
    main()