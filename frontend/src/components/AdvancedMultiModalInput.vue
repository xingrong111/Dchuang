<template>
 <div class="multi-modal-input">
  <div class="mode-switch" role="tablist" aria-label="输入方式"><button v-for="mode in modes" :key="mode.id" role="tab" :aria-selected="currentMode===mode.id" :class="{active:currentMode===mode.id}" :disabled="busy" @click="currentMode=mode.id">{{ mode.name }}</button></div>
  <section v-if="currentMode==='text'" class="input-mode"><label for="creation-text">作品描述</label><textarea id="creation-text" v-model="textInput" :disabled="busy" maxlength="2000" placeholder="描述造型、色彩和配件，例如：朱红衣袍的阿福，怀抱瑞狮，圆润陶土质感。"/><span class="counter">{{ textInput.length }}/2000</span><p class="feedback" aria-live="polite">{{ textFeedback }}</p><button :disabled="busy" @click="sendTextInput">提交创作</button></section>
  <section v-else-if="currentMode==='voice'" class="input-mode"><p class="hint">语音识别后可编辑文字，再提交创作。首次使用需要允许麦克风。</p><div class="image-actions"><button :disabled="busy||isListening||!voiceSupported" @click="startVoiceInput">{{ isListening?'正在聆听…':'开始语音输入' }}</button><button v-if="isListening" class="secondary" @click="stopVoiceInput">停止收音</button></div><p class="feedback" aria-live="polite">{{ voiceSupported?voiceFeedback:'当前浏览器不支持语音识别，请使用文本输入。' }}</p><label for="voice-text">识别文本（可修改）</label><textarea id="voice-text" v-model="textInput" :disabled="busy||isListening" maxlength="2000" placeholder="识别文字将在这里显示，也可直接输入。"/><button :disabled="busy||isListening||!textInput.trim()" @click="sendTextInput">提交创作</button></section>
  <section v-else class="input-mode"><label for="reference-image">参考图片</label><input id="reference-image" ref="fileInput" type="file" :disabled="busy" accept=".png,.jpg,.jpeg,.webp,.gif" @change="handleImageUpload"/><div class="drag-area" :aria-disabled="busy" @drop.prevent="handleDrop" @dragover.prevent>拖拽一张图片到此处<br/><small>PNG / JPG / WEBP / GIF，最大10 MB</small></div><img v-if="imagePreview" :src="imagePreview" alt="所选参考图片预览" class="image-preview"/><p v-if="pendingFile" class="file-name">{{ pendingFile.name }}</p><p class="feedback" aria-live="polite">{{ imageFeedback }}</p><div class="image-actions"><button :disabled="busy||!pendingFile" @click="sendImage('generate')">以图创作</button><button class="secondary" :disabled="busy||!pendingFile" @click="sendImage('analyze')">风格分析</button><button v-if="pendingFile" class="secondary" :disabled="busy" @click="clearImage">移除图片</button></div></section>
 </div>
</template>
<script setup>
import { ref, computed, watch, onUnmounted, onDeactivated } from 'vue'
import { uploadFile } from '@/api/workshop'
import { useUserStore } from '@/store/userStore'
const props=defineProps({disabled:{type:Boolean,default:false}}),emit=defineEmits(['generate','analyze']),userStore=useUserStore()
const modes=[{id:'text',name:'文本输入'},{id:'voice',name:'语音输入'},{id:'image',name:'图像输入'}]
const currentMode=ref('text'),textInput=ref(''),textFeedback=ref(''),voiceFeedback=ref(''),imageFeedback=ref(''),imagePreview=ref(''),pendingFile=ref(null),fileInput=ref(null),isListening=ref(false),isUploading=ref(false)
const busy=computed(()=>props.disabled||isUploading.value),voiceSupported=!!(window.SpeechRecognition||window.webkitSpeechRecognition)
let recognition=null,disposed=false,voiceVersion=0,fileVersion=0
const stopVoiceInput=()=>{try{recognition?.stop()}catch{isListening.value=false}}
const abortVoice=()=>{voiceVersion++;try{recognition?.abort()}catch{/* Already stopped */}recognition=null;isListening.value=false}
watch(currentMode,()=>abortVoice())
watch(()=>props.disabled,value=>{if(value)abortVoice()})
onDeactivated(abortVoice)
onUnmounted(()=>{disposed=true;fileVersion++;abortVoice();if(imagePreview.value)URL.revokeObjectURL(imagePreview.value)})
const startVoiceInput=()=>{
 if(busy.value||isListening.value||!voiceSupported)return
 if(!window.isSecureContext){voiceFeedback.value='语音输入需要HTTPS或本机地址，请改用文本输入。';return}
 abortVoice();const version=voiceVersion,Speech=window.SpeechRecognition||window.webkitSpeechRecognition
 try{
  const speech=new Speech();recognition=speech;speech.lang='zh-CN';speech.interimResults=false;speech.continuous=false;speech.maxAlternatives=1
  speech.onresult=event=>{if(disposed||version!==voiceVersion)return;const text=Array.from(event.results).map(result=>result[0]?.transcript||'').join(' ').trim();if(text){textInput.value=text.slice(0,2000);voiceFeedback.value='识别完成，可修改文字后提交。'}else voiceFeedback.value='没有识别到文字，请重新收音。'}
  speech.onerror=event=>{if(disposed||version!==voiceVersion)return;const messages={'not-allowed':'麦克风权限被拒绝，请在浏览器设置中允许麦克风。','service-not-allowed':'语音识别服务不可用，请使用文本输入。','audio-capture':'没有可用麦克风，请检查设备连接。','no-speech':'没有检测到语音，请重试。','network':'语音识别网络不可用，请使用文本输入。','aborted':'已停止收音。'};voiceFeedback.value=messages[event.error]||'语音识别失败，请重试或使用文本输入。';isListening.value=false}
  speech.onend=()=>{if(version===voiceVersion){isListening.value=false;recognition=null}}
  speech.start();isListening.value=true;voiceFeedback.value='正在收音，请描述你的作品。'
 }catch{isListening.value=false;voiceFeedback.value='无法启动语音识别，请检查麦克风权限或使用文本输入。'}
}
const clearImage=()=>{fileVersion++;pendingFile.value=null;if(imagePreview.value)URL.revokeObjectURL(imagePreview.value);imagePreview.value='';imageFeedback.value='';if(fileInput.value)fileInput.value.value=''}
const acceptFile=async file=>{
 if(busy.value||!file)return
 const version=++fileVersion,extension=file.name.split('.').pop().toLowerCase()
 pendingFile.value=null;if(imagePreview.value)URL.revokeObjectURL(imagePreview.value);imagePreview.value=''
 if(!['png','jpg','jpeg','webp','gif'].includes(extension)||!['image/png','image/jpeg','image/webp','image/gif'].includes(file.type)){imageFeedback.value='请选择PNG、JPG、WEBP或GIF格式的图片。';return}
 if(!file.size||file.size>10*1024*1024){imageFeedback.value='图片不能为空，且不能超过10 MB。';return}
 const url=URL.createObjectURL(file)
 try{const img=new Image();img.src=url;await img.decode();if(!img.naturalWidth||!img.naturalHeight)throw Error('Invalid image');if(disposed||version!==fileVersion){URL.revokeObjectURL(url);return}
  if(imagePreview.value)URL.revokeObjectURL(imagePreview.value);pendingFile.value=file;imagePreview.value=url;imageFeedback.value='图片已选择，请选择创作或风格分析。'
 }catch{URL.revokeObjectURL(url);if(!disposed&&version===fileVersion)imageFeedback.value='无法读取这张图片，请选择有效图片文件。'}
}
const handleImageUpload=event=>{acceptFile(event.target.files[0]);event.target.value=''}
const handleDrop=event=>{if(busy.value)return;if(event.dataTransfer.files.length!==1){imageFeedback.value='每次请选择一张参考图片。';return}acceptFile(event.dataTransfer.files[0])}
const sendTextInput=()=>{if(busy.value)return;if(!textInput.value.trim()){textFeedback.value='请先填写作品描述。';return}if(!userStore.user?.token){textFeedback.value='请先登录后提交创作。';return}textFeedback.value='描述已提交，请等待处理结果。';emit('generate',{task_type:'text_to_3d',prompt:textInput.value.trim()})}
const sendImage=async action=>{
 if(busy.value||!pendingFile.value)return
 if(!userStore.user?.token){imageFeedback.value='请先登录后上传图片。';return}
 const file=pendingFile.value;isUploading.value=true;imageFeedback.value='正在上传参考图片…'
 try{const response=await uploadFile(file);if(disposed)return;imageFeedback.value=action==='generate'?'参考图片已提交创作。':'参考图片已提交分析。';emit(action,action==='generate'?{task_type:'image_to_3d',input_url:response.data.url}:{input_url:response.data.url})}
 catch{if(!disposed)imageFeedback.value='图片上传失败，请重试。'}finally{isUploading.value=false}
}
</script>
<style scoped>
.multi-modal-input{padding:8px 0}.mode-switch{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:22px}.mode-switch button{padding:10px 14px;border:1px solid #d3dbd3;border-radius:20px;background:white;color:#365e58;cursor:pointer}.mode-switch .active{color:white;background:#365e58}.input-mode{display:flex;flex-direction:column;gap:10px}.input-mode label{font-size:14px;color:#365e58}.input-mode textarea{box-sizing:border-box;width:100%;min-height:145px;resize:vertical;padding:12px;font:inherit;border:1px solid #d3dbd3;border-radius:10px;line-height:1.7}.input-mode button{border:0;border-radius:8px;padding:10px 15px;background:#365e58;color:white;cursor:pointer}.input-mode button.secondary{background:#a1794f}.input-mode button:disabled,.mode-switch button:disabled{opacity:.5;cursor:not-allowed}.counter{text-align:right;font-size:12px;color:#776e5f}.feedback,.hint{font-size:13px;line-height:1.8;color:#67726a;overflow-wrap:anywhere}.image-actions{display:flex;gap:8px;flex-wrap:wrap}.image-preview{max-width:100%;max-height:230px;object-fit:contain;border-radius:10px}.drag-area{text-align:center;padding:24px 8px;border:1px dashed #b7c3b5;border-radius:10px;line-height:1.8;color:#68776b}.file-name{overflow-wrap:anywhere;font-size:12px;color:#68776b}input[type=file]{max-width:100%}
</style>
