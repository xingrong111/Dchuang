<template>
  <article class="page-container information"><h1>{{ page.title }}</h1>
    <section v-for="item in page.sections" :key="item.title"><h2>{{ item.title }}</h2><p>{{ item.text }}</p></section>
    <RouterLink to="/about">项目介绍</RouterLink> · <RouterLink to="/profile">个人中心</RouterLink>
  </article>
</template>
<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
const route = useRoute()
const pages = {
  '/help': { title: '帮助中心', sections: [
    { title: '浏览和创作', text: '数字博物馆和资产库可直接浏览。注册登录后进入工坊：输入描述或上传图片分析，也可点击部件组装。移动端用单指旋转、双指缩放。' },
    { title: '保存和发布', text: '在编辑器选择保存并发布，作品会出现在社区和个人中心。GLB 导出包含彩绘材质，OBJ 仅保存几何网格。作品所有者可在个人中心删除作品。' },
    { title: '创作与积分', text: '创作请求按站内规则消耗积分，失败任务自动退款。演示模式提供固定模型，不代表真实云端制作；缺少真实服务配置时会明确提示错误。' },
    { title: '文创设计', text: '文创页面提供产品图片、文化故事和三维模型，可下载GLB或加入购物车。当前暂未开售的产品不能购买、结算或定制，开售状态以商品页面为准。' },
    { title: '登录与故障', text: '忘记密码可通过邮箱验证码重置。任务失败、库存不足或文件加载失败时请按页面提示重试；不要重复提交仍在处理的生成任务。' }
  ] },
  '/terms': { title: '使用说明', sections: [
    { title: '作品与素材', text: '请仅上传自己拥有使用权的内容，发布前确认公开范围。文化资料图片的来源及待核实事项见博物馆资料详情，程序化演示模型的来源见项目说明；浏览权限不自动授予商业复制权。' },
    { title: '作品结果', text: '创作结果需由创作者检查造型、文化内容和使用权。模型导出用于数字展示与进一步编辑，不保证可直接用于制造。' },
    { title: '账户和交易', text: '请妥善保管密码。站内积分用于任务计量，不是现金或数字货币。加入购物车不形成交易，暂未开售的产品不能购买。' }
  ] },
  '/privacy': { title: '数据使用说明', sections: [
    { title: '账户与作品', text: '平台保存注册邮箱、用户名和密码哈希，以及用户自愿填写的资料、上传文件和作品互动记录。公开作品会显示作者名；私有作品由后端限制访问。' },
    { title: '订单与服务', text: '订单保存收件人、电话、地址和商品快照，仅本人及管理员可通过相关接口访问。云端创作服务启用后，提交的描述或图片会发送至所选服务提供方处理；请避免上传个人敏感信息。' },
    { title: '浏览器与管理', text: '登录信息与访问令牌保存在浏览器本地存储，退出时清除本地登录信息和服务端会话。服务端保留任务、积分和管理操作记录以便排查与审计。' },
    { title: '修改和移除', text: '可在个人中心修改资料和删除自己的作品。删除作品记录不会立即删除可能被其他记录引用的上传文件。涉及账户或订单数据处理，请联系实际运营方；部署方应补充真实联系渠道和保留期限。' }
  ] }
}
const page = computed(() => pages[route.path] || pages['/help'])
</script>
<style scoped>.information{max-width:900px}.information section{margin:28px 0}.information h2{font-size:22px;color:#2d6172}.information p{line-height:1.9;color:#53616c}</style>
