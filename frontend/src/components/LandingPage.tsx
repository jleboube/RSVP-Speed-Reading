import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Zap,
  FileText,
  Sliders,
  Download,
  Play,
  ChevronRight,
  Eye,
  Clock,
  Palette,
  BookOpen,
} from 'lucide-react'

interface LandingPageProps {
  onGetStarted: () => void
}

const DEMO_WORDS = [
  'Speed',
  'reading',
  'just',
  'got',
  'faster.',
  'Transform',
  'text',
  'into',
  'dynamic',
  'video.',
]

function RSVPDemo() {
  const [currentIndex, setCurrentIndex] = useState(0)
  const [isPlaying, setIsPlaying] = useState(true)

  useEffect(() => {
    if (!isPlaying) return
    const interval = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % DEMO_WORDS.length)
    }, 300)
    return () => clearInterval(interval)
  }, [isPlaying])

  const word = DEMO_WORDS[currentIndex]
  const orpIndex = Math.floor(word.length / 3)

  return (
    <motion.div
      className="relative bg-gray-900 rounded-2xl p-8 shadow-2xl overflow-hidden"
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5, delay: 0.3 }}
    >
      <div className="absolute inset-0 bg-gradient-to-br from-blue-600/10 to-cyan-600/10" />
      <div className="absolute top-0 left-1/2 w-0.5 h-4 bg-red-500 transform -translate-x-1/2" />

      <div className="relative h-32 flex items-center justify-center">
        <AnimatePresence mode="wait">
          <motion.div
            key={currentIndex}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.1 }}
            className="text-5xl md:text-6xl font-bold tracking-wide"
          >
            {word.split('').map((char, i) => (
              <span
                key={i}
                className={i === orpIndex ? 'text-red-500' : 'text-white'}
              >
                {char}
              </span>
            ))}
          </motion.div>
        </AnimatePresence>
      </div>

      <div className="flex justify-center mt-4">
        <button
          onClick={() => setIsPlaying(!isPlaying)}
          className="flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/20 rounded-full text-white/80 text-sm transition-colors"
        >
          {isPlaying ? (
            <>
              <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
              Playing at 200 WPM
            </>
          ) : (
            <>
              <Play className="w-4 h-4" />
              Click to play
            </>
          )}
        </button>
      </div>
    </motion.div>
  )
}

const features = [
  {
    icon: FileText,
    title: 'Multiple Formats',
    description: 'Upload TXT, PDF, DOCX, or Markdown files, or simply paste your text.',
    color: 'from-blue-500 to-cyan-500',
  },
  {
    icon: Sliders,
    title: 'Fully Customizable',
    description: 'Adjust speed from 100-800 WPM, colors, fonts, and word grouping.',
    color: 'from-teal-500 to-cyan-400',
  },
  {
    icon: Eye,
    title: 'ORP Highlighting',
    description: 'Optimal Recognition Point highlighting guides your eye for faster reading.',
    color: 'from-orange-500 to-red-500',
  },
  {
    icon: Download,
    title: 'Export to MP4',
    description: 'Download your RSVP video in high-quality MP4 format.',
    color: 'from-green-500 to-emerald-500',
  },
]

const steps = [
  {
    number: '01',
    title: 'Input Your Text',
    description: 'Paste text directly or upload a document in various formats.',
    icon: FileText,
  },
  {
    number: '02',
    title: 'Customize Settings',
    description: 'Adjust reading speed, colors, and display preferences.',
    icon: Sliders,
  },
  {
    number: '03',
    title: 'Generate Video',
    description: 'Click generate and watch your RSVP video come to life.',
    icon: Zap,
  },
  {
    number: '04',
    title: 'Download & Read',
    description: 'Download your video and experience speed reading anywhere.',
    icon: Download,
  },
]

const stats = [
  { value: '700+', label: 'WPM Possible', icon: Zap },
  { value: '10K', label: 'Words Supported', icon: BookOpen },
  { value: '3x', label: 'Faster Reading', icon: Clock },
  { value: '∞', label: 'Customizations', icon: Palette },
]

export default function LandingPage({ onGetStarted }: LandingPageProps) {
  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-gray-800 to-gray-900 text-white overflow-hidden">
      {/* Animated background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-500/20 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-cyan-500/20 rounded-full blur-3xl animate-pulse delay-1000" />
      </div>

      {/* Header */}
      <header className="relative z-10">
        <nav className="max-w-7xl mx-auto px-4 py-6 flex items-center justify-between">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center gap-2"
          >
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-xl flex items-center justify-center">
              <Zap className="w-6 h-6" />
            </div>
            <span className="text-xl font-bold">RSVP Generator</span>
          </motion.div>

          <motion.button
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            onClick={onGetStarted}
            className="px-6 py-2 bg-white/10 hover:bg-white/20 rounded-full font-medium transition-colors"
          >
            Get Started
          </motion.button>
        </nav>
      </header>

      {/* Hero Section */}
      <section className="relative z-10 max-w-7xl mx-auto px-4 pt-12 pb-24">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <h1 className="text-5xl md:text-6xl font-bold leading-tight mb-6">
              Read{' '}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-400">
                700+ Words
              </span>{' '}
              Per Minute
            </h1>
            <p className="text-xl text-gray-300 mb-8 leading-relaxed">
              Transform any text into a dynamic speed-reading video using RSVP
              (Rapid Serial Visual Presentation). Reduce eye movement, increase
              comprehension, and unlock your reading potential.
            </p>
            <div className="flex flex-wrap gap-4">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={onGetStarted}
                className="px-8 py-4 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-xl font-semibold text-lg flex items-center gap-2 shadow-lg shadow-blue-500/25"
              >
                Start Creating
                <ChevronRight className="w-5 h-5" />
              </motion.button>
              <motion.a
                href="#how-it-works"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="px-8 py-4 border border-white/20 hover:bg-white/5 rounded-xl font-semibold text-lg flex items-center gap-2"
              >
                <Play className="w-5 h-5" />
                See How It Works
              </motion.a>
            </div>
          </motion.div>

          <div className="lg:pl-8">
            <RSVPDemo />
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="relative z-10 py-16 border-y border-white/10">
        <div className="max-w-7xl mx-auto px-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {stats.map((stat, index) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                viewport={{ once: true }}
                className="text-center"
              >
                <stat.icon className="w-8 h-8 mx-auto mb-3 text-blue-400" />
                <div className="text-4xl font-bold mb-1">{stat.value}</div>
                <div className="text-gray-400">{stat.label}</div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="relative z-10 py-24">
        <div className="max-w-7xl mx-auto px-4">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl font-bold mb-4">Powerful Features</h2>
            <p className="text-xl text-gray-400 max-w-2xl mx-auto">
              Everything you need to create professional RSVP videos
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                viewport={{ once: true }}
                whileHover={{ y: -5 }}
                className="p-6 bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 hover:border-white/20 transition-colors"
              >
                <div
                  className={`w-12 h-12 rounded-xl bg-gradient-to-br ${feature.color} flex items-center justify-center mb-4`}
                >
                  <feature.icon className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-xl font-semibold mb-2">{feature.title}</h3>
                <p className="text-gray-400">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="relative z-10 py-24 bg-black/20">
        <div className="max-w-7xl mx-auto px-4">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl font-bold mb-4">How It Works</h2>
            <p className="text-xl text-gray-400 max-w-2xl mx-auto">
              Create your first RSVP video in four simple steps
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {steps.map((step, index) => (
              <motion.div
                key={step.number}
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.15 }}
                viewport={{ once: true }}
                className="relative"
              >
                {index < steps.length - 1 && (
                  <div className="hidden lg:block absolute top-12 left-full w-full h-0.5 bg-gradient-to-r from-blue-500/50 to-transparent" />
                )}
                <div className="text-6xl font-bold text-white/5 mb-4">
                  {step.number}
                </div>
                <div className="w-12 h-12 rounded-xl bg-blue-500/20 flex items-center justify-center mb-4">
                  <step.icon className="w-6 h-6 text-blue-400" />
                </div>
                <h3 className="text-xl font-semibold mb-2">{step.title}</h3>
                <p className="text-gray-400">{step.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative z-10 py-24">
        <div className="max-w-4xl mx-auto px-4 text-center">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            className="p-12 rounded-3xl bg-gradient-to-br from-blue-600/20 to-cyan-600/20 border border-white/10"
          >
            <h2 className="text-4xl font-bold mb-4">
              Ready to Supercharge Your Reading?
            </h2>
            <p className="text-xl text-gray-300 mb-8 max-w-2xl mx-auto">
              Join thousands of students, professionals, and speed-reading
              enthusiasts who have transformed how they consume information.
            </p>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={onGetStarted}
              className="px-10 py-4 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-xl font-semibold text-xl shadow-lg shadow-blue-500/25"
            >
              Get Started Free
            </motion.button>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 border-t border-white/10 py-8">
        <div className="max-w-7xl mx-auto px-4 text-center text-gray-400">
          <p>
            Built with FFmpeg, React, and FastAPI. Open source and free to use.
          </p>
        </div>
      </footer>
    </div>
  )
}
