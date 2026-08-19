# WAVE-FIXTURE AI Backend

波峰焊治具智能设计系统 - 后端 API

## 技术栈

- **FastAPI 0.104** - Web 框架
- **SQLAlchemy 2.0** - ORM
- **SQLite/PostgreSQL** - 数据库
- **gerbonara** - Gerber 解析
- **Shapely 2.0** - 几何计算
- **ezdxf** - DXF 生成
- **Celery + Redis** - 异步任务队列（待实现）

## 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件根据需要修改配置
```

### 3. 启动服务

```bash
# 开发模式（自动重载）
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 或直接运行
python app/main.py
```

### 4. 访问 API 文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 端点

### 核心端点

- `POST /api/jobs` - 上传 Gerber ZIP 创建任务
- `GET /api/jobs/{jobId}` - 查询任务状态
- `GET /api/jobs/{jobId}/analysis` - 获取 PCB 分析
- `POST /api/jobs/{jobId}/layers/confirm` - 确认图层
- `PUT /api/jobs/{jobId}/parameters` - 更新参数
- `POST /api/jobs/{jobId}/regenerate` - 重新生成
- `GET /api/jobs/{jobId}/result` - 获取结果
- `GET /api/jobs/{jobId}/preview.svg` - 获取 SVG
- `GET /api/jobs/{jobId}/result.dxf` - 下载 DXF

## 项目结构

```
backend/
├── app/
│   ├── api/v1/          # API 路由
│   ├── core/            # 核心配置
│   ├── models/          # 数据模型
│   ├── services/        # 业务逻辑
│   │   ├── gerber/      # Gerber 处理
│   │   ├── fixture/     # 治具生成
│   │   └── exporters/   # 导出
│   ├── tasks/           # Celery 任务
│   ├── utils/           # 工具函数
│   └── main.py          # 应用入口
├── tests/               # 测试
├── uploads/             # 上传文件
├── outputs/             # 生成文件
└── requirements.txt
```

## 开发状态

### ✅ 已完成
- [x] FastAPI 项目架构
- [x] 数据库模型和 Schema
- [x] 核心 API 端点
- [x] 文件上传和存储
- [x] CORS 配置
- [x] API 文档

### 🚧 进行中
- [ ] Gerber 解析服务
- [ ] 治具生成算法
- [ ] SVG/DXF 导出
- [ ] Celery 异步任务

### 📋 待开发
- [ ] DRC 检查
- [ ] 单元测试
- [ ] 性能优化
- [ ] Docker 部署

## 前端对接

前端需要配置环境变量：

```env
VITE_USE_MOCK_API=false
VITE_API_BASE_URL=http://localhost:8000
```

## 测试

```bash
# 运行测试
pytest

# 带覆盖率
pytest --cov=app tests/
```

## License

MIT
