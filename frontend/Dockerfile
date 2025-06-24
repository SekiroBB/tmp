# 第一阶段：构建阶段
FROM harbor.xz.com:8448/spiritx-platform/node:22-alpine3.22 AS builder

# 设置工作目录
WORKDIR /app

# 复制 package.json 和 pnpm-lock.yaml
COPY package.json pnpm-lock.yaml ./

# 安装 pnpm
RUN npm install -g pnpm

# 设置阿里云 npm 源
RUN pnpm config set registry https://registry.npmmirror.com/

# 安装依赖
RUN pnpm install --frozen-lockfile

# 复制源代码
COPY . .

# 构建项目
RUN pnpm run build

# 第二阶段：生产阶段
FROM harbor.xz.com:8448/spiritx-platform/nginx:stable-alpine3.20


# 复制构建产物到 nginx 默认目录
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 nginx 配置（可选）
# COPY nginx.conf /etc/nginx/nginx.conf

# 暴露端口
EXPOSE 80

# 启动 nginx
CMD ["nginx", "-g", "daemon off;"]
