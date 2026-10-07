<template>
  <div class="page-container">
    <h1>运营管理</h1>
    <p v-if="error">{{ error }}</p>
    <template v-else-if="ready">
      <el-button @click="refresh" :loading="loading">刷新</el-button>
      <el-tabs v-model="tab">
        <el-tab-pane label="概览" name="overview">
          <div class="overview-grid"><div v-for="metric in overviewMetrics" :key="metric.label" class="overview-metric"><span>{{ metric.label }}</span><strong>{{ metric.value }}</strong></div></div>
          <h3>最近七天积分消耗</h3><el-table :data="statistics.credits?.daily || []"><el-table-column prop="date" label="日期"/><el-table-column prop="consumed" label="消耗积分"/></el-table>
        </el-tab-pane>
        <el-tab-pane label="创作任务" name="tasks"><el-table :data="tasks"><el-table-column prop="id" label="任务编号"/><el-table-column prop="provider" label="服务"/><el-table-column prop="status" label="状态"/><el-table-column prop="error_message" label="错误"/></el-table></el-tab-pane>
        <el-tab-pane label="模型服务" name="providers"><el-table :data="providers"><el-table-column prop="name" label="服务"/><el-table-column prop="enabled" label="启用"/><el-table-column label="操作"><template #default="{row}"><el-button @click="toggleProvider(row)">{{ row.enabled ? '停用' : '启用' }}</el-button></template></el-table-column></el-table></el-tab-pane>
        <el-tab-pane label="商品" name="products">
          <el-form class="product-form"><el-input v-model="productForm.name" placeholder="商品名称"/><el-input v-model="productForm.image" placeholder="商品图片：本站上传地址或 HTTPS" maxlength="500"/><el-input v-model="productForm.description" type="textarea" placeholder="商品介绍、材质、尺寸与售后说明" maxlength="5000" show-word-limit/><el-select v-model="productForm.category"><el-option v-for="c in ['clay','embroidery','pottery','digital','stationery']" :key="c" :value="c" :label="c"/></el-select><el-input-number v-model="productForm.price_cents" :min="0" :precision="0"/><span>价格（分）</span><el-input-number v-model="productForm.stock" :min="0" :precision="0"/><span>库存</span><el-switch v-model="productForm.active" active-text="上架"/><el-button @click="saveProduct" :loading="saving">保存商品</el-button><el-button @click="resetProduct">新商品</el-button></el-form>
          <el-table :data="products"><el-table-column prop="name" label="商品"/><el-table-column prop="price" label="价格"/><el-table-column prop="stock" label="库存"/><el-table-column prop="active" label="上架"/><el-table-column label="编辑"><template #default="{row}"><el-button @click="productForm = {...row}">编辑</el-button></template></el-table-column></el-table>
        </el-tab-pane>
        <el-tab-pane label="订单" name="orders"><el-table :data="orders"><el-table-column prop="id" label="订单"/><el-table-column prop="receiver" label="收件人"/><el-table-column prop="total" label="金额"/><el-table-column prop="status" label="状态"/><el-table-column label="操作"><template #default="{row}"><el-button v-if="transitions[row.status]" @click="advanceOrder(row)">{{ transitions[row.status] }}</el-button></template></el-table-column></el-table></el-tab-pane>
        <el-tab-pane label="审计日志" name="logs"><el-table :data="logs"><el-table-column prop="action" label="操作"/><el-table-column prop="target_id" label="对象"/><el-table-column prop="created_at" label="时间"/><el-table-column prop="detail" label="详情"/></el-table></el-tab-pane>
      </el-tabs>
      <el-button @click="loadMore" v-if="hasMore" :loading="loading">加载更多任务、订单与日志</el-button>
    </template>
  </div>
</template>
<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/api/index'
const ready=ref(false), error=ref(''), loading=ref(false), saving=ref(false), tab=ref('overview')
const statistics=ref({}), tasks=ref([]), providers=ref([]), orders=ref([]), products=ref([]), logs=ref([])
const overviewMetrics=computed(()=>[
  {label:'注册用户',value:statistics.value.users?.total_users ?? '—'},
  {label:'可用账号',value:statistics.value.users?.active_users ?? '—'},
  {label:'今日新用户',value:statistics.value.users?.new_users_today ?? '—'},
  {label:'创作任务',value:statistics.value.ai?.total_tasks ?? '—'},
  {label:'成功任务',value:statistics.value.ai?.success ?? '—'},
  {label:'失败任务',value:statistics.value.ai?.failed ?? '—'},
  {label:'运行中',value:statistics.value.ai?.running ?? '—'},
  {label:'今日积分消耗',value:statistics.value.credits?.today_consumed ?? '—'}
])
const transitions={'待确认':'待发货','待发货':'已发货','已发货':'已完成'}
const productForm=ref({}), resetProduct=()=>{productForm.value={name:'',image:'',description:'',category:'clay',price_cents:0,stock:0,active:false}}
resetProduct()
let page=1
const more=ref({tasks:false,orders:false,logs:false}), hasMore=computed(()=>Object.values(more.value).some(Boolean))
const fetchPage=async (append=false)=>{
  for(const [name,state,path] of [['tasks',tasks,'/admin/tasks'],['orders',orders,'/admin/orders'],['logs',logs,'/admin/logs']]) {
    if(append && !more.value[name]) continue
    const response=await request.get(path,{params:{page,per_page:30}})
    state.value=append?[...state.value,...response.data]:response.data
    more.value[name]=!!response.meta?.pagination?.has_next
  }
}
const refresh=async()=>{
  loading.value=true; error.value=''; page=1
  try {
    const result={}
    for(const name of ['users','ai','credits']) result[name]=(await request.get('/admin/statistics/'+name)).data
    statistics.value=result
    providers.value=(await request.get('/admin/providers')).data.providers || []
    products.value=(await request.get('/admin/products')).data || []
    await fetchPage(); ready.value=true
  } catch { error.value='无法访问运营后台，请确认账号管理员权限和服务状态' }
  finally { loading.value=false }
}
const loadMore=async()=>{loading.value=true;page++;try{await fetchPage(true)}catch{page--}finally{loading.value=false}}
const toggleProvider=async row=>{await ElMessageBox.confirm(`确认${row.enabled?'停用':'启用'} ${row.name}？`,'服务配置');await request.post(`/admin/providers/${row.id}/toggle`,{enabled:!row.enabled});await refresh()}
const saveProduct=async()=>{if(saving.value)return;saving.value=true;try{const p=productForm.value;await request[p.id?'put':'post']('/admin/products'+(p.id?'/'+p.id:''),p);ElMessage.success('商品已保存');resetProduct();await refresh()}catch{/*请求错误已提示*/}finally{saving.value=false}}
const advanceOrder=async row=>{try{await ElMessageBox.confirm(`确认订单变更为${transitions[row.status]}？`,'订单');const payload={status:transitions[row.status]};if(payload.status==='已发货'){payload.carrier=(await ElMessageBox.prompt('填写物流公司','发货',{inputValidator:v=>!!v?.trim()&&v.length<=80})).value;payload.tracking_number=(await ElMessageBox.prompt('填写运单号','发货',{inputValidator:v=>!!v?.trim()&&v.length<=100})).value}await request.put('/admin/orders/'+row.id,payload);await refresh()}catch{/*取消或请求错误由拦截器处理*/}}
onMounted(refresh)
</script>

<style scoped>.product-form{display:flex;flex-wrap:wrap;gap:12px;margin:20px 0}.product-form>.el-input,.product-form>.el-textarea{width:100%}.product-form>.el-select{width:180px}.overview-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:16px;margin:20px 0}.overview-metric{padding:20px;background:white;border-radius:12px;display:grid;gap:12px}.overview-metric strong{font-size:28px;color:#2d6172}</style>
