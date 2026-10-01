import { Routes, Route } from 'react-router-dom'
import { CheckProvider } from './CheckContext'
import Splash from './pages/Splash'
import Home from './pages/Home'
import RiskQuestion from './pages/RiskQuestion'
import Waiting from './pages/Waiting'
import Approved from './pages/Approved'
import Denied from './pages/Denied'
import Timeout from './pages/Timeout'
import Verifier from './pages/Verifier'

export default function App() {
  return (
    <CheckProvider>
      <Routes>
        <Route path="/" element={<Splash />} />
        <Route path="/home" element={<Home />} />
        <Route path="/check/:step" element={<RiskQuestion />} />
        <Route path="/waiting" element={<Waiting />} />
        <Route path="/result/approved" element={<Approved />} />
        <Route path="/result/denied" element={<Denied />} />
        <Route path="/result/timeout" element={<Timeout />} />
        <Route path="/verify" element={<Verifier />} />
      </Routes>
    </CheckProvider>
  )
}
