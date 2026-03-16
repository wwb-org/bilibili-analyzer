import api from './index'

export const login = (data) => api.post('/auth/login', data)
export const register = (data) => api.post('/auth/register', data)
export const getProfile = () => api.get('/auth/profile')
export const changePassword = (data) => api.put('/auth/password', data)
export const changeUsername = (data) => api.put('/auth/username', data)
export const bindBilibili = (uid) => api.put('/auth/bind-bilibili', { uid })
export const unbindBilibili = () => api.delete('/auth/unbind-bilibili')

export const uploadAvatar = (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/auth/avatar', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export const logout = () => {
  localStorage.removeItem('token')
}
