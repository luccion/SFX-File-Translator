import os
import json
import requests
import time
from openai import OpenAI
from dotenv import load_dotenv

class APIClient:
    """统一的API客户端基类"""
    
    def __init__(self, config):
        self.config = config
        self.api_url = config.get('api_url')
        self.api_key = config.get('api_key')
        self.model = config.get('model')
        self.name = config.get('name', 'Unknown')
        self.client_type = config.get('client_type', 'openai')
    
    def call_api(self, messages, max_retries=3):
        """调用API的抽象方法，子类需要实现"""
        raise NotImplementedError
    
    def get_name(self):
        """获取服务商名称"""
        return self.name

class OpenAIClient(APIClient):
    """OpenAI兼容的API客户端（支持通义千问、硅基流动等）"""
    
    def __init__(self, config):
        super().__init__(config)
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.api_url,
        )
    
    def call_api(self, messages, max_retries=3):
        for attempt in range(max_retries):
            try:
                completion = self.client.chat.completions.create(
                    model=self.model,
                    temperature=self.config.get('temperature', 1.3),
                    messages=messages,
                    response_format={"type": "json_object"}
                )
                
                result_json = json.loads(completion.choices[0].message.content)
                return result_json
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                time.sleep(2 + attempt * 2)
        
        raise Exception("所有重试都失败")
    
    def create_batch_request(self, requests_data, batch_description="SFX Translation Batch"):
        """创建批量请求（支持通义千问Batch API）"""
        try:
            # 检查是否支持批量API
            if "dashscope" in self.api_url.lower():
                return self._create_dashscope_batch(requests_data, batch_description)
            else:
                # 对于其他OpenAI兼容服务，使用常规批量处理
                return self._create_openai_batch(requests_data, batch_description)
        except Exception as e:
            print(f"创建批量请求失败: {e}")
            return None
    
    def _create_dashscope_batch(self, requests_data, batch_description):
        """创建通义千问批量请求"""
        try:
            # 准备批量请求数据
            batch_input = []
            for i, request in enumerate(requests_data):
                batch_input.append({
                    "custom_id": f"request-{i}",
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": self.model,
                        "messages": request["messages"],
                        "response_format": {"type": "json_object"},
                        "temperature": self.config.get('temperature', 1.3)
                    }
                })
            
            # 创建批量作业
            batch_job = self.client.batches.create(
                input_file_id=self._upload_batch_file(batch_input),
                endpoint="/v1/chat/completions",
                completion_window="24h",
                metadata={
                    "description": batch_description,
                    "created_by": "SFXRenamer"
                }
            )
            
            print(f"✓ 批量作业已创建: {batch_job.id}")
            return batch_job
            
        except Exception as e:
            print(f"创建通义千问批量请求失败: {e}")
            return None
    
    def _create_openai_batch(self, requests_data, batch_description):
        """创建OpenAI标准批量请求"""
        try:
            # 对于其他服务，可能需要不同的实现
            # 这里先返回None，表示不支持批量
            return None
        except Exception as e:
            print(f"创建OpenAI批量请求失败: {e}")
            return None
    
    def _upload_batch_file(self, batch_input):
        """上传批量请求文件"""
        import tempfile
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            for item in batch_input:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
            temp_file_path = f.name
        
        try:
            # 上传文件
            with open(temp_file_path, 'rb') as f:
                file_response = self.client.files.create(
                    file=f,
                    purpose="batch"
                )
            
            return file_response.id
        finally:
            # 清理临时文件
            os.unlink(temp_file_path)
    
    def get_batch_status(self, batch_id):
        """获取批量作业状态"""
        try:
            return self.client.batches.retrieve(batch_id)
        except Exception as e:
            print(f"获取批量作业状态失败: {e}")
            return None
    
    def get_batch_results(self, batch_id):
        """获取批量作业结果"""
        try:
            batch = self.client.batches.retrieve(batch_id)
            if batch.status == "completed" and batch.output_file_id:
                # 下载结果文件
                result_file = self.client.files.content(batch.output_file_id)
                results = []
                for line in result_file.text.strip().split('\n'):
                    if line:
                        results.append(json.loads(line))
                return results
            else:
                return None
        except Exception as e:
            print(f"获取批量作业结果失败: {e}")
            return None
    
    def supports_batch(self):
        """检查是否支持批量API"""
        return "dashscope" in self.api_url.lower()

class SiliconFlowClient(APIClient):
    """硅基流动API客户端（使用HTTP请求）"""
    
    def __init__(self, config):
        super().__init__(config)
    
    def call_api(self, messages, max_retries=3):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": self.config.get('temperature', 1.3)
        }
        
        for attempt in range(max_retries):
            try:
                response = requests.post(self.api_url, headers=headers, json=data)
                response.raise_for_status()
                result = response.json()
                
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"]
                    # 尝试解析JSON，如果失败则返回原始内容
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        # 如果不是JSON格式，尝试从文本中提取JSON
                        import re
                        json_match = re.search(r'\{.*\}', content, re.DOTALL)
                        if json_match:
                            return json.loads(json_match.group())
                        else:
                            raise Exception(f"无法解析响应内容为JSON: {content}")
                else:
                    raise Exception(f"API返回格式异常: {result}")
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                time.sleep(2 + attempt * 2)
        
        raise Exception("所有重试都失败")

class ProvidersConfig:
    """服务商配置管理类"""
    
    def __init__(self, config_file=None):
        if config_file is None:
            config_file = os.path.join(os.path.dirname(__file__), '..', 'config', 'providers.json')
        
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"配置文件不存在: {self.config_file}")
        except json.JSONDecodeError as e:
            raise ValueError(f"配置文件格式错误: {e}")
    
    def get_providers(self):
        """获取所有服务商配置"""
        return self.config.get('providers', {})
    
    def get_provider_config(self, provider_id, model_id=None):
        """获取指定服务商配置"""
        providers = self.get_providers()
        if provider_id not in providers:
            raise ValueError(f"未找到服务商: {provider_id}")
        
        provider_config = providers[provider_id].copy()
        common_settings = self.config.get('common_settings', {})
        
        # 合并通用设置
        for key, value in common_settings.items():
            if key not in provider_config:
                provider_config[key] = value
        
        # 设置模型
        if model_id:
            provider_config['model'] = model_id
        else:
            provider_config['model'] = provider_config.get('default_model', 
                                                          provider_config.get('models', [{}])[0].get('id', ''))
        
        return provider_config
    
    def get_provider_models(self, provider_id):
        """获取指定服务商的模型列表"""
        providers = self.get_providers()
        if provider_id not in providers:
            raise ValueError(f"未找到服务商: {provider_id}")
        
        return providers[provider_id].get('models', [])
    
    def get_default_provider(self):
        """获取默认服务商ID"""
        return self.config.get('default_provider', list(self.get_providers().keys())[0])
    
    def get_default_model(self, provider_id):
        """获取服务商的默认模型"""
        providers = self.get_providers()
        if provider_id not in providers:
            raise ValueError(f"未找到服务商: {provider_id}")
        
        provider = providers[provider_id]
        return provider.get('default_model', provider.get('models', [{}])[0].get('id', ''))
    
    def list_providers(self):
        """列出所有可用的服务商"""
        providers = self.get_providers()
        return [(pid, pconfig.get('name', pid)) for pid, pconfig in providers.items()]

class APIClientFactory:
    """API客户端工厂类"""
    
    @staticmethod
    def create_client(provider_config):
        """根据配置创建对应的客户端"""
        client_type = provider_config.get('client_type', 'openai')
        
        if client_type == 'openai':
            return OpenAIClient(provider_config)
        elif client_type == 'siliconflow':
            return SiliconFlowClient(provider_config)
        else:
            raise ValueError(f"不支持的客户端类型: {client_type}")
    
    @staticmethod
    def get_available_providers():
        """获取可用的服务商列表"""
        config = ProvidersConfig()
        return [pid for pid, _ in config.list_providers()]

def get_client_by_provider(provider_id, model_id=None):
    """根据服务商ID和模型ID获取配置好的客户端"""
    config = ProvidersConfig()
    provider_config = config.get_provider_config(provider_id, model_id)
    return APIClientFactory.create_client(provider_config)