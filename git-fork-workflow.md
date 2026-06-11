# Git Fork 二次开发工作流指南

本文档说明基于 GitHub Fork 进行 Blender 插件二次开发的完整工作流程。

---

## 一、角色说明

| 名称 | 地址 | 说明 |
|------|------|------|
| **upstream（上游）** | `XQFAAAA/BlenderXqfaTools` | 原作者的仓库，持续更新中 |
| **origin（你的 Fork）** | `yequ172672/BlenderXqfaTools-editor` | 你 fork 出来的副本，你拥有完全控制权 |
| **本地仓库** | 你电脑上的文件夹 | 实际编辑代码的地方 |

三者的关系：
```
上游(upstream) ──fork──> 你的Fork(origin) ──clone──> 本地仓库
     ↑                                                    │
     └────────────── push PR 贡献回上游 ──────────────────┘
```

---

## 二、初始设置（只需做一次）

### 步骤 1：克隆你的 Fork 到本地

```bash
git clone https://github.com/yequ172672/BlenderXqfaTools-editor.git
cd BlenderXqfaTools-editor
```

**做了什么：** 把你 Fork 仓库的完整代码下载到电脑上，并自动设置一个名为 `origin` 的远程地址指向你的 Fork。

### 步骤 2：添加上游仓库

```bash
git remote add upstream https://github.com/XQFAAAA/BlenderXqfaTools.git
```

**做了什么：** 给本地仓库登记一个名为 `upstream` 的远程地址，指向原作者的仓库。这样以后就能从上游拉取更新了。注意这里只是"登记地址"，不会下载任何东西。

### 步骤 3：验证设置

```bash
git remote -v
```

**做了什么：** 列出所有已登记的远程仓库地址，确认 `origin` 和 `upstream` 都正确指向各自的仓库。

---

## 三、日常开发流程

### 步骤 1：创建功能分支

```bash
git checkout -b feature/新功能名
```

**做了什么：** 基于当前分支创建一个新分支并切换过去。所有的代码修改都在这个分支上进行，**不要直接改 main 分支**，这样可以让你的改动和上游代码保持清晰的分界，减少冲突。

### 步骤 2：开发并提交

```bash
git add .
git commit -m "描述这次改了什么"
```

**做了什么：**
- `git add .`：把当前所有修改过的文件加入"暂存区"，告诉 Git 这些文件准备提交。
- `git commit`：把暂存区的修改正式记录到本地 Git 历史中，附上说明信息。

### 步骤 3：推送到你的 Fork

```bash
git push origin feature/新功能名
```

**做了什么：** 把你本地的功能分支上传到你的 GitHub Fork 仓库，这样代码就有了远程备份，也可以在 GitHub 上查看或发起 Pull Request。

---

## 四、同步上游更新（核心操作）

当原作者更新了代码，你需要把上游的新功能/修复合并进来时：

### 步骤 1：拉取上游最新代码

```bash
git fetch upstream
```

**做了什么：** 从上游仓库下载所有最新的提交记录和分支信息，但**不会自动合并**到你的代码中。只是让你本地知道上游有什么新变化。

### 步骤 2：切换到主分支

```bash
git checkout main
```

**做了什么：** 切换回主分支，准备把上游的更新合并进来。

### 步骤 3：合并上游更新到主分支

```bash
git merge upstream/main
```

**做了什么：** 把上游的 main 分支内容合并到你本地的 main 分支。如果上游的修改和你的修改没有冲突，Git 会自动合并；如果有冲突（同一个地方双方都改了），需要你手动选择保留哪部分。

### 步骤 4：推送更新到你的 Fork

```bash
git push origin main
```

**做了什么：** 把合并后的 main 分支同步到你 GitHub 上的 Fork，保持线上也是最新的。

### 步骤 5：把更新应用到你的功能分支

```bash
git checkout feature/新功能名
git rebase main
```

**做了什么：**
- 先切回你的功能分支。
- `rebase`（变基）会把你的功能分支"接"到最新的 main 分支上，就像你的代码是基于最新版本写的一样。比 `merge` 更推荐，因为它能保持提交历史的整洁，不会产生多余的合并提交记录。

---

## 五、遇到冲突怎么办

冲突发生在：你和上游修改了同一个文件的同一处代码。

### 解决步骤：

1. **Git 会提示哪些文件冲突了**，打开那些文件
2. **找到冲突标记**，格式如下：
   ```
   <<<<<<< HEAD
   你的代码
   =======
   上游的代码
   >>>>>>> upstream/main
   ```
3. **手动决定保留哪些**，删除冲突标记（`<<<`、`===`、`>>>`）
4. **保存后继续**：
   ```bash
   git add .
   git commit        # 如果是 merge 操作
   # 或
   git rebase --continue   # 如果是 rebase 操作
   ```

### 减少冲突的建议：

- 尽量在**独立的文件**中添加新功能，而不是修改上游的文件
- 如果必须修改上游文件，**改动范围尽量小**
- **定期同步上游**，不要等积累很多更新再合并

---

## 六、完整命令速查

```bash
# ===== 一次性设置 =====
git clone https://github.com/yequ172672/BlenderXqfaTools-editor.git
cd BlenderXqfaTools-editor
git remote add upstream https://github.com/XQFAAAA/BlenderXqfaTools.git

# ===== 开发新功能 =====
git checkout -b feature/新功能名
# ... 编辑代码 ...
git add .
git commit -m "说明改动"
git push origin feature/新功能名

# ===== 同步上游更新 =====
git fetch upstream
git checkout main
git merge upstream/main
git push origin main
git checkout feature/新功能名
git rebase main

# ===== 查看状态 =====
git status              # 当前修改了哪些文件
git log --oneline       # 查看提交历史
git remote -v           # 查看远程仓库地址
git branch -a           # 查看所有分支
```
