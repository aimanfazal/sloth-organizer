import { Route, Routes } from 'react-router-dom'
import Home from './pages/Home'
import Scan from './pages/Scan'
import Organize from './pages/Organize'
import Tasks from './pages/Tasks'
import Review from './pages/Review'
import Apply from './pages/Apply'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/scan" element={<Scan />} />
      <Route path="/organize" element={<Organize />} />
      <Route path="/tasks" element={<Tasks />} />
      <Route path="/review" element={<Review />} />
      <Route path="/apply" element={<Apply />} />
    </Routes>
  )
}
