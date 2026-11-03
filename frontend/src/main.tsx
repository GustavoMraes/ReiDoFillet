import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import { AuthProvider } from './auth/AuthContext.tsx'
import { MensagensProvider } from './components/Mensagens.tsx'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider>
      <MensagensProvider>
        <App />
      </MensagensProvider>
    </AuthProvider>
  </StrictMode>,
)
