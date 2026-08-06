<template>
  <div class="multi-modal-view">
    <!-- 左侧多模态输入模式选择 -->
    <div class="input-panel">
      <h3>多模态输入</h3>
      <AdvancedMultiModalInput />
    </div>

    <!-- 右侧3D模型预览 -->
    <div class="preview-panel" ref="previewContainer"></div>
  </div>
</template>

<script>
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';
import AdvancedMultiModalInput from '@/components/AdvancedMultiModalInput.vue';

export default {
  name: 'MultiModalInputView',
  components: { AdvancedMultiModalInput },
  mounted() {
    this.init3DPreview();
  },
  methods: {
    init3DPreview() {
      const container = this.$refs.previewContainer;
      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(
        75,
        container.clientWidth / container.clientHeight,
        0.1,
        1000
      );
      const renderer = new THREE.WebGLRenderer();
      renderer.setSize(container.clientWidth, container.clientHeight);
      container.appendChild(renderer.domElement);

      const light = new THREE.DirectionalLight(0xffffff, 1);
      light.position.set(10, 10, 10);
      scene.add(light);

      const geometry = new THREE.BoxGeometry();
      const material = new THREE.MeshStandardMaterial({ color: 0x007bff });
      const cube = new THREE.Mesh(geometry, material);
      scene.add(cube);

      const controls = new OrbitControls(camera, renderer.domElement);
      camera.position.z = 5;

      const animate = () => {
        requestAnimationFrame(animate);
        cube.rotation.x += 0.01;
        cube.rotation.y += 0.01;
        renderer.render(scene, camera);
      };
      animate();
    },
  },
};
</script>

<style scoped>
.multi-modal-view {
  display: flex;
  height: 100%;
}
.input-panel {
  width: 30%;
  background: #f9f9f9;
  padding: 20px;
  border-right: 1px solid #ddd;
}
.preview-panel {
  flex: 1;
  background: #eaeaea;
}
</style>
