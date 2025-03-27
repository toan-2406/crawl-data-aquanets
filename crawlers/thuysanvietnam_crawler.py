"""
Module crawler cho trang Thủy Sản Việt Nam
"""

import os
import sys
import json
import time
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import uuid

# Thêm thư mục gốc vào đường dẫn import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawlers.base_crawler import BaseCrawler
from config.config import RAW_DATA_DIR

# Thiết lập logging
logger = logging.getLogger(__name__)


class ThuySanVietNamCrawler(BaseCrawler):
    """
    Crawler chuyên biệt cho trang web Thủy Sản Việt Nam
    https://thuysanvietnam.com.vn
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Khởi tạo crawler cho Thủy Sản Việt Nam
        
        Args:
            output_dir: Thư mục lưu dữ liệu (mặc định: RAW_DATA_DIR)
        """
        super().__init__(
            name="ThuySanVietNam",
            base_url="https://thuysanvietnam.com.vn",
            output_dir=output_dir
        )
        
        # Các từ khóa liên quan đến tôm
        self.shrimp_keywords = [
            "tôm", "tôm sú", "tôm thẻ", "tôm càng xanh", "tôm hùm", "tôm hùm nước ngọt",
            "tôm he", "tôm chân trắng", "penaeus", "litopenaeus", "vannamei", "monodon",
            "shrimp", "prawn", "tiger shrimp", "white leg shrimp", "lobster",
            "tôm giống", "ấu trùng tôm", "post-larvae", "nauplii"
        ]
        
        # Các từ khóa liên quan đến bệnh tôm
        self.shrimp_disease_keywords = [
            "bệnh đốm trắng", "bệnh đầu vàng", "hoại tử gan tụy", "đốm trắng", "EMS",
            "WSSV", "white spot syndrome", "hepatopancreatic necrosis", "early mortality syndrome",
            "bệnh phân trắng", "bệnh mềm vỏ", "bệnh đỏ thân", "bệnh đen mang", "vibrio",
            "vi khuẩn", "virus", "nấm", "ký sinh trùng", "nhiễm khuẩn", "dịch bệnh"
        ]
        
        # Các từ khóa liên quan đến kỹ thuật nuôi tôm
        self.farming_keywords = [
            "nuôi tôm", "ao nuôi", "nuôi thâm canh", "nuôi bán thâm canh", "nuôi quảng canh",
            "biofloc", "RAS", "recirculating aquaculture", "tuần hoàn nước", "hệ thống lọc",
            "ao lót bạt", "ao đất", "thức ăn tôm", "cho tôm ăn", "quy trình nuôi", "kỹ thuật nuôi",
            "cải tạo ao", "xử lý nước", "men vi sinh", "probiotic", "chất xử lý nước"
        ]
        
        # Từ khóa ngăn chặn (không liên quan đến nuôi tôm)
        self.exclude_keywords = [
            "xuất khẩu hàng hóa", "tàu biển", "đánh bắt", "khai thác", "hải sản",
            "cảng cá", "cá ngừ", "cá tra", "cá basa", "ngao", "nghêu", "sò", "ốc",
            "rong biển", "tảo", "logistics", "vận chuyển hàng hóa", "thuế xuất nhập khẩu"
        ]
        
        logger.info("Đã khởi tạo crawler cho Thủy Sản Việt Nam")
    
    def is_shrimp_related(self, url: str, title: str, content: str = "") -> bool:
        """
        Kiểm tra xem bài viết có liên quan đến tôm không
        
        Args:
            url: URL của bài viết
            title: Tiêu đề bài viết
            content: Nội dung bài viết (nếu có)
            
        Returns:
            True nếu bài viết liên quan đến tôm, False nếu không
        """
        # Nếu URL có chứa từ khóa liên quan đến tôm
        url_lower = url.lower()
        if any(keyword in url_lower for keyword in ["tom", "tôm", "shrimp", "prawn"]):
            return True
            
        # Nếu tiêu đề có chứa từ khóa liên quan đến tôm
        title_lower = title.lower()
        if any(keyword.lower() in title_lower for keyword in self.shrimp_keywords):
            return True
            
        # Kiểm tra từ khóa bệnh tôm
        if any(keyword.lower() in title_lower for keyword in self.shrimp_disease_keywords):
            return True
            
        # Kiểm tra từ khóa kỹ thuật nuôi tôm
        if any(keyword.lower() in title_lower for keyword in self.farming_keywords):
            return True
            
        # Kiểm tra nội dung (nếu có)
        if content:
            content_lower = content.lower()
            # Đếm số lần xuất hiện của từ khóa liên quan đến tôm
            shrimp_keyword_count = sum(content_lower.count(keyword.lower()) for keyword in self.shrimp_keywords)
            # Nếu có nhiều từ khóa tôm trong nội dung
            if shrimp_keyword_count >= 3:
                return True
                
            # Kiểm tra từ khóa bệnh tôm và kỹ thuật nuôi tôm
            disease_keyword_count = sum(content_lower.count(keyword.lower()) for keyword in self.shrimp_disease_keywords)
            farming_keyword_count = sum(content_lower.count(keyword.lower()) for keyword in self.farming_keywords)
            if (disease_keyword_count + farming_keyword_count) >= 3:
                return True
                
        # Mặc định không liên quan
        return False
    
    def extract_article_data(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Trích xuất dữ liệu từ một bài viết
        
        Args:
            url: URL của bài viết
            
        Returns:
            Dict chứa dữ liệu bài viết hoặc None nếu không trích xuất được
        """
        try:
            # Gửi request lấy nội dung bài viết
            response = self.make_request(url)
            html_content = response.text
            
            # Parse HTML
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Trích xuất tiêu đề
            title_tag = soup.select_one("h1.title")
            if not title_tag:
                title_tag = soup.select_one("h1.cms-title")
            if not title_tag:
                title_tag = soup.select_one("h1.detail-title")
            
            if not title_tag:
                logger.warning(f"Không tìm thấy tiêu đề bài viết tại {url}")
                return None
                
            title = title_tag.get_text(strip=True)
            
            # Trích xuất thời gian đăng
            time_tag = soup.select_one("span.cms-date")
            if not time_tag:
                time_tag = soup.select_one(".detail-time")
            if not time_tag:
                time_tag = soup.select_one(".time")
                
            published_date = time_tag.get_text(strip=True) if time_tag else None
            
            # Trích xuất tác giả
            author_tag = soup.select_one(".author")
            if not author_tag:
                author_tag = soup.select_one(".detail-author")
            
            author = author_tag.get_text(strip=True) if author_tag else None
            
            # Trích xuất phần tóm tắt
            summary_tag = soup.select_one(".cms-desc")
            if not summary_tag:
                summary_tag = soup.select_one(".sapo")
            if not summary_tag:
                summary_tag = soup.select_one(".detail-sapo")
                
            summary = summary_tag.get_text(strip=True) if summary_tag else None
            
            # Trích xuất nội dung bài viết
            content_tag = soup.select_one(".detail-content")
            if not content_tag:
                content_tag = soup.select_one(".cms-body")
            if not content_tag:
                content_tag = soup.select_one(".body-content")
                
            if not content_tag:
                logger.warning(f"Không tìm thấy nội dung bài viết tại {url}")
                return None
                
            # Loại bỏ các thẻ script, style, và các elements không cần thiết
            for element in content_tag.select("script, style, .related-news, .adv, .banner, .social-share"):
                element.decompose()
                
            # Trích xuất nội dung văn bản
            content_text = content_tag.get_text("\n", strip=True)
            
            # Trích xuất HTML nội dung
            content_html = str(content_tag)
            
            # Trích xuất các hình ảnh
            images = []
            for img_tag in content_tag.select("img"):
                src = img_tag.get("src", "")
                if src and not src.startswith("data:"):
                    # Chuyển đổi URL tương đối thành tuyệt đối
                    img_url = urljoin(url, src)
                    images.append(img_url)
            
            # Trích xuất các thẻ (tags)
            tags = []
            tags_container = soup.select_one(".tags")
            if tags_container:
                for tag in tags_container.select("a"):
                    tag_text = tag.get_text(strip=True)
                    if tag_text:
                        tags.append(tag_text)
            
            # Kiểm tra xem bài viết có liên quan đến tôm không
            if not self.is_shrimp_related(url, title, content_text):
                logger.info(f"Bài viết không liên quan đến nuôi tôm: {url}")
                return None
            
            # Tạo đối tượng dữ liệu bài viết
            article_data = {
                "id": str(uuid.uuid4()),
                "url": url,
                "title": title,
                "published_date": published_date,
                "author": author,
                "summary": summary,
                "content_text": content_text,
                "content_html": content_html,
                "images": images,
                "tags": tags,
                "source": "thuysanvietnam",
                "language": "vi",
                "content_type": "article"
            }
            
            logger.info(f"Đã trích xuất dữ liệu bài viết: {title}")
            return article_data
            
        except Exception as e:
            logger.error(f"Lỗi khi trích xuất dữ liệu bài viết {url}: {str(e)}")
            return None
    
    def get_category_urls(self) -> List[str]:
        """
        Lấy danh sách URL của các danh mục liên quan đến tôm
        
        Returns:
            Danh sách URL của các danh mục
        """
        try:
            # Các URL danh mục cố định đã biết
            category_urls = [
                "https://thuysanvietnam.com.vn/tom/",
                "https://thuysanvietnam.com.vn/nuoi-trong/",
                "https://thuysanvietnam.com.vn/nuoi-tom/",
                "https://thuysanvietnam.com.vn/benh-tom/",
                "https://thuysanvietnam.com.vn/ky-thuat-nuoi-tom/",
                "https://thuysanvietnam.com.vn/ky-thuat-nuoi-trong/",
                "https://thuysanvietnam.com.vn/con-giong/",
                "https://thuysanvietnam.com.vn/moi-truong-nuoi/"
            ]
            
            # Tìm thêm các danh mục khác từ trang chủ
            response = self.make_request(self.base_url)
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Tìm các liên kết danh mục từ menu chính
            nav_elements = soup.select("nav ul li a, .menu a, .navigation a")
            
            for a_tag in nav_elements:
                href = a_tag.get("href", "")
                text = a_tag.get_text(strip=True).lower()
                
                # Chỉ thêm URL nếu liên quan đến tôm hoặc nuôi trồng
                if href and (
                    "tom" in href or "nuoi" in href or 
                    any(keyword in text for keyword in ["tôm", "nuôi", "thủy sản", "bệnh", "kỹ thuật"])
                ):
                    category_url = urljoin(self.base_url, href)
                    if category_url not in category_urls:
                        category_urls.append(category_url)
            
            logger.info(f"Đã tìm thấy {len(category_urls)} danh mục liên quan đến tôm")
            return category_urls
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách danh mục: {str(e)}")
            return []
    
    def get_article_urls_from_category(self, category_url: str, max_pages: int = 5) -> List[str]:
        """
        Lấy danh sách URL các bài viết từ một danh mục
        
        Args:
            category_url: URL của danh mục
            max_pages: Số trang tối đa để crawl (từ trang đầu)
            
        Returns:
            Danh sách URL các bài viết
        """
        article_urls = []
        
        try:
            for page in range(1, max_pages + 1):
                # Tạo URL trang danh mục
                page_url = category_url
                if page > 1:
                    # Kiểm tra cấu trúc URL để thêm tham số trang phù hợp
                    if "?" in category_url:
                        page_url = f"{category_url}&page={page}"
                    else:
                        page_url = f"{category_url}page/{page}/"
                
                logger.info(f"Crawling trang danh mục: {page_url}")
                
                # Gửi request lấy trang danh mục
                response = self.make_request(page_url)
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Tìm các liên kết bài viết
                article_tags = soup.select(".list-news article, .cms-list article, .news-item")
                if not article_tags:
                    article_tags = soup.select(".list-news a, .news-list a")
                if not article_tags:
                    article_tags = soup.select(".item a.title, .item .info")
                
                # Nếu không tìm thấy bài viết nào, thử dùng selector khác
                if not article_tags:
                    article_tags = soup.select("a.title, h3.title a, .list a")
                
                # Trích xuất URL bài viết
                for article_tag in article_tags:
                    # Tìm thẻ a nếu article_tag không phải là thẻ a
                    if article_tag.name != "a":
                        a_tag = article_tag.select_one("a")
                        if not a_tag:
                            continue
                    else:
                        a_tag = article_tag
                    
                    href = a_tag.get("href", "")
                    if href:
                        article_url = urljoin(category_url, href)
                        if article_url not in article_urls:
                            article_urls.append(article_url)
                
                # Nếu không tìm thấy bài viết nào, có thể đã hết trang
                if not article_tags:
                    logger.info(f"Không tìm thấy bài viết nào ở trang {page}, dừng.")
                    break
                    
                # Thêm delay trước khi sang trang tiếp theo
                time.sleep(self.delay)
            
            logger.info(f"Đã tìm thấy {len(article_urls)} URL bài viết từ danh mục {category_url}")
            return article_urls
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy URL bài viết từ danh mục {category_url}: {str(e)}")
            return article_urls
    
    def search_by_keyword(self, keyword: str, max_pages: int = 3) -> List[str]:
        """
        Tìm kiếm bài viết theo từ khóa
        
        Args:
            keyword: Từ khóa tìm kiếm
            max_pages: Số trang tối đa để crawl
            
        Returns:
            Danh sách URL các bài viết
        """
        article_urls = []
        
        try:
            # Tạo URL tìm kiếm - thử các cấu trúc URL khác nhau
            search_urls = [
                f"{self.base_url}/tim-kiem?q={keyword}",
                f"{self.base_url}/tim-kiem/{keyword}",
                f"{self.base_url}/search?q={keyword}"
            ]
            
            for search_url in search_urls:
                try:
                    logger.info(f"Thử tìm kiếm với URL: {search_url}")
                    response = self.make_request(search_url, method="GET")
                    
                    # Nếu request thành công, tiếp tục với URL này
                    if response.status_code == 200:
                        logger.info(f"Tìm thấy URL tìm kiếm hợp lệ: {search_url}")
                        
                        for page in range(1, max_pages + 1):
                            # Tạo URL trang tìm kiếm
                            page_url = search_url
                            if page > 1:
                                if "?" in search_url:
                                    page_url = f"{search_url}&page={page}"
                                else:
                                    page_url = f"{search_url}/page/{page}"
                            
                            logger.info(f"Crawling trang tìm kiếm: {page_url}")
                            
                            # Gửi request lấy trang tìm kiếm
                            page_response = self.make_request(page_url)
                            soup = BeautifulSoup(page_response.text, "html.parser")
                            
                            # Tìm các liên kết bài viết với nhiều bộ selector khác nhau
                            article_selectors = [
                                ".search-result article, .search-result .item",
                                ".search-results a, .result-list a",
                                "a.title, h3.title a, .list a",
                                ".item-news, .news-item, .article-item",
                                ".list-news article, .list-news .item",
                                ".result-item a, .news-title a"
                            ]
                            
                            found_articles = False
                            for selector in article_selectors:
                                article_tags = soup.select(selector)
                                if article_tags:
                                    found_articles = True
                                    # Trích xuất URL bài viết
                                    for article_tag in article_tags:
                                        # Tìm thẻ a nếu article_tag không phải là thẻ a
                                        if article_tag.name != "a":
                                            a_tag = article_tag.select_one("a")
                                            if not a_tag:
                                                continue
                                        else:
                                            a_tag = article_tag
                                        
                                        href = a_tag.get("href", "")
                                        if href:
                                            article_url = urljoin(self.base_url, href)
                                            if article_url not in article_urls:
                                                article_urls.append(article_url)
                                    
                                    break  # Nếu đã tìm thấy bài viết với một selector, dừng lại
                            
                            # Nếu không tìm thấy bài viết nào, có thể đã hết trang
                            if not found_articles:
                                logger.info(f"Không tìm thấy bài viết nào ở trang {page}, dừng.")
                                break
                                
                            # Thêm delay trước khi sang trang tiếp theo
                            time.sleep(self.delay)
                        
                        # Tìm thấy URL hoạt động, không cần thử URL khác
                        break
                    
                except Exception as e:
                    logger.warning(f"Lỗi khi thử URL tìm kiếm {search_url}: {str(e)}")
                    continue
            
            # Thử cách thứ hai: tìm kiếm bài viết từ các danh mục liên quan đến từ khóa 
            if not article_urls:
                logger.info(f"Tất cả URL tìm kiếm đều không hoạt động, thử tìm từ danh mục")
                
                # Lấy danh sách URL của các danh mục
                category_urls = self.get_category_urls()
                
                # Lấy URL bài viết từ mỗi danh mục
                for category_url in category_urls:
                    urls_from_category = self.get_article_urls_from_category(
                        category_url,
                        max_pages=1  # Chỉ lấy trang đầu tiên để tiết kiệm thời gian
                    )
                    
                    # Thêm vào danh sách tổng hợp
                    for url in urls_from_category:
                        if url not in article_urls:
                            article_urls.append(url)
                
                # Lọc URL liên quan đến từ khóa
                keyword_lower = keyword.lower()
                filtered_urls = [
                    url for url in article_urls 
                    if keyword_lower in url.lower()
                ]
                
                article_urls = filtered_urls
            
            logger.info(f"Đã tìm thấy {len(article_urls)} URL bài viết từ tìm kiếm '{keyword}'")
            return article_urls
            
        except Exception as e:
            logger.error(f"Lỗi khi tìm kiếm bài viết với từ khóa '{keyword}': {str(e)}")
            return article_urls
    
    def crawl(self, max_articles: int = 100) -> List[Dict[str, Any]]:
        """
        Thực hiện crawl dữ liệu từ trang Thủy Sản Việt Nam
        
        Args:
            max_articles: Số lượng bài viết tối đa cần crawl
            
        Returns:
            Danh sách các bài viết đã crawl được
        """
        articles = []
        article_urls = []
        
        try:
            # Lấy danh sách URL của các danh mục
            category_urls = self.get_category_urls()
            
            # Lấy URL bài viết từ mỗi danh mục
            for category_url in category_urls:
                # Tính toán số trang tối đa để crawl mỗi danh mục (phân bổ đều)
                max_pages_per_category = 2
                
                # Lấy URL bài viết từ danh mục
                urls_from_category = self.get_article_urls_from_category(
                    category_url,
                    max_pages=max_pages_per_category
                )
                
                # Thêm vào danh sách tổng hợp
                for url in urls_from_category:
                    if url not in article_urls:
                        article_urls.append(url)
                        
                # Nếu đã có đủ URL, dừng lại
                if len(article_urls) >= max_articles * 2:  # Lấy gấp đôi để dự phòng
                    break
            
            # Thêm tìm kiếm theo từ khóa liên quan đến tôm
            for keyword in ["tôm sú", "tôm thẻ chân trắng", "nuôi tôm", "bệnh tôm"]:
                # Bỏ qua nếu đã đủ URL
                if len(article_urls) >= max_articles * 2:
                    break
                    
                # Tìm kiếm bài viết theo từ khóa
                urls_from_search = self.search_by_keyword(keyword, max_pages=2)
                
                # Thêm vào danh sách tổng hợp
                for url in urls_from_search:
                    if url not in article_urls:
                        article_urls.append(url)
            
            logger.info(f"Tổng cộng có {len(article_urls)} URL bài viết để crawl")
            
            # Trích xuất dữ liệu từ mỗi URL bài viết
            count = 0
            for url in article_urls:
                try:
                    # Kiểm tra xem đã đạt đủ số lượng bài viết chưa
                    if count >= max_articles:
                        break
                        
                    # Trích xuất dữ liệu từ bài viết
                    article_data = self.extract_article_data(url)
                    
                    # Chỉ lưu nếu trích xuất thành công và có nội dung
                    if article_data and article_data.get("content_text"):
                        # Lưu dữ liệu thô
                        self.save_raw_data(article_data)
                        
                        # Thêm vào danh sách kết quả
                        articles.append(article_data)
                        count += 1
                        
                        logger.info(f"Đã crawl {count}/{max_articles} bài viết")
                    
                    # Thêm delay
                    time.sleep(self.delay)
                    
                except Exception as e:
                    logger.error(f"Lỗi khi crawl bài viết {url}: {str(e)}")
                    continue
            
            logger.info(f"Đã hoàn thành crawl {len(articles)} bài viết từ Thủy Sản Việt Nam")
            return articles
            
        except Exception as e:
            logger.error(f"Lỗi khi crawl dữ liệu từ Thủy Sản Việt Nam: {str(e)}")
            return articles


if __name__ == "__main__":
    # Cấu hình logging khi chạy trực tiếp
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Khởi tạo crawler
    crawler = ThuySanVietNamCrawler()
    
    # Thực hiện crawl (giới hạn 5 bài viết khi chạy thử)
    articles = crawler.crawl(max_articles=5)
    
    print(f"Đã crawl được {len(articles)} bài viết")
    for i, article in enumerate(articles, 1):
        print(f"{i}. {article['title']} - {article['url']}")