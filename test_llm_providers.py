#!/usr/bin/env python3
"""
测试LLM提供商配置
Test LLM Provider Configuration
"""
import os
from dotenv import load_dotenv
from src.config import Config
from src.llm_providers import get_llm_provider

# 加载环境变量
load_dotenv()

def test_provider_config():
    """测试provider配置是否正确"""
    print("=" * 60)
    print("测试LLM提供商配置 / Testing LLM Provider Configuration")
    print("=" * 60)
    
    # 加载配置
    try:
        config = Config()
        print("\n✅ 配置文件加载成功 / Config file loaded successfully")
    except Exception as e:
        print(f"\n❌ 配置文件加载失败 / Config loading failed: {e}")
        return False
    
    # 检查provider设置
    provider_name = config.llm_provider
    print(f"\n📋 当前Provider / Current Provider: {provider_name}")
    
    if config.llm_model:
        print(f"📋 指定模型 / Specified Model: {config.llm_model}")
    else:
        print(f"📋 使用默认模型 / Using default model")
    
    # 检查API密钥
    api_key = config.llm_api_key
    if api_key:
        masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        print(f"✅ API密钥已配置 / API Key configured: {masked_key}")
    else:
        print(f"❌ API密钥未配置 / API Key not configured")
        if provider_name == "claude":
            print(f"   请设置 ANTHROPIC_API_KEY / Please set ANTHROPIC_API_KEY")
        elif provider_name == "deepseek":
            print(f"   请设置 DEEPSEEK_API_KEY / Please set DEEPSEEK_API_KEY")
        return False
    
    # 尝试初始化provider
    print(f"\n🔧 正在初始化 {provider_name} provider...")
    try:
        provider = get_llm_provider(
            provider_name=provider_name,
            api_key=api_key,
            model=config.llm_model
        )
        print(f"✅ Provider初始化成功 / Provider initialized successfully")
        print(f"   Provider名称 / Name: {provider.provider_name}")
        print(f"   使用模型 / Model: {provider.model}")
    except Exception as e:
        print(f"❌ Provider初始化失败 / Initialization failed: {e}")
        return False
    
    # 测试简单生成
    print(f"\n🧪 测试基础生成功能 / Testing basic generation...")
    try:
        test_message = [
            {"role": "user", "content": "请用一句话介绍AI新闻机器人。/ Introduce AI news bot in one sentence."}
        ]
        response = provider.generate(messages=test_message, max_tokens=100)
        print(f"✅ 生成测试成功 / Generation test successful")
        print(f"\n回复预览 / Response Preview:")
        print(f"   {response[:200]}...")
    except Exception as e:
        print(f"❌ 生成测试失败 / Generation test failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！/ All tests passed!")
    print("=" * 60)
    return True


def show_quick_switch_guide():
    """显示快速切换指南"""
    print("\n" + "=" * 60)
    print("快速切换指南 / Quick Switch Guide")
    print("=" * 60)
    
    print("\n📝 方法1: 修改 config.yaml / Method 1: Edit config.yaml")
    print("""
llm:
  provider: deepseek  # 或 claude / or claude
  # model: deepseek-chat  # 可选 / optional
""")
    
    print("\n📝 方法2: 设置环境变量 / Method 2: Set environment variables")
    print("""
# .env 文件
LLM_PROVIDER=deepseek
LLM_MODEL=deepseek-chat  # 可选 / optional
DEEPSEEK_API_KEY=sk-xxx...
""")
    
    print("\n📖 详细文档 / Detailed Documentation:")
    print("   查看 MULTI_LLM_GUIDE.md / See MULTI_LLM_GUIDE.md")
    print("=" * 60)


if __name__ == "__main__":
    try:
        success = test_provider_config()
        
        if success:
            show_quick_switch_guide()
        else:
            print("\n⚠️  配置有问题，请检查上面的错误信息")
            print("   Configuration issues detected, please check errors above")
            show_quick_switch_guide()
            exit(1)
            
    except KeyboardInterrupt:
        print("\n\n测试被中断 / Test interrupted")
        exit(130)
    except Exception as e:
        print(f"\n❌ 测试出错 / Test error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
