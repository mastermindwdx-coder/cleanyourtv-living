# 可复现构建与签名

本说明指“从公开源码重建功能”，不承诺不同环境的 APK 字节完全一致。无需作者签名文件、本机 SDK 路径、私人配置或第三方 APK。

## 环境

JDK 17、Python 3.12、Android SDK `platforms;android-36` / `build-tools;35.0.0` / platform-tools。Gradle wrapper 8.14.3、AGP 8.12.0 已固定。首次需联网获取依赖，后续依赖齐备可加 `--offline`。设置 ANDROID_HOME，或在本地 launcher/local.properties 写 sdk.dir；该文件不提交。Robolectric 测试会获取 SDK 测试资源，不等于运行时依赖。

## 无密钥构建

仓库根目录执行（Windows 把 `sh launcher/gradlew` 换成 `launcher/gradlew.bat`）：

```sh
sh launcher/gradlew -p launcher --no-daemon testReleaseUnitTest lintRelease assembleDebug assembleRelease
sh companion/android/gradlew -p companion/android --no-daemon lintRelease assembleDebug assembleRelease
python -m pip install -r companion/scripts/requirements.txt
python -m unittest discover -s custom-tools -p 'test_*.py' -v
python -m unittest discover -s companion/tests -v
python scripts/check_public.py
```

Debug 生成 app-debug.apk（开发签名，可安装）；未提供签名时 Release 生成 app-release-unsigned.apk（不能直接安装）。Launcher 体积预算 768 KiB，Companion 256 KiB，用 `python scripts/check_apk_size.py` 检查。它们是本分支预算，不冒充通过上游 576 KiB 门槛。

## 自己签名、长期更新

两模块均只从进程环境读取：`CYT_STORE_FILE`、`CYT_STORE_PASSWORD`、`CYT_KEY_ALIAS`、`CYT_KEY_PASSWORD`。四项全部未设置就输出 unsigned；只设置部分会明确报错。密钥放仓库外，由本人保管。不要把密码放命令行参数、工作流文件或共享终端日志。

用 Android Studio 的签名向导或 `keytool` 交互创建密钥；经本人安全方式设置上述环境变量后执行 assembleRelease。同包名升级需要兼容签名：新生成的 key 不能覆盖作者个人 local.2 或其他人的构建。遇签名冲突先备份并说明，不自动卸载、清数据或承诺恢复账号。

官方签名规则：[Android app signing](https://developer.android.com/studio/publish/app-signing)。当前核心包名仍为 com.gathin.tvhome，与上游相同；这避免假装换 package 即可绕开主题/服务硬编码。需要长期并存需独立完成包名适配，不能只改 applicationId。

## CI 做什么

`.github/workflows/ci.yml` 运行定向 Python 测试、公开文件检查、两个 Android 项目的构建/lint、桌面 JVM 测试、APK 体积检查、中文格式化与实际下载速率计量检查。上传测试报告和开发/未签名构建供审阅，不自动创建 Release 或对电视安装。没有复制上游维护者机器人。

本仓库是核心源码提取，不带上游完整 examples/themes/addons 及依赖其表格的 Python 全量套件；不宣称通过那些测试。需要研究原完整工程可按 THIRD_PARTY_NOTICES.md 中固定提交获取。CI 文件已准备不等于 GitHub 云端已跑绿，当前验证见 VERIFICATION.md。

## 导出源码

```sh
python scripts/export_source.py --output ../cleanyourtv-living-source.zip
```

导出前做公开预检，并使用 `public-files.json` 的明确文件清单。新增源文件需审阅后更新清单；不能把整个工作目录打包。输出已存在时拒绝覆盖，包内含最终逐文件哈希及许可证，排除 Git、本地构建、密钥与个人材料。
