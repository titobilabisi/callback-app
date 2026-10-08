import { Routes, Route } from 'react-router-dom'
import { AuthProvider } from './AuthContext'
import { CheckProvider } from './CheckContext'
import Protected from './components/Protected'
import Splash from './pages/Splash'
import SignIn from './pages/SignIn'
import Signup from './pages/Signup'
import Join from './pages/Join'
import Family from './pages/Family'
import Home from './pages/Home'
import RiskQuestion from './pages/RiskQuestion'
import CallerNote from './pages/CallerNote'
import Waiting from './pages/Waiting'
import Approved from './pages/Approved'
import Denied from './pages/Denied'
import Timeout from './pages/Timeout'
import Verifier from './pages/Verifier'

// The role gates here only decide which screen to show. The server checks
// the role again on every request, so these are not the security boundary.
const elder = (page) => <Protected role="elder">{page}</Protected>

export default function App() {
  return (
    <AuthProvider>
      <CheckProvider>
        <Routes>
          <Route path="/" element={<Splash />} />
          <Route path="/signin" element={<SignIn />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/join/:token" element={<Join />} />
          <Route path="/home" element={elder(<Home />)} />
          <Route path="/family" element={elder(<Family />)} />
          <Route path="/check/note" element={elder(<CallerNote />)} />
          <Route path="/check/:step" element={elder(<RiskQuestion />)} />
          <Route path="/waiting" element={elder(<Waiting />)} />
          <Route path="/result/approved" element={elder(<Approved />)} />
          <Route path="/result/denied" element={elder(<Denied />)} />
          <Route path="/result/timeout" element={elder(<Timeout />)} />
          <Route path="/verify" element={<Protected role="verifier"><Verifier /></Protected>} />
        </Routes>
      </CheckProvider>
    </AuthProvider>
  )
}
