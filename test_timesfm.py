#!/usr/bin/env python3
"""
TimesFM 模型测试脚本
测试 TimesFM 2.5 模型的基本功能
"""

import numpy as np
import timesfm
import torch

def test_timesfm_basic():
    """测试 TimesFM 基本功能"""
    print("🚀 开始测试 TimesFM 2.5 模型...")
    
    try:
        # 检查 CUDA 是否可用
        print(f"CUDA 可用: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"CUDA 设备数量: {torch.cuda.device_count()}")
            print(f"当前 CUDA 设备: {torch.cuda.current_device()}")
        
        # 初始化模型
        print("\n📦 初始化 TimesFM 2.5 200M 模型...")
        model = timesfm.TimesFM_2p5_200M_torch()
        
        # 加载检查点
        print("📥 加载模型检查点...")
        model.load_checkpoint()
        
        # 编译模型
        print("⚙️ 编译模型...")
        model.compile(
            timesfm.ForecastConfig(
                max_context=1024,
                max_horizon=256,
                normalize_inputs=True,
                use_continuous_quantile_head=True,
                force_flip_invariance=True,
                infer_is_positive=True,
                fix_quantile_crossing=True,
            )
        )
        
        # 准备测试数据
        print("\n📊 准备测试数据...")
        test_inputs = [
            np.linspace(0, 1, 100),  # 线性增长
            np.sin(np.linspace(0, 20, 67)),  # 正弦波
            np.random.randn(50) * 0.1 + np.linspace(0, 1, 50),  # 带噪声的线性增长
        ]
        
        print(f"测试数据形状: {[arr.shape for arr in test_inputs]}")
        
        # 进行预测
        print("\n🔮 开始预测...")
        point_forecast, quantile_forecast = model.forecast(
            horizon=12,
            inputs=test_inputs,
        )
        
        print(f"✅ 预测完成!")
        print(f"点预测形状: {point_forecast.shape}")
        print(f"分位数预测形状: {quantile_forecast.shape}")
        
        # 显示预测结果
        print("\n📈 预测结果预览:")
        for i, (point_pred, quantile_pred) in enumerate(zip(point_forecast, quantile_forecast)):
            print(f"时间序列 {i+1}:")
            print(f"  点预测: {point_pred[:5]}... (前5个值)")
            print(f"  分位数预测 (均值): {quantile_pred[0, :5]}... (前5个值)")
            print(f"  分位数预测 (90%分位数): {quantile_pred[-1, :5]}... (前5个值)")
        
        print("\n🎉 TimesFM 模型测试成功完成!")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_simple_forecast():
    """测试简单预测功能"""
    print("\n🔬 测试简单预测功能...")
    
    try:
        # 创建简单的测试数据
        test_data = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        print(f"输入数据: {test_data}")
        
        # 初始化模型
        model = timesfm.TimesFM_2p5_200M_torch()
        model.load_checkpoint()
        
        # 使用默认配置
        model.compile()
        
        # 进行预测
        point_forecast, quantile_forecast = model.forecast(
            horizon=5,
            inputs=[test_data],
        )
        
        print(f"预测结果: {point_forecast[0]}")
        print("✅ 简单预测测试成功!")
        return True
        
    except Exception as e:
        print(f"❌ 简单预测测试失败: {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("TimesFM 2.5 模型测试")
    print("=" * 60)
    
    # 运行测试
    success1 = test_simple_forecast()
    success2 = test_timesfm_basic()
    
    print("\n" + "=" * 60)
    if success1 and success2:
        print("🎉 所有测试都通过了！TimesFM 模型配置成功！")
    else:
        print("⚠️ 部分测试失败，请检查配置。")
    print("=" * 60)
