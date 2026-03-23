"""
EKV 文献检索模块 - 实现本地 PDF 文档的检索功能

本模块提供对 EKV_docs 目录下 PDF 文件的文本提取和检索功能，
支持按关键词检索相关段落并返回引用信息。
"""

import os
import re
import json
import hashlib
from typing import List, Dict, Any, Optional, Tuple
import logging

# 尝试导入 PDF 处理库，如果不可用则使用回退方案
try:
    import pymupdf as fitz  # PyMuPDF
    PDF_AVAILABLE = True
except ImportError:
    try:
        import fitz  # 备用导入方式
        PDF_AVAILABLE = True
    except ImportError:
        PDF_AVAILABLE = False
        logging.warning("PyMuPDF 不可用，将使用回退的文本文件检索")

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EKV_DOCS_DIR = os.path.join(PROJECT_ROOT, "EKV_docs")

# 文档配置
DOCUMENTS = {
    "guideline_2021": {
        "name": "中国脑卒中防治指导规范（2021 年版）",
        "filename": "中国脑卒中防治指导规范（2021 年版）.pdf",
        "short_name": "卒中防治指南2021"
    },
    "consensus_2025": {
        "name": "急性缺血卒中血管内治疗技术中国专家共识2025",
        "filename": "急性缺血卒中血管内治疗技术中国专家共识2025.pdf",
        "short_name": "血管内治疗共识2025"
    }
}

# 缓存目录
CACHE_DIR = os.path.join(PROJECT_ROOT, ".ekv_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# 检索关键词映射（针对不同 claim 类型）
CLAIM_KEYWORDS = {
    "hemisphere": ["侧别", "偏侧", "左侧", "右侧", "半球", "hemisphere", "lateralization"],
    "core_volume_ml": ["核心梗死", "梗死核心", "核心体积", "core infarct", "core volume", "梗死体积"],
    "penumbra_volume_ml": ["半暗带", "缺血半暗带", "penumbra", "ischemic penumbra", "半暗带体积"],
    "mismatch_ratio": ["不匹配", "mismatch", "不匹配比", "mismatch ratio", "灌注不匹配"],
    "significant_mismatch_present": ["显著不匹配", "明显不匹配", "significant mismatch", "明显灌注不匹配"],
    "treatment_window_hint": ["时间窗", "治疗时间窗", "time window", "治疗窗", "发病时间", "onset to treatment"]
}

class PDFRetrievalError(Exception):
    """PDF 检索相关错误"""
    pass

class DocumentIndex:
    """文档索引类，管理 PDF 文档的文本提取和检索"""
    
    def __init__(self, use_cache=True):
        self.use_cache = use_cache
        self.documents = {}
        self.index = {}  # 关键词到文档片段的映射
        self._load_documents()
    
    def _get_cache_key(self, doc_id: str) -> str:
        """生成缓存键"""
        filepath = os.path.join(EKV_DOCS_DIR, DOCUMENTS[doc_id]["filename"])
        if not os.path.exists(filepath):
            return None
        
        # 使用文件修改时间和大小生成缓存键
        stat = os.stat(filepath)
        key_data = f"{doc_id}_{stat.st_mtime}_{stat.st_size}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _load_document_text(self, doc_id: str) -> List[Dict[str, Any]]:
        """加载文档文本（从缓存或重新提取）"""
        cache_key = self._get_cache_key(doc_id)
        cache_file = os.path.join(CACHE_DIR, f"{doc_id}_{cache_key}.json") if cache_key else None
        
        # 尝试从缓存加载
        if self.use_cache and cache_file and os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.warning(f"加载缓存失败 {cache_file}: {e}")
        
        # 提取文本
        chunks = self._extract_pdf_text(doc_id)
        
        # 保存到缓存
        if self.use_cache and cache_file:
            try:
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(chunks, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logging.warning(f"保存缓存失败 {cache_file}: {e}")
        
        return chunks
    
    def _extract_pdf_text(self, doc_id: str) -> List[Dict[str, Any]]:
        """提取 PDF 文本"""
        if not PDF_AVAILABLE:
            logging.warning("PDF 处理库不可用，返回空文本")
            return []
        
        doc_info = DOCUMENTS[doc_id]
        filepath = os.path.join(EKV_DOCS_DIR, doc_info["filename"])
        
        if not os.path.exists(filepath):
            logging.error(f"PDF 文件不存在: {filepath}")
            return []
        
        try:
            doc = fitz.open(filepath)
            chunks = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                
                if text.strip():
                    # 改进的段落分割：处理多种换行情况
                    # 先按换行分割，然后合并连续的短行
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    
                    # 合并段落
                    paragraphs = []
                    current_para = []
                    
                    for line in lines:
                        # 如果行以句号、问号、感叹号结尾，或者行很短，可能是段落结束
                        if line.endswith(('。', '？', '！', '.', '?', '!')) or len(line) < 20:
                            current_para.append(line)
                            if current_para:
                                para_text = ' '.join(current_para)
                                if len(para_text) > 20:  # 降低长度阈值
                                    paragraphs.append(para_text)
                                current_para = []
                        else:
                            current_para.append(line)
                    
                    # 处理最后一段
                    if current_para:
                        para_text = ' '.join(current_para)
                        if len(para_text) > 20:
                            paragraphs.append(para_text)
                    
                    # 如果没有通过上述方法找到段落，回退到原始方法
                    if not paragraphs:
                        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
                    
                    for para in paragraphs:
                        if len(para) > 20:  # 降低长度阈值
                            chunks.append({
                                "doc_id": doc_id,
                                "doc_name": doc_info["name"],
                                "short_name": doc_info["short_name"],
                                "page": page_num + 1,
                                "text": para,
                                "keywords": self._extract_keywords(para)
                            })
            
            doc.close()
            logging.info(f"提取文档 {doc_id}: {len(chunks)} 个文本块")
            return chunks
            
        except Exception as e:
            logging.error(f"提取 PDF 文本失败 {filepath}: {e}")
            return []
    
    def _extract_keywords(self, text: str) -> List[str]:
        """从文本中提取关键词"""
        # 简单的关键词提取：查找医学术语和数字
        keywords = []
        
        # 医学术语模式
        medical_terms = [
            r'核心梗死', r'半暗带', r'不匹配', r'时间窗', r'血管内治疗',
            r'机械取栓', r'静脉溶栓', r'NIHSS', r'CTP', r'CTA', r'NCCT',
            r'灌注', r'缺血', r'卒中', r'脑梗死'
        ]
        
        for term in medical_terms:
            if re.search(term, text):
                keywords.append(term)
        
        # 数字模式（体积、比例等）
        volume_patterns = [
            r'(\d+\.?\d*)\s*ml',  # 体积
            r'(\d+\.?\d*)\s*%',   # 百分比
            r'比值\s*(\d+\.?\d*)', # 比值
            r'比例\s*(\d+\.?\d*:\d+\.?\d*)'  # 比例
        ]
        
        for pattern in volume_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                keywords.append(f"数值:{match}")
        
        return list(set(keywords))
    
    def _load_documents(self):
        """加载所有文档"""
        for doc_id in DOCUMENTS:
            chunks = self._load_document_text(doc_id)
            self.documents[doc_id] = chunks
            
            # 构建索引
            for chunk in chunks:
                for keyword in chunk.get("keywords", []):
                    if keyword not in self.index:
                        self.index[keyword] = []
                    self.index[keyword].append(chunk)
    
    def search(self, query: str, claim_type: str = None, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        搜索相关文本块
        
        Args:
            query: 查询文本
            claim_type: claim 类型（用于选择相关关键词）
            top_k: 返回结果数量
            
        Returns:
            相关文本块列表，包含引用信息
        """
        # 如果指定了 claim_type，使用相关的关键词
        search_terms = []
        if claim_type and claim_type in CLAIM_KEYWORDS:
            search_terms.extend(CLAIM_KEYWORDS[claim_type])
        
        # 从查询中提取关键词
        query_terms = re.findall(r'[\u4e00-\u9fff]+|\w+', query.lower())
        search_terms.extend(query_terms)
        
        # 去重
        search_terms = list(set(search_terms))
        
        # 收集相关文本块
        candidates = []
        seen = set()
        
        for term in search_terms:
            if term in self.index:
                for chunk in self.index[term]:
                    chunk_key = f"{chunk['doc_id']}_{chunk['page']}_{hash(chunk['text'][:50])}"
                    if chunk_key not in seen:
                        seen.add(chunk_key)
                        
                        # 计算简单相关性分数
                        score = 0
                        # 关键词匹配
                        for st in search_terms:
                            if st in chunk['text'].lower():
                                score += 2
                            if st in ' '.join(chunk.get('keywords', [])).lower():
                                score += 1
                        
                        candidates.append({
                            **chunk,
                            "score": score,
                            "matched_terms": [st for st in search_terms if st in chunk['text'].lower()]
                        })
        
        # 按分数排序并返回 top_k
        candidates.sort(key=lambda x: x['score'], reverse=True)
        return candidates[:top_k]
    
    def get_citation(self, chunk: Dict[str, Any]) -> str:
        """生成引用字符串"""
        return f"{chunk['short_name']} 第{chunk['page']}页"

# 全局索引实例
_global_index = None

def get_global_index() -> DocumentIndex:
    """获取全局文档索引实例（单例模式）"""
    global _global_index
    if _global_index is None:
        _global_index = DocumentIndex(use_cache=True)
    return _global_index

def query_guideline_kb(claim_text: str, claim_type: str = None) -> List[Dict[str, Any]]:
    """
    查询指南知识库（替代原来的占位函数）
    
    Args:
        claim_text: 需要验证的声明文本
        claim_type: claim 类型（如 "core_volume_ml"）
        
    Returns:
        相关证据列表，每个包含文本和引用信息
    """
    try:
        index = get_global_index()
        results = index.search(claim_text, claim_type, top_k=2)
        
        # 格式化结果
        evidence_list = []
        for result in results:
            evidence_list.append({
                "text": result["text"],
                "citation": index.get_citation(result),
                "doc_name": result["doc_name"],
                "page": result["page"],
                "score": result["score"],
                "matched_terms": result.get("matched_terms", [])
            })
        
        return evidence_list
        
    except Exception as e:
        logging.error(f"查询指南知识库失败: {e}")
        # 返回空结果而不是失败
        return []

def initialize_ekv_retrieval():
    """初始化 EKV 检索模块（在应用启动时调用）"""
    try:
        index = get_global_index()
        total_chunks = sum(len(chunks) for chunks in index.documents.values())
        logging.info(f"EKV 检索模块初始化完成，加载 {total_chunks} 个文本块")
        return True
    except Exception as e:
        logging.error(f"EKV 检索模块初始化失败: {e}")
        return False

# 测试函数
if __name__ == "__main__":
    # 简单测试
    import sys
    logging.basicConfig(level=logging.INFO)
    
    print("测试 EKV 检索模块...")
    
    # 初始化
    success = initialize_ekv_retrieval()
    print(f"初始化: {'成功' if success else '失败'}")
    
    if success:
        # 测试查询
        test_queries = [
            ("核心梗死体积大于50ml", "core_volume_ml"),
            ("半暗带体积", "penumbra_volume_ml"),
            ("不匹配比值", "mismatch_ratio"),
        ]
        
        for query, claim_type in test_queries:
            print(f"\n查询: {query} (类型: {claim_type})")
            results = query_guideline_kb(query, claim_type)
            
            if results:
                for i, result in enumerate(results):
                    print(f"  结果 {i+1}: {result['citation']}")
                    print(f"      文本: {result['text'][:100]}...")
                    print(f"      分数: {result['score']}")
            else:
                print("  无相关结果")