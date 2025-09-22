# Python编程教育系统

一个基于大模型RAG（检索增强生成）和Function Calling技术的Python编程教育系统，提供代码执行、知识问答、测验生成等功能，支持命令行和Gradio图形界面操作。

该系统专为Python编程学习者设计，能够提供实时代码执行环境、生成个性化测验题目、解释编程概念，并通过RAG技术提供基于知识库的精准回答。系统后端采用FastAPI构建，前端使用Gradio框架，提供直观易用的用户界面。

系统包含完善的API密钥保护机制，通过环境变量和专用配置文件隔离敏感信息，确保密钥安全。

## 系统架构

本系统采用模块化设计，主要包含以下几个核心模块：

1. **核心教育系统**：负责整体业务逻辑和功能集成
2. **LLM客户端**：与大语言模型交互的接口
3. **RAG管理器**：处理文档检索和增强生成
4. **代码执行器**：安全地执行用户提交的Python代码
5. **API服务器**：提供HTTP接口供前端或其他系统调用
6. **图形界面**：提供直观的GUI操作界面，适合非技术用户

## 项目结构

```
hku_capstone/
├── main.py              # 主入口文件
├── start_gui.py         # 前端启动脚本
├── requirements.txt     # 项目依赖
├── README.md            # 项目说明文档
├── config.yaml          # 配置文件
├── src/                 # 源代码目录
│   ├── __pycache__/     # 编译后的Python文件
│   └── education_system.py  # 教育系统核心实现
├── models/              # 模型存储目录
├── utils/               # 工具函数
│   ├── config.py        # 配置管理
│   ├── logger.py        # 日志工具
│   └── code_executor.py # 代码执行器
├── api/                 # API接口
│   ├── __pycache__/     # 编译后的Python文件
│   └── server.py        # FastAPI服务器实现
├── gui/                 # 图形用户界面
│   ├── README.md        # GUI使用说明
│   └── gradio_app.py    # Gradio GUI应用主程序
├── data/                # 数据存储目录
├── logs/                # 日志文件目录
└── verify_backend.py    # 后端服务验证脚本
```

## 功能特性

1. **代码执行**：安全地执行用户提交的Python代码并返回结果
2. **RAG增强**：基于知识库的检索增强生成，提供更准确的回答
3. **测验生成**：根据主题生成Python编程测验
4. **答案检查**：检查用户提交的答案是否正确并提供反馈
5. **概念解释**：解释Python编程中的各种概念，适应不同学习水平
6. **工具调用**：大模型可以自动调用系统提供的工具完成复杂任务
7. **图形界面**：提供直观的GUI操作界面，适合非技术用户

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置系统

#### API密钥保护机制

为了保护敏感的API密钥信息，系统采用了多层次的安全保护机制：

1. **环境变量优先级** - 系统会优先从环境变量中读取API密钥，避免在代码中硬编码
2. **专用配置文件** - 敏感信息存储在独立的`.env`文件中，该文件不应提交到代码仓库
3. **配置文件安全** - 即使在`config.yaml`中配置了API密钥，环境变量中的值仍会覆盖它

#### 配置步骤

1. **创建.env文件**

   在项目根目录创建一个`.env`文件，格式如下：
   ```env
   # .env 文件 - 存储敏感配置信息
   # 注意：此文件不应提交到代码仓库
   
   # 大语言模型API密钥
   LLM_API_KEY=your-api-key-here
   
   # 可以添加其他环境变量
   # LLM_MODEL_NAME=deepseek-chat
   # LLM_TEMPERATURE=0.7
   ```

2. **配置config.yaml**

   项目已包含`config.yaml`配置文件，主要用于非敏感配置：
   ```yaml
   llm:
     model_name: "deepseek-chat"
     api_base: "https://api.deepseek.com"
     temperature: 0.7
     max_tokens: 1000
   rag:
     vector_store_path: "./data/vector_store"
     chunk_size: 500
     chunk_overlap: 50
     embedding_model: "m3e-base"
   api_port: 8888
   debug: false
   data_dir: "./data"
   models_dir: "./models"
   allowed_functions:
   - execute_code
   - search_knowledge
   - generate_quiz
   - check_answer
   - explain_concept
   ```

   > 注意：由于系统会优先从环境变量读取API密钥，您可以在`config.yaml`中省略`api_key`字段，或仅保留占位符。

### 启动系统

#### 使用图形界面（推荐）

```bash
python start_gui.py
```

该脚本会自动启动后端服务并打开图形界面，提供完整的交互体验。

#### 仅启动后端服务

```bash
python main.py
```

系统启动后，API服务器将在 http://localhost:8888 运行

### API文档

启动系统后，可以访问以下地址查看交互式API文档：
- Swagger UI: http://localhost:8888/docs
- ReDoc: http://localhost:8888/redoc

## 使用指南

### 图形界面使用

启动`start_gui.py`后，您将看到一个基于Gradio的图形界面，主要包含以下功能区域：

1. **对话区域** - 与系统进行自然语言交互，获取编程相关问题的答案
2. **代码编辑器** - 编写和运行Python代码，支持语法高亮
3. **运行按钮** - 执行代码并显示结果
4. **输出区域** - 显示代码执行结果、错误信息等
5. **状态显示** - 显示系统连接状态和操作进度

Gradio界面提供了直观的交互体验，支持拖拽上传文件和实时代码执行。

### 后端服务验证

项目包含一个`verify_backend.py`脚本，用于验证后端服务的状态：

```bash
python verify_backend.py
```

该脚本会检查：
1. 配置文件是否正确加载
2. API服务器端口是否被占用
3. 是否能成功连接到API服务器
4. 当前运行的Python进程列表

如果遇到连接问题，可以运行此脚本进行排查。

### 代码执行

通过`/execute_code`接口可以执行Python代码：

```bash
curl -X POST "http://localhost:8888/execute_code" \n  -H "Content-Type: application/json" \n  -d '{"code": "print(\"Hello, Python!\")"}'
```

### 生成测验

通过`/generate_quiz`接口可以生成Python编程测验：

```bash
curl -X POST "http://localhost:8888/generate_quiz" \n  -H "Content-Type: application/json" \n  -d '{"topic": "Python列表操作", "difficulty": "beginner", "num_questions": 5}'
```

### 检查答案

通过`/check_answer`接口可以检查答案：

```bash
curl -X POST "http://localhost:8888/check_answer" \n  -H "Content-Type: application/json" \n  -d '{"question": "Python中如何创建一个空列表？", "user_answer": "empty_list = []"}'
```

### 解释概念

通过`/explain_concept`接口可以获取概念解释：

```bash
curl -X POST "http://localhost:8888/explain_concept" \n  -H "Content-Type: application/json" \n  -d '{"concept": "装饰器", "level": "intermediate"}'
```

### 通用查询

通过`/query`接口可以进行通用查询，系统会根据情况自动调用工具：

```bash
curl -X POST "http://localhost:8888/query" \n  -H "Content-Type: application/json" \n  -d '{"query": "写一个Python函数来计算斐波那契数列的第n项"}'
```

## 知识库管理

将Python编程相关的文档放入`./data/knowledge/`目录，系统会自动加载这些文档到向量存储中，用于RAG检索。

支持的文档格式：
- 文本文件 (.txt)
- Markdown文件 (.md)
- PDF文件 (.pdf) - 需安装额外依赖
- Word文件 (.docx, .doc) - 需安装额外依赖

## 安全注意事项

### API密钥安全

1. **环境变量存储** - 敏感的API密钥应存储在`.env`文件中，而不是直接写入代码或配置文件
2. **配置文件保护** - 即使在配置文件中设置了API密钥，系统仍会优先使用环境变量中的值
3. **版本控制排除** - `.env`文件应添加到`.gitignore`中，避免将敏感信息提交到代码仓库
4. **权限管理** - 确保`.env`文件的权限设置正确，仅允许必要的用户访问

### 代码执行安全

1. **隔离执行环境** - 系统使用Python内置的`subprocess`模块在独立进程中执行代码，并设置了超时机制（默认为30秒），有效防止恶意代码长时间运行
2. **输入验证** - 系统对所有用户输入进行验证和清理，防止注入攻击
3. **资源限制** - 代码执行器对内存使用和CPU时间进行监控，防止资源滥用
4. **日志监控** - 系统记录所有代码执行操作和API调用，便于审计和问题排查

### 生产环境建议

1. **访问控制** - 实施细粒度的访问控制，限制对系统的访问
2. **网络安全** - 默认情况下，系统只绑定到localhost（127.0.0.1），如需公开访问，请确保配置了适当的安全措施，如添加防火墙规则
3. **定期更新** - 定期更新系统依赖，确保使用最新的安全补丁
4. **备份机制** - 实施数据备份机制，防止数据丢失
5. **监控告警** - 建立完善的监控和告警机制，及时发现和处理安全问题

## 扩展开发

### 添加新功能

1. **工具函数扩展** - 可以在`education_system.py`中添加新的工具函数，然后在`config.yaml`的`allowed_functions`列表中注册它们，使大模型能够调用这些函数。

2. **模型集成** - 系统支持集成其他大语言模型，只需在`config.yaml`中配置相应的API参数，或修改`llm_client.py`中的实现。

3. **界面定制** - 可以修改`gradio_app.py`来自定义Gradio界面的布局和功能，添加新的交互组件。

4. **知识库扩展** - 将新的学习资料放入`data/knowledge/`目录，可以丰富系统的知识库内容，提高回答质量。

### 架构扩展建议

1. **多用户支持** - 可以添加用户认证和会话管理功能，支持多用户同时使用系统。

2. **学习进度跟踪** - 可以添加数据库来存储用户的学习进度、测验成绩等信息。

3. **更多API端点** - 可以在`api/server.py`中添加更多的API端点，提供更丰富的功能接口。

## 故障排除

### 代码修改不生效问题解决

项目包含一个`fix_code_update_issue.py`脚本，专门用于解决代码修改不生效的问题：

```bash
python fix_code_update_issue.py
```

该脚本会执行以下操作：
1. **查找并杀死相关进程** - 确保所有运行中的Python进程（如main.py、uvicorn、start_gui.py）被正确终止
2. **清除Python缓存** - 删除所有.pyc文件和__pycache__目录，确保使用最新的代码
3. **修复潜在错误** - 自动修复education_system.py中的常见逻辑错误

当您修改代码后发现更改没有生效时，建议运行此脚本后再重新启动系统。

### 常见问题

1. **HTTP连接超时错误**
   - 确认API服务器是否已启动（运行`main.py`）
   - 检查`config.yaml`中的`api_port`是否与实际运行端口一致
   - 运行`verify_backend.py`脚本检查服务状态
   - 检查防火墙设置，确保端口未被阻止

2. **代码执行失败**
   - 检查代码是否包含语法错误
   - 确认代码没有超时（默认30秒）
   - 查看日志文件了解详细错误信息

3. **API密钥错误**
   - 确认`.env`文件中设置了正确的`LLM_API_KEY`环境变量
   - 检查`.env`文件的格式是否正确（无引号、无空格）
   - 验证环境变量是否被正确加载：系统会优先使用`.env`中的值，即使在`config.yaml`中设置了API密钥
   - 检查网络连接，确保能够访问大模型API服务
   - 确认API密钥是否过期或被限制使用

4. **Gradio界面问题**
   - 确认所有依赖已正确安装（运行`pip install -r requirements.txt`）
   - 检查浏览器兼容性，建议使用Chrome或Firefox
   - 尝试清除浏览器缓存后重新加载页面

## 贡献指南

欢迎提交Issue和Pull Request来改进这个项目。贡献前请确保：

1. 代码符合项目的风格规范
2. 添加了适当的文档注释
3. 通过了基本的功能测试

## 许可证

本项目采用MIT许可证 - 详见 [LICENSE](LICENSE) 文件。

MIT许可证是一种宽松的开源许可证，允许您自由使用、修改和分发本软件，无论是商业用途还是非商业用途，只需保留原始版权和许可证声明即可。