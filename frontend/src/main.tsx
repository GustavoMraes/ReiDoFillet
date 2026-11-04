import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import { AuthProvider } from './auth/AuthContext.tsx'
import LimiteDeErro from './components/LimiteDeErro.tsx'
import { MensagensProvider } from './components/Mensagens.tsx'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {/* Falhas fora das telas (cabeçalho, provedores): página de erro geral em vez de página em branco. */}
    <LimiteDeErro variante="geral">
      <AuthProvider>
        <MensagensProvider>
          <App />
        </MensagensProvider>
      </AuthProvider>
    </LimiteDeErro>
  </StrictMode>,
)
