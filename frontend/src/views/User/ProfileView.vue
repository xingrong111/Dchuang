<template>
  <div class="profile page-container">
    <div class="profile-header">
      <div class="avatar-section">
        <div class="avatar-wrapper">
          <div class="avatar">
            <img v-if="userStore.user?.avatar && userStore.user.avatar !== 'default_avatar.png'" :src="userStore.user.avatar" style="width:100%;height:100%;object-fit:cover;border-radius:50%" alt="头像" /><User v-else />
          </div>
          <label class="avatar-edit-btn" @click="uploadAvatar">
            <el-icon><EditPen /></el-icon>
          </label>
        </div>
        <div class="user-info">
          <h2>{{ userStore.user?.username || userStore.user?.email || '用户' }}</h2>
          <p>{{ userStore.user?.email }}</p>
        </div>
      </div>
      <div class="header-actions">
        <el-button @click="editProfile">编辑资料</el-button>
        <el-button type="primary" @click="activeTab = 'works'">我的作品</el-button>
      </div>
    </div>

    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-icon">
          <Upload />
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ statistics.works }}</span>
          <span class="stat-label">作品数</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">
          <Star />
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ statistics.collections }}</span>
          <span class="stat-label">收藏数</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon credits">
          <Wallet />
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ credits ?? '--' }}</span>
          <span class="stat-label">积分余额</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">
          <Star />
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ statistics.likes }}</span>
          <span class="stat-label">获赞数</span>
        </div>
      </div>
    </div>

    <div class="profile-tabs">
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="我的作品" name="works">
          <div class="tab-toolbar">
            <el-button type="primary" @click="$router.push('/workshop')">
              <el-icon><Plus /></el-icon>
              发布作品
            </el-button>
            <div class="filter-options">
              <el-select v-model="worksFilter" placeholder="筛选" style="width: 120px;">
                <el-option label="全部" value="all" />
                <el-option label="已发布" value="已发布" />
                <el-option label="私有" value="私有" />
              </el-select>
              <el-select v-model="worksSort" placeholder="排序" style="width: 120px;">
                <el-option label="最新发布" value="newest" />
                <el-option label="最多点赞" value="likes" />
              </el-select>
            </div>
          </div>
          <div class="works-list">
            <div v-if="filteredWorks.length === 0" class="empty-state">
              <el-icon size="64" color="#ccc"><Upload /></el-icon>
              <p>还没有作品，快去创作吧！</p>
              <el-button type="primary" @click="$router.push('/workshop')">开始创作</el-button>
            </div>
            <div v-else class="works-grid">
              <div class="work-card" v-for="work in filteredWorks" :key="work.id">
                <div class="work-image-wrapper">
                  <img :src="work.thumbnail || logoUrl" :alt="work.title" />
                  <div class="work-status" :class="work.status">{{ work.status }}</div>
                </div>
                <div class="work-content">
                  <h4>{{ work.title }}</h4>
                  <div class="work-stats">
                    <span><el-icon><Star /></el-icon> {{ work.likes }}</span>
                    <span><el-icon><Picture /></el-icon> {{ work.views }}</span>
                  </div>
                  <div class="work-actions">
                    <el-button size="small" @click="viewWorkDetail(work)">查看</el-button>
                    <el-button size="small" type="danger" @click="deleteWork(work)">删除</el-button>
                    <el-button size="small" @click="submitCertificate(work)">提交存证</el-button>
                    <el-button size="small" @click="verifyCertificate(work)">验证存证</el-button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="我的收藏" name="collections">
          <div class="collections-list">
            <div v-for="work in collections" :key="work.id" class="work-card" @click="viewWorkDetail({ ...work, likes: work.like_count, views: work.view_count })"><h4>{{ work.title }}</h4><p>{{ work.description }}</p></div>
            <div v-if="!collections.length" class="empty-state">
              <el-icon size="64" color="#ccc"><Star /></el-icon>
              <p>还没有收藏作品</p>
              <el-button type="primary" @click="$router.push('/community')">去社区逛逛</el-button>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="历史订单" name="orders">
          <p>当前文创页面为概念展示，不提供购买。此处保留历史演示订单记录。</p>
          <div class="tab-toolbar">
            <el-select v-model="ordersFilter" placeholder="订单状态" style="width: 120px;">
              <el-option label="全部" value="all" />
              <el-option label="待确认" value="待确认" /><el-option label="已取消" value="已取消" />
              <el-option label="待发货" value="待发货" />
              <el-option label="已发货" value="已发货" />
              <el-option label="已完成" value="已完成" />
            </el-select>
          </div>
          <div class="orders-list">
            <div v-for="order in filteredOrders" :key="order.id" class="work-card"><h4>订单 {{ order.id.slice(0, 8) }} · {{ order.status }}</h4><p v-for="item in order.items" :key="item.product_id">{{ item.name }} × {{ item.quantity }}</p><p>合计 ¥{{ order.total }}</p><el-button v-if="order.status === '待确认'" @click="doCancelOrder(order)">取消订单</el-button></div>
            <div v-if="!filteredOrders.length" class="empty-state">
              <el-icon size="64" color="#ccc"><ShoppingCart /></el-icon>
              <p>暂无符合条件的订单</p>
              <el-button type="primary" @click="$router.push('/shop')">浏览文创设计</el-button>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="创作任务历史" name="ai-history">
          <el-table :data="aiHistory"><el-table-column prop="task_type" label="类型"/><el-table-column prop="provider" label="服务"/><el-table-column prop="status" label="状态"/><el-table-column prop="error_message" label="错误"/><el-table-column label="模型"><template #default="{ row }"><a v-if="row.artwork?.model_url || row.result_url" :href="row.artwork?.model_url || row.result_url" target="_blank" rel="noopener">下载模型</a></template></el-table-column></el-table>
        </el-tab-pane>
        <el-tab-pane label="个人设置" name="settings">
          <div class="settings-container">
            <div class="settings-section">
              <h3><el-icon><User /></el-icon> 基本信息</h3>
              <el-form :model="profileForm" label-width="100px">
                <el-form-item label="用户名">
                  <el-input v-model="profileForm.username" />
                </el-form-item>
                <el-form-item label="邮箱">
                  <el-input v-model="profileForm.email" disabled />
                </el-form-item>
                <el-form-item label="简介">
                  <el-input v-model="profileForm.bio" type="textarea" :rows="3" placeholder="介绍一下自己..." />
                </el-form-item>
                <el-form-item label="头像">
                  <div class="avatar-upload">
                    <div class="preview-avatar">
                      <User />
                    </div>
                    <el-upload
                      :http-request="doUploadAvatar"
                      :show-file-list="false"
                      accept="image/*"
                    >
                      <el-button size="small" type="primary">上传头像</el-button>
                    </el-upload>
                  </div>
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="saveProfile">保存修改</el-button>
                </el-form-item>
              </el-form>
            </div>

            <div class="settings-section">
              <h3><el-icon><Key /></el-icon> 修改密码</h3>
              <el-form :model="passwordForm" label-width="100px">
                <el-form-item label="当前密码">
                  <el-input type="password" v-model="passwordForm.currentPassword" placeholder="请输入当前密码" />
                </el-form-item>
                <el-form-item label="新密码">
                  <el-input type="password" v-model="passwordForm.newPassword" placeholder="请输入新密码" />
                </el-form-item>
                <el-form-item label="确认密码">
                  <el-input type="password" v-model="passwordForm.confirmPassword" placeholder="请再次输入新密码" />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="changePassword">修改密码</el-button>
                </el-form-item>
              </el-form>
            </div>



          </div>
        </el-tab-pane>
      </el-tabs>
      <el-pagination v-if="activeTab !== 'settings' && totals[activeTab] > 12"
        :current-page="pages[activeTab]" :page-size="12" :total="totals[activeTab]"
        layout="prev, pager, next, total" @current-change="changePage" />
    </div>

    <el-dialog title="作品详情" v-model="showWorkDialog" width="650px" top="30px">
      <div v-if="selectedWork" class="work-detail-content">
        <img :src="selectedWork.thumbnail || logoUrl" class="detail-img" />
        <h3>{{ selectedWork.title }}</h3>
        <ModelPreview v-if="selectedWork.model_url" :url="selectedWork.model_url" />
        <p>{{ selectedWork.description }}</p>
        <div class="detail-stats">
          <span><el-icon><Star /></el-icon> {{ selectedWork.likes }}</span>
          <span><el-icon><Picture /></el-icon> {{ selectedWork.views }}</span>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import ModelPreview from '@/components/ModelPreview.vue'
import logoUrl from '@/assets/images/logo.svg'
import { ElMessage, ElDialog } from 'element-plus'
import { User, Upload, Star, ShoppingCart, EditPen, Plus, Picture, Key, Wallet } from '@element-plus/icons-vue'
import { useUserStore } from '@/store/userStore'
import { deleteWork as deleteWorkApi, certifyWork, getCertificate } from '@/api/workshop'
import { ElMessageBox } from 'element-plus'
import { getUserCredits, uploadAvatar as uploadAvatarApi, updateProfile, updatePassword, getCollections, getOwnWorks, getUserStatistics } from '@/api/user'
import { getOrders, cancelOrder } from '@/api/shop'
import { getAIHistory } from '@/api/ai'

const userStore = useUserStore()
const activeTab = ref('works')
const statistics = ref({ works: 0, collections: 0, likes: 0 })
const pages = ref({ works: 1, collections: 1, orders: 1, 'ai-history': 1 })
const totals = ref({ works: 0, collections: 0, orders: 0, 'ai-history': 0 })
const refreshStatistics = async () => { statistics.value = (await getUserStatistics()).data }


const profileForm = ref({
  username: userStore.user?.username || '',
  email: userStore.user?.email || '',
  bio: userStore.user?.bio || ''
})

const passwordForm = ref({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})


const worksFilter = ref('all')
const worksSort = ref('newest')
const ordersFilter = ref('all')

const showWorkDialog = ref(false)
const selectedWork = ref(null)

// --- 真实数据（后端接入） ---
const credits = ref(null)
const myWorks = ref([])
const worksLoading = ref(false)
let worksRequest = 0
const tabRequests = {}

const loadCredits = async () => {
  try {
    const resp = await getUserCredits({ page: 1, per_page: 1 })
    credits.value = resp.data?.balance ?? null
  } catch {
    credits.value = null
  }
}

const fetchMyWorks = async () => {
  const authorId = userStore.user?.id
  if (!authorId) return
  worksLoading.value = true
  const version = ++worksRequest
  try {
    const resp = await getOwnWorks({ page: pages.value.works, per_page: 12, sort: worksSort.value === 'likes' ? 'likes' : 'latest', visibility: worksFilter.value === 'all' ? undefined : worksFilter.value === '私有' ? 'private' : 'public' })
    if (version !== worksRequest) return
    totals.value.works = resp.meta?.pagination?.total || 0
    myWorks.value = (resp.data || []).map((w) => ({
      ...w,
      likes: w.like_count ?? 0,
      views: w.view_count ?? 0,
      status: w.is_public ? '已发布' : '私有'
    }))
  } finally {
    if (version === worksRequest) worksLoading.value = false
  }
}

onMounted(async () => {
  try { await Promise.all([loadCredits(), fetchMyWorks(), refreshStatistics()]) }
  catch { /* API 拦截器提示 */ }
})

const filteredWorks = computed(() => myWorks.value)
watch([worksFilter, worksSort], async () => {
  pages.value.works = 1
  try { await fetchMyWorks() } catch { /* API 拦截器提示 */ }
})
watch(ordersFilter, () => { pages.value.orders = 1; handleTabChange('orders') })

const editProfile = () => {
  activeTab.value = 'settings'
}
const submitCertificate = async work => {
  await ElMessageBox.confirm('将向配置的区块链节点提交作品指纹。节点可能收取链上费用，确认提交？', '作品存证')
  const response = await certifyWork(work.id)
  ElMessage.info(response.data.status === 'CONFIRMED' ? '作品已存证' : '交易已提交，等待链上确认')
}
const verifyCertificate = async work => {
  const response = await getCertificate(work.id)
  await ElMessageBox.alert(`状态：${response.data.status}；内容指纹：${response.data.digest}；交易：${response.data.transaction_id || '尚未提交'}`, '存证验证')
}

const saveProfile = async () => {
  if (savingProfile.value) return
  savingProfile.value = true
  try {
    await updateProfile({ username: profileForm.value.username, bio: profileForm.value.bio })
    await userStore.fetchUserInfo()
    ElMessage.success('资料已保存')
  } finally { savingProfile.value = false }
}

const changePassword = async () => {
  if (changingPassword.value) return
  const form = passwordForm.value
  if (form.newPassword !== form.confirmPassword) return ElMessage.warning('两次输入的密码不一致')
  changingPassword.value = true
  try {
    await updatePassword({ current_password: form.currentPassword, new_password: form.newPassword })
    passwordForm.value = { currentPassword: '', newPassword: '', confirmPassword: '' }
    ElMessage.success('密码已修改')
  } finally { changingPassword.value = false }
}

const uploadAvatar = () => { activeTab.value = 'settings' }

const doUploadAvatar = async ({ file }) => {
  try {
    await uploadAvatarApi(file)
    ElMessage.success('头像上传成功')
    await userStore.fetchUserInfo()
  } catch {
    /* 错误提示由 axios 拦截器统一处理 */
  }
}

const deleteWork = async (work) => {
  try {
    await deleteWorkApi(work.id)
    if (myWorks.value.length === 1 && pages.value.works > 1) pages.value.works--
    await Promise.all([fetchMyWorks(), refreshStatistics()])
    ElMessage.success('作品已删除')
  } catch {
    /* 错误提示由 axios 拦截器统一处理 */
  }
}

const viewWorkDetail = (work) => {
  selectedWork.value = work
  showWorkDialog.value = true
}

const savingProfile = ref(false)
const changingPassword = ref(false)
const collections = ref([])
const orders = ref([])
const filteredOrders = computed(() => ordersFilter.value === 'all' ? orders.value : orders.value.filter(o => o.status === ordersFilter.value))
const aiHistory = ref([])
const handleTabChange = async (tab) => {
  try {
    if (tab === 'works') return await fetchMyWorks()
    const loaders = { collections: getCollections, orders: getOrders, 'ai-history': getAIHistory }
    if (!loaders[tab]) return
    const version = tabRequests[tab] = (tabRequests[tab] || 0) + 1
    const resp = await loaders[tab]({ page: pages.value[tab], per_page: 12, status: tab === 'orders' && ordersFilter.value !== 'all' ? ordersFilter.value : undefined })
    if (version !== tabRequests[tab]) return
    totals.value[tab] = resp.meta?.pagination?.total || 0
    const targets = { collections, orders, 'ai-history': aiHistory }
    targets[tab].value = resp.data || []
  } catch { /* API 拦截器提示 */ }
}
const changePage = async page => {
  pages.value[activeTab.value] = page
  await handleTabChange(activeTab.value)
}
const doCancelOrder = async (order) => {
  await cancelOrder(order.id)
  await handleTabChange('orders')
}
</script>

<style scoped>
.profile {
  max-width: 1280px;
}

.profile-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  padding: 2.5rem;
  background: linear-gradient(135deg, #4a90a4 0%, #2d6172 100%);
  border-radius: 20px;
  color: white;
  box-shadow: 0 8px 24px rgba(74, 144, 164, 0.3);
}

.avatar-section {
  display: flex;
  align-items: center;
  gap: 2rem;
}

.avatar-wrapper {
  position: relative;
}

.avatar {
  width: 110px;
  height: 110px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 52px;
  border: 4px solid rgba(255, 255, 255, 0.3);
}

.avatar-edit-btn {
  position: absolute;
  bottom: 2px;
  right: 2px;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: #4a90a4;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 16px;
  border: 3px solid white;
}

.user-info h2 {
  margin: 0;
  font-size: 1.6rem;
  font-weight: 700;
}

.user-info p {
  margin: 0.6rem 0 0;
  opacity: 0.85;
  font-size: 1rem;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.stats-row {
  display: flex;
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.stat-card {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 1.2rem;
  padding: 1.8rem;
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
  transition: all 0.2s;
}

.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
}

.stat-icon {
  width: 55px;
  height: 55px;
  border-radius: 14px;
  background: linear-gradient(135deg, #4a90a4, #2d6172);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 26px;
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 1.7rem;
  font-weight: 700;
  color: #2c3e50;
}

.stat-label {
  font-size: 0.85rem;
  color: #999;
}

.profile-tabs {
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

.tab-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #eee;
}

.filter-options {
  display: flex;
  gap: 12px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #999;
}

.empty-state p {
  margin: 16px 0;
  font-size: 1rem;
}

.works-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 20px;
  padding: 1.5rem;
}

.work-card {
  background: white;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
  transition: all 0.3s;
}

.work-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.12);
}

.work-image-wrapper {
  position: relative;
}

.work-image-wrapper img {
  width: 100%;
  height: 180px;
  object-fit: cover;
  background: #f5f5f5;
}

.work-status {
  position: absolute;
  top: 12px;
  right: 12px;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 0.75rem;
  color: white;
}

.work-status.已发布 {
  background: #4a90a4;
}

.work-status.草稿 {
  background: #f5a623;
}

.collection-type {
  position: absolute;
  top: 12px;
  left: 12px;
  padding: 6px 14px;
  background: rgba(74, 144, 164, 0.9);
  color: white;
  border-radius: 20px;
  font-size: 0.75rem;
}

.work-content {
  padding: 18px;
}

.work-card h4 {
  margin: 0 0 12px;
  font-size: 1rem;
  font-weight: 600;
  color: #2c3e50;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.work-card .author {
  margin: 0 0 12px;
  font-size: 0.85rem;
  color: #999;
}

.work-stats {
  display: flex;
  gap: 1.5rem;
  margin-bottom: 14px;
  color: #666;
  font-size: 0.85rem;
}

.work-actions {
  display: flex;
  gap: 8px;
}

.orders-list-container {
  padding: 1.5rem;
}

.order-card {
  border: 1px solid #eee;
  border-radius: 12px;
  margin-bottom: 1.5rem;
  overflow: hidden;
  background: white;
}

.order-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.2rem;
  background: #f9f9f9;
}

.order-id {
  font-size: 0.9rem;
  color: #666;
}

.order-items {
  padding: 1.2rem;
}

.order-item {
  display: flex;
  gap: 1.2rem;
  margin-bottom: 1.2rem;
}

.order-item:last-child {
  margin-bottom: 0;
}

.order-item-img {
  width: 90px;
  height: 90px;
  object-fit: cover;
  border-radius: 8px;
  background: #f5f5f5;
}

.order-item-info {
  flex: 1;
}

.order-item-name {
  margin: 0 0 0.4rem;
  font-weight: 600;
  color: #333;
}

.order-item-spec {
  margin: 0 0 0.4rem;
  font-size: 0.85rem;
  color: #999;
}

.order-item-price-row {
  display: flex;
  justify-content: space-between;
}

.order-item-price {
  color: #e74c3c;
  font-weight: 600;
}

.order-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.2rem;
  border-top: 1px dashed #eee;
}

.order-time {
  font-size: 0.85rem;
  color: #999;
}

.order-total {
  font-size: 1.1rem;
  color: #e74c3c;
}

.order-total strong {
  font-size: 1.4rem;
}

.order-actions {
  display: flex;
  gap: 10px;
}

.settings-container {
  padding: 1.5rem;
}

.settings-section {
  padding: 20px;
  border-radius: 12px;
  background: #f9f9f9;
  margin-bottom: 1.5rem;
}

.settings-section:last-child {
  margin-bottom: 0;
}

.settings-section h3 {
  margin: 0 0 1.2rem;
  font-size: 1.1rem;
  font-weight: 600;
  color: #2c3e50;
  display: flex;
  align-items: center;
  gap: 10px;
}

.avatar-upload {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.preview-avatar {
  width: 90px;
  height: 90px;
  border-radius: 50%;
  background: #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36px;
}

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.2rem 0;
  border-bottom: 1px dashed #ddd;
}

.setting-item:last-child {
  border-bottom: none;
}

.setting-item span {
  font-size: 0.95rem;
  color: #333;
}

.work-detail-content {
  text-align: center;
}

.detail-img {
  width: 100%;
  height: 320px;
  object-fit: cover;
  border-radius: 12px;
  background: #f5f5f5;
  margin-bottom: 1.5rem;
}

.detail-stats {
  display: flex;
  justify-content: center;
  gap: 3rem;
  margin-top: 1.5rem;
  font-size: 1rem;
  color: #666;
}

.order-detail-content {
  text-align: left;
}

.detail-section {
  margin-bottom: 1.5rem;
}

.detail-section h4 {
  margin: 0 0 1rem;
  font-size: 1rem;
  font-weight: 600;
  color: #2c3e50;
  display: flex;
  align-items: center;
  gap: 8px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 0.6rem 0;
  border-bottom: 1px dashed #eee;
  color: #666;
}

.detail-row.total {
  font-weight: bold;
  color: #e74c3c;
  border-bottom: none;
  font-size: 1.1rem;
}

@media (max-width: 992px) {
  .profile-header {
    flex-direction: column;
    gap: 1.5rem;
    text-align: center;
  }

  .stats-row {
    flex-direction: column;
  }

  .stat-card {
    flex-direction: row;
  }

  .works-grid {
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  }

  .order-footer {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }
}
</style>
