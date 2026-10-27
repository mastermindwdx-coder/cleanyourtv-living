# 安全与隐私

核心桌面无 INTERNET 权限；可选 Companion 与网络/影音客户端权限独立。Home 守护涉及无障碍、通知监听及系统设置能力，只按设备需要授权；不把它包装成零权限工具。

系统变更先记录、只动白名单、保留原 Home 与输入服务。公开安装默认 keep_adb=false；结束维护按 docs/INSTALL.md 关闭并核验 ADB。处于授权维护中不突然断连。

不要公开账号、订阅、节点认证、ADB/签名私钥、连接码、个人地址、设备标识或原始系统日志。private/、local/、构建目录被忽略；实际导出还受 public-files.json 允许清单限制，不能只依赖 .gitignore。

发现漏洞请先在本地生成最小脱敏复现。GitHub 项目建立后维护者应启用 Private vulnerability reporting，再通过 Security → Report a vulnerability 私下提交；该渠道未开启前，不将密钥或可直接利用的敏感内容写到公开 Issue。当前没有编造一个尚不存在的维护邮箱或仓库地址。
