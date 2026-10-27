# SmartTube 中文提示与实时网速补丁（可选）

上游 [yuliskov/SmartTube](https://github.com/yuliskov/SmartTube)，固定 commit `94553dd7151e8a911926ef2c9e3ef30fca007b48`（32.68s）。MediaServiceCore `b83ff1db5cdd8de097bd811eafd907b344b27e87`，两个 SharedModules 均 `d4f09b11133036d90826baf012e120d06486ae73`，以固定提交的 gitlink 为准。

当前 [补丁](chinese-prompts.patch) 只含 Java/XML/Gradle 文本：常见错误与恢复提示中文化；保留错误码、从界面隐藏敏感原始 URL；独立 org.cleantv.smarttube 包名；禁止不匹配签名的上游自动安装；10 项格式化测试。没有更改登录协议，也没有改服务器许可。

随后应用 [实时网速补丁](playback-network-status.patch)：加载时显示“实时网速＋已缓存秒数”，每秒刷新、恢复播放后自动隐藏；详细统计是另行开启的面板。计量使用当前应用UID实际接收字节差，包含音视频、缩略图和网络开销，KB/MB采用1024进位；不是整机带宽上限或纯视频码率。首次/不可计量时不伪报零，正常间歇下载的0网速也不自动判断为断网。15项无Android依赖的计量测试覆盖时间间隔、计数重置、不支持计量和单位边界。

**已剔除作者私人版本中替换 YouTube 图标的二进制改动。** 使用上游 SmartTube 图形，不冒充 Google 官方客户端。原 MIT [LICENSE](LICENSE) 保留；其他依赖遵循各自许可。本目录只交付源补丁，不打包第三方 APK。

```sh
git clone --no-checkout https://github.com/yuliskov/SmartTube.git SmartTube-personal
cd SmartTube-personal
git checkout 94553dd7151e8a911926ef2c9e3ef30fca007b48
git submodule update --init --recursive
git apply --check PATH_TO_CHINESE_PROMPTS_PATCH
git apply PATH_TO_CHINESE_PROMPTS_PATCH
git apply --check PATH_TO_PLAYBACK_NETWORK_STATUS_PATCH
git apply PATH_TO_PLAYBACK_NETWORK_STATUS_PATCH
```

随后按上游构建配置准备 JDK17/SDK34 与个人签名，使用项目 Gradle 7.5 wrapper 构建 `:smarttubetv:assembleStfdroidDebug` 或自行签名 Release。不要拷贝作者 keystore.properties。两补丁叠加为32.68-local.4；versionCode仍为2459，用于同签名的本地覆盖迭代与回退。对外维护的后续发行需自行规划递增版本号，换签名不能覆盖已有安装。仓库图形与作者个人APK不同，不能声称哈希相同。

`python scripts/check_smarttube_patch.py` 校验两份文本补丁并编译/执行25项便携Java检查。固定上游上的顺序应用、构建与实播范围见 [验证记录](../../VERIFICATION.md)。网络适配与诊断方法见 [播放与自动选线](../../docs/PLAYBACK-NETWORK.md)。补丁只记本地速率、缓存、画质和进度计数，不记录标题、视频ID、播放地址或账号；没有远程遥测。
