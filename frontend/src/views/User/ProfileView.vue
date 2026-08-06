<template>
  <div class="profile page-container">
    <div class="profile-header">
      <div class="avatar-section">
        <div class="avatar-wrapper">
          <div class="avatar">
            <User />
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
          <span class="stat-value">{{ myWorks.length }}</span>
          <span class="stat-label">作品数</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">
          <Star />
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ myCollections.length }}</span>
          <span class="stat-label">收藏数</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">
          <ShoppingCart />
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ myOrders.length }}</span>
          <span class="stat-label">订单数</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">
          <Star />
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ totalLikes }}</span>
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
                <el-option label="已发布" value="published" />
                <el-option label="草稿" value="draft" />
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
                  <img :src="work.image || '/assets/images/logo.svg'" :alt="work.title" />
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
                    <el-button size="small">编辑</el-button>
                    <el-button size="small" type="danger" @click="deleteWork(work)">删除</el-button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="我的收藏" name="collections">
          <div class="tab-toolbar">
            <el-select v-model="collectionsFilter" placeholder="筛选" style="width: 120px;">
              <el-option label="全部" value="all" />
              <el-option label="作品" value="work" />
              <el-option label="商品" value="product" />
            </el-select>
          </div>
          <div class="collections-list">
            <div v-if="filteredCollections.length === 0" class="empty-state">
              <el-icon size="64" color="#ccc"><Star /></el-icon>
              <p>还没有收藏任何内容</p>
              <el-button type="primary" @click="$router.push('/community')">去发现</el-button>
            </div>
            <div v-else class="works-grid">
              <div class="work-card" v-for="work in filteredCollections" :key="work.id">
                <div class="work-image-wrapper">
                  <img :src="work.image || '/assets/images/logo.svg'" :alt="work.title" />
                  <div class="collection-type">{{ work.type === 'work' ? '作品' : '商品' }}</div>
                </div>
                <div class="work-content">
                  <h4>{{ work.title }}</h4>
                  <p class="author">by {{ work.author }}</p>
                  <div class="work-stats">
                    <span><el-icon><Star /></el-icon> {{ work.likes }}</span>
                  </div>
                  <div class="work-actions">
                    <el-button size="small" @click="viewCollectionDetail(work)">查看</el-button>
                    <el-button size="small" type="danger" @click="removeCollection(work)">取消收藏</el-button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="我的订单" name="orders">
          <div class="tab-toolbar">
            <el-select v-model="ordersFilter" placeholder="订单状态" style="width: 120px;">
              <el-option label="全部" value="all" />
              <el-option label="待付款" value="待付款" />
              <el-option label="待发货" value="待发货" />
              <el-option label="已发货" value="已发货" />
              <el-option label="已完成" value="已完成" />
            </el-select>
          </div>
          <div class="orders-list">
            <div v-if="filteredOrders.length === 0" class="empty-state">
              <el-icon size="64" color="#ccc"><ShoppingCart /></el-icon>
              <p>还没有订单</p>
              <el-button type="primary" @click="$router.push('/shop')">去购物</el-button>
            </div>
            <div v-else class="orders-list-container">
              <div v-for="order in filteredOrders" :key="order.id" class="order-card">
                <div class="order-header">
                  <span class="order-id">订单号: {{ order.id }}</span>
                  <el-tag :type="getStatusType(order.status)">{{ order.status }}</el-tag>
                </div>
                <div class="order-items">
                  <div v-for="item in order.items" :key="item.id" class="order-item">
                    <img :src="item.image || '/assets/images/logo.svg'" class="order-item-img" />
                    <div class="order-item-info">
                      <p class="order-item-name">{{ item.name }}</p>
                      <p class="order-item-spec">规格: {{ item.spec }}</p>
                      <div class="order-item-price-row">
                        <span class="order-item-price">{{ item.price }}</span>
                        <span class="order-item-quantity">x{{ item.quantity }}</span>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="order-footer">
                  <span class="order-time">{{ order.createTime }}</span>
                  <div class="order-total">
                    <span>合计: </span>
                    <strong>{{ order.totalPrice }}</strong>
                  </div>
                  <div class="order-actions">
                    <el-button v-if="order.status === '待付款'" type="primary" @click="payOrder(order)">立即付款</el-button>
                    <el-button v-if="order.status === '待发货'" @click="remindSeller(order)">提醒发货</el-button>
                    <el-button v-if="order.status === '已发货'" type="success" @click="confirmReceipt(order)">确认收货</el-button>
                    <el-button v-if="order.status === '已完成'" @click="viewOrder(order)">查看详情</el-button>
                    <el-button @click="viewOrder(order)">订单详情</el-button>
                  </div>
                </div>
              </div>
            </div>
          </div>
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
                      action="/api/user/upload-avatar"
                      :on-success="handleAvatarUpload"
                      :on-error="handleAvatarError"
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

            <div class="settings-section">
              <h3><el-icon><Lock /></el-icon> 安全设置</h3>
              <div class="setting-item">
                <span>账号绑定</span>
                <el-switch v-model="bindPhone" />
              </div>
              <div class="setting-item">
                <span>邮箱验证</span>
                <el-switch v-model="verifyEmail" />
              </div>
              <div class="setting-item">
                <span>开启推送通知</span>
                <el-switch v-model="pushNotification" />
              </div>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <el-dialog title="作品详情" v-model="showWorkDialog" width="650px" top="30px">
      <div v-if="selectedWork" class="work-detail-content">
        <img :src="selectedWork.image || '/assets/images/logo.svg'" class="detail-img" />
        <h3>{{ selectedWork.title }}</h3>
        <p>{{ selectedWork.description }}</p>
        <div class="detail-stats">
          <span><el-icon><Star /></el-icon> {{ selectedWork.likes }}</span>
          <span><el-icon><Picture /></el-icon> {{ selectedWork.views }}</span>
        </div>
      </div>
    </el-dialog>

    <el-dialog title="订单详情" v-model="showOrderDialog" width="750px" top="30px">
      <div v-if="selectedOrder" class="order-detail-content">
        <div class="detail-section">
          <h4><el-icon><Document /></el-icon> 订单信息</h4>
          <div class="detail-row">
            <span>订单号</span>
            <span>{{ selectedOrder.id }}</span>
          </div>
          <div class="detail-row">
            <span>下单时间</span>
            <span>{{ selectedOrder.createTime }}</span>
          </div>
          <div class="detail-row">
            <span>订单状态</span>
            <el-tag :type="getStatusType(selectedOrder.status)">{{ selectedOrder.status }}</el-tag>
          </div>
        </div>

        <div class="detail-section">
          <h4><el-icon><MapLocation /></el-icon> 收货信息</h4>
          <div class="detail-row">
            <span>收货人</span>
            <span>{{ selectedOrder.receiver }}</span>
          </div>
          <div class="detail-row">
            <span>联系电话</span>
            <span>{{ selectedOrder.phone }}</span>
          </div>
          <div class="detail-row">
            <span>收货地址</span>
            <span>{{ selectedOrder.address }}</span>
          </div>
        </div>

        <div class="detail-section">
          <h4><el-icon><ShoppingBag /></el-icon> 商品清单</h4>
          <el-table :data="selectedOrder.items" stripe>
            <el-table-column prop="name" label="商品" />
            <el-table-column prop="spec" label="规格" />
            <el-table-column prop="price" label="单价" />
            <el-table-column prop="quantity" label="数量" />
            <el-table-column label="小计">
              <template #default="scope">{{ (scope.row.price * scope.row.quantity).toFixed(2) }}</template>
            </el-table-column>
          </el-table>
        </div>

        <div class="detail-section">
          <h4><el-icon><Wallet /></el-icon> 费用明细</h4>
          <div class="detail-row">
            <span>商品总价</span>
            <span>{{ selectedOrder.totalPrice }}</span>
          </div>
          <div class="detail-row">
            <span>运费</span>
            <span>免运费</span>
          </div>
          <div class="detail-row total">
            <span>实付金额</span>
            <span>{{ selectedOrder.totalPrice }}</span>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage, ElDialog, ElTag, ElTable, ElTableColumn } from 'element-plus'
import { User, Upload, Star, StarFilled, ShoppingCart, EditPen, Plus, Picture, Key, Lock, Document, MapLocation, ShoppingBag, Wallet } from '@element-plus/icons-vue'
import { useUserStore } from '@/store/userStore'

const userStore = useUserStore()
const activeTab = ref('works')

const profileForm = ref({
  username: userStore.user?.username || '',
  email: userStore.user?.email || '',
  bio: ''
})

const passwordForm = ref({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const bindPhone = ref(false)
const verifyEmail = ref(true)
const pushNotification = ref(true)

const worksFilter = ref('all')
const worksSort = ref('newest')
const collectionsFilter = ref('all')
const ordersFilter = ref('all')

const showWorkDialog = ref(false)
const showOrderDialog = ref(false)
const selectedWork = ref(null)
const selectedOrder = ref(null)

const myWorks = ref([
  { id: 1, title: '我的第一个作品', description: '这是我的第一个创作作品', likes: 12, views: 56, image: null, status: '已发布' },
  { id: 2, title: '惠山泥人创作', description: '传统惠山泥人风格作品', likes: 8, views: 34, image: null, status: '已发布' },
  { id: 3, title: '数字锡绣设计', description: '锡绣风格数字艺术作品', likes: 23, views: 89, image: null, status: '草稿' }
])

const myCollections = ref([
  { id: 101, title: '现代风格惠山泥人', author: '创意达人', likes: 124, image: null, type: 'work' },
  { id: 102, title: '数字锡绣-江南水乡', author: '绣娘传人', likes: 89, image: null, type: 'work' },
  { id: 103, title: '3D泥人摆件', author: '文创商城', likes: 328, image: null, type: 'product' }
])

const myOrders = ref([
  {
    id: 'DD20240101001',
    createTime: '2024-01-01 10:30',
    status: '已完成',
    totalPrice: 199,
    receiver: '张三',
    phone: '138****1234',
    address: '江苏省无锡市滨湖区XX街道XX小区1栋101室',
    items: [
      { id: 1, name: '3D泥人摆件', spec: '树脂材质 / 10cm x 10cm', price: 99, quantity: 2 }
    ]
  },
  {
    id: 'DD20240105002',
    createTime: '2024-01-05 14:20',
    status: '待发货',
    totalPrice: 69,
    receiver: '张三',
    phone: '138****1234',
    address: '江苏省无锡市滨湖区XX街道XX小区1栋101室',
    items: [
      { id: 2, name: '手机壳', spec: 'TPU材质 / iPhone 14', price: 69, quantity: 1 }
    ]
  },
  {
    id: 'DD20240110003',
    createTime: '2024-01-10 09:15',
    status: '待付款',
    totalPrice: 298,
    receiver: '张三',
    phone: '138****1234',
    address: '江苏省无锡市滨湖区XX街道XX小区1栋101室',
    items: [
      { id: 3, name: '紫砂茶杯', spec: '紫砂材质 / 200ml', price: 199, quantity: 1 },
      { id: 4, name: '非遗主题书签', spec: '金属材质 / 4枚/套', price: 29, quantity: 3 }
    ]
  },
  {
    id: 'DD20240112004',
    createTime: '2024-01-12 16:45',
    status: '已发货',
    totalPrice: 159,
    receiver: '张三',
    phone: '138****1234',
    address: '江苏省无锡市滨湖区XX街道XX小区1栋101室',
    items: [
      { id: 5, name: '刺绣丝巾', spec: '真丝材质 / 140cm x 140cm', price: 159, quantity: 1 }
    ]
  }
])

const totalLikes = computed(() => {
  return myWorks.value.reduce((sum, work) => sum + work.likes, 0)
})

const filteredWorks = computed(() => {
  let result = [...myWorks.value]

  if (worksFilter.value !== 'all') {
    result = result.filter(w => w.status === worksFilter.value)
  }

  if (worksSort.value === 'likes') {
    result.sort((a, b) => b.likes - a.likes)
  } else {
    result.sort((a, b) => b.id - a.id)
  }

  return result
})

const filteredCollections = computed(() => {
  if (collectionsFilter.value === 'all') {
    return myCollections.value
  }
  return myCollections.value.filter(c => c.type === collectionsFilter.value)
})

const filteredOrders = computed(() => {
  if (ordersFilter.value === 'all') {
    return myOrders.value
  }
  return myOrders.value.filter(o => o.status === ordersFilter.value)
})

const getStatusType = (status) => {
  const types = {
    '待付款': 'warning',
    '待发货': 'primary',
    '已发货': 'success',
    '已完成': 'info'
  }
  return types[status] || 'info'
}

const editProfile = () => {
  activeTab.value = 'settings'
}

const saveProfile = () => {
  ElMessage.success('资料保存成功')
}

const changePassword = () => {
  if (!passwordForm.value.currentPassword) {
    ElMessage.warning('请输入当前密码')
    return
  }
  if (!passwordForm.value.newPassword) {
    ElMessage.warning('请输入新密码')
    return
  }
  if (passwordForm.value.newPassword !== passwordForm.value.confirmPassword) {
    ElMessage.error('两次输入的密码不一致')
    return
  }
  ElMessage.success('密码修改成功')
  passwordForm.value = { currentPassword: '', newPassword: '', confirmPassword: '' }
}

const uploadAvatar = () => {
  ElMessage.info('点击上传头像')
}

const handleAvatarUpload = () => {
  ElMessage.success('头像上传成功')
}

const handleAvatarError = () => {
  ElMessage.error('头像上传失败')
}

const deleteWork = (work) => {
  myWorks.value = myWorks.value.filter(w => w.id !== work.id)
  ElMessage.success('作品已删除')
}

const viewWorkDetail = (work) => {
  selectedWork.value = work
  showWorkDialog.value = true
}

const removeCollection = (work) => {
  myCollections.value = myCollections.value.filter(w => w.id !== work.id)
  ElMessage.success('已取消收藏')
}

const viewCollectionDetail = (work) => {
  ElMessage.info(`查看收藏: ${work.title}`)
}

const viewOrder = (order) => {
  selectedOrder.value = order
  showOrderDialog.value = true
}

const payOrder = (order) => {
  order.status = '待发货'
  ElMessage.success('付款成功')
}

const remindSeller = (order) => {
  ElMessage.info('已提醒卖家发货')
}

const confirmReceipt = (order) => {
  order.status = '已完成'
  ElMessage.success('已确认收货')
}

const handleTabChange = () => {}
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
