"""
Module cung cấp class BaseCrawler làm nền tảng cho tất cả các crawler khác
"""

import os
import sys
import json
import time
import random
import logging
import re
import requests
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from datetime import datetime
import uuid

# Thêm thư mục gốc vào đường dẫn import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import (
    RAW_DATA_DIR, 
    CRAWL_SETTINGS
)

# Thiết lập logging
logger = logging.getLogger(__name__)


class BaseCrawler:
    """
    Lớp cơ sở cho tất cả các crawler, cung cấp các phương thức chung
    """
    
    def __init__(self, name: str, base_url: str, output_dir: Optional[str] = None):
        """
        Khởi tạo BaseCrawler
        
        Args:
            name: Tên của crawler
            base_url: URL cơ sở của trang web cần crawl
            output_dir: Thư mục lưu dữ liệu (mặc định: RAW_DATA_DIR)
        """
        self.name = name
        self.base_url = base_url
        self.output_dir = output_dir or RAW_DATA_DIR
        
        # Lấy các cài đặt từ config
        self.headers = CRAWL_SETTINGS["HEADERS"].copy()
        self.user_agents = CRAWL_SETTINGS["USER_AGENTS"]
        self.delay = CRAWL_SETTINGS["DELAY_BETWEEN_REQUESTS"]
        self.timeout = CRAWL_SETTINGS["TIMEOUT"]
        self.max_retries = CRAWL_SETTINGS["MAX_RETRIES"]
        self.respect_robots = CRAWL_SETTINGS["RESPECT_ROBOTS_TXT"]
        
        # Khởi tạo danh sách URL được phép/không được phép (nếu respect_robots=True)
        self.allowed_urls = []
        self.disallowed_urls = []
        
        # Tạo thư mục output nếu chưa tồn tại
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Parse robots.txt nếu cần
        if self.respect_robots:
            self._parse_robots_txt()
            
        logger.info(f"Đã khởi tạo crawler {self.name} cho {self.base_url}")
    
    def _parse_robots_txt(self) -> None:
        """Parse file robots.txt của trang web"""
        try:
            robots_url = urljoin(self.base_url, "/robots.txt")
            response = requests.get(robots_url, timeout=self.timeout)
            
            if response.status_code == 200:
                lines = response.text.split('\n')
                user_agent_applies = False
                
                for line in lines:
                    line = line.strip().lower()
                    
                    if line.startswith('user-agent:'):
                        agent = line[11:].strip()
                        # Kiểm tra xem rule có áp dụng cho chúng ta không
                        user_agent_applies = agent == '*' or 'python' in agent
                    
                    if user_agent_applies:
                        if line.startswith('disallow:'):
                            path = line[9:].strip()
                            if path:
                                self.disallowed_urls.append(urljoin(self.base_url, path))
                        elif line.startswith('allow:'):
                            path = line[6:].strip()
                            if path:
                                self.allowed_urls.append(urljoin(self.base_url, path))
                                
                logger.info(f"Đã parse robots.txt: {len(self.disallowed_urls)} URLs bị cấm")
            else:
                logger.warning(f"Không thể tải robots.txt từ {robots_url}")
                
        except Exception as e:
            logger.error(f"Lỗi khi parse robots.txt: {str(e)}")
    
    def _is_url_allowed(self, url: str) -> bool:
        """
        Kiểm tra xem URL có được phép crawl không (dựa vào robots.txt)
        
        Args:
            url: URL cần kiểm tra
            
        Returns:
            True nếu URL được phép crawl, False nếu không
        """
        if not self.respect_robots:
            return True
            
        # Kiểm tra xem URL có nằm trong danh sách bị cấm không
        for disallowed in self.disallowed_urls:
            if url.startswith(disallowed):
                # Kiểm tra xem có exception cho phép không
                for allowed in self.allowed_urls:
                    if url.startswith(allowed) and len(allowed) > len(disallowed):
                        return True
                return False
                
        return True
    
    def get_random_user_agent(self) -> str:
        """Lấy ngẫu nhiên một User-Agent từ danh sách"""
        return random.choice(self.user_agents)
    
    def make_request(self, url: str, method: str = "GET", 
                    params: Optional[Dict[str, Any]] = None, 
                    data: Optional[Dict[str, Any]] = None) -> requests.Response:
        """
        Thực hiện HTTP request với retry logic
        
        Args:
            url: URL cần request
            method: Phương thức HTTP (GET, POST,...)
            params: Query parameters
            data: Form data hoặc JSON data
            
        Returns:
            Đối tượng Response
            
        Raises:
            Exception: Nếu request không thành công sau số lần thử lại
        """
        if not self._is_url_allowed(url):
            raise ValueError(f"URL {url} không được phép crawl theo robots.txt")
            
        # Chuẩn bị headers với User-Agent ngẫu nhiên
        headers = self.headers.copy()
        headers["User-Agent"] = self.get_random_user_agent()
        
        for attempt in range(self.max_retries):
            try:
                # Thêm delay giữa các request
                if attempt > 0:
                    time.sleep(self.delay * (attempt + 1))  # Tăng dần delay
                else:
                    time.sleep(self.delay)
                    
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    data=data,
                    timeout=self.timeout
                )
                
                # Kiểm tra status code
                response.raise_for_status()
                
                return response
                
            except (requests.exceptions.RequestException, Exception) as e:
                logger.warning(f"Lỗi khi request {url} (lần thử {attempt+1}/{self.max_retries}): {str(e)}")
                
                # Nếu là lần thử cuối cùng, ném ra ngoại lệ
                if attempt == self.max_retries - 1:
                    logger.error(f"Không thể request {url} sau {self.max_retries} lần thử")
                    raise
    
    def save_raw_data(self, data: Dict[str, Any], filename: Optional[str] = None) -> str:
        """
        Lưu dữ liệu thô vào file
        
        Args:
            data: Dữ liệu cần lưu
            filename: Tên file (tự động tạo nếu không cung cấp)
            
        Returns:
            Đường dẫn đến file đã lưu
        """
        if not filename:
            # Tạo tên file từ id hoặc ngẫu nhiên
            file_id = data.get("id", str(uuid.uuid4()))
            source = data.get("source", "").replace("/", "-")
            if source:
                filename = f"{source}_{file_id}.json"
            else:
                filename = f"{file_id}.json"
                
        filepath = os.path.join(self.output_dir, filename)
        
        # Thêm metadata về thời gian crawl
        data["crawled_at"] = datetime.now().isoformat()
        data["crawler"] = self.name
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Đã lưu dữ liệu vào {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Lỗi khi lưu dữ liệu: {str(e)}")
            raise
    
    def extract_links(self, html_content: str, base_url: str) -> List[str]:
        """
        Trích xuất các liên kết từ nội dung HTML
        
        Args:
            html_content: Nội dung HTML
            base_url: URL cơ sở để giải quyết các URL tương đối
            
        Returns:
            Danh sách các URL tuyệt đối
        """
        links = []
        
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                
                # Chuyển đổi URL tương đối thành tuyệt đối
                absolute_url = urljoin(base_url, href)
                
                # Bỏ qua URL không phù hợp và các fragment
                parsed_url = urlparse(absolute_url)
                
                # Chỉ giữ http và https
                if parsed_url.scheme not in ("http", "https"):
                    continue
                    
                # Làm sạch URL
                cleaned_url = self.clean_url(absolute_url)
                
                if cleaned_url and self._is_url_allowed(cleaned_url):
                    links.append(cleaned_url)
                    
            return list(set(links))  # Loại bỏ trùng lặp
            
        except Exception as e:
            logger.error(f"Lỗi khi trích xuất links: {str(e)}")
            return []
    
    def clean_url(self, url: str) -> str:
        """
        Làm sạch URL, loại bỏ các tham số không cần thiết
        
        Args:
            url: URL cần làm sạch
            
        Returns:
            URL đã làm sạch
        """
        parsed_url = urlparse(url)
        
        # Các tham số query thường không cần
        params_to_remove = [
            "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
            "fbclid", "gclid", "ref", "source", "ref_src", "ref_url"
        ]
        
        if parsed_url.query:
            # Parse query parameters
            query_params = {}
            for param in parsed_url.query.split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    query_params[key] = value
            
            # Loại bỏ các tham số không cần thiết
            for param in params_to_remove:
                if param in query_params:
                    del query_params[param]
            
            # Xây dựng lại query string
            new_query = "&".join([f"{k}={v}" for k, v in query_params.items()])
            
            # Xây dựng lại URL
            clean_url = urlparse(url)._replace(query=new_query).geturl()
            
            # Loại bỏ fragment (phần sau #)
            clean_url = clean_url.split("#")[0]
            
            return clean_url
        
        # Nếu không có query parameters, chỉ cần loại bỏ fragment
        return url.split("#")[0]
    
    def crawl(self, max_pages: int = 10) -> List[Dict[str, Any]]:
        """
        Phương thức crawl cơ bản, các lớp con cần override
        
        Args:
            max_pages: Số trang tối đa để crawl
            
        Returns:
            Danh sách dữ liệu đã thu thập
        """
        raise NotImplementedError("Lớp con phải override phương thức crawl()")