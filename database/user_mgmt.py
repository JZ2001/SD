#!/usr/bin/env python
# 用户管理工具

import os
import sys
import argparse
import sqlite3
from pathlib import Path

# 添加当前目录的父目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import db_utils

def list_users():
    """列出所有用户"""
    users = db_utils.get_all_users()
    
    if not users:
        print("没有找到任何用户。")
        return
    
    print(f"共找到 {len(users)} 个用户:")
    print("-" * 80)
    print(f"{'ID':<4} | {'用户名':<10} | {'账号':<15} | {'邮箱':<20} | {'积分':<6} | {'注册时间':<20} | {'最后登录':<20}")
    print("-" * 80)
    
    for user in users:
        print(f"{user['id']:<4} | {user['username']:<10} | {user['account']:<15} | {user['email'] or '无':<20} | {user['points']:<6} | {user['created_at']:<20} | {user['last_login'] or '从未登录':<20}")

def add_user(username, account, password, email="", points=0):
    """添加新用户"""
    user_id = db_utils.add_user(username, account, password, email, points)
    
    if user_id:
        print(f"成功添加用户: {username} (ID: {user_id})")
    else:
        print(f"添加用户失败：用户名或账号可能已存在")

def update_points(user_id, points_delta):
    """更新用户积分"""
    success = db_utils.update_user_points(user_id, points_delta)
    
    if success:
        print(f"成功更新用户(ID: {user_id})积分: {'+' if points_delta >= 0 else ''}{points_delta}")
    else:
        print(f"更新积分失败：用户ID可能不存在")

def clean_sessions():
    """清理过期会话"""
    deleted_count = db_utils.clean_expired_sessions()
    print(f"已清理 {deleted_count} 个过期会话")

def main():
    parser = argparse.ArgumentParser(description='用户数据库管理工具')
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # 列出用户命令
    list_parser = subparsers.add_parser('list', help='列出所有用户')
    
    # 添加用户命令
    add_parser = subparsers.add_parser('add', help='添加新用户')
    add_parser.add_argument('--username', '-u', required=True, help='用户名')
    add_parser.add_argument('--account', '-a', required=True, help='账号')
    add_parser.add_argument('--password', '-p', required=True, help='密码')
    add_parser.add_argument('--email', '-e', default='', help='邮箱')
    add_parser.add_argument('--points', '-pt', type=int, default=0, help='积分')
    
    # 更新积分命令
    points_parser = subparsers.add_parser('points', help='更新用户积分')
    points_parser.add_argument('--user-id', '-id', type=int, required=True, help='用户ID')
    points_parser.add_argument('--delta', '-d', type=int, required=True, help='积分变化量（可为负）')
    
    # 清理会话命令
    clean_parser = subparsers.add_parser('clean', help='清理过期会话')
    
    args = parser.parse_args()
    
    if args.command == 'list':
        list_users()
    elif args.command == 'add':
        add_user(args.username, args.account, args.password, args.email, args.points)
    elif args.command == 'points':
        update_points(args.user_id, args.delta)
    elif args.command == 'clean':
        clean_sessions()
    else:
        parser.print_help()

if __name__ == '__main__':
    main() 