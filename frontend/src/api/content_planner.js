import api from './index'

export const getCategories = () => api.get('/content-planner/categories')

export const getCategoryAnalysis = (category) =>
  api.get('/content-planner/category-analysis', { params: { category } })

export const getViralKeywords = (category, top_k = 20) =>
  api.get('/content-planner/keywords', { params: { category, top_k } })

export const getTitleSuggestions = (category, num = 5) =>
  api.get('/content-planner/title-suggestions', { params: { category, num } })

export const scoreTitle = (title, category) =>
  api.post('/content-planner/score-title', { title, category })
