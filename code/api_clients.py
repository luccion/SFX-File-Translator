import os
import json
import requests
import time
from openai import OpenAI
from dotenv import load_dotenv

class APIClient:
    """统一的API客户端基类"""
    
    def __init__(self, api_url, api_key, model, temperature=1.3):
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
    
    def call_api(self, messages, max_retries=3):
        """调用API的抽象方法，子类需要实现"""
        raise NotImplementedError
    
    def get_name(self):
        """获取服务商名称"""
        return self.__class__.__name__

class OpenAIClient(APIClient):
    """OpenAI兼容的API客户端（支持通义千问、硅基流动等）"""
    
    def __init__(self, api_url, api_key, model, temperature=1.3):
        super().__init__(api_url, api_key, model, temperature)
        self.client = OpenAI(
            api_key=api_key,
            base_url=api_url,
        )
    
    def get_name(self):
        """获取服务商名称"""
        return "OpenAI兼容服务"
    
    def call_api(self, messages, max_retries=3):
        for attempt in range(max_retries):
            try:
                completion = self.client.chat.completions.create(
                    model=self.model,
                    temperature=self.temperature,
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

class SiliconFlowClient(APIClient):
    """硅基流动API客户端"""
    
    def __init__(self, api_url, api_key, model, temperature=1.3):
        super().__init__(api_url, api_key, model, temperature)
    
    def get_name(self):
        """获取服务商名称"""
        return "硅基流动"
    
    def call_api(self, messages, max_retries=3):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature
        }
        
        for attempt in range(max_retries):
            try:
                response = requests.post(self.api_url, headers=headers, json=data)
                response.raise_for_status()
                result = response.json()
                
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"]
                    return json.loads(content)
                else:
                    raise Exception(f"API返回格式异常: {result}")
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                time.sleep(2 + attempt * 2)
        
        raise Exception("所有重试都失败")

class APIClientFactory:
    """API客户端工厂类"""
    
    @staticmethod
    def create_client(provider, api_url, api_key, model, temperature=1.3):
        """根据服务商类型创建对应的客户端"""
        if provider.lower() == 'openai':
            return OpenAIClient(api_url, api_key, model, temperature)
        elif provider.lower() == 'siliconflow':
            return SiliconFlowClient(api_url, api_key, model, temperature)
        else:
            raise ValueError(f"不支持的服务商: {provider}")
    
    @staticmethod
    def get_available_providers():
        """获取可用的服务商列表"""
        return ['openai', 'siliconflow']

def load_provider_config(provider_name):
    """从环境变量加载指定服务商的配置"""
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
    
    if provider_name.lower() == 'openai':
        return {
            'api_url': os.getenv("SFX_API_URL"),
            'api_key': os.getenv("SFX_API_KEY"),
            'model': os.getenv("SFX_MODEL"),
            'temperature': float(os.getenv("SFX_TEMPERATURE", "1.3"))
        }
    elif provider_name.lower() == 'siliconflow':
        return {
            'api_url': os.getenv("SFX_FALLBACK_API_URL", "https://api.siliconflow.cn/v1/chat/completions"),
            'api_key': os.getenv("SFX_FALLBACK_API_KEY"),
            'model': os.getenv("SFX_FALLBACK_MODEL", "Qwen/Qwen2.5-7B-Instruct"),
            'temperature': float(os.getenv("SFX_TEMPERATURE", "1.3"))
        }
    else:
        raise ValueError(f"不支持的服务商: {provider_name}")

def get_client_by_provider(provider_name):
    """根据服务商名称获取配置好的客户端"""
    config = load_provider_config(provider_name)
    return APIClientFactory.create_client(
        provider_name,
        config['api_url'],
        config['api_key'],
        config['model'],
        config['temperature']
    )