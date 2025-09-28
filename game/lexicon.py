"""
动词词典模块

这个模块负责加载和管理西班牙语动词的变位数据
"""

import json
import os
from typing import List, Dict, Optional, Any


class VerbLexicon:
    """
    动词词典类，用于加载和查询西班牙语动词变位
    """
    
    def __init__(self):
        """初始化动词词典"""
        self.verbs: List[Dict[str, Any]] = []
        self._data_loaded = False
    
    def load(self) -> None:
        """
        从JSON文件加载动词数据
        
        Raises:
            FileNotFoundError: 如果找不到数据文件
            json.JSONDecodeError: 如果JSON格式错误
        """
        # 获取数据文件路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        data_file = os.path.join(os.path.dirname(current_dir), "data", "verbs.json")
        
        if not os.path.exists(data_file):
            raise FileNotFoundError(f"动词数据文件不存在: {data_file}")
        
        # 加载JSON数据
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 提取动词列表
        self.verbs = data.get("verbs", [])
        self._data_loaded = True
    
    def list_infinitives(self) -> List[str]:
        """
        获取所有动词原形的列表
        
        Returns:
            动词原形列表
        """
        if not self._data_loaded:
            self.load()
        
        return [verb.get("infinitive", "") for verb in self.verbs if verb.get("infinitive")]
    
    def get_present_form(self, infinitive: str, person: str) -> Optional[str]:
        """
        获取指定动词和人称的现在时变位
        
        Args:
            infinitive: 动词原形
            person: 人称（如"直陈式现在时+第一人称单数"）
            
        Returns:
            变位形式，如果找不到则返回None
        """
        if not self._data_loaded:
            self.load()
        
        # 查找指定的动词
        for verb in self.verbs:
            if verb.get("infinitive") == infinitive:
                present_forms = verb.get("present_indicative", {})
                return present_forms.get(person)
        
        return None
    
    def get_verb_data(self, infinitive: str) -> Optional[Dict[str, Any]]:
        """
        获取指定动词的完整数据
        
        Args:
            infinitive: 动词原形
            
        Returns:
            动词数据字典，如果找不到则返回None
        """
        if not self._data_loaded:
            self.load()
        
        for verb in self.verbs:
            if verb.get("infinitive") == infinitive:
                return verb
        
        return None
    
    def is_loaded(self) -> bool:
        """
        检查数据是否已加载
        
        Returns:
            如果数据已加载返回True，否则返回False
        """
        return self._data_loaded


