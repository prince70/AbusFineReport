import axios from 'axios'

axios.defaults.baseURL = '/'
axios.defaults.withCredentials = true

const authStore = {
  getUser() {
    return JSON.parse(localStorage.getItem('user') || '{}')
  },
  getPermissions() {
    return JSON.parse(localStorage.getItem('permissions') || '[]')
  },
  getMenus() {
    return JSON.parse(localStorage.getItem('menus') || '[]')
  },
  saveAuth(payload) {
    localStorage.setItem('user', JSON.stringify(payload.user || {}))
    localStorage.setItem('permissions', JSON.stringify(payload.permissions || []))
    localStorage.setItem('menus', JSON.stringify(payload.menus || []))
  },
  clear() {
    localStorage.removeItem('user')
    localStorage.removeItem('permissions')
    localStorage.removeItem('menus')
  }
}

export function installAuthInterceptor(router) {
  axios.interceptors.response.use(
    response => response,
    error => {
      if (error.response && error.response.status === 401) {
        authStore.clear()
        if (router.currentRoute.path !== '/login') {
          router.push('/login')
        }
      }
      return Promise.reject(error)
    }
  )
}

export async function tryRestoreSession() {
  try {
    const res = await axios.get('/api/check-login')
    if (res.data.loggedIn) {
      authStore.saveAuth({
        user: res.data.user,
        permissions: res.data.permissions,
        menus: res.data.menus
      })
      return true
    }
  } catch (error) {
    // Ignore errors and fallback to unauthenticated state.
  }
  authStore.clear()
  return false
}

export default authStore
