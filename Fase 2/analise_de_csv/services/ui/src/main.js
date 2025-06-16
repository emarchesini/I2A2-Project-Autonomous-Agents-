import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createVuetify } from 'vuetify'
import { createRouter, createWebHistory } from 'vue-router'
import axios from 'axios'

// Configurar axios para usar URLs relativas
axios.defaults.baseURL = ''
axios.defaults.timeout = 30000

// Vuetify
import 'vuetify/styles'
import { aliases, mdi } from 'vuetify/iconsets/mdi'

// Components
import App from './App.vue'
import Home from './views/Home.vue'

// Router
const routes = [
  { path: '/', name: 'Home', component: Home }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Vuetify
const vuetify = createVuetify({
  theme: {
    defaultTheme: 'light',
    themes: {
      light: {
        colors: {
          primary: '#1976D2',
          secondary: '#424242',
          accent: '#82B1FF',
          error: '#FF5252',
          info: '#2196F3',
          success: '#4CAF50',
          warning: '#FFC107',
        },
      },
    },
  },
  icons: {
    defaultSet: 'mdi',
    aliases,
    sets: {
      mdi,
    },
  },
})

// Pinia
const pinia = createPinia()

// Create app
const app = createApp(App)

app.use(pinia)
app.use(router)
app.use(vuetify)

app.mount('#app') 