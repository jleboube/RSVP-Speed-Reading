import { useState, useRef } from 'react'
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
  const fileInputRef = useRef<HTMLInputElement>(null)

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

  const handleGenerate = async () => {
    if (!text.trim() && !file) {
      setError('Please enter text or upload a file')
      return
    }

    setIsGenerating(true)
    setError(null)
    setResult(null)

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

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Generation failed')
      }

      const data: GenerationResult = await response.json()
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setIsGenerating(false)
    }
  }

  const clearFile = () => {
    setFile(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-gray-800 to-gray-900">
      <header className="border-b border-white/10">
        <div className="max-w-4xl mx-auto py-4 px-4 flex items-center gap-4">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={onBack}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors text-white"
          >
            <ArrowLeft className="w-5 h-5" />
          </motion.button>
          <div>
            <h1 className="text-xl font-bold text-white">RSVP Video Generator</h1>
            <p className="text-sm text-gray-400">Create your speed-reading video</p>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto py-8 px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6 mb-6"
        >
          <h2 className="text-lg font-semibold mb-4 text-white">Input Text</h2>

          <div className="mb-4">
            <label htmlFor="text-input" className="block text-sm font-medium text-gray-300 mb-2">
              Paste your text
            </label>
            <textarea
              id="text-input"
              className="w-full h-48 p-4 bg-white/5 border border-white/10 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent text-white placeholder-gray-500 resize-none"
              placeholder="Paste your text here (up to 10,000 words)..."
              value={text}
              onChange={(e) => setText(e.target.value)}
              disabled={!!file}
            />
            <p className="mt-2 text-sm text-gray-400">
              Word count: {text.trim() ? text.trim().split(/\s+/).length : 0}
            </p>
          </div>

          <div className="flex items-center gap-4 mb-4">
            <div className="flex-1 h-px bg-white/10" />
            <span className="text-gray-500 text-sm">or</span>
            <div className="flex-1 h-px bg-white/10" />
          </div>

          <div className="mb-4">
            <label htmlFor="file-input" className="block text-sm font-medium text-gray-300 mb-2">
              Upload a document
            </label>
            <div className="flex items-center gap-4">
              <label className="flex-1 flex items-center justify-center gap-2 p-4 border-2 border-dashed border-white/20 rounded-xl hover:border-blue-500/50 hover:bg-blue-500/5 cursor-pointer transition-colors">
                <Upload className="w-5 h-5 text-gray-400" />
                <span className="text-gray-400">
                  {file ? file.name : 'Choose file or drag here'}
                </span>
                <input
                  ref={fileInputRef}
                  id="file-input"
                  type="file"
                  accept=".txt,.md,.pdf,.docx"
                  onChange={handleFileChange}
                  className="hidden"
                />
              </label>
              {file && (
                <button
                  onClick={clearFile}
                  className="p-2 text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              )}
            </div>
            <p className="mt-2 text-sm text-gray-500">
              Supported: TXT, PDF, DOCX, Markdown (max 5MB)
            </p>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6 mb-6"
        >
          <h2 className="text-lg font-semibold mb-4 text-white">Settings</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label htmlFor="wpm" className="block text-sm font-medium text-gray-300 mb-2">
                Speed (WPM): <span className="text-blue-400">{wpm}</span>
              </label>
              <input
                id="wpm"
                type="range"
                min="100"
                max="800"
                value={wpm}
                onChange={(e) => setWpm(Number(e.target.value))}
                className="w-full h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>100</span>
                <span>800</span>
              </div>
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
                className="w-full h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-blue-500"
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
                className="h-5 w-5 text-blue-500 bg-white/5 border-white/20 rounded focus:ring-blue-500"
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
              Generated video with {result.word_count} words
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
    </div>
  )
}
