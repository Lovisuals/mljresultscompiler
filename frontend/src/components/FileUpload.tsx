'use client'

import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'

interface FileUploadProps {
  onFilesSelected: (files: File[]) => void
  disabled?: boolean
}

export default function FileUpload({ onFilesSelected, disabled }: FileUploadProps) {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setSelectedFiles(acceptedFiles)
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
    },
    disabled,
    multiple: true,
  })

  const handleUpload = () => {
    if (selectedFiles.length > 0) {
      onFilesSelected(selectedFiles)
      setSelectedFiles([])
    }
  }

  const removeFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index))
  }

  return (
    <div className="border border-gray-700 rounded p-4 bg-gray-900">
      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded p-8 text-center cursor-pointer transition-colors
          ${isDragActive 
            ? 'border-terminal-green bg-green-900/20' 
            : 'border-gray-600 hover:border-gray-500'
          }
          ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <input {...getInputProps()} />
        <div className="text-terminal-text">
          {isDragActive ? (
            <p className="text-terminal-green">
              📁 Drop the Excel files here...
            </p>
          ) : (
            <div className="space-y-2">
              <p className="text-terminal-yellow">
                📂 Drag & drop Excel files here, or click to select
              </p>
              <p className="text-sm text-gray-500">
                Accepts .xlsx and .xls files (TEST_1, TEST_2, TEST_3, TEST_4, TEST_5)
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Selected Files List */}
      {selectedFiles.length > 0 && (
        <div className="mt-4 space-y-2">
          <div className="text-terminal-green text-sm font-semibold">
            Selected Files ({selectedFiles.length}):
          </div>
          <div className="space-y-1">
            {selectedFiles.map((file, index) => (
              <div
                key={index}
                className="flex items-center justify-between bg-gray-800 p-2 rounded text-sm"
              >
                <div className="flex items-center gap-2">
                  <span className="text-terminal-blue">📄</span>
                  <span className="text-terminal-text">{file.name}</span>
                  <span className="text-gray-500">
                    ({(file.size / 1024).toFixed(2)} KB)
                  </span>
                </div>
                <button
                  onClick={() => removeFile(index)}
                  className="text-terminal-red hover:bg-red-900/20 px-2 py-1 rounded transition-colors"
                  disabled={disabled}
                >
                  ✕
                </button>
              </div>
            ))}
          </div>

          {/* Upload Button */}
          <button
            onClick={handleUpload}
            disabled={disabled || selectedFiles.length === 0}
            className={`w-full py-2 px-4 rounded font-semibold transition-colors
              ${disabled || selectedFiles.length === 0
                ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                : 'bg-terminal-green text-black hover:bg-green-600'
              }
            `}
          >
            {disabled ? 'Processing...' : `Upload ${selectedFiles.length} file(s)`}
          </button>
        </div>
      )}
    </div>
  )
}
