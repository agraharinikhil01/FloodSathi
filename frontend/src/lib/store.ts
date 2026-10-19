import { create } from 'zustand'

interface AppState {
  theme: 'dark' | 'light'
  toggleTheme: () => void
  selectedDistrict: string
  setSelectedDistrict: (district: string) => void
  isSosOpen: boolean
  setSosOpen: (open: boolean) => void
  userToken: string | null
  userRole: string | null
  setUserAuth: (token: string | null, role: string | null) => void
}

export const useAppStore = create<AppState>((set) => ({
  theme: 'dark',
  toggleTheme: () =>
    set((state) => {
      const nextTheme = state.theme === 'dark' ? 'light' : 'dark'
      if (nextTheme === 'dark') {
        document.documentElement.classList.add('dark')
      } else {
        document.documentElement.classList.remove('dark')
      }
      return { theme: nextTheme }
    }),
  selectedDistrict: 'Patna',
  setSelectedDistrict: (district) => set({ selectedDistrict: district }),
  isSosOpen: false,
  setSosOpen: (open) => set({ isSosOpen: open }),
  userToken: localStorage.getItem('token'),
  userRole: localStorage.getItem('role'),
  setUserAuth: (token, role) => {
    if (token) localStorage.setItem('token', token)
    else localStorage.removeItem('token')
    if (role) localStorage.setItem('role', role)
    else localStorage.removeItem('role')
    set({ userToken: token, userRole: role })
  },
}))
