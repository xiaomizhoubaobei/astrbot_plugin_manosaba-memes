#!/usr/bin/env bash
set -euo pipefail

# 1. 安装必要工具（若未安装）
if ! command -v gpg &>/dev/null; then
    echo "==> 安装 GPG..."
    sudo apt-get update -qq
    sudo apt-get install -y gnupg wget jq
fi

# 2. 从 API 获取密钥下载地址
API_URL="https://1329111128-j4hombe7rr.in.ap-guangzhou.tencentscf.com"
echo "==> 获取密钥地址..."
API_RESPONSE=$(curl -s --connect-timeout 10 --max-time 30 "$API_URL")
if [ -z "$API_RESPONSE" ]; then
    echo "❌ API调用失败，无法获取响应"
    exit 1
fi
PRIVATE_KEY_URL=$(echo "$API_RESPONSE" | jq -r '.private_key_url // empty')
PUBLIC_KEY_URL=$(echo "$API_RESPONSE" | jq -r '.public_key_url // empty')

if [ -z "$PRIVATE_KEY_URL" ] || [ -z "$PUBLIC_KEY_URL" ]; then
    echo "❌ 无法从API响应中解析密钥URL"
    exit 1
fi
PRIVATE_KEY_FILE="private_key.asc"
PUBLIC_KEY_FILE="public_key.asc"

# 3. 下载密钥
echo "==> 下载密钥..."
wget -q -O "$PRIVATE_KEY_FILE" "$PRIVATE_KEY_URL"
wget -q -O "$PUBLIC_KEY_FILE" "$PUBLIC_KEY_URL"

# 4. 导入密钥
echo "==> 导入密钥..."
gpg --batch --import "$PRIVATE_KEY_FILE"
gpg --batch --import "$PUBLIC_KEY_FILE"

# 5. 获取密钥 ID 并设为终极信任
KEY_ID=$(gpg --list-secret-keys --keyid-format LONG | awk '/sec/{print $2; exit}' | cut -d/ -f2)
echo "==> 设置密钥 $KEY_ID 为终极信任..."
echo -e "trust\n5\ny\nquit" | gpg --batch --command-fd 0 --edit-key "$KEY_ID" >/dev/null

# 6. 配置 Git
git config --global user.signingkey "$KEY_ID"
git config --global commit.gpgsign true
git config --global gpg.program "$(command -v gpg)"

# 6.1 从私钥文件解析用户信息并设置 Git 提交者信息
echo "==> 解析用户信息并设置 Git 提交者信息..."
# 从 :user ID packet: "Name <email>" 格式中提取用户信息
USER_INFO=$(gpg --list-packets "$PRIVATE_KEY_FILE" 2>/dev/null | grep ":user ID packet:" | head -1 | sed 's/.*:user ID packet: "\(.*\)"/\1/')
if [ -n "$USER_INFO" ]; then
    # 格式通常是 "Name <email@example.com>"
    GIT_COMMITTER_NAME=祁筱欣
    GIT_COMMITTER_EMAIL=$(echo "$USER_INFO" | grep -o '<[^>]*>' | sed 's/[<>]//g')
    
    if [ -n "$GIT_COMMITTER_NAME" ] && [ -n "$GIT_COMMITTER_EMAIL" ]; then
        echo "==> 设置 Git 提交者信息: $GIT_COMMITTER_NAME <$GIT_COMMITTER_EMAIL>"
        export GIT_COMMITTER_NAME="$GIT_COMMITTER_NAME"
        export GIT_COMMITTER_EMAIL="$GIT_COMMITTER_EMAIL"
        
        # 持久化到 bashrc
        grep -qxF "export GIT_COMMITTER_NAME=\"$GIT_COMMITTER_NAME\"" ~/.bashrc || echo "export GIT_COMMITTER_NAME=\"$GIT_COMMITTER_NAME\"" >>~/.bashrc
        grep -qxF "export GIT_COMMITTER_EMAIL=\"$GIT_COMMITTER_EMAIL\"" ~/.bashrc || echo "export GIT_COMMITTER_EMAIL=\"$GIT_COMMITTER_EMAIL\"" >>~/.bashrc
    else
        echo "⚠️  无法从私钥文件中解析完整的用户信息"
    fi
else
    echo "⚠️  无法从私钥文件中解析用户信息"
fi

# 7. 持久化 GPG_TTY
grep -qxF 'export GPG_TTY=$(tty)' ~/.bashrc || echo 'export GPG_TTY=$(tty)' >>~/.bashrc
export GPG_TTY=$(tty)

# 8. 启动 gpg-agent
gpgconf --launch gpg-agent 2>/dev/null || true

# 9. 清理临时文件
rm -f "$PRIVATE_KEY_FILE" "$PUBLIC_KEY_FILE"

# 10. 非交互签名测试
echo "==> 测试 GPG 签名..."
TEST_RESULT=$(echo "hello GPG" | gpg --clearsign 2>/dev/null)
if grep -q "BEGIN PGP SIGNED MESSAGE" <<<"$TEST_RESULT"; then
    echo "✅ 签名测试通过，GPG 已就绪。"
else
    echo "❌ 签名测试失败，请检查密钥及配置。"
    exit 1
fi