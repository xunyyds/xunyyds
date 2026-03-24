#!/system/bin/sh
 
GITHUB_TOKEN=" "   # 填入你的GitHub Token

OWNER=" "  # 用户名
REPO="ABC"      #仓库名
BRANCH="main"    #仓库/分支
COMMIT_MSG="feat: "  #提交信息

# 本地绝对路径
SOURCE_DIR="/storage/emulated/0/ "

# 本地文件（只需放在绝对路径中，下方填文件名即可） → 仓库目标路径 一行一个即可
declare -A FILES=(
    ["文件名.kt"]="app/src/main/"
)

# 检查文件
echo "检查本地文件..."
for f in "${!FILES[@]}"; do
    path="$SOURCE_DIR/$f"
    if [ ! -f "$path" ]; then
        echo "缺失文件：$path"
        exit 1
    fi
done

# 获取分支最新SHA
echo "获取仓库分支信息..."
REF_URL="https://api.github.com/repos/$OWNER/$REPO/git/refs/heads/$BRANCH"
REF_RES=$(curl -s -H "Authorization: token $GITHUB_TOKEN" "$REF_URL")

BASE_SHA=$(echo "$REF_RES" | grep -A 5 '"object"' | grep '"sha"' | head -1 | cut -d '"' -f 4)

if [ -z "$BASE_SHA" ]; then
    echo "获取分支SHA失败"
    echo "$REF_RES"
    exit 1
fi
echo "最新Commit SHA：$BASE_SHA"

# 生成所有blob
echo "上传文件到GitHub..."
TREE_LIST=""
for local_name in "${!FILES[@]}"; do
    repo_path="${FILES[$local_name]}"
    local_path="$SOURCE_DIR/$local_name"
    
    echo "处理：$repo_path"
    
    # 转换成base64
    content=$(base64 "$local_path" | tr -d '\n\r')
    
    # 创建blob
    blob_res=$(curl -s -X POST \
        -H "Authorization: token $GITHUB_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"content\":\"$content\",\"encoding\":\"base64\"}" \
        "https://api.github.com/repos/$OWNER/$REPO/git/blobs")
    
    blob_sha=$(echo "$blob_res" | grep '"sha"' | head -1 | cut -d '"' -f 4)
    if [ -z "$blob_sha" ]; then
        echo "上传失败：$local_name"
        echo "$blob_res"
        exit 1
    fi
    
    TREE_LIST="$TREE_LIST{\"path\":\"$repo_path\",\"mode\":\"100644\",\"type\":\"blob\",\"sha\":\"$blob_sha\"},"
done
TREE_LIST="${TREE_LIST%,}"

# 创建tree
tree_res=$(curl -s -X POST \
    -H "Authorization: token $GITHUB_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"base_tree\":\"$BASE_SHA\",\"tree\":[$TREE_LIST]}" \
    "https://api.github.com/repos/$OWNER/$REPO/git/trees")
tree_sha=$(echo "$tree_res" | grep '"sha"' | head -1 | cut -d '"' -f 4)

if [ -z "$tree_sha" ]; then
    echo "创建Tree失败"
    echo "$tree_res"
    exit 1
fi

# 创建commit
commit_res=$(curl -s -X POST \
    -H "Authorization: token $GITHUB_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"message\":\"$COMMIT_MSG\",\"tree\":\"$tree_sha\",\"parents\":[\"$BASE_SHA\"]}" \
    "https://api.github.com/repos/$OWNER/$REPO/git/commits")
commit_sha=$(echo "$commit_res" | grep '"sha"' | head -1 | cut -d '"' -f 4)

if [ -z "$commit_sha" ]; then
    echo "创建Commit失败"
    echo "$commit_res"
    exit 1
fi

# 更新分支
curl -s -X PATCH \
    -H "Authorization: token $GITHUB_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"sha\":\"$commit_sha\",\"force\":false}" \
    "https://api.github.com/repos/$OWNER/$REPO/git/refs/heads/$BRANCH"

echo ""
echo "已提交成功！"
echo "新Commit：$commit_sha"
