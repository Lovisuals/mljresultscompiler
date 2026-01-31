import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData()
    const files = formData.getAll('files') as File[]

    if (!files || files.length === 0) {
      return NextResponse.json(
        { error: 'No files provided' },
        { status: 400 }
      )
    }

    // Validate files
    const validFiles = files.filter(file => 
      file.name.endsWith('.xlsx') || file.name.endsWith('.xls')
    )

    if (validFiles.length === 0) {
      return NextResponse.json(
        { error: 'No valid Excel files provided' },
        { status: 400 }
      )
    }

    // Extract file information
    const fileInfos = await Promise.all(
      validFiles.map(async (file) => {
        const bytes = await file.arrayBuffer()
        return {
          name: file.name,
          size: file.size,
          type: file.type,
          data: Buffer.from(bytes).toString('base64'),
        }
      })
    )

    // Determine month/year
    const currentDate = new Date()
    const monthYear = `${currentDate.toLocaleString('default', { month: 'long' })}_${currentDate.getFullYear()}`

    // NOTE: On Vercel, Python scripts can't run directly
    // You would need to either:
    // 1. Deploy Python backend separately (e.g., Railway, Render, AWS Lambda)
    // 2. Convert Python logic to JavaScript
    // 3. Use a webhook/API to trigger Python processing elsewhere
    
    // For demo purposes, return success with file info
    return NextResponse.json({
      message: 'Files received successfully',
      filesReceived: validFiles.length,
      files: validFiles.map(f => f.name),
      outputFile: `Final_Results_${monthYear}.xlsx`,
      errorLog: `Collation_Errors_${monthYear}.txt`,
      note: 'Python processing requires separate backend deployment',
      fileData: fileInfos.map(f => ({
        name: f.name,
        size: f.size,
        type: f.type,
      })),
    })

  } catch (error) {
    console.error('Error processing files:', error)
    return NextResponse.json(
      { 
        error: 'Internal server error',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    )
  }
}
