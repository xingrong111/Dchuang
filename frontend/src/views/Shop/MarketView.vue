<template>
  <div class="market page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">文创商城</h1>
        <p class="page-subtitle">按名称与类别发现文创，查看设计细节，收藏喜欢的作品。</p>
      </div>
      <el-button @click="showCartDialog = true" type="primary" class="cart-btn">
        <el-icon><ShoppingCart /></el-icon>
        购物车 ({{ cartStore.totalCount }})
      </el-button>
    </div>

    <p class="commerce-note">当前目录包含原创文创设计，尚未实物销售。设计条目可搜索、浏览和收藏；正式上架且有库存的商品才能加入购物车。<RouterLink to="/shop/designs">阅读设计故事与查看三维模型 ↗</RouterLink></p>
    <div class="toolbar">
      <div class="search-bar">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索商品..."
          :prefix-icon="Search"
          @keyup.enter="handleSearch"
          clearable
        />
        <el-button type="primary" @click="handleSearch">搜索</el-button>
      </div>

      <div class="filter-section">
        <el-select v-model="selectedCategory" placeholder="分类筛选" style="width: 150px;">
          <el-option label="全部" value="" />
          <el-option label="泥人摆件" value="clay" />
          <el-option label="刺绣制品" value="embroidery" />
          <el-option label="紫砂陶艺" value="pottery" />
          <el-option label="数码周边" value="digital" />
          <el-option label="文创文具" value="stationery" />
        </el-select>

        <el-select v-model="sortBy" placeholder="排序方式" style="width: 120px;">
          <el-option label="默认排序" value="default" />
          <el-option label="价格从低到高" value="price_asc" />
          <el-option label="价格从高到低" value="price_desc" />
          
        </el-select>
      </div>
    </div>

    <div class="market-main">
      <div class="categories-sidebar">
        <div class="sidebar-card">
          <h3><el-icon><Grid /></el-icon> 商品分类</h3>
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
          <h3><el-icon><TrendCharts /></el-icon> 价格区间</h3>
          <div class="price-filter">
            <el-slider
              v-model="priceRange"
              :min="0"
              :max="priceCeiling"
              range
              show-input
            />
          </div>
        </div>

        <div class="sidebar-card">
          <h3><el-icon><StarFilled /></el-icon> 本页商品</h3>
          <div class="hot-list">
            <div v-for="(item, idx) in hotProducts" :key="item.id" class="hot-item" @click="viewProductDetail(item)">
              <span class="hot-rank" :class="'rank-' + (idx + 1)">{{ idx + 1 }}</span>
              <span class="hot-name">{{ item.name }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="products-area">
        <div v-if="productsLoading" class="empty-state" v-loading="true"><p>正在加载文创目录…</p></div>
        <div v-else-if="productsError" class="empty-state"><p>文创目录暂时无法加载</p><el-button @click="loadProducts">重新加载</el-button></div>
        <div v-else-if="filteredProducts.length === 0" class="empty-state">
          <el-icon size="64" color="#ccc"><Box /></el-icon>
          <p>没有找到相关商品</p>
          <el-button type="primary" @click="resetFilters">重置筛选</el-button>
        </div>
        <div v-else class="products-grid">
          <div class="product-card" v-for="product in filteredProducts" :key="product.id">
            <div class="product-image-wrapper">
              <div class="product-image">
                <img :src="product.image || logoUrl" :alt="product.name" />
              </div>
              <div class="category-tag">{{ getCategoryName(product.category) }}</div>
              <div v-if="product.discount" class="discount-tag">{{ product.discount }}%</div>
            </div>
            <div class="product-content">
              <h3 class="product-name">{{ product.name }}</h3>
              <p class="product-description">{{ product.description }}</p>
              <div v-if="!product.specs?.display_only" class="product-rating">
                <el-rate v-if="product.rating" :model-value="product.rating" disabled size="small" /><span v-else>暂无评分</span>
                <span class="rating-count">({{ product.reviewCount }})</span>
              </div>
              <p v-if="!product.specs?.display_only" class="product-price">
                <span class="current-price">{{ '¥' + product.price.toFixed(2) }}</span>
                <span v-if="product.originalPrice" class="original-price">{{ product.originalPrice }}</span>
              </p>
              <p class="product-sales">{{ product.specs?.display_only ? '原创设计 · 尚未实物销售' : '库存 ' + product.stock + ' 件' }}</p>
              <div class="product-actions">
                <el-button size="small" @click="viewProductDetail(product)">详情</el-button><el-button size="small" :disabled="favoriteBusy" @click="favorite(product)">{{ favoriteIds.has(product.id)?'已收藏':'收藏' }}</el-button>
                <el-button v-if="product.specs?.display_only" type="primary" size="small" @click="openDesign(product)">查看模型</el-button>
                <el-button v-else type="primary" size="small" @click="addToCart(product)" :disabled="cartStore.busy || product.stock < 1">
                  <el-icon><Plus /></el-icon>
                  加入购物车
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <el-pagination v-model:current-page="page" :page-size="24" :total="total" layout="total,prev,pager,next" @current-change="loadProducts" />
    <el-dialog title="商品详情" v-model="showDetailDialog" width="800px" top="30px">
      <div v-if="selectedProduct" class="product-detail">
        <div class="detail-main">
          <div class="detail-image-wrapper">
            <img :src="selectedProduct.image || logoUrl" :alt="selectedProduct.name" class="detail-image" />
          </div>
          <div class="detail-info">
            <div class="detail-header">
              <h3>{{ selectedProduct.name }}</h3>
              <span class="detail-category">{{ getCategoryName(selectedProduct.category) }}</span>
            </div>
            <div v-if="selectedProduct.rating" class="detail-rating">
              <el-rate :model-value="selectedProduct.rating" disabled />
              <span>{{ selectedProduct.rating }}分</span>
              <span class="review-count">({{ selectedProduct.reviewCount }}条评价)</span>
            </div>
            <p class="detail-desc">{{ selectedProduct.description }}</p>
            <div class="detail-price-area">
              <span class="current-price">{{ selectedProduct.specs?.display_only ? '原创文创设计' : '¥' + selectedProduct.price.toFixed(2) }}</span>
              <span v-if="selectedProduct.originalPrice" class="original-price">{{ selectedProduct.originalPrice }}</span>
              <span v-if="selectedProduct.discount" class="discount-badge">限时{{ selectedProduct.discount }}%</span>
            </div>
            <div class="sales-info">{{ selectedProduct.specs?.display_only ? '文创模型，尚未实物销售' : '库存 ' + selectedProduct.stock + ' 件' }}</div>
            <div class="detail-specs">
              <h4><el-icon><Document /></el-icon> 规格参数</h4>
              <ul>
                <li v-for="(spec, key) in publicSpecs(selectedProduct)" :key="key">{{ key }}: {{ spec }}</li>
              </ul>
            </div>
            <div v-if="selectedProduct.specs?.display_only" class="detail-actions"><el-button type="primary" @click="openDesign(selectedProduct)">查看设计与三维模型</el-button></div>
            <div v-else class="detail-actions">
              <el-input-number v-model="buyQuantity" :min="1" :max="Math.max(1, Math.min(99, selectedProduct.stock))" style="width: 100px;" />
              <el-button type="primary" @click="addToCart(selectedProduct, buyQuantity)" :disabled="cartStore.busy || selectedProduct.stock < 1" size="large">
                <el-icon><ShoppingCart /></el-icon>
                加入购物车
              </el-button>
              <el-button type="danger" @click="buyNow(selectedProduct)" :disabled="selectedProduct.stock < 1" size="large">立即购买</el-button>
            </div>
          </div>
        </div>

        <div v-if="!selectedProduct.specs?.display_only" class="reviews-section">
          <h4><el-icon><Message /></el-icon> 商品评价 ({{ selectedProduct.reviewCount }})</h4>
          <div class="reviews-list">
            <div v-for="review in selectedProduct.reviews" :key="review.id" class="review-item">
              <div class="review-header">
                <span class="review-author">{{ review.author }}</span>
                <el-rate :model-value="review.rating" disabled size="small" />
                <span class="review-time">{{ review.time }}</span>
              </div>
              <p class="review-content">{{ review.content }}</p>
              <div v-if="review.images && review.images.length" class="review-images">
                <img v-for="(img, idx) in review.images" :key="idx" :src="img" class="review-img" />
              </div>
            </div>
            <el-button v-if="reviewHasNext" @click="moreReviews">更多评价</el-button><p v-if="!selectedProduct.reviews || selectedProduct.reviews.length === 0" class="no-reviews">暂无评价</p>
          </div>
        </div>
      </div>
    </el-dialog>

    <el-dialog title="购物车" v-model="showCartDialog" width="850px" top="30px">
      <div v-if="cartStore.items.length === 0" class="empty-cart">
        <el-icon size="64" color="#ccc"><ShoppingCart /></el-icon>
        <p>购物车是空的</p>
        <el-button type="primary" @click="showCartDialog = false">去逛逛</el-button>
      </div>
      <div v-else>
        <el-table :data="cartStore.items" stripe>
          <el-table-column label="商品" width="350">
            <template #default="scope">
              <div class="cart-item-info">
                <img :src="scope.row.image || logoUrl" class="cart-item-img" />
                <span>{{ scope.row.name }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="price" label="单价" width="120" />
          <el-table-column label="数量" width="120">
            <template #default="scope">
              <el-input-number
                :model-value="scope.row.quantity"
                :min="1"
                :max="Math.min(99, scope.row.stock)"
                :disabled="cartStore.busy"
                @change="updateQuantity(scope.row.id, $event)"
              />
            </template>
          </el-table-column>
          <el-table-column label="小计" width="120">
            <template #default="scope">
              <span class="subtotal">{{ (scope.row.price * scope.row.quantity).toFixed(2) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100">
            <template #default="scope">
              <el-button type="danger" size="small" @click="removeFromCart(scope.row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="cart-summary">
          <div class="cart-total">
            <span>共 {{ cartStore.totalCount }} 件商品</span>
            <span>总计: <strong>{{ cartStore.totalPrice.toFixed(2) }}</strong></span>
          </div>
          <el-button type="primary" @click="checkout" size="large">去结算</el-button>
        </div>
      </div>
    </el-dialog>

    <el-dialog title="确认订单" v-model="showCheckoutDialog" width="750px" top="30px">
      <div class="checkout-address"><p>当前不收取线上支付，提交后等待商家确认。</p><el-select v-model="selectedAddress" clearable placeholder="选择已保存地址" @change="applyAddress"><el-option v-for="row in addresses" :key="row.id" :value="row.id" :label="row.receiver+' · '+row.address" /></el-select><RouterLink to="/shop/account">管理地址</RouterLink>
        <h4><el-icon><MapLocation /></el-icon> 收货地址</h4>
        <el-form :model="orderForm" label-width="100px">
          <el-form-item label="收货人">
            <el-input v-model="orderForm.receiver" placeholder="请输入收货人姓名" />
          </el-form-item>
          <el-form-item label="联系电话">
            <el-input v-model="orderForm.phone" placeholder="请输入联系电话" />
          </el-form-item>
          <el-form-item label="收货地址">
            <el-input v-model="orderForm.address" type="textarea" placeholder="请输入详细收货地址" :rows="3" />
          </el-form-item>
          <el-form-item label="备注">
            <el-input v-model="orderForm.note" placeholder="请输入备注信息" />
          </el-form-item>
        </el-form>
      </div>

      <div class="checkout-items">
        <h4><el-icon><ShoppingBag /></el-icon> 商品清单</h4>
        <el-table :data="checkoutItems" stripe>
          <el-table-column prop="name" label="商品" width="250" />
          <el-table-column prop="price" label="单价" width="100" />
          <el-table-column prop="quantity" label="数量" width="80" />
          <el-table-column label="小计" width="100">
            <template #default="scope">
              {{ (scope.row.price * scope.row.quantity).toFixed(2) }}
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="checkout-summary">
        <div class="summary-row">
          <span>商品总价</span>
          <span>{{ checkoutTotal.toFixed(2) }}</span>
        </div>
        <div class="summary-row">
          <span>运费</span>
          <span>由商家确认；当前订单仅记录商品金额</span>
        </div>
        <div class="summary-row total">
          <span>订单金额</span>
          <span>{{ checkoutTotal.toFixed(2) }}</span>
        </div>
      </div>

      <template #footer>
        <el-button @click="showCheckoutDialog = false">取消</el-button>
        <el-button type="danger" @click="submitOrder" :loading="submittingOrder" :disabled="!orderForm.receiver || !orderForm.phone || !orderForm.address" size="large">
          提交订单 ({{ checkoutTotal.toFixed(2) }})
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import request from '@/api/index'
import { getProducts, createOrder } from '@/api/shop'
import { ElMessage } from 'element-plus'
import { ShoppingCart, Plus, Search, Grid, TrendCharts, Box, StarFilled, Document, Message, MapLocation, ShoppingBag } from '@element-plus/icons-vue'
import { useCartStore } from '@/store/cartStore'
import { useUserStore } from '@/store/userStore'
import logoUrl from '@/assets/images/logo.svg'

const cartStore = useCartStore()
const userStore = useUserStore()
const router = useRouter()
const openDesign = product => router.push({path:'/shop/designs',query:{design:product.specs.design_id}})
const publicSpecs = product => Object.fromEntries(Object.entries(product.specs || {}).filter(([key]) => !['display_only','design_id','model_url'].includes(key)))
const checkoutItems = ref([])
const checkoutTotal = computed(() => checkoutItems.value.reduce((sum, item) => sum + Math.round(item.price * 100) * item.quantity, 0) / 100)

const categories = [
  { label: '全部', value: '' },
  { label: '泥人摆件', value: 'clay' },
  { label: '刺绣制品', value: 'embroidery' },
  { label: '紫砂陶艺', value: 'pottery' },
  { label: '数码周边', value: 'digital' },
  { label: '文创文具', value: 'stationery' }
]

const products = ref([])
const productsLoading = ref(true), productsError = ref(false)
const submittingOrder = ref(false)
let requestKey = null

const showDetailDialog = ref(false)
const showCartDialog = ref(false)
const showCheckoutDialog = ref(false)
const selectedProduct = ref(null)
const buyQuantity = ref(1)
const reviewPage=ref(1),reviewHasNext=ref(false)
const moreReviews=async()=>{const pid=selectedProduct.value?.id;if(!pid)return;try{const r=await request.get(`/shop/products/${pid}/reviews`,{params:{page:reviewPage.value+1}});if(selectedProduct.value?.id===pid){selectedProduct.value.reviews.push(...r.data);reviewPage.value++;reviewHasNext.value=!!r.meta.pagination.has_next}}catch{/*已提示*/}}

const searchKeyword = ref('')
const selectedCategory = ref('')
const sortBy = ref('default')
const priceRange = ref([0, 10000])
const priceCeiling = computed(() => 10000)

const orderForm = ref({
  receiver: '',
  phone: '',
  address: '',
  note: ''
})

const filteredProducts=computed(()=>products.value)
const hotProducts=computed(()=>products.value.slice(0,5))
const page=ref(1),total=ref(0),favoriteIds=ref(new Set()),favoriteBusy=ref(false),addresses=ref([]),selectedAddress=ref(null)
let sequence=0,timer
const loadProducts=async()=>{
 const current=++sequence
 productsLoading.value=true;productsError.value=false
 try{const r=await getProducts({page:page.value,per_page:24,q:searchKeyword.value,category:selectedCategory.value||undefined,sort:sortBy.value==='default'?'newest':sortBy.value,min_price:Math.round(priceRange.value[0]*100),max_price:priceRange.value[1]===priceCeiling.value?undefined:Math.round(priceRange.value[1]*100)});if(current===sequence){products.value=r.data;total.value=r.meta.pagination.total}}
 catch{if(current===sequence)productsError.value=true}
 finally{if(current===sequence)productsLoading.value=false}
}
watch([searchKeyword,selectedCategory,sortBy,priceRange],()=>{clearTimeout(timer);timer=setTimeout(()=>{page.value=1;loadProducts()},300)},{deep:true})
onUnmounted(()=>{sequence++;clearTimeout(timer)})
const loadFavorites=async()=>{if(!userStore.user?.token){favoriteIds.value=new Set();return}favoriteIds.value=new Set((await request.get('/shop/favorites')).data.map(p=>p.id))}
const favorite=async product=>{if(!userStore.user?.token)return ElMessage.warning('请先登录');if(favoriteBusy.value)return;favoriteBusy.value=true;try{await request[favoriteIds.value.has(product.id)?'delete':'put']('/shop/favorites/'+product.id);await loadFavorites()}catch{/*已提示*/}finally{favoriteBusy.value=false}}
watch(showCheckoutDialog,async value=>{if(value){try{addresses.value=(await request.get('/shop/addresses')).data;const row=addresses.value.find(a=>a.is_default);if(row){selectedAddress.value=row.id;applyAddress(row.id)}}catch{/*已提示*/}}})
const applyAddress=id=>{const row=addresses.value.find(a=>a.id===id);if(row)orderForm.value={...orderForm.value,receiver:row.receiver,phone:row.phone,address:row.address}}
onMounted(async()=>{await loadProducts();try{await loadFavorites();if(userStore.user?.token)await cartStore.refresh()}catch{/*已提示*/}})

const getCategoryName = (category) => {
  const cat = categories.find(c => c.value === category)
  return cat ? cat.label : '其他'
}

const handleSearch = () => {
  showDetailDialog.value = false;page.value=1;loadProducts()
}

const resetFilters = () => {
  searchKeyword.value = ''
  selectedCategory.value = ''
  sortBy.value = 'default'
  priceRange.value = [0, priceCeiling.value]
}

const viewProductDetail = async (product) => {
  selectedProduct.value = product
  buyQuantity.value = 1
  showDetailDialog.value = true
  try{const r=await request.get(`/shop/products/${product.id}/reviews`);if(selectedProduct.value?.id===product.id){selectedProduct.value={...product,reviews:r.data};reviewPage.value=1;reviewHasNext.value=!!r.meta.pagination.has_next}}catch{/*已提示*/}
}

const addToCart = async (product, quantity = 1) => {
  if (!userStore.user?.token) return ElMessage.warning('请先登录')
  try {
    if (await cartStore.addToCart(product, quantity)) {
      ElMessage.success('已加入购物车'); showDetailDialog.value = false; buyQuantity.value = 1
    }
  } catch { /* 拦截器显示服务端错误 */ }
}

const buyNow = (product) => {
  if (!userStore.user?.token) return ElMessage.warning('请先登录')
  checkoutItems.value = [{ ...product, quantity: buyQuantity.value }]
  requestKey = null
  showDetailDialog.value = false
  showCheckoutDialog.value = true
}

const removeFromCart = async productId => {
  try { if (await cartStore.removeFromCart(productId)) ElMessage.success('已移除') } catch { /* 已提示 */ }
}
const updateQuantity = async (productId, quantity) => {
  try { await cartStore.updateQuantity(productId, quantity) } catch { /* 绑定服务端数量，失败不污染本地 */ }
}
const checkout = () => {
  if (!userStore.user?.token) return ElMessage.warning('请先登录')
  checkoutItems.value = cartStore.items.map(item => ({ ...item }))
  requestKey = null
  showCartDialog.value = false
  showCheckoutDialog.value = true
}

const submitOrder = async () => {
  if (submittingOrder.value) return
  if (!checkoutItems.value.length) return ElMessage.warning('购物车为空')
  submittingOrder.value = true
  requestKey ||= crypto.randomUUID()
  try {
    const response = await createOrder({ ...orderForm.value, request_key: requestKey,
      items: checkoutItems.value.map(item => ({ product_id: item.id, quantity: item.quantity })) })
    ElMessage.success(`订单 ${response.data.id.slice(0, 8)} 已记录，等待商家确认`)
    await cartStore.refresh()
    checkoutItems.value = []
    requestKey = null
    showCheckoutDialog.value = false
    orderForm.value = { receiver: '', phone: '', address: '', note: '' }
  } catch { /* 后端错误由拦截器提示，保留购物车与幂等编号 */ }
  finally { submittingOrder.value = false }
}

</script>

<style scoped>
.market{max-width:1240px}.products-area{min-width:0}.market .products-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.market .product-actions{flex-wrap:wrap;gap:8px}.market .product-actions .el-button{margin-left:0}.market .categories-sidebar{width:210px;position:sticky;top:90px;align-self:flex-start}.commerce-note{background:#f3eee5;padding:16px 20px;line-height:1.8;border-radius:12px;margin:0 0 24px;color:#72654f}.commerce-note a{color:#2d6172}.market .product-description{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}@media(min-width:1400px){.market .products-grid{grid-template-columns:repeat(3,minmax(0,1fr))}}@media(max-width:600px){.market .products-grid{grid-template-columns:1fr}.market .search-bar{width:100%;display:flex}.market .search-bar .el-input{width:auto;flex:1;min-width:0}.market .categories-sidebar{width:100%;position:static}.market .toolbar{padding:16px}.market .page-header{align-items:flex-start;gap:12px}}
.commerce-note{line-height:1.8;color:#66756e}.commerce-note a{color:#2d6172}.product-actions{flex-wrap:wrap}.market :deep(.el-pagination){margin-top:24px;flex-wrap:wrap}

.market {
  max-width: 1280px;
}

.page-header {
  margin-bottom: 30px;
}

.cart-btn {
  height: 40px;
}

.toolbar {
  padding: 16px 20px;
}

.search-bar .el-input {
  width: 350px;
}

.market-main {
  display: flex;
  gap: 24px;
}

.categories-sidebar {
  width: 240px;
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

.category-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.category-list span {
  padding: 10px 14px;
  background: #f5f5f5;
  border-radius: 10px;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.2s;
  color: #666;
  text-align: left;
}

.category-list span:hover, .category-list span.active {
  background: #4a90a4;
  color: white;
}

.price-filter {
  background: #f9f9f9;
  padding: 10px;
  border-radius: 10px;
}

.hot-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.hot-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px dashed #eee;
  cursor: pointer;
  transition: background 0.2s;
}

.hot-item:last-child {
  border-bottom: none;
}

.hot-item:hover {
  background: #f9f9f9;
}

.hot-rank {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #eee;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  font-weight: 600;
  color: #666;
}

.hot-rank.rank-1 {
  background: #e74c3c;
  color: white;
}

.hot-rank.rank-2 {
  background: #f39c12;
  color: white;
}

.hot-rank.rank-3 {
  background: #f5a623;
  color: white;
}

.hot-name {
  font-size: 0.85rem;
  color: #333;
}

.products-area {
  flex: 1;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  background: white;
  border-radius: 16px;
}

.empty-state p {
  margin: 16px 0;
  color: #999;
}

.products-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.product-card {
  background: white;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
  transition: all 0.3s ease;
}

.product-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.12);
}

.product-image-wrapper {
  position: relative;
}

.product-image {
  width: 100%;
  height: 200px;
  background: #f5f5f5;
  overflow: hidden;
}

.product-image img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.category-tag {
  position: absolute;
  top: 12px;
  left: 12px;
  padding: 5px 14px;
  background: rgba(74, 144, 164, 0.9);
  color: white;
  font-size: 0.75rem;
  border-radius: 15px;
}

.discount-tag {
  position: absolute;
  top: 12px;
  right: 12px;
  padding: 5px 14px;
  background: #e74c3c;
  color: white;
  font-size: 0.75rem;
  border-radius: 15px;
}

.product-content {
  padding: 20px;
}

.product-name {
  font-size: 1.1rem;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 8px;
}

.product-description {
  color: #666;
  font-size: 0.85rem;
  margin: 0 0 12px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.6;
}

.product-rating {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
}

.rating-count {
  font-size: 0.8rem;
  color: #999;
}

.product-price {
  margin-bottom: 8px;
}

.current-price {
  color: #e74c3c;
  font-size: 1.5rem;
  font-weight: 700;
}

.original-price {
  text-decoration: line-through;
  color: #999;
  font-size: 0.9rem;
  margin-left: 10px;
}

.product-sales {
  font-size: 0.8rem;
  color: #999;
  margin-bottom: 16px;
}

.product-actions {
  display: flex;
  gap: 10px;
}

.product-detail {
  text-align: left;
}

.detail-main {
  display: flex;
  gap: 30px;
  margin-bottom: 25px;
}

.detail-image-wrapper {
  width: 320px;
  height: 320px;
  flex-shrink: 0;
}

.detail-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
  border-radius: 16px;
  background: #f5f5f5;
}

.detail-info {
  flex: 1;
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 15px;
}

.detail-header h3 {
  font-size: 1.5rem;
  font-weight: 700;
  color: #2c3e50;
  margin: 0;
}

.detail-category {
  padding: 6px 16px;
  background: #4a90a4;
  color: white;
  border-radius: 20px;
  font-size: 0.85rem;
}

.detail-rating {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 15px;
}

.detail-rating span {
  color: #666;
  font-size: 0.9rem;
}

.detail-desc {
  color: #666;
  line-height: 1.7;
  margin: 0 0 20px;
}

.detail-price-area {
  margin-bottom: 15px;
}

.detail-price-area .current-price {
  font-size: 2.2rem;
}

.discount-badge {
  padding: 6px 14px;
  background: #e74c3c;
  color: white;
  border-radius: 20px;
  font-size: 0.85rem;
  margin-left: 15px;
}

.sales-info {
  color: #999;
  font-size: 0.9rem;
  margin-bottom: 20px;
}

.detail-specs {
  margin-bottom: 25px;
}

.detail-specs h4 {
  font-size: 1rem;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.detail-specs ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.detail-specs li {
  padding: 10px 0;
  border-bottom: 1px dashed #eee;
  color: #666;
}

.detail-actions {
  display: flex;
  align-items: center;
  gap: 15px;
}

.reviews-section {
  padding-top: 25px;
  border-top: 1px solid #eee;
}

.reviews-section h4 {
  font-size: 1rem;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 15px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.reviews-list {
  margin-bottom: 15px;
}

.review-item {
  padding: 15px 0;
  border-bottom: 1px dashed #eee;
}

.review-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.review-author {
  font-weight: 600;
  color: #333;
}

.review-time {
  font-size: 0.8rem;
  color: #999;
}

.review-content {
  color: #666;
  line-height: 1.6;
}

.review-images {
  display: flex;
  gap: 12px;
  margin-top: 10px;
}

.review-img {
  width: 80px;
  height: 80px;
  object-fit: cover;
  border-radius: 10px;
}

.no-reviews {
  text-align: center;
  color: #999;
  padding: 30px;
}

.empty-cart {
  text-align: center;
  padding: 50px;
}

.empty-cart p {
  color: #999;
  margin: 16px 0;
}

.cart-item-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.cart-item-img {
  width: 60px;
  height: 60px;
  object-fit: cover;
  border-radius: 8px;
  background: #f5f5f5;
}

.subtotal {
  color: #e74c3c;
  font-weight: 600;
}

.cart-summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid #eee;
}

.cart-total {
  display: flex;
  gap: 30px;
  color: #666;
}

.cart-total strong {
  color: #e74c3c;
  font-size: 1.4rem;
}

.checkout-address, .checkout-items {
  margin-bottom: 20px;
}

.checkout-address h4, .checkout-items h4 {
  margin: 0 0 15px;
  font-size: 1rem;
  font-weight: 600;
  color: #2c3e50;
  display: flex;
  align-items: center;
  gap: 8px;
}

.checkout-summary {
  background: #f9f9f9;
  padding: 20px;
  border-radius: 12px;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  color: #666;
}

.summary-row.total {
  font-weight: bold;
  font-size: 1.3rem;
  color: #e74c3c;
  border-top: 1px dashed #ddd;
  margin-top: 8px;
  padding-top: 12px;
}

@media (max-width: 992px) {
  .market-main {
    flex-direction: column;
  }

  .categories-sidebar {
    width: 100%;
  }

  .category-list {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .search-bar .el-input {
    width: 100%;
  }

  .toolbar {
    flex-direction: column;
    gap: 16px;
  }

  .detail-main {
    flex-direction: column;
  }

  .detail-image-wrapper {
    width: 100%;
    height: auto;
  }

  .detail-image {
    height: 250px;
  }
}
</style>
