# 用户数据库系统

本目录包含SoDesign.AI WebUI的用户数据库系统，用于存储用户信息和会话数据。

## 数据库结构

数据库文件: `user.db` (SQLite3)

### 表结构

#### users 表 - 用户数据
- `id`: 用户ID (主键)
- `username`: 用户名
- `account`: 账号（登录名）
- `password`: 密码（哈希值）
- `email`: 邮箱
- `points`: 积分
- `created_at`: 创建时间
- `last_login`: 最后登录时间

#### sessions 表 - 会话数据
- `token`: 会话令牌 (主键)
- `user_id`: 用户ID (外键)
- `created_at`: 创建时间
- `expires_at`: 过期时间

## 工具说明

本目录包含以下工具文件：

1. **init_db.py**: 初始化数据库，创建表结构
2. **db_utils.py**: 数据库操作函数库
3. **user_mgmt.py**: 用户管理命令行工具

## 使用方法

### 数据库初始化

初次使用时，需要初始化数据库：

```bash
python database/init_db.py
```

这将创建数据库文件和表结构，并添加默认管理员用户。

### 用户管理

用户管理工具提供以下命令：

1. **列出所有用户**:

```bash
python database/user_mgmt.py list
```

2. **添加新用户**:

```bash
python database/user_mgmt.py add --username "用户名" --account "账号" --password "密码" --email "邮箱" --points 100
```

3. **更新用户积分**:

```bash
python database/user_mgmt.py points --user-id 1 --delta 50
```

4. **清理过期会话**:

```bash
python database/user_mgmt.py clean
```

## 与WebUI集成

该数据库系统已与WebUI的认证系统集成。用户登录后，会在数据库中创建会话记录。

- 用户可以通过`/login`页面登录
- 用户信息可通过`/user_info`API获取
- 退出登录通过`/logout`路径实现

## 默认用户

系统初始化时会创建一个默认管理员用户：

- 用户名: 管理员
- 账号: admin
- 密码: 123456
 