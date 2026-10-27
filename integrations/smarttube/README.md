# SmartTube 中文提示补丁（可选）

上游 [yuliskov/SmartTube](https://github.com/yuliskov/SmartTube)，固定 commit `94553dd7151e8a911926ef2c9e3ef30fca007b48`（32.68s）。MediaServiceCore `b83ff1db5cdd8de097bd811eafd907b344b27e87`，两个 SharedModules 均 `d4f09b11133036d90826baf012e120d06486ae73`，以固定提交的 gitlink 为准。

当前 [补丁](chinese-prompts.patch) 只含 Java/XML/Gradle 文本：常见错误与恢复提示中文化；保留错误码、从界面隐藏敏感原始 URL；独立 org.cleantv.smarttube 包名；禁止不匹配签名的上游自动安装；10 项格式化测试。没有更改登录协议，也没有改服务器许可。

**已剔除作者私人版本中替换 YouTube 图标的二进制改动。** 使用上游 SmartTube 图形，不冒充 Google 官方客户端。原 MIT [LICENSE](LICENSE) 保留；其他依赖遵循各自许可。本目录只交付源补丁，不打包第三方 APK。

```sh
git clone --no-checkout https://github.com/yuliskov/SmartTube.git SmartTube-personal
cd SmartTube-personal
git checkout 94553dd7151e8a911926ef2c9e3ef30fca007b48
git submodule update --init --recursive
git apply --check PATH_TO_PATCH
git apply PATH_TO_PATCH
```

随后按上游构建配置准备 JDK17/SDK34 与个人签名，使用项目 Gradle 7.5 wrapper 构建 `:smarttubetv:assembleStfdroidDebug` 或自行签名 Release。不要拷贝作者 keystore.properties。补丁版本仍保留来源标识 32.68-local.2；公开包的图形与作者个人 APK 不同，不能声称哈希相同。

`python scripts/check_smarttube_patch.py` 在本仓库校验文本补丁边界并编译/执行其中无 Android 依赖的中文错误格式化测试。固定上游上的 git apply --check 结果另记于 VERIFICATION.md；本轮不再对电视安装或修改账号。
