# TEMU 服装成本计算器 — PWA 应用

## 📦 文件结构

```
temu-app/
├── temu.html          # 主应用（单文件，3900+ 行）
├── start_cj.py         # CJ 匹配入口脚本
├── manifest.json       # PWA 清单
├── service-worker.js   # Service Worker（离线缓存）
├── icon-192.png        # 应用图标 192×192
├── icon-512.png        # 应用图标 512×512
├── icon.svg            # 图标源文件
└── README.md           # 本文件
```

## 🚀 使用方式

### 方式一：本地打开（基础功能）
直接用浏览器打开 `temu.html`，所有计算功能正常可用，但**无法安装为应用**。

### 方式二：本地服务器（完整 PWA）
PWA 要求 HTTPS 或 localhost。启动本地服务器：

```bash
# Python
cd temu-app && python3 -m http.server 8080

# Node.js
npx serve temu-app -l 8080

# PHP
cd temu-app && php -S localhost:8080
```

然后访问 `http://localhost:8080`，浏览器会显示「安装」按钮。

### 方式三：部署到线上（推荐）
将整个 `temu-app/` 目录部署到任意静态托管：

| 平台 | 命令/操作 |
|------|----------|
| **GitHub Pages** | 推送到 gh-pages 分支 |
| **Vercel** | `vercel --prod` |
| **Netlify** | 拖拽上传文件夹 |
| **Cloudflare Pages** | 连接 Git 仓库 |
| **Nginx** | 复制到 webroot 目录 |

> ⚠️ 必须通过 HTTPS 访问才能安装为 PWA

## 📱 安装到设备

### 桌面 Chrome / Edge
1. 打开应用 URL
2. 地址栏右侧出现 ⟶ 安装图标，点击安装
3. 或：菜单 → 「安装 TEMU 计算器」

### Android Chrome
1. 打开应用 URL
2. 浏览器自动弹出「添加到主屏幕」提示
3. 或：菜单 → 「添加到主屏幕」

### iOS Safari
1. 打开应用 URL
2. 点击分享按钮 (□↑)
3. 选择 「添加到主屏幕」

## ✨ PWA 特性

- ✅ **可安装** — 像原生 App 一样出现在桌面/应用列表
- ✅ **离线可用** — Service Worker 缓存所有资源，断网也能用
- ✅ **自适应** — 响应式布局，手机/平板/桌面都适配
- ✅ **暗色模式** — 跟随系统或手动切换
- ✅ **自动更新** — 检测到新版本时提示刷新

## 🧩 CJ 匹配

通过 `start_cj.py` 脚本连接 CJ API，自动匹配商品价格数据：

```bash
python start_cj.py
```

匹配结果会自动写入 `temu.html` 的价格字段，用于批量核价计算。

## 🔧 技术细节

- **零依赖** — 纯 HTML + CSS + JS，无需 npm/node/构建
- **单文件** — 主应用 200KB，所有逻辑内联
- **XLSX 解析** — 手写纯 JS 解析器（基于 DecompressionStream API）
- **XLSX 生成** — 手写 ZIP 构建器 + XML 生成，无外部库
- **本地存储** — 所有参数/数据保存在浏览器 localStorage
- **实时汇率** — 通过 frankfurter.app API 获取（可选）
