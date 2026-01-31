'use client'

import { useState, useRef, useEffect } from 'react'
import FileUpload from './FileUpload'

interface Message {
  id: number
  type: 'system' | 'user' | 'success' | 'error' | 'info'
  content: string
  timestamp: Date
}

export default function Terminal() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      type: 'system',
      content: 'MLJ Results Compiler v1.0.0',
      timestamp: new Date(),
    },
    {
      id: 2,
      type: 'system',
      content: '─'.repeat(60),
      timestamp: new Date(),
    },
    {
      id: 3,
      type: 'info',
      content: 'Welcome to the Test Results Collation System',
      timestamp: new Date(),
    },
    {
      id: 4,
      type: 'info',
      content: 'Drop your Excel files (TEST_1 through TEST_5) below to begin processing.',
      timestamp: new Date(),
    },
    {
      id: 5,
      type: 'system',
      content: '─'.repeat(60),
      timestamp: new Date(),
    },
  ])

  const [isProcessing, setIsProcessing] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const addMessage = (type: Message['type'], content: string) => {
    setMessages((prev) => [
      ...prev,
      {
        id: Date.now(),
        type,
        content,
        timestamp: new Date(),
      },
    ])
  }

  const handleFilesSelected = async (files: File[]) => {
    setIsProcessing(true)
    
    addMessage('user', `Selected ${files.length} file(s):`)
    files.forEach((file) => {
      addMessage('info', `  - ${file.name} (${(file.size / 1024).toFixed(2)} KB)`)
    })

    addMessage('system', 'Uploading files...')

    try {
      const formData = new FormData()
      files.forEach((file) => {
        formData.append('files', file)
      })

      const response = await fetch('/api/process', {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()

      if (response.ok) {
        addMessage('success', '✓ Upload successful!')
        addMessage('system', '─'.repeat(60))
        addMessage('info', 'Processing Summary:')
        
        if (data.message) {
          addMessage('info', data.message)
        }
        
        if (data.filesReceived) {
          addMessage('info', `Files received: ${data.filesReceived}`)
        }

        if (data.outputFile) {
          addMessage('success', `✓ Output file generated: ${data.outputFile}`)
        }

        if (data.errorLog) {
          addMessage('info', `Error log: ${data.errorLog}`)
        }

        addMessage('system', '─'.repeat(60))
      } else {
        addMessage('error', `✗ Error: ${data.error || 'Processing failed'}`)
      }
    } catch (error) {
      addMessage('error', `✗ Network error: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setIsProcessing(false)
    }
  }

  const getMessageColor = (type: Message['type']) => {
    switch (type) {
      case 'system':
        return 'text-terminal-text'
      case 'user':
        return 'text-terminal-blue'
      case 'success':
        return 'text-terminal-green'
      case 'error':
        return 'text-terminal-red'
      case 'info':
        return 'text-terminal-yellow'
      default:
        return 'text-terminal-text'
    }
  }

  const getPrefix = (type: Message['type']) => {
    switch (type) {
      case 'user':
        return '$ '
      case 'system':
        return ''
      case 'success':
        return '[OK] '
      case 'error':
        return '[ERROR] '
      case 'info':
        return '[INFO] '
      default:
        return ''
    }
  }

  return (
    <div className="flex flex-col h-screen p-4 font-mono">
      {/* Terminal Header */}
      <div className="flex items-center gap-2 mb-4 pb-2 border-b border-gray-700">
        <div className="flex gap-2">
          <div className="w-3 h-3 rounded-full bg-red-500"></div>
          <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
          <div className="w-3 h-3 rounded-full bg-green-500"></div>
        </div>
        <span className="text-terminal-text ml-4">
          MLJ Results Compiler Terminal
        </span>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto mb-4 space-y-1">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`${getMessageColor(message.type)} font-mono text-sm`}
          >
            <span className="text-gray-500">
              [{message.timestamp.toLocaleTimeString()}]
            </span>{' '}
            {getPrefix(message.type)}
            {message.content}
          </div>
        ))}
        {isProcessing && (
          <div className="text-terminal-green flex items-center gap-2">
            <span className="animate-pulse">Processing</span>
            <span className="cursor-blink">█</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* File Upload Area */}
      <FileUpload 
        onFilesSelected={handleFilesSelected} 
        disabled={isProcessing}
      />
    </div>
  )
}
