import { useState } from 'react'
import LandingPage from './components/LandingPage'
import Generator from './components/Generator'

type View = 'landing' | 'generator'

function App() {
  const [view, setView] = useState<View>('landing')

  if (view === 'landing') {
    return <LandingPage onGetStarted={() => setView('generator')} />
  }

  return <Generator onBack={() => setView('landing')} />
}

export default App
