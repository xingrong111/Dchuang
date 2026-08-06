<template>
  <div class="multi-modal-input">
    <!-- 模块切换按钮 -->
    <div class="mode-switch">
      <button @click="currentMode = 'text'" :class="{ active: currentMode === 'text' }">文本输入</button>
      <button @click="currentMode = 'voice'" :class="{ active: currentMode === 'voice' }">语音输入</button>
      <button @click="currentMode = 'image'" :class="{ active: currentMode === 'image' }">图像输入</button>
    </div>

    <!-- 文本输入模块 -->
    <div v-if="currentMode === 'text'" class="input-mode">
      <textarea v-model="textInput" placeholder="请输入文本..."></textarea>
      <p class="feedback">{{ textFeedback }}</p>
      <button @click="sendTextInput">确认</button>
    </div>

    <!-- 语音输入模块 -->
    <div v-if="currentMode === 'voice'" class="input-mode">
      <button @click="startVoiceInput">开始语音输入</button>
      <p>{{ voiceFeedback }}</p>
    </div>

    <!-- 图像输入模块 -->
    <div v-if="currentMode === 'image'" class="input-mode">
      <input type="file" @change="handleImageUpload" accept="image/*,video/*" />
      <div class="drag-area" @drop.prevent="handleDrop" @dragover.prevent>
        拖拽文件到此处上传
      </div>
      <img v-if="imagePreview" :src="imagePreview" alt="预览" class="image-preview" />
      <button @click="sendImageInput">确认</button>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue';
import { uploadFile } from '@/api/workshop';

export default {
  name: 'AdvancedMultiModalInput',
  setup() {
    const currentMode = ref('text');
    const textInput = ref('');
    const textFeedback = ref('AI 正在分析您的输入...');
    const voiceFeedback = ref('');
    const imagePreview = ref(null);

    const startVoiceInput = () => {
      voiceFeedback.value = '语音输入中...';

      // 使用 Web Speech API 实现语音识别
      const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
      recognition.lang = 'zh-CN';
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;

      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        voiceFeedback.value = `识别结果: ${transcript}`;
      };

      recognition.onerror = (event) => {
        voiceFeedback.value = `语音识别错误: ${event.error}`;
      };

      recognition.start();
    };

    const handleImageUpload = (event) => {
      const file = event.target.files[0];
      if (file) {
        imagePreview.value = URL.createObjectURL(file);
        textFeedback.value = '正在上传图片...';
        uploadFile(file)
          .then(() => {
            textFeedback.value = '图片上传成功！';
          })
          .catch(() => {
            textFeedback.value = '图片上传失败，请检查网络连接。';
          });
      }
    };

    const handleDrop = (event) => {
      const file = event.dataTransfer.files[0];
      if (file) {
        imagePreview.value = URL.createObjectURL(file);
      }
    };

    const sendTextInput = () => {
      if (textInput.value.trim() !== '') {
        textFeedback.value = '正在发送文本数据...';
        // 模拟发送数据到后端
        setTimeout(() => {
          textFeedback.value = '文本数据已成功发送！';
        }, 1000);
      } else {
        textFeedback.value = '请输入有效的文本内容。';
      }
    };

    return {
      currentMode,
      textInput,
      textFeedback,
      voiceFeedback,
      imagePreview,
      startVoiceInput,
      handleImageUpload,
      handleDrop,
      sendTextInput,
    };
  },
};
</script>

<style scoped>
.multi-modal-input {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
}
.mode-switch {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}
.mode-switch button {
  padding: 12px 24px;
  border: none;
  cursor: pointer;
  background: linear-gradient(135deg, #4a90a4, #2d6172);
  color: white;
  font-weight: bold;
  border-radius: 25px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s, box-shadow 0.2s;
}
.mode-switch button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 8px rgba(0, 0, 0, 0.15);
}
.mode-switch button.active {
  background: linear-gradient(135deg, #2d6172, #4a90a4);
  box-shadow: 0 6px 8px rgba(0, 0, 0, 0.2);
}

/* 美化确认按钮 */
.input-mode button {
  margin-top: 15px;
  padding: 10px 20px;
  background: #4a90a4;
  color: white;
  border: none;
  border-radius: 20px;
  font-size: 16px;
  font-weight: bold;
  cursor: pointer;
  transition: background 0.3s, transform 0.2s;
}
.input-mode button:hover {
  background: #2d6172;
  transform: scale(1.05);
}

/* 其他样式 */
textarea {
  width: 100%;
  height: 100px;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 5px;
}
.feedback {
  margin-top: 10px;
  color: #888;
}
.drag-area {
  width: 100%;
  height: 100px;
  border: 2px dashed #ccc;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 10px;
  border-radius: 5px;
}
.image-preview {
  margin-top: 10px;
  max-width: 100%;
  border-radius: 5px;
}
</style>
