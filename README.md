# 代码规范 #
- 项目使用python2.7版本
- 数据库为mongodb, 版本>=3.0
- 关系数据库为mysql, 版本>=5.6
- 缓存使用redis, 版本>=3.0
- 项目遵循flake8编码格式, 每行字符调整为不超过100
- 项目新增库需要记录在requirements.txt文件中
- 及时删除无用代码
- 代码提交之前需要执行测试用例(runtest.py)并全部通过
- 每次提交代码必须写明注释
- 新增接口要写相应的接口测试
- 代码提交忽略logs和static目录

# 目录介绍 #
- docs: API文档
- files: 需要使用的额外文件
- config.py: 配置文件
- runadmin.py: 启动本地admin(编辑后台)服务
- runserver.py: 启动本地api(核心接口)服务
- runasyncserver.py: 异步方式启动本地api(核心接口)服务
- runtest.py: 执行测试用例
- wanx: 核心代码
- wanx.admin：admin(编辑后台)相关代码
- wanx.base：基础库
- wanx.models: 数据抽象定义和操作
- wanx.platforms: 第三方平台相关
- wanx.share: 分享模块
- wanx.tests: 测试用例模块
- wanx.views: API接口模块
