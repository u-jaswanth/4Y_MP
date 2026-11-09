import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

// Typefaces: Source Serif 4 for explanations and headings, Hanken
// Grotesk for the interface. Loaded here rather than with a CSS
// @import, which browsers ignore once it is no longer the first rule
// in a bundled stylesheet. If the request fails the CSS falls back to
// Georgia / system-ui, so nothing breaks offline.
const fonts = document.createElement('link')
fonts.rel = 'stylesheet'
fonts.href =
  'https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600;700;800&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,500;0,8..60,600;1,8..60,400;1,8..60,500&display=swap'
document.head.appendChild(fonts)

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
