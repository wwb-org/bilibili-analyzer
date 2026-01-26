<template>
  <div class="home-page">
    <div class="page-header">
      <h1 class="page-title">首页仪表盘</h1>
      <p class="page-desc">数据概览与核心指标监控</p>
    </div>
    
    <div class="dashboard-grid">
      <!-- 核心指标卡片占位 -->
      <div class="stat-card">
        <div class="stat-title">视频总数</div>
        <div class="stat-value">--</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">总播放量</div>
        <div class="stat-value">--</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">总评论数</div>
        <div class="stat-value">--</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">总弹幕数</div>
        <div class="stat-value">--</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home-page {
  padding: 24px;
}

.page-header {
  margin-bottom: 32px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.page-desc {
  font-size: 14px;
  color: var(--text-secondary);
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
}

.stat-card {
  background: var(--bg-white);
  padding: 24px;
  border-radius: 12px;
  border: 1px solid var(--border-light);
}

.stat-title {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: var(--text-primary);
}
</style>
