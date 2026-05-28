# -*- coding: utf-8 -*-
"""
灵学 LumiLearn - 持续自动化任务
从当前时间运行到北京时间上午7点，每小时执行一次数据采集
"""
import os
import sys
import time
import json
import subprocess
from datetime import datetime, timedelta

LUMILEARN_DIR = r"e:\学习LLM\lumilearn"
SCRIPTS_DIR = os.path.join(LUMILEARN_DIR, "scripts")
MASTER_CSV = os.path.join(LUMILEARN_DIR, "lumilearn_master.csv")
TODAY = datetime.now().strftime("%Y-%m-%d")

# 目标结束时间：上午7点
END_HOUR = 7
INTERVAL_MINUTES = 60  # 每小时执行一次


def get_current_count():
    """获取当前数据量"""
    if os.path.exists(MASTER_CSV):
        with open(MASTER_CSV, "r", encoding="utf-8") as f:
            return sum(1 for _ in f) - 1
    return 0


def run_data_collection():
    """执行数据采集"""
    daily_auto = os.path.join(LUMILEARN_DIR, "lumilearn_daily_auto.py")
    if os.path.exists(daily_auto):
        try:
            result = subprocess.run(
                [sys.executable, daily_auto],
                cwd=LUMILEARN_DIR,
                capture_output=True,
                text=True,
                timeout=300
            )
            return result.returncode == 0
        except:
            return False
    return False


def main():
    print("=" * 70)
    print("灵学 LumiLearn - 持续自动化任务")
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"目标结束: 今日 {END_HOUR}:00 (北京时间)")
    print(f"执行间隔: 每 {INTERVAL_MINUTES} 分钟")
    print("=" * 70)
    
    # 计算结束时间
    now = datetime.now()
    end_time = now.replace(hour=END_HOUR, minute=0, second=0, microsecond=0)
    if end_time <= now:
        end_time += timedelta(days=1)
    
    total_seconds = (end_time - now).total_seconds()
    print(f"\n预计运行时长: {total_seconds/3600:.1f} 小时")
    
    initial_count = get_current_count()
    print(f"初始数据量: {initial_count} 条")
    
    cycle = 0
    total_added = 0
    
    while datetime.now() < end_time:
        cycle += 1
        now_str = datetime.now().strftime("%H:%M:%S")
        
        print(f"\n{'='*50}")
        print(f"[周期 {cycle}] {now_str}")
        print(f"{'='*50}")
        
        # 执行数据采集
        print("  执行数据采集...")
        success = run_data_collection()
        
        # 统计新增
        current_count = get_current_count()
        added = current_count - initial_count - total_added
        total_added = current_count - initial_count
        
        if success:
            print(f"  ✅ 采集完成，本周期新增: {added} 条")
        else:
            print(f"  ⚠️ 采集未产生新数据")
        
        print(f"  当前总量: {current_count} 条，累计新增: {total_added} 条")
        
        # 计算剩余时间
        remaining = (end_time - datetime.now()).total_seconds()
        if remaining <= 0:
            break
        
        print(f"  剩余时间: {remaining/3600:.1f} 小时")
        
        # 等待下一个周期
        if remaining > INTERVAL_MINUTES * 60:
            print(f"  等待 {INTERVAL_MINUTES} 分钟后执行下一周期...")
            time.sleep(INTERVAL_MINUTES * 60)
        else:
            print(f"  等待 {remaining/60:.0f} 分钟后结束...")
            time.sleep(remaining)
    
    # 最终报告
    final_count = get_current_count()
    
    print(f"\n{'='*70}")
    print("📊 持续自动化任务报告")
    print(f"{'='*70}")
    print(f"  开始时间:     {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  结束时间:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  执行周期:     {cycle} 次")
    print(f"  ─────────────────────────────")
    print(f"  初始数据:     {initial_count} 条")
    print(f"  最终数据:     {final_count} 条")
    print(f"  新增数据:     {total_added} 条")
    print(f"{'='*70}")
    print("✅ 持续自动化任务完成！")


if __name__ == "__main__":
    main()
