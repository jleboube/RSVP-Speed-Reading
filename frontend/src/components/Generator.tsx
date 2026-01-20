import { useState, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { ArrowLeft, Upload, X, Loader2, Download, Play } from 'lucide-react'

interface GeneratorProps {
  onBack: () => void
}

interface GenerationResult {
  job_id: string
  word_count: number
  download_url: string
}

interface JobStatus {
  job_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  percent: number
  message?: string
  current?: number
  total?: number
  download_url?: string
  word_count?: number
}

export default function Generator({ onBack }: GeneratorProps) {
  const [text, setText] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [wpm, setWpm] = useState(300)
  const [font, setFont] = useState('arial')
  const [textColor, setTextColor] = useState('#000000')
  const [bgColor, setBgColor] = useState('#FFFFFF')
  const [highlightColor, setHighlightColor] = useState('#FF0000')
  const [pauseOnPunctuation, setPauseOnPunctuation] = useState(true)
  const [wordGrouping, setWordGrouping] = useState(1)
  const [isGenerating, setIsGenerating] = useState(false)
  const [result, setResult] = useState<GenerationResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
      }
    }
  }, [])

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile) {
      const validTypes = [
        'text/plain',
        'text/markdown',
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      ]
      const validExtensions = ['.txt', '.md', '.pdf', '.docx']
      const hasValidExtension = validExtensions.some((ext) =>
        selectedFile.name.toLowerCase().endsWith(ext)
      )

      if (!validTypes.includes(selectedFile.type) && !hasValidExtension) {
        setError('Invalid file type. Supported: TXT, PDF, DOCX, Markdown')
        return
      }
      if (selectedFile.size > 5 * 1024 * 1024) {
        setError('File too large. Maximum size is 5MB.')
        return
      }
      setFile(selectedFile)
      setError(null)
    }
  }

  const pollJobStatus = async (jobId: string) => {
    try {
      const response = await fetch(`/api/status/${jobId}`)
      if (!response.ok) {
        throw new Error('Failed to get job status')
      }

      const status: JobStatus = await response.json()
      setJobStatus(status)

      if (status.status === 'completed') {
        // Stop polling
        if (pollingRef.current) {
          clearInterval(pollingRef.current)
          pollingRef.current = null
        }
        setIsGenerating(false)
        setResult({
          job_id: jobId,
          word_count: status.word_count || 0,
          download_url: status.download_url || `/api/download/${jobId}`,
        })
      } else if (status.status === 'failed') {
        // Stop polling
        if (pollingRef.current) {
          clearInterval(pollingRef.current)
          pollingRef.current = null
        }
        setIsGenerating(false)
        setError(status.message || 'Video generation failed')
      }
    } catch (err) {
      console.error('Polling error:', err)
    }
  }

  const handleGenerate = async () => {
    if (!text.trim() && !file) {
      setError('Please enter text or upload a file')
      return
    }

    setIsGenerating(true)
    setError(null)
    setResult(null)
    setJobStatus(null)

    const formData = new FormData()
    if (file) {
      formData.append('file', file)
    } else {
      formData.append('text', text)
    }
    formData.append('wpm', wpm.toString())
    formData.append('font', font)
    formData.append('text_color', textColor)
    formData.append('bg_color', bgColor)
    formData.append('highlight_color', highlightColor)
    formData.append('pause_on_punctuation', pauseOnPunctuation.toString())
    formData.append('word_grouping', wordGrouping.toString())

    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        body: formData,
      })

      const contentType = response.headers.get('content-type') || ''

      if (!response.ok) {
        if (contentType.includes('application/json')) {
          const errorData = await response.json()
          throw new Error(errorData.detail || 'Generation failed')
        } else {
          if (response.status === 504 || response.status === 408) {
            throw new Error('Request timed out. Try reducing the text length or increasing the WPM speed.')
          }
          throw new Error(`Server error (${response.status}). The document may be too large or the server is busy.`)
        }
      }

      if (!contentType.includes('application/json')) {
        throw new Error('Unexpected server response. Please try again.')
      }

      const data = await response.json()

      // Job submitted successfully - start polling for status
      setJobStatus({
        job_id: data.job_id,
        status: 'pending',
        percent: 0,
        message: 'Job submitted, waiting to start...',
      })

      // Start polling every 1 second
      pollingRef.current = setInterval(() => {
        pollJobStatus(data.job_id)
      }, 1000)

      // Initial poll
      pollJobStatus(data.job_id)

    } catch (err) {
      setIsGenerating(false)
      if (err instanceof TypeError && err.message.includes('Failed to fetch')) {
        setError('Connection error. The server may be busy processing a large document.')
      } else {
        setError(err instanceof Error ? err.message : 'An error occurred')
      }
    }
  }

  const clearFile = () => {
    setFile(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-gray-800 to-gray-900 text-white">
      {/* Header */}
      <header className="border-b border-white/10">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-4">
          <button
            onClick={onBack}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <h1 className="text-xl font-semibold">Create RSVP Video</h1>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        {/* Text Input */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6 mb-6"
        >
          <div className="flex justify-between items-center mb-4">
            <label htmlFor="text-input" className="block text-lg font-medium">
              Enter Your Text
            </label>
            <span className="text-sm text-gray-400">Word count: {wordCount}</span>
          </div>
          <textarea
            id="text-input"
            className="w-full h-48 p-4 bg-white/5 border border-white/10 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent text-white placeholder-gray-500 resize-none"
            placeholder="Paste your text here..."
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={!!file}
          />

          <div className="mt-4 flex items-center justify-center">
            <span className="text-gray-400 text-sm">or</span>
          </div>

          {/* File Upload */}
          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Upload a document
            </label>
            <div
              className={`border-2 border-dashed rounded-xl p-6 text-center transition-colors ${
                file
                  ? 'border-blue-500/50 bg-blue-500/10'
                  : 'border-white/20 hover:border-white/40'
              }`}
            >
              {file ? (
                <div className="flex items-center justify-center gap-3">
                  <Upload className="w-5 h-5 text-blue-400" />
                  <span className="text-white">{file.name}</span>
                  <button
                    onClick={clearFile}
                    className="p-1 hover:bg-white/10 rounded-full text-red-400"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ) : (
                <label className="cursor-pointer">
                  <Upload className="w-8 h-8 mx-auto mb-2 text-gray-400" />
                  <span className="text-gray-400">Click to upload or drag and drop</span>
                  <input
                    ref={fileInputRef}
                    type="file"
                    className="hidden"
                    accept=".txt,.pdf,.docx,.md"
                    onChange={handleFileChange}
                  />
                </label>
              )}
            </div>
            <p className="mt-2 text-xs text-gray-500">
              Supported: TXT, PDF, DOCX, Markdown (max 5MB)
            </p>
          </div>
        </motion.div>

        {/* Settings */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6 mb-6"
        >
          <h2 className="text-lg font-semibold mb-4">Settings</h2>

          <div className="grid md:grid-cols-2 gap-6">
            {/* Speed Zone Slider */}
            <div className="md:col-span-2 mb-2">
              <label htmlFor="wpm" className="block text-sm font-medium text-gray-300 mb-2">
                Speed (WPM):{' '}
                <span className={
                  wpm <= 300 ? 'text-green-400' :
                  wpm <= 500 ? 'text-blue-400' :
                  wpm <= 800 ? 'text-cyan-400' :
                  wpm <= 1200 ? 'text-yellow-400' :
                  wpm <= 2000 ? 'text-orange-400' :
                  'text-red-400'
                }>
                  {wpm}
                </span>
                <span className={`ml-2 text-xs px-2 py-0.5 rounded-full ${
                  wpm <= 300 ? 'bg-green-500/20 text-green-400' :
                  wpm <= 500 ? 'bg-blue-500/20 text-blue-400' :
                  wpm <= 800 ? 'bg-cyan-500/20 text-cyan-400' :
                  wpm <= 1200 ? 'bg-yellow-500/20 text-yellow-400' :
                  wpm <= 2000 ? 'bg-orange-500/20 text-orange-400' :
                  'bg-red-500/20 text-red-400'
                }`}>
                  {wpm <= 300 ? 'Beginner' :
                   wpm <= 500 ? 'Normal' :
                   wpm <= 800 ? 'Advanced' :
                   wpm <= 1200 ? 'Pro' :
                   wpm <= 2000 ? 'Ultra' :
                   'Non-Human'}
                </span>
              </label>

              {/* Slider track with zone colors */}
              <div className="relative mt-3 mb-1">
                <div className="absolute inset-0 h-2 rounded-lg overflow-hidden flex">
                  <div className="bg-green-500/40 h-full" style={{ width: '4%' }} />
                  <div className="bg-blue-500/40 h-full" style={{ width: '4%' }} />
                  <div className="bg-cyan-500/40 h-full" style={{ width: '6%' }} />
                  <div className="bg-yellow-500/40 h-full" style={{ width: '8%' }} />
                  <div className="bg-orange-500/40 h-full" style={{ width: '16%' }} />
                  <div className="bg-red-500/40 h-full" style={{ width: '62%' }} />
                </div>
                <input
                  id="wpm"
                  type="range"
                  min="100"
                  max="5000"
                  step="10"
                  value={wpm}
                  onChange={(e) => setWpm(Number(e.target.value))}
                  className="relative w-full h-2 bg-transparent rounded-lg appearance-none cursor-pointer z-10"
                />
              </div>

              {/* Speed zone markers */}
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>100</span>
                <span className="text-green-500">300</span>
                <span className="text-blue-500">500</span>
                <span className="text-cyan-500">800</span>
                <span className="text-yellow-500">1.2K</span>
                <span className="text-orange-500">2K</span>
                <span className="text-red-500">5K</span>
              </div>

              {/* Warning for extreme speeds */}
              {wpm > 1200 && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  className={`mt-2 text-xs p-2 rounded-lg ${
                    wpm > 2000
                      ? 'bg-red-500/10 border border-red-500/20 text-red-400'
                      : 'bg-orange-500/10 border border-orange-500/20 text-orange-400'
                  }`}
                >
                  {wpm > 2000
                    ? '⚠️ Non-human speed: ~' + Math.round(60000/wpm) + 'ms per word. Beyond human perception threshold.'
                    : '⚡ Ultra speed: Comprehension may be significantly reduced at this rate.'}
                </motion.div>
              )}
            </div>

            <div>
              <label htmlFor="word-grouping" className="block text-sm font-medium text-gray-300 mb-2">
                Words per frame: <span className="text-blue-400">{wordGrouping}</span>
              </label>
              <input
                id="word-grouping"
                type="range"
                min="1"
                max="3"
                value={wordGrouping}
                onChange={(e) => setWordGrouping(Number(e.target.value))}
                className="w-full h-2 bg-white/10 rounded-lg appearance-none cursor-pointer"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>1</span>
                <span>3</span>
              </div>
            </div>

            <div>
              <label htmlFor="font" className="block text-sm font-medium text-gray-300 mb-2">
                Font
              </label>
              <select
                id="font"
                value={font}
                onChange={(e) => setFont(e.target.value)}
                className="w-full p-3 bg-white/5 border border-white/10 rounded-xl text-white focus:ring-2 focus:ring-blue-500"
              >
                <option value="arial">Sans-serif (DejaVu Sans)</option>
                <option value="serif">Serif (DejaVu Serif)</option>
                <option value="mono">Monospace (DejaVu Mono)</option>
              </select>
            </div>

            <div className="flex items-center">
              <input
                id="pause-punctuation"
                type="checkbox"
                checked={pauseOnPunctuation}
                onChange={(e) => setPauseOnPunctuation(e.target.checked)}
                className="w-5 h-5 rounded bg-white/10 border-white/20 text-blue-500 focus:ring-blue-500"
              />
              <label htmlFor="pause-punctuation" className="ml-3 text-sm text-gray-300">
                Pause on punctuation
              </label>
            </div>

            <div>
              <label htmlFor="text-color" className="block text-sm font-medium text-gray-300 mb-2">
                Text Color
              </label>
              <div className="flex items-center gap-3">
                <input
                  id="text-color"
                  type="color"
                  value={textColor}
                  onChange={(e) => setTextColor(e.target.value)}
                  className="h-10 w-16 rounded-lg cursor-pointer bg-transparent"
                />
                <span className="text-sm text-gray-400 font-mono">{textColor}</span>
              </div>
            </div>

            <div>
              <label htmlFor="bg-color" className="block text-sm font-medium text-gray-300 mb-2">
                Background Color
              </label>
              <div className="flex items-center gap-3">
                <input
                  id="bg-color"
                  type="color"
                  value={bgColor}
                  onChange={(e) => setBgColor(e.target.value)}
                  className="h-10 w-16 rounded-lg cursor-pointer bg-transparent"
                />
                <span className="text-sm text-gray-400 font-mono">{bgColor}</span>
              </div>
            </div>

            <div className="md:col-span-2">
              <label htmlFor="highlight-color" className="block text-sm font-medium text-gray-300 mb-2">
                Highlight Color (ORP)
              </label>
              <div className="flex items-center gap-3">
                <input
                  id="highlight-color"
                  type="color"
                  value={highlightColor}
                  onChange={(e) => setHighlightColor(e.target.value)}
                  className="h-10 w-16 rounded-lg cursor-pointer bg-transparent"
                />
                <span className="text-sm text-gray-400 font-mono">{highlightColor}</span>
              </div>
            </div>
          </div>
        </motion.div>

        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-3 rounded-xl mb-6"
          >
            {error}
          </motion.div>
        )}

        {/* Progress indicator */}
        {isGenerating && jobStatus && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-blue-500/10 border border-blue-500/20 px-4 py-4 rounded-xl mb-6"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-blue-400 font-medium">
                {jobStatus.status === 'pending' && 'Queued...'}
                {jobStatus.status === 'processing' && 'Processing...'}
              </span>
              <span className="text-blue-400">{jobStatus.percent}%</span>
            </div>
            <div className="w-full bg-white/10 rounded-full h-2">
              <motion.div
                className="bg-gradient-to-r from-blue-500 to-cyan-500 h-2 rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${jobStatus.percent}%` }}
                transition={{ duration: 0.3 }}
              />
            </div>
            {jobStatus.message && (
              <p className="text-sm text-gray-400 mt-2">{jobStatus.message}</p>
            )}
            {jobStatus.current !== undefined && jobStatus.total !== undefined && (
              <p className="text-xs text-gray-500 mt-1">
                {jobStatus.current.toLocaleString()} / {jobStatus.total.toLocaleString()} words
              </p>
            )}
          </motion.div>
        )}

        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={handleGenerate}
          disabled={isGenerating || (!text.trim() && !file)}
          className="w-full py-4 bg-gradient-to-r from-blue-500 to-cyan-500 text-white rounded-xl font-semibold text-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-blue-500/25"
        >
          {isGenerating ? (
            <span className="flex items-center justify-center gap-2">
              <Loader2 className="w-5 h-5 animate-spin" />
              Generating Video...
            </span>
          ) : (
            'Generate Video'
          )}
        </motion.button>

        {result && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6 mt-6"
          >
            <h2 className="text-lg font-semibold mb-4 text-white flex items-center gap-2">
              <Play className="w-5 h-5 text-green-400" />
              Your Video is Ready
            </h2>
            <p className="text-gray-400 mb-4">
              Generated video with {result.word_count.toLocaleString()} words
            </p>

            <div className="mb-4 rounded-xl overflow-hidden bg-black">
              <video
                controls
                className="w-full"
                src={result.download_url}
              >
                Your browser does not support the video tag.
              </video>
            </div>

            <motion.a
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              href={result.download_url}
              download="rsvp_video.mp4"
              className="inline-flex items-center gap-2 px-6 py-3 bg-green-500 hover:bg-green-600 text-white rounded-xl font-semibold transition-colors"
            >
              <Download className="w-5 h-5" />
              Download MP4
            </motion.a>
          </motion.div>
        )}
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-white/10 py-8 mt-12">
        <div className="max-w-4xl mx-auto px-4 text-center text-gray-500 text-sm">
          Copyright 2026 Joe LeBoube
        </div>
      </footer>
    </div>
  )
}
