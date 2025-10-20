#!/usr/bin/env python3
"""
ComfyUI 学习进度跟踪器
帮助跟踪学习进度，记录学习心得，管理学习任务
"""

import json
import os
import datetime
from pathlib import Path
from typing import Dict, List, Optional
import argparse

class LearningTracker:
    def __init__(self, data_file="学习进度.json"):
        self.data_file = Path(data_file)
        self.data = self.load_data()
    
    def load_data(self) -> Dict:
        """加载学习数据"""
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载数据失败: {e}")
                return self.create_default_data()
        else:
            return self.create_default_data()
    
    def create_default_data(self) -> Dict:
        """创建默认数据结构"""
        return {
            "学习阶段": {
                "第一阶段_基础架构": {
                    "状态": "进行中",
                    "开始时间": datetime.datetime.now().isoformat(),
                    "完成时间": None,
                    "进度": 0,
                    "任务": {
                        "理解main.py启动流程": {"状态": "未开始", "完成时间": None, "心得": ""},
                        "掌握server.py架构": {"状态": "未开始", "完成时间": None, "心得": ""},
                        "熟悉execution.py机制": {"状态": "未开始", "完成时间": None, "心得": ""},
                        "了解nodes.py管理": {"状态": "未开始", "完成时间": None, "心得": ""},
                        "修改基本配置参数": {"状态": "未开始", "完成时间": None, "心得": ""},
                        "理解日志系统": {"状态": "未开始", "完成时间": None, "心得": ""}
                    }
                },
                "第二阶段_节点系统": {
                    "状态": "未开始",
                    "开始时间": None,
                    "完成时间": None,
                    "进度": 0,
                    "任务": {}
                },
                "第三阶段_AI模型": {
                    "状态": "未开始",
                    "开始时间": None,
                    "完成时间": None,
                    "进度": 0,
                    "任务": {}
                },
                "第四阶段_高级功能": {
                    "状态": "未开始",
                    "开始时间": None,
                    "完成时间": None,
                    "进度": 0,
                    "任务": {}
                }
            },
            "学习记录": [],
            "代码片段": [],
            "问题记录": [],
            "学习统计": {
                "总学习时间": 0,
                "完成任务数": 0,
                "解决问题数": 0,
                "代码片段数": 0
            }
        }
    
    def save_data(self):
        """保存学习数据"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            print(f"数据已保存到: {self.data_file}")
        except Exception as e:
            print(f"保存数据失败: {e}")
    
    def start_phase(self, phase_name: str):
        """开始学习阶段"""
        if phase_name in self.data["学习阶段"]:
            phase = self.data["学习阶段"][phase_name]
            if phase["状态"] == "未开始":
                phase["状态"] = "进行中"
                phase["开始时间"] = datetime.datetime.now().isoformat()
                print(f"开始学习阶段: {phase_name}")
                self.save_data()
            else:
                print(f"阶段 {phase_name} 已经开始了")
        else:
            print(f"未知的学习阶段: {phase_name}")
    
    def complete_task(self, phase_name: str, task_name: str, notes: str = ""):
        """完成任务"""
        if phase_name in self.data["学习阶段"]:
            phase = self.data["学习阶段"][phase_name]
            if task_name in phase["任务"]:
                task = phase["任务"][task_name]
                task["状态"] = "已完成"
                task["完成时间"] = datetime.datetime.now().isoformat()
                if notes:
                    task["心得"] = notes
                
                # 更新阶段进度
                completed_tasks = sum(1 for t in phase["任务"].values() if t["状态"] == "已完成")
                total_tasks = len(phase["任务"])
                phase["进度"] = int((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0
                
                # 更新统计
                self.data["学习统计"]["完成任务数"] += 1
                
                print(f"任务完成: {phase_name} - {task_name}")
                print(f"阶段进度: {phase['进度']}%")
                
                # 检查阶段是否完成
                if phase["进度"] == 100:
                    phase["状态"] = "已完成"
                    phase["完成时间"] = datetime.datetime.now().isoformat()
                    print(f"🎉 阶段 {phase_name} 已完成！")
                
                self.save_data()
            else:
                print(f"任务 {task_name} 不存在于阶段 {phase_name}")
        else:
            print(f"阶段 {phase_name} 不存在")
    
    def add_learning_record(self, title: str, content: str, phase: str = ""):
        """添加学习记录"""
        record = {
            "标题": title,
            "内容": content,
            "阶段": phase,
            "时间": datetime.datetime.now().isoformat()
        }
        self.data["学习记录"].append(record)
        print(f"学习记录已添加: {title}")
        self.save_data()
    
    def add_code_snippet(self, name: str, code: str, description: str = "", phase: str = ""):
        """添加代码片段"""
        snippet = {
            "名称": name,
            "代码": code,
            "描述": description,
            "阶段": phase,
            "时间": datetime.datetime.now().isoformat()
        }
        self.data["代码片段"].append(snippet)
        self.data["学习统计"]["代码片段数"] += 1
        print(f"代码片段已添加: {name}")
        self.save_data()
    
    def add_problem(self, problem: str, solution: str = "", phase: str = ""):
        """添加问题记录"""
        issue = {
            "问题": problem,
            "解决方案": solution,
            "阶段": phase,
            "时间": datetime.datetime.now().isoformat(),
            "状态": "已解决" if solution else "待解决"
        }
        self.data["问题记录"].append(issue)
        if solution:
            self.data["学习统计"]["解决问题数"] += 1
        print(f"问题记录已添加: {problem[:50]}...")
        self.save_data()
    
    def get_progress_report(self):
        """获取进度报告"""
        report = []
        report.append("=== ComfyUI 学习进度报告 ===\n")
        
        for phase_name, phase_data in self.data["学习阶段"].items():
            report.append(f"📚 {phase_name}")
            report.append(f"   状态: {phase_data['状态']}")
            report.append(f"   进度: {phase_data['进度']}%")
            
            if phase_data['开始时间']:
                start_time = datetime.datetime.fromisoformat(phase_data['开始时间'])
                report.append(f"   开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if phase_data['完成时间']:
                complete_time = datetime.datetime.fromisoformat(phase_data['完成时间'])
                report.append(f"   完成时间: {complete_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 任务详情
            if phase_data['任务']:
                report.append("   任务列表:")
                for task_name, task_data in phase_data['任务'].items():
                    status_icon = "✅" if task_data['状态'] == "已完成" else "⏳"
                    report.append(f"     {status_icon} {task_name}")
                    if task_data['心得']:
                        report.append(f"        💭 {task_data['心得']}")
            
            report.append("")
        
        # 学习统计
        stats = self.data["学习统计"]
        report.append("📊 学习统计")
        report.append(f"   完成任务数: {stats['完成任务数']}")
        report.append(f"   解决问题数: {stats['解决问题数']}")
        report.append(f"   代码片段数: {stats['代码片段数']}")
        report.append("")
        
        return "\n".join(report)
    
    def get_phase_tasks(self, phase_name: str):
        """获取阶段任务列表"""
        if phase_name in self.data["学习阶段"]:
            phase = self.data["学习阶段"][phase_name]
            tasks = []
            for task_name, task_data in phase["任务"].items():
                tasks.append({
                    "任务": task_name,
                    "状态": task_data["状态"],
                    "完成时间": task_data["完成时间"],
                    "心得": task_data["心得"]
                })
            return tasks
        return []
    
    def search_records(self, keyword: str):
        """搜索学习记录"""
        results = []
        keyword = keyword.lower()
        
        for record in self.data["学习记录"]:
            if keyword in record["标题"].lower() or keyword in record["内容"].lower():
                results.append(record)
        
        for snippet in self.data["代码片段"]:
            if keyword in snippet["名称"].lower() or keyword in snippet["描述"].lower():
                results.append(snippet)
        
        for problem in self.data["问题记录"]:
            if keyword in problem["问题"].lower() or keyword in problem["解决方案"].lower():
                results.append(problem)
        
        return results

def main():
    parser = argparse.ArgumentParser(description='ComfyUI 学习进度跟踪器')
    parser.add_argument('--start-phase', help='开始学习阶段')
    parser.add_argument('--complete-task', nargs=2, metavar=('PHASE', 'TASK'), help='完成任务')
    parser.add_argument('--add-record', nargs=2, metavar=('TITLE', 'CONTENT'), help='添加学习记录')
    parser.add_argument('--add-snippet', nargs=3, metavar=('NAME', 'CODE', 'DESCRIPTION'), help='添加代码片段')
    parser.add_argument('--add-problem', nargs=2, metavar=('PROBLEM', 'SOLUTION'), help='添加问题记录')
    parser.add_argument('--report', action='store_true', help='显示进度报告')
    parser.add_argument('--search', help='搜索记录')
    parser.add_argument('--tasks', help='显示阶段任务')
    
    args = parser.parse_args()
    
    tracker = LearningTracker()
    
    if args.start_phase:
        tracker.start_phase(args.start_phase)
    elif args.complete_task:
        phase, task = args.complete_task
        notes = input("请输入学习心得（可选）: ")
        tracker.complete_task(phase, task, notes)
    elif args.add_record:
        title, content = args.add_record
        phase = input("请输入学习阶段（可选）: ")
        tracker.add_learning_record(title, content, phase)
    elif args.add_snippet:
        name, code, description = args.add_snippet
        phase = input("请输入学习阶段（可选）: ")
        tracker.add_code_snippet(name, code, description, phase)
    elif args.add_problem:
        problem, solution = args.add_problem
        phase = input("请输入学习阶段（可选）: ")
        tracker.add_problem(problem, solution, phase)
    elif args.report:
        print(tracker.get_progress_report())
    elif args.search:
        results = tracker.search_records(args.search)
        if results:
            print(f"找到 {len(results)} 条相关记录:")
            for i, result in enumerate(results, 1):
                print(f"{i}. {result.get('标题', result.get('名称', result.get('问题', 'Unknown')))}")
        else:
            print("没有找到相关记录")
    elif args.tasks:
        tasks = tracker.get_phase_tasks(args.tasks)
        if tasks:
            print(f"=== {args.tasks} 任务列表 ===")
            for task in tasks:
                status_icon = "✅" if task["状态"] == "已完成" else "⏳"
                print(f"{status_icon} {task['任务']}")
                if task["心得"]:
                    print(f"   💭 {task['心得']}")
        else:
            print(f"阶段 {args.tasks} 没有任务或不存在")
    else:
        print("请指定一个操作，使用 --help 查看帮助信息")

if __name__ == "__main__":
    main()
