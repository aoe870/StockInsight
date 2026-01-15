<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import MainLayout from './layouts/MainLayout.vue'

const route = useRoute()

// 判断是否为公开页面（如登录页）
const isPublicPage = computed(() => route.meta.public === true)
</script>

<template>
  <!-- 公开页面直接渲染 -->
  <router-view v-if="isPublicPage" />
  <!-- 需要认证的页面使用主布局 -->
  <MainLayout v-else />
</template>

<style>
html, body, #app {
  margin: 0;
  padding: 0;
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}
</style>

