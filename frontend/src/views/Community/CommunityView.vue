<template>
  <div class="community page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">创作社区</h1>
        <p class="page-subtitle">浏览无锡非遗主题的完整人物与摆件，打开作品旋转观察造型与细节。</p>
      </div>
      <el-button type="primary" class="btn-gradient" @click="openUploadDialog">
        <el-icon><Upload /></el-icon>
        上传作品
      </el-button>
    </div>

    <div class="toolbar">
      <div class="search-bar">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索作品..."
          :prefix-icon="Search"
          clearable
        />
      </div>

      <div class="filter-section">
        <el-select v-model="selectedCategory" placeholder="分类筛选" style="width: 150px;" clearable>
          <el-option v-for="cat in categories" :key="cat" :label="cat" :value="cat" />
        </el-select>

        <el-select v-model="sortBy" placeholder="排序方式" style="width: 120px;">
          <el-option label="最新发布" value="newest" />
          <el-option label="最受欢迎" value="popular" />
          <el-option label="最多评论" value="comments" />
        </el-select>
      </div>
    </div>

    <div class="community-main">
      <div class="works-area">
        <div v-if="isLoading" class="loading-state">
          <el-icon class="is-loading" size="40" color="#4a90a4"><Loading /></el-icon>
          <p>正在加载作品...</p>
        </div>
        <div v-else-if="loadError" class="empty-state" role="alert"><p>作品暂时无法加载</p><el-button @click="refreshPage">重新加载</el-button></div>
        <div v-else-if="filteredWorks.length === 0" class="empty-state">
          <el-icon size="64" color="#ccc"><Picture /></el-icon>
          <p>没有找到相关作品</p>
          <el-button type="primary" @click="openUploadDialog">发布作品</el-button>
        </div>
        <template v-else>
          <div class="works-grid">
            <div class="work-card" v-for="work in filteredWorks" :key="work.id">
              <div class="work-image-wrapper" @click="viewWorkDetail(work)">
                <div class="work-image">
                  <img v-if="work.thumbnail" :src="work.thumbnail" :alt="work.title" />
                  <div v-else class="work-image-placeholder">
                    <el-icon size="40" color="#b8c4cc"><Picture /></el-icon>
                  </div>
                </div>
                <div class="category-tag">
                  <span v-if="work.isAi" class="ai-badge">数字创作</span>
                  {{ getFirstTag(work) }}
                </div>
              </div>
              <div class="work-content">
                <h4 class="work-title">{{ work.title }}</h4>
                <p class="work-description">{{ work.description || '暂无描述' }}</p>
                <p class="work-author">by {{ work.author }}</p>
                <div class="work-stats">
                  <span class="like-btn" @click="handleLike(work)">
                    <el-icon :color="work.isLiked ? '#e74c3c' : '#999'"><Star /></el-icon>
                    {{ work.likes }}
                  </span>
                  <span>
                    <el-icon><Picture /></el-icon>
                    {{ work.views }}
                  </span>
                  <span>
                    <el-icon><ChatRound /></el-icon>
                    {{ work.commentCount }}
                  </span>
                </div>
                <button class="view-detail-btn" @click="viewWorkDetail(work)">查看详情</button>
              </div>
            </div>
          </div>
          <div v-if="hasMore" class="load-more">
            <el-button :loading="isLoadingMore" @click="loadMore">加载更多</el-button>
          </div>
        </template>
      </div>

      <div class="sidebar">
        <div class="sidebar-card">
          <h3><el-icon><Trophy /></el-icon> 热门排行榜</h3>
          <div class="ranking-list">
            <div v-for="(work, index) in rankingWorks" :key="work.id" class="ranking-item" @click="viewWorkDetail(work)">
              <span class="rank" :class="{ 'rank-1': index === 0, 'rank-2': index === 1, 'rank-3': index === 2 }">{{ index + 1 }}</span>
              <div class="rank-content">
                <span class="rank-title">{{ work.title }}</span>
                <span class="rank-likes">{{ work.likes }} 赞</span>
              </div>
            </div>
            <p v-if="rankingWorks.length === 0" class="no-comments">暂无数据</p>
          </div>
        </div>

        <div class="sidebar-card">
          <h3><el-icon><Grid /></el-icon> 作品分类</h3>
          <div class="category-list">
            <span
              v-for="cat in categories"
              :key="cat"
              :class="{ active: selectedCategory === cat }"
              @click="selectedCategory = selectedCategory === cat ? '' : cat"
            >
              {{ cat }}
            </span>
          </div>
        </div>

        <div class="sidebar-card">
          <h3><el-icon><Clock /></el-icon> 最新动态</h3>
          <div class="latest-list">
            <div v-for="work in latestWorks" :key="work.id" class="latest-item" @click="viewWorkDetail(work)">
              <span class="latest-title">{{ work.title }}</span>
              <span class="latest-author">{{ work.author }}</span>
            </div>
            <p v-if="latestWorks.length === 0" class="no-comments">暂无数据</p>
          </div>
        </div>
      </div>
    </div>

    <el-dialog title="上传作品" v-model="showUploadDialog" width="520px" top="50px">
      <el-form :model="uploadForm" label-width="90px" class="upload-form">
        <el-form-item label="作品标题" required>
          <el-input v-model="uploadForm.title" placeholder="请输入作品标题" maxlength="200" />
        </el-form-item>
        <el-form-item label="作品描述">
          <el-input v-model="uploadForm.description" type="textarea" placeholder="请输入作品描述" :rows="3" />
        </el-form-item>
        <el-form-item label="作品分类">
          <el-select v-model="uploadForm.category" placeholder="请选择分类" clearable>
            <el-option v-for="cat in categories" :key="cat" :label="cat" :value="cat" />
          </el-select>
        </el-form-item>
        <el-form-item label="封面图片">
          <el-upload
            action="/api/workshop/upload"
            :headers="uploadHeaders"
            :on-success="handleUploadSuccess"
            :on-error="handleUploadError"
            :show-file-list="false"
            accept="image/*"
          >
            <el-button type="primary">选择图片</el-button>
          </el-upload>
          <img v-if="uploadForm.thumbnail" :src="uploadForm.thumbnail" class="upload-preview" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitUpload" :disabled="!uploadForm.title">提交</el-button>
      </template>
    </el-dialog>

    <el-dialog title="作品详情" v-model="showDetailDialog" width="650px" top="30px" @closed="selectedWork = null">
      <div v-if="selectedWork" v-loading="detailLoading" class="work-detail">
        <div class="detail-image-wrapper">
          <img v-if="selectedWork.thumbnail" :src="selectedWork.thumbnail" :alt="selectedWork.title" class="detail-image" />
          <div v-else class="detail-image detail-image-placeholder">
            <el-icon size="48" color="#b8c4cc"><Picture /></el-icon>
            <p v-if="selectedWork.modelUrl">这是一个 3D 模型作品</p>
          </div>
          <div class="detail-category">
            <span v-if="selectedWork.isAi" class="ai-badge">数字创作</span>
            {{ getFirstTag(selectedWork) }}
          </div>
        </div>
        <h3 class="detail-title">{{ selectedWork.title }}</h3>
        <ModelPreview v-if="selectedWork.modelUrl" :url="selectedWork.modelUrl" />
        <p class="detail-desc">{{ selectedWork.description || '暂无描述' }}</p>
        <div class="detail-meta">
          <span class="detail-author">作者: {{ selectedWork.author }}</span>
          <div class="detail-stats">
            <span @click="handleLike(selectedWork)" class="like-action">
              <el-icon :color="selectedWork.isLiked ? '#e74c3c' : '#999'"><Star /></el-icon>
              {{ selectedWork.likes }}
            </span>
            <span @click="handleCollect(selectedWork)" class="like-action">
              <el-icon :color="selectedWork.isCollected ? '#b8860b' : '#999'"><CollectionTag /></el-icon>
              {{ selectedWork.isCollected ? '已收藏' : '收藏' }}
            </span>
            <span>
              <el-icon><Picture /></el-icon>
              {{ selectedWork.views }}
            </span>
          </div>
        </div>

        <div class="comments-section">
          <h4><el-icon><ChatRound /></el-icon> 评论 ({{ selectedWork.commentCount }})</h4>
          <div class="comment-list">
            <div v-for="comment in comments" :key="comment.id" class="comment-item">
              <div class="comment-header">
                <span class="comment-author">{{ comment.author?.username || '用户' }}</span>
                <span class="comment-time">{{ formatTime(comment.created_at) }}</span>
              </div>
              <p class="comment-content">{{ comment.content }}</p>
              <div class="comment-actions" v-if="isOwnComment(comment)">
                <span class="reply-btn" @click="handleDeleteComment(comment)">
                  <el-icon><Delete /></el-icon> 删除
                </span>
              </div>
            </div>
            <p v-if="comments.length === 0" class="no-comments">暂无评论，快来发表第一条评论吧</p>
          </div>
          <el-button v-if="commentsHasMore" :loading="commentsLoading" @click="loadMoreComments">加载更多评论</el-button>
          <el-input
            v-model="newComment"
            placeholder="发表评论..."
            @keyup.enter="submitComment"
            :disabled="!isLoggedIn"
            clearable
          />
          <el-button type="primary" @click="submitComment" :disabled="!newComment.trim() || !isLoggedIn" style="margin-top: 12px;">
            发表评论
          </el-button>
          <p v-if="!isLoggedIn" class="no-comments" style="padding: 8px 0 0;">登录后即可评论</p>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import ModelPreview from '@/components/ModelPreview.vue'
import { useUserStore } from '@/store/userStore'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Upload, Star, Picture, ChatRound, Trophy, Grid, Clock, Delete, CollectionTag, Loading } from '@element-plus/icons-vue'
import {
  getWorks, getWorkDetail, saveWork, likeWork, unlikeWork,
  collectWork, uncollectWork, getComments, postComment, deleteComment
} from '@/api/workshop'

// 后端以 tags 字段承载分类，分类项与社区筛选一致
const categories = ['惠山泥人', '锡绣', '紫砂陶艺', '吴歌', '其他']

const works = ref([])
const rankingWorks = ref([])
const latestWorks = ref([])
let loadedPage = 0, requestVersion = 0, filterTimer
const isLoading = ref(true)
const loadError = ref(false)
const isLoadingMore = ref(false)
const hasMore = ref(false)

const showUploadDialog = ref(false)
const showDetailDialog = ref(false)
const selectedWork = ref(null)
const detailLoading = ref(false)
const isAuthor = ref(false)
const comments = ref([])
const commentsHasMore = ref(false), commentsLoading = ref(false)
let commentPage = 1, detailVersion = 0
const newComment = ref('')
const submitting = ref(false)

const searchKeyword = ref('')
const selectedCategory = ref('')
const sortBy = ref('newest')

const uploadForm = ref({
  title: '',
  description: '',
  category: '',
  thumbnail: null
})

const userStore = useUserStore()
const isLoggedIn = computed(() => !!userStore.user)
const currentUser = computed(() => userStore.user)
const uploadHeaders = computed(() => {
  const token = currentUser.value?.token
  return token ? { Authorization: `Bearer ${token}` } : {}
})

// ---- 后端字段 → 视图字段映射 ----
const mapWork = (w) => ({
  id: w.id,
  title: w.title,
  description: w.description,
  tags: w.tags || [],
  thumbnail: w.thumbnail,
  modelUrl: w.model_url,
  isAi: !!w.is_ai_generated,
  author: w.author?.username || '未知作者',
  likes: w.like_count ?? 0,
  views: w.view_count ?? 0,
  commentCount: w.comment_count ?? 0,
  collected: !!w.current_user_status?.collected,
  isLiked: !!w.current_user_status?.liked,
  isCollected: !!w.current_user_status?.collected
})

const fetchWorks = async (page = 1) => {
  const version = ++requestVersion
  const resp = await getWorks({ page, per_page: 12, q: searchKeyword.value.trim(),
    category: selectedCategory.value, sort: sortBy.value === 'newest' ? 'latest' : sortBy.value })
  if (version !== requestVersion) return
  const mapped = (resp.data || []).map(mapWork)
  loadError.value = false
  if (page === 1) {
    works.value = mapped
  } else {
    works.value.push(...mapped)
  }
  hasMore.value = !!resp.meta?.pagination?.has_next
  loadedPage = page
}

const refreshSidebar = async () => {
  const [ranking, latest] = await Promise.all([
    getWorks({ sort: 'popular', per_page: 5 }), getWorks({ sort: 'latest', per_page: 5 })
  ])
  rankingWorks.value = (ranking.data || []).map(mapWork)
  latestWorks.value = (latest.data || []).map(mapWork)
}
watch([searchKeyword, selectedCategory, sortBy], () => {
  clearTimeout(filterTimer)
  ++requestVersion
  hasMore.value = false
  isLoading.value = true
  filterTimer = setTimeout(async () => {
    try { await fetchWorks(1) } catch { loadError.value = true }
    finally { isLoading.value = false }
  }, 250)
})
onUnmounted(() => { clearTimeout(filterTimer); ++requestVersion })

const refreshPage = async () => {
  isLoading.value = true
  const [main] = await Promise.allSettled([fetchWorks(1), refreshSidebar()])
  loadError.value = main.status === 'rejected'
  isLoading.value = false
}
onMounted(refreshPage)

const loadMore = async () => {
  isLoadingMore.value = true
  try {
    await fetchWorks(loadedPage + 1)
  } catch {
    /* API 拦截器提示；保留当前页用于重试 */
  } finally {
    isLoadingMore.value = false
  }
}

const getFirstTag = (work) => {
  return (work.tags && work.tags.length > 0) ? work.tags[0] : '未分类'
}


const filteredWorks = computed(() => works.value)
const syncWork = (work, changes) => {
  Object.assign(work, changes)
  for (const list of [works.value, rankingWorks.value, latestWorks.value]) {
    const item = list.find(candidate => candidate.id === work.id)
    if (item) Object.assign(item, changes)
  }
  if (selectedWork.value?.id === work.id) Object.assign(selectedWork.value, changes)
}
const interactionBusy = new Set()

// ---- 互动 ----
const handleLike = async (work) => {
  if (!isLoggedIn.value) {
    ElMessage.warning('请先登录')
    return
  }
  if (interactionBusy.has(work.id)) return
  interactionBusy.add(work.id)
  try {
    const resp = work.isLiked ? await unlikeWork(work.id) : await likeWork(work.id)
    syncWork(work, { isLiked: resp.data.liked, likes: resp.data.like_count })
  } catch {
    // 拦截器已提示
  } finally { interactionBusy.delete(work.id) }
}

const handleCollect = async (work) => {
  if (!isLoggedIn.value) {
    ElMessage.warning('请先登录')
    return
  }
  if (interactionBusy.has(work.id)) return
  interactionBusy.add(work.id)
  try {
    const resp = work.isCollected ? await uncollectWork(work.id) : await collectWork(work.id)
    syncWork(work, { isCollected: resp.data.collected, collected: resp.data.collected })
    ElMessage.success(resp.data.collected ? '收藏成功' : '已取消收藏')
  } catch {
    // 拦截器已提示
  } finally { interactionBusy.delete(work.id) }
}

const isOwnComment = (comment) => {
  return comment.user_id && currentUser.value?.id && comment.user_id === currentUser.value.id
}

const formatTime = (iso) => {
  if (!iso) return ''
  return new Date(iso).toLocaleString('zh-CN')
}

// ---- 详情 ----
const viewWorkDetail = async (work) => {
  const version = ++detailVersion
  selectedWork.value = null
  newComment.value = ''
  commentsHasMore.value = false
  showDetailDialog.value = true
  detailLoading.value = true
  comments.value = []
  try {
    const resp = await getWorkDetail(work.id)
    if (version !== detailVersion || !showDetailDialog.value) return
    const d = resp.data
    const mapped = mapWork(d)
    mapped.isLiked = !!d.current_user_status?.liked
    mapped.isCollected = !!d.current_user_status?.collected
    isAuthor.value = !!d.current_user_status?.is_author
    selectedWork.value = mapped
    // 同步卡片交互状态
    const card = works.value.find(w => w.id === work.id)
    if (card) {
      card.isLiked = mapped.isLiked
      card.likes = mapped.likes
    }
    await loadComments(work.id, 1, version)
  } catch {
    if (version === detailVersion) showDetailDialog.value = false
  } finally {
    if (version === detailVersion) detailLoading.value = false
  }
}

const loadComments = async (workId, page = 1, version = detailVersion) => {
  const resp = await getComments(workId, { page, per_page: 20 })
  if (version !== detailVersion || selectedWork.value?.id !== workId || !showDetailDialog.value) return
  const items = resp.data || []
  if (page === 1) comments.value = items
  else comments.value.push(...items.filter(item => !comments.value.some(existing => existing.id === item.id)))
  commentPage = page
  commentsHasMore.value = !!resp.meta?.pagination?.has_next
}
const loadMoreComments = async () => {
  if (commentsLoading.value || !selectedWork.value) return
  commentsLoading.value = true
  try { await loadComments(selectedWork.value.id, commentPage + 1) }
  catch { /* API 拦截器提示 */ }
  finally { commentsLoading.value = false }
}

const submitComment = async () => {
  if (!newComment.value.trim() || !isLoggedIn.value || !selectedWork.value) return
  const work = selectedWork.value
  if (interactionBusy.has(work.id)) return
  interactionBusy.add(work.id)
  try {
    const resp = await postComment(work.id, { content: newComment.value.trim() })
    if (selectedWork.value?.id !== work.id || !showDetailDialog.value) return
    // 评论列表按 created_at 倒序（最新在前），新评论插到列表头部
    comments.value.unshift(resp.data.comment)
    syncWork(selectedWork.value, { commentCount: selectedWork.value.commentCount + 1 })
    newComment.value = ''
    ElMessage.success('评论成功')
  } catch {
    // 拦截器已提示
  } finally { interactionBusy.delete(work.id) }
}

const handleDeleteComment = async (comment) => {
  try {
    await ElMessageBox.confirm('确定删除这条评论吗？', '提示', { type: 'warning' })
  } catch {
    return
  }
  try {
    await deleteComment(comment.id)
    comments.value = comments.value.filter(c => c.id !== comment.id)
    if (selectedWork.value) syncWork(selectedWork.value, { commentCount: Math.max(0, selectedWork.value.commentCount - 1) })
    ElMessage.success('评论已删除')
  } catch {
    // 拦截器已提示
  }
}

// ---- 发布作品 ----
const openUploadDialog = () => {
  if (!isLoggedIn.value) {
    ElMessage.warning('请先登录')
    return
  }
  showUploadDialog.value = true
}

const handleUploadSuccess = (response) => {
  if (response.code === 200) {
    uploadForm.value.thumbnail = response.data.url
    ElMessage.success('图片上传成功')
  } else {
    ElMessage.error(response.message || '图片上传失败')
  }
}

const handleUploadError = () => {
  ElMessage.error('图片上传失败')
}

const submitUpload = async () => {
  submitting.value = true
  try {
    await saveWork({
      title: uploadForm.value.title,
      description: uploadForm.value.description || null,
      tags: uploadForm.value.category ? [uploadForm.value.category] : [],
      thumbnail: uploadForm.value.thumbnail || null
    })
    showUploadDialog.value = false
    uploadForm.value = { title: '', description: '', category: '', thumbnail: null }
    ElMessage.success('作品发布成功')
    await Promise.all([fetchWorks(1), refreshSidebar()])
  } catch {
    // 拦截器已提示
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.community{max-width:1240px}.works-area{min-width:0}.community .works-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.community .work-image img{object-fit:contain;background:#f3eee5}.community .work-description{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}.community .sidebar{position:sticky;top:90px;align-self:flex-start}@media(min-width:1400px){.community .works-grid{grid-template-columns:repeat(3,minmax(0,1fr))}}@media(max-width:600px){.community .works-grid{grid-template-columns:1fr}.community .search-bar,.community .search-bar .el-input{width:100%}.community .sidebar{position:static}.community .toolbar{padding:16px}.community .page-header{align-items:flex-start}}
.community {
  max-width: 1280px;
}

.page-header {
  margin-bottom: 30px;
}

.page-title {
  font-size: 2rem;
  font-weight: 700;
  color: #2c3e50;
  margin: 0;
}

.page-subtitle {
  font-size: 1rem;
  color: #666;
  margin: 8px 0 0;
}

.btn-gradient {
  background: linear-gradient(135deg, #4a90a4, #2d6172) !important;
  border: none !important;
  font-weight: 600 !important;
}

.toolbar {
  padding: 16px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.search-bar .el-input {
  width: 350px;
}

.community-main {
  display: flex;
  gap: 24px;
}

.works-area {
  flex: 1;
}

.loading-state {
  text-align: center;
  padding: 60px 20px;
  background: white;
  border-radius: 16px;
}

.loading-state p {
  margin: 16px 0 0;
  color: #999;
  font-size: 1rem;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  background: white;
  border-radius: 16px;
}

.empty-state p {
  margin: 16px 0 24px;
  color: #999;
  font-size: 1rem;
}

.load-more {
  text-align: center;
  padding: 24px 0;
}

.works-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.work-card {
  background: white;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
  transition: all 0.3s ease;
}

.work-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.12);
}

.work-image-wrapper {
  position: relative;
  cursor: pointer;
}

.work-image {
  width: 100%;
  height: 200px;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
  overflow: hidden;
}

.work-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.work-image-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.category-tag {
  position: absolute;
  top: 12px;
  left: 12px;
  padding: 5px 14px;
  background: rgba(255, 255, 255, 0.95);
  color: #4a90a4;
  font-size: 0.8rem;
  font-weight: 500;
  border-radius: 20px;
  backdrop-filter: blur(4px);
}

.ai-badge {
  display: inline-block;
  padding: 1px 8px;
  margin-right: 6px;
  background: linear-gradient(135deg, #b8860b, #c7693d);
  color: white;
  font-size: 0.7rem;
  border-radius: 10px;
}

.work-content {
  padding: 20px;
}

.work-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 10px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.work-description {
  color: #666;
  font-size: 0.9rem;
  margin: 0 0 12px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.6;
}

.work-author {
  color: #999;
  font-size: 0.85rem;
  margin: 0 0 15px;
}

.work-stats {
  display: flex;
  justify-content: space-between;
  color: #888;
  font-size: 0.85rem;
  margin-bottom: 16px;
}

.like-btn {
  cursor: pointer;
  transition: color 0.2s;
  display: flex;
  align-items: center;
  gap: 4px;
}

.view-detail-btn {
  width: 100%;
  padding: 10px;
  background: linear-gradient(135deg, #4a90a4, #2d6172);
  color: white;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  font-weight: 500;
  font-size: 0.95rem;
  transition: all 0.2s;
}

.view-detail-btn:hover {
  transform: scale(1.02);
  opacity: 0.95;
}

.sidebar {
  width: 280px;
  flex-shrink: 0;
}

.sidebar-card {
  background: white;
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.sidebar-card h3 {
  margin: 0 0 16px;
  font-size: 1rem;
  font-weight: 600;
  color: #2c3e50;
  display: flex;
  align-items: center;
  gap: 8px;
}

.ranking-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.ranking-item {
  display: flex;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px dashed #eee;
  cursor: pointer;
  transition: background 0.2s;
}

.ranking-item:last-child {
  border-bottom: none;
}

.ranking-item:hover {
  background: #f9f9f9;
}

.rank {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f0f0;
  border-radius: 50%;
  font-size: 0.85rem;
  font-weight: 600;
  margin-right: 12px;
}

.rank-1 {
  background: linear-gradient(135deg, #ffd700, #ffb700);
  color: white;
}

.rank-2 {
  background: linear-gradient(135deg, #c0c0c0, #a8a8a8);
  color: white;
}

.rank-3 {
  background: linear-gradient(135deg, #cd7f32, #b87333);
  color: white;
}

.rank-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.rank-title {
  font-size: 0.85rem;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.rank-likes {
  font-size: 0.75rem;
  color: #e74c3c;
}

.category-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.category-list span {
  padding: 6px 14px;
  background: #f5f5f5;
  border-radius: 20px;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s;
  color: #666;
}

.category-list span:hover, .category-list span.active {
  background: #4a90a4;
  color: white;
}

.latest-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.latest-item {
  padding: 10px 0;
  border-bottom: 1px dashed #eee;
  cursor: pointer;
  transition: background 0.2s;
}

.latest-item:last-child {
  border-bottom: none;
}

.latest-item:hover {
  background: #f9f9f9;
}

.latest-title {
  display: block;
  font-size: 0.85rem;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.latest-author {
  display: block;
  font-size: 0.75rem;
  color: #999;
}

.upload-preview {
  max-width: 200px;
  margin-top: 12px;
  border-radius: 8px;
}

.work-detail {
  text-align: center;
  min-height: 200px;
}

.detail-image-wrapper {
  position: relative;
  margin-bottom: 20px;
}

.detail-image {
  width: 100%;
  max-height: 400px;
  object-fit: cover;
  border-radius: 16px;
  background: #f5f5f5;
}

.detail-image-placeholder {
  height: 260px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #999;
}

.detail-image-placeholder p {
  margin: 0;
  font-size: 0.9rem;
}

.detail-category {
  position: absolute;
  top: 15px;
  left: 15px;
  padding: 6px 16px;
  background: rgba(255, 255, 255, 0.95);
  color: #4a90a4;
  font-size: 0.85rem;
  font-weight: 500;
  border-radius: 20px;
}

.detail-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #2c3e50;
  margin: 0 0 12px;
}

.detail-desc {
  color: #666;
  font-size: 1rem;
  line-height: 1.7;
  margin: 0 0 20px;
}

.detail-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid #eee;
}

.detail-author {
  color: #666;
  font-size: 0.9rem;
}

.detail-stats {
  display: flex;
  gap: 24px;
  color: #666;
}

.like-action {
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.comments-section {
  text-align: left;
  margin-top: 20px;
}

.comments-section h4 {
  font-size: 1.1rem;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 20px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.comment-list {
  margin: 0 0 20px;
  max-height: 350px;
  overflow-y: auto;
}

.comment-item {
  padding: 16px 0;
  border-bottom: 1px dashed #eee;
}

.comment-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.comment-author {
  font-weight: 600;
  color: #333;
}

.comment-time {
  font-size: 0.8rem;
  color: #999;
}

.comment-content {
  color: #666;
  line-height: 1.6;
  margin: 0;
}

.comment-actions {
  margin-top: 10px;
}

.reply-btn {
  font-size: 0.85rem;
  color: #e74c3c;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
}

.no-comments {
  text-align: center;
  color: #999;
  padding: 20px;
}

@media (max-width: 992px) {
  .community-main {
    flex-direction: column;
  }

  .sidebar {
    width: 100%;
  }

  .search-bar .el-input {
    width: 100%;
  }
}
</style>
