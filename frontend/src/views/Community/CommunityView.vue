<template>
  <div class="community page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">创作社区</h1>
        <p class="page-subtitle">分享你的作品，发现更多灵感</p>
      </div>
      <el-button type="primary" class="btn-gradient" @click="showUploadDialog = true">
        <el-icon><Upload /></el-icon>
        上传作品
      </el-button>
    </div>

    <div class="toolbar">
      <div class="search-bar">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索作品..."
          prefix-icon="Search"
          @keyup.enter="handleSearch"
          clearable
        />
        <el-button type="primary" @click="handleSearch">搜索</el-button>
      </div>

      <div class="filter-section">
        <el-select v-model="selectedCategory" placeholder="分类筛选" style="width: 150px;">
          <el-option label="全部" value="" />
          <el-option label="惠山泥人" value="huishan" />
          <el-option label="锡绣" value="xixiu" />
          <el-option label="紫砂陶艺" value="zisha" />
          <el-option label="吴歌" value="wuge" />
          <el-option label="其他" value="other" />
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
        <div v-if="filteredWorks.length === 0" class="empty-state">
          <el-icon size="64" color="#ccc"><Picture /></el-icon>
          <p>没有找到相关作品</p>
          <el-button type="primary" @click="showUploadDialog = true">发布作品</el-button>
        </div>
        <div v-else class="works-grid">
          <div class="work-card" v-for="work in filteredWorks" :key="work.id">
            <div class="work-image-wrapper">
              <div class="work-image">
                <img :src="work.image || '/assets/images/logo.svg'" :alt="work.title" />
              </div>
              <div class="category-tag">{{ getCategoryName(work.category) }}</div>
            </div>
            <div class="work-content">
              <h4 class="work-title">{{ work.title }}</h4>
              <p class="work-description">{{ work.description }}</p>
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
          </div>
        </div>

        <div class="sidebar-card">
          <h3><el-icon><Grid /></el-icon> 作品分类</h3>
          <div class="category-list">
            <span
              v-for="cat in categories"
              :key="cat.value"
              :class="{ active: selectedCategory === cat.value }"
              @click="selectedCategory = cat.value"
            >
              {{ cat.label }}
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
          </div>
        </div>
      </div>
    </div>

    <el-dialog title="上传作品" v-model="showUploadDialog" width="520px" top="50px">
      <el-form :model="uploadForm" label-width="90px" class="upload-form">
        <el-form-item label="作品标题" required>
          <el-input v-model="uploadForm.title" placeholder="请输入作品标题" />
        </el-form-item>
        <el-form-item label="作品描述" required>
          <el-input v-model="uploadForm.description" type="textarea" placeholder="请输入作品描述" :rows="3" />
        </el-form-item>
        <el-form-item label="作品分类" required>
          <el-select v-model="uploadForm.category" placeholder="请选择分类">
            <el-option v-for="cat in categories" :key="cat.value" :label="cat.label" :value="cat.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="作品图片">
          <el-upload
            action="/api/workshop/upload"
            :on-success="handleUploadSuccess"
            :on-error="handleUploadError"
            :show-file-list="false"
            accept="image/*"
          >
            <el-button type="primary">选择图片</el-button>
          </el-upload>
          <img v-if="uploadForm.image" :src="uploadForm.image" class="upload-preview" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button type="primary" @click="submitUpload" :disabled="!uploadForm.title || !uploadForm.category">提交</el-button>
      </template>
    </el-dialog>

    <el-dialog title="作品详情" v-model="showDetailDialog" width="650px" top="30px">
      <div v-if="selectedWork" class="work-detail">
        <div class="detail-image-wrapper">
          <img :src="selectedWork.image || '/assets/images/logo.svg'" :alt="selectedWork.title" class="detail-image" />
          <div class="detail-category">{{ getCategoryName(selectedWork.category) }}</div>
        </div>
        <h3 class="detail-title">{{ selectedWork.title }}</h3>
        <p class="detail-desc">{{ selectedWork.description }}</p>
        <div class="detail-meta">
          <span class="detail-author">作者: {{ selectedWork.author }}</span>
          <div class="detail-stats">
            <span @click="handleLike(selectedWork)" class="like-action">
              <el-icon :color="selectedWork.isLiked ? '#e74c3c' : '#999'"><Star /></el-icon>
              {{ selectedWork.likes }}
            </span>
            <span>
              <el-icon><Picture /></el-icon>
              {{ selectedWork.views }}
            </span>
            <span>
              <el-icon><ChatRound /></el-icon>
              {{ selectedWork.commentCount }}
            </span>
          </div>
        </div>

        <div class="comments-section">
          <h4><el-icon><ChatRound /></el-icon> 评论 ({{ selectedWork.commentCount }})</h4>
          <div class="comment-list">
            <div v-for="comment in selectedWork.comments" :key="comment.id" class="comment-item">
              <div class="comment-header">
                <span class="comment-author">{{ comment.author }}</span>
                <span class="comment-time">{{ comment.time }}</span>
              </div>
              <p class="comment-content">{{ comment.content }}</p>
              <div class="comment-actions">
                <span class="reply-btn" @click="replyToComment(comment)">
                  <el-icon><Message /></el-icon> 回复
                </span>
                <span v-if="comment.replies && comment.replies.length">
                  <el-icon><ChatDotSquare /></el-icon> {{ comment.replies.length }}
                </span>
              </div>
              <div v-if="comment.replies && comment.replies.length" class="reply-list">
                <div v-for="reply in comment.replies" :key="reply.id" class="reply-item">
                  <span class="reply-author">{{ reply.author }}:</span>
                  <span class="reply-content">{{ reply.content }}</span>
                </div>
              </div>
              <div v-if="replyingTo === comment.id" class="reply-input">
                <el-input
                  v-model="replyContent"
                  placeholder="输入回复..."
                  @keyup.enter="submitReply(comment)"
                  size="small"
                />
                <el-button size="small" type="primary" @click="submitReply(comment)">发送</el-button>
                <el-button size="small" @click="replyingTo = null">取消</el-button>
              </div>
            </div>
            <p v-if="!selectedWork.comments || selectedWork.comments.length === 0" class="no-comments">暂无评论，快来发表第一条评论吧</p>
          </div>
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
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Upload, Star, Picture, ChatRound, Search, Trophy, Grid, Clock, Message, ChatDotSquare } from '@element-plus/icons-vue'

const categories = [
  { label: '惠山泥人', value: 'huishan' },
  { label: '锡绣', value: 'xixiu' },
  { label: '紫砂陶艺', value: 'zisha' },
  { label: '吴歌', value: 'wuge' },
  { label: '其他', value: 'other' }
]

const works = ref([
  {
    id: 1,
    title: '现代风格惠山泥人',
    description: '结合现代审美重新设计的惠山泥人作品，保留传统工艺的同时融入了当代艺术元素。',
    author: '创意达人',
    likes: 124,
    views: 568,
    commentCount: 23,
    isLiked: false,
    image: null,
    category: 'huishan',
    comments: [
      { id: 1, author: '艺术爱好者', content: '非常有创意！', time: '2024-01-15 10:30', replies: [
        { id: 101, author: '创意达人', content: '谢谢！' }
      ]},
      { id: 2, author: '非遗传承人', content: '传统与现代的完美结合', time: '2024-01-15 11:00', replies: [] }
    ]
  },
  {
    id: 2,
    title: '数字锡绣-江南水乡',
    description: '运用数字技术还原江南水乡的细腻之美，展现锡绣的独特魅力。',
    author: '绣娘传人',
    likes: 89,
    views: 342,
    commentCount: 15,
    isLiked: true,
    image: null,
    category: 'xixiu',
    comments: [
      { id: 1, author: '文化学者', content: '太美了，江南水乡的韵味十足', time: '2024-01-14 09:15', replies: [] }
    ]
  },
  {
    id: 3,
    title: 'Q版紫砂茶宠',
    description: '以传统紫砂工艺为基础，设计的可爱Q版茶宠系列。',
    author: '陶艺新手',
    likes: 156,
    views: 623,
    commentCount: 31,
    isLiked: false,
    image: null,
    category: 'zisha',
    comments: []
  },
  {
    id: 4,
    title: '吴歌主题插画',
    description: '以吴歌为主题创作的插画作品，展现江南民歌的意境之美。',
    author: '音乐爱好者',
    likes: 67,
    views: 289,
    commentCount: 8,
    isLiked: false,
    image: null,
    category: 'wuge',
    comments: []
  },
  {
    id: 5,
    title: '精微绣花鸟图',
    description: '传承百年的精微绣技艺，一针一线勾勒出栩栩如生的花鸟。',
    author: '非遗大师',
    likes: 234,
    views: 890,
    commentCount: 45,
    isLiked: false,
    image: null,
    category: 'xixiu',
    comments: []
  },
  {
    id: 6,
    title: '传统惠山泥人阿福',
    description: '经典的惠山泥人阿福形象，寓意吉祥如意，福寿安康。',
    author: '泥人世家',
    likes: 178,
    views: 543,
    commentCount: 28,
    isLiked: true,
    image: null,
    category: 'huishan',
    comments: []
  }
])

const showUploadDialog = ref(false)
const showDetailDialog = ref(false)
const selectedWork = ref(null)
const newComment = ref('')
const replyContent = ref('')
const replyingTo = ref(null)

const searchKeyword = ref('')
const selectedCategory = ref('')
const sortBy = ref('newest')

const uploadForm = ref({
  title: '',
  description: '',
  image: null,
  category: ''
})

const isLoggedIn = computed(() => localStorage.getItem('user') !== null)

const filteredWorks = computed(() => {
  let result = [...works.value]
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    result = result.filter(w =>
      w.title.toLowerCase().includes(keyword) ||
      w.description.toLowerCase().includes(keyword) ||
      w.author.toLowerCase().includes(keyword)
    )
  }
  if (selectedCategory.value) {
    result = result.filter(w => w.category === selectedCategory.value)
  }
  switch (sortBy.value) {
    case 'newest':
      result.sort((a, b) => b.id - a.id)
      break
    case 'popular':
      result.sort((a, b) => b.likes - a.likes)
      break
    case 'comments':
      result.sort((a, b) => b.commentCount - a.commentCount)
      break
  }
  return result
})

const rankingWorks = computed(() => {
  return [...works.value].sort((a, b) => b.likes - a.likes).slice(0, 5)
})

const latestWorks = computed(() => {
  return [...works.value].sort((a, b) => b.id - a.id).slice(0, 5)
})

const getCategoryName = (category) => {
  const cat = categories.find(c => c.value === category)
  return cat ? cat.label : '其他'
}

const handleSearch = () => {
  showDetailDialog.value = false
}

const handleLike = (work) => {
  if (!isLoggedIn.value) {
    ElMessage.warning('请先登录')
    return
  }
  work.isLiked = !work.isLiked
  work.likes += work.isLiked ? 1 : -1
  ElMessage.success(work.isLiked ? '点赞成功' : '取消点赞')
}

const viewWorkDetail = (work) => {
  selectedWork.value = work
  work.views++
  showDetailDialog.value = true
}

const submitComment = () => {
  if (!newComment.value.trim() || !isLoggedIn.value) return
  const user = JSON.parse(localStorage.getItem('user'))
  selectedWork.value.comments.push({
    id: Date.now(),
    author: user.username || '用户',
    content: newComment.value.trim(),
    time: new Date().toLocaleString('zh-CN'),
    replies: []
  })
  selectedWork.value.commentCount++
  newComment.value = ''
  ElMessage.success('评论成功')
}

const replyToComment = (comment) => {
  if (!isLoggedIn.value) {
    ElMessage.warning('请先登录')
    return
  }
  replyingTo.value = replyingTo.value === comment.id ? null : comment.id
}

const submitReply = (comment) => {
  if (!replyContent.value.trim() || !isLoggedIn.value) return
  const user = JSON.parse(localStorage.getItem('user'))
  if (!comment.replies) comment.replies = []
  comment.replies.push({
    id: Date.now(),
    author: user.username || '用户',
    content: replyContent.value.trim()
  })
  replyContent.value = ''
  replyingTo.value = null
  ElMessage.success('回复成功')
}

const handleUploadSuccess = (response) => {
  uploadForm.value.image = response.data.url
  ElMessage.success('图片上传成功')
}

const handleUploadError = () => {
  ElMessage.error('图片上传失败')
}

const submitUpload = () => {
  const user = JSON.parse(localStorage.getItem('user'))
  works.value.unshift({
    id: Date.now(),
    title: uploadForm.value.title,
    description: uploadForm.value.description,
    image: uploadForm.value.image,
    author: user?.username || '用户',
    likes: 0,
    views: 0,
    commentCount: 0,
    isLiked: false,
    category: uploadForm.value.category,
    comments: []
  })
  showUploadDialog.value = false
  uploadForm.value = { title: '', description: '', image: null, category: '' }
  ElMessage.success('作品上传成功')
}
</script>

<style scoped>
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
}

.comment-actions {
  margin-top: 10px;
}

.reply-btn {
  font-size: 0.85rem;
  color: #4a90a4;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
}

.reply-list {
  margin-top: 12px;
  padding-left: 20px;
  border-left: 2px solid #ddd;
}

.reply-item {
  padding: 10px 0;
}

.reply-author {
  font-weight: 500;
  color: #333;
}

.reply-content {
  color: #666;
}

.reply-input {
  display: flex;
  gap: 10px;
  margin-top: 12px;
  align-items: center;
}

.reply-input .el-input {
  flex: 1;
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

  .toolbar {
    flex-direction: column;
    gap: 16px;
  }
}
</style>
