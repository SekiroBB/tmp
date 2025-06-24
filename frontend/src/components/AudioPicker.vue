<template>
  <div class="visualizer">
    <canvas ref="canvasRef" :width="width" :height="height" class="canvas"></canvas>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from "vue";

const props = defineProps({
  volume: {
    type: Number,
    required: true,
    default: 0,
    validator: (value) => value >= 0 && value <= 1
  },
  width: {
    type: Number,
    default: 400,
  },
  height: {
    type: Number,
    default: 400,
  }
});

const canvasRef = ref(null);
let ctx = ref(null);
let animationFrame = ref(null);
let currentVolume = ref(0); // 当前显示的音量值
const EASING_FACTOR = 0.1; // 缓动系数，控制过渡速度

// 主要绘制函数
const draw = () => {
  if (!ctx.value) return;

  // 计算当前音量和目标音量之间的差值
  const volumeDiff = props.volume - currentVolume.value;
  
  // 使用缓动公式更新当前音量
  currentVolume.value += volumeDiff * EASING_FACTOR;

  // 清除画布内容
  ctx.value.clearRect(0, 0, props.width, props.height);

  // 设置基本绘图参数
  const centerX = props.width / 2;  // 画布中心X坐标
  const centerY = props.height / 2;  // 画布中心Y坐标
  const baseRadius = Math.min(props.width, props.height) / 2.5;  // 基础半径
  const radius = baseRadius * (0.5 + currentVolume.value * 0.5);  // 使用currentVolume来控制半径大小

  // 创建渐变色
  const gradient = ctx.value.createLinearGradient(0, 0, props.width, props.height);
  gradient.addColorStop(0, '#ff00ff');  // 渐变起始色
  gradient.addColorStop(0.5, '#00ffff'); // 渐变中间色
  gradient.addColorStop(1, '#0080ff');   // 渐变结束色
  
  // 设置绘图样式
  ctx.value.imageSmoothingEnabled = true;  // 启用图像平滑
  ctx.value.imageSmoothingQuality = 'high';  // 设置最高质量的平滑
  ctx.value.shadowBlur = 20;  // 阴影模糊程度
  ctx.value.shadowColor = '#00ffff';  // 阴影颜色
  ctx.value.strokeStyle = gradient;  // 使用渐变作为描边样式
  ctx.value.lineWidth = 4;  // 线条宽度
  ctx.value.lineCap = 'round';  // 线条端点样式
  ctx.value.lineJoin = 'round';  // 线条连接处样式

  // 绘制圆形
  ctx.value.beginPath();
  ctx.value.arc(centerX, centerY, radius, 0, Math.PI * 2);
  ctx.value.closePath();
  ctx.value.stroke();
};

// 动画循环
const animate = () => {
  draw();
  animationFrame.value = requestAnimationFrame(animate);
};

onMounted(() => {
  if (canvasRef.value) {
    canvasRef.value.width = props.width;
    canvasRef.value.height = props.height;
    ctx.value = canvasRef.value.getContext('2d', {
      alpha: true // 确保 canvas 支持透明
    });
    // 启动动画循环
    animate();
  }
});

onUnmounted(() => {
  if (animationFrame.value) {
    cancelAnimationFrame(animationFrame.value);
  }
});
</script>

<style scoped>
.visualizer {
  border-radius: 8px;
  overflow: hidden;
  aspect-ratio: 1;
  width: 100%;
  max-width: 400px;
  margin: 0 auto;
  display: flex;
  justify-content: center;
  align-items: center;
}

.canvas {
  width: 100%;
  height: 100%;
  display: block;
}
</style>