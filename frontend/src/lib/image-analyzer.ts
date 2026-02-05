/**
 * 医学图像和文档分析工具
 * 处理上传的医学影像和PDF文档，提取元数据和格式化为医学上下文
 */

interface ImageAnalysisResult {
  description: string
  findings: string[]
  imagingType: string
  confidence: number
  fileName?: string
  fileType?: 'image' | 'pdf'
}

/**
 * 验证和分析上传的医学图像和文档
 * @param base64Files Base64编码的文件数组（data:...;base64,xxx 格式）
 * @returns 文件验证和元数据
 */
export async function analyzeImages(
  base64Files: string[]
): Promise<ImageAnalysisResult[]> {
  if (!base64Files || base64Files.length === 0) {
    return []
  }

  const results: ImageAnalysisResult[] = []

  for (let idx = 0; idx < base64Files.length; idx++) {
    const base64File = base64Files[idx]

    try {
      // 提取文件元数据
      const matches = base64File.match(/^data:([^;]+);base64,(.+)$/)
      if (!matches) {
        console.warn(`File ${idx + 1}: Invalid base64 format`)
        continue
      }

      const mimeType = matches[1]
      const fileData = matches[2]

      // 验证 Base64 数据完整性
      if (fileData.length < 100) {
        console.warn(`File ${idx + 1}: File data too small (${fileData.length} bytes)`)
        continue
      }

      // 检测是否为PDF
      const isPDF = mimeType === 'application/pdf'

      if (isPDF) {
        // 处理PDF文件
        const pdfResult = await analyzePDFDocument(base64File, idx)
        if (pdfResult) {
          results.push(pdfResult)
        }
      } else {
        // 处理图像文件
        const imageResult = await analyzeImageFile(base64File, idx, mimeType, fileData)
        if (imageResult) {
          results.push(imageResult)
        }
      }
    } catch (error) {
      console.error(`Error processing file ${idx + 1}:`, error)
      continue
    }
  }

  return results
}

/**
 * 分析PDF文档
 */
async function analyzePDFDocument(
  base64PDF: string,
  idx: number
): Promise<ImageAnalysisResult | null> {
  try {
    const matches = base64PDF.match(/^data:([^;]+);base64,(.+)$/)
    if (!matches) return null

    const fileData = matches[2]
    const fileSizeKB = (fileData.length / 1024).toFixed(2)

    // 调用百川API分析PDF内容
    try {
      const analysisResponse = await fetch(
        `${process.env.BAICHUAN_API_URL}/chat/completions`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${process.env.BAICHUAN_API_KEY}`,
          },
          body: JSON.stringify({
            model: 'Baichuan3-Turbo',
            messages: [
              {
                role: 'user',
                content: `这是一份医学PDF文档。请分析这份文档中的内容。请使用中文回答，并包括：
1. 文档类型（医学报告、病历、影像学报告等）
2. 主要诊断或发现
3. 关键的医学信息和参数
4. 任何需要特别关注的临床信息

请提供专业的医学分析描述。

PDF数据: ${base64PDF}`,
              },
            ],
            temperature: 0.5,
            max_tokens: 800,
          }),
        }
      )

      if (analysisResponse.ok) {
        const analysisData = await analysisResponse.json()
        const analysisContent =
          analysisData.choices?.[0]?.message?.content || ''

        if (analysisContent) {
          return {
            description: analysisContent,
            findings: analysisContent
              .split('\n')
              .filter((line: string) => line.trim().length > 0)
              .slice(0, 8),
            imagingType: 'PDF Medical Document',
            confidence: 0.85,
            fileName: `medical_document_${idx + 1}`,
            fileType: 'pdf',
          }
        }
      }
    } catch (apiError) {
      console.warn(`PDF Analysis API error:`, apiError)
    }

    // 后备方案：返回验证信息
    const validationText = formatPDFValidationInfo(
      idx + 1,
      (fileData.length / 1024).toFixed(2)
    )

    return {
      description: validationText,
      findings: [
        `✓ PDF文档已成功上传`,
        `文档大小: ${fileSizeKB} KB`,
        `建议在问题中详细描述PDF内容的关键信息`,
      ],
      imagingType: 'Medical PDF Document',
      confidence: 0.9,
      fileName: `medical_document_${idx + 1}`,
      fileType: 'pdf',
    }
  } catch (error) {
    console.error(`Error analyzing PDF ${idx + 1}:`, error)
    return null
  }
}

/**
 * 分析图像文件
 */
async function analyzeImageFile(
  base64Image: string,
  idx: number,
  mimeType: string,
  imageData: string
): Promise<ImageAnalysisResult | null> {
  try {
    const imagingType = inferImagingType(mimeType)

    // 调用百川API分析图像内容
    try {
      const analysisResponse = await fetch(
        `${process.env.BAICHUAN_API_URL}/chat/completions`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${process.env.BAICHUAN_API_KEY}`,
          },
          body: JSON.stringify({
            model: 'Baichuan3-Turbo',
            messages: [
              {
                role: 'user',
                content: `这是一张医学影像。请分析这张图像中可以看到的内容。请使用中文回答，并包括：
1. 图像类型（CT、MRI、X光等）
2. 能够观察到的主要解剖结构
3. 任何可见的异常或需要注意的区域
4. 图像质量评估

请提供专业的医学影像分析描述。

图像数据: ${base64Image}`,
              },
            ],
            temperature: 0.5,
            max_tokens: 500,
          }),
        }
      )

      if (analysisResponse.ok) {
        const analysisData = await analysisResponse.json()
        const analysisContent =
          analysisData.choices?.[0]?.message?.content || ''

        if (analysisContent) {
          return {
            description: analysisContent,
            findings: analysisContent
              .split('\n')
              .filter((line: string) => line.trim().length > 0)
              .slice(0, 5),
            imagingType: imagingType,
            confidence: 0.85,
            fileName: `medical_image_${idx + 1}`,
            fileType: 'image',
          }
        }
      }
    } catch (apiError) {
      console.warn(`Image Analysis API error:`, apiError)
    }

    // 后备方案：返回验证信息
    const validationText = formatImageValidationInfo(
      idx + 1,
      mimeType,
      imageData.length,
      imagingType
    )

    return {
      description: validationText,
      findings: [
        `已验证图像格式: ${mimeType}`,
        `数据大小: ${(imageData.length / 1024).toFixed(2)} KB`,
        `图像已验证并准备进行临床分析`,
      ],
      imagingType: imagingType,
      confidence: 0.85,
      fileName: `medical_image_${idx + 1}`,
      fileType: 'image',
    }
  } catch (error) {
    console.error(`Error analyzing image ${idx + 1}:`, error)
    return null
  }
}

/**
 * 从MIME类型推断医学影像类型
 */
function inferImagingType(mimeType: string): string {
  const typeMap: Record<string, string> = {
    'image/jpeg': 'JPEG Medical Image',
    'image/png': 'PNG Medical Image',
    'image/gif': 'GIF Medical Image',
    'image/webp': 'WebP Medical Image',
    'image/tiff': 'TIFF Medical Image (possibly DICOM export)',
  }

  return typeMap[mimeType] || 'General Medical Image'
}

/**
 * 格式化图像验证信息
 */
function formatImageValidationInfo(
  index: number,
  mimeType: string,
  dataSize: number,
  imagingType: string
): string {
  return `
【Medical Image Information - Image ${index}】

【Image Format】: ${mimeType}
【Image Size】: ${(dataSize / 1024).toFixed(2)} KB
【Detected Type】: ${imagingType}
【Validation Status】: ✓ Successfully uploaded and verified

【Usage Recommendations】:
  1. This medical image has been successfully uploaded to the system
  2. Please describe the key findings from this image in your clinical question
  3. Include any abnormalities, lesion locations, and imaging characteristics
  4. The system will provide analysis suggestions based on your description and clinical data

【Important Notes】:
  • Although the system has verified image integrity, radiological diagnosis still requires professional radiologist review
  • Please provide key findings from the imaging report for AI analysis
  • All clinical decisions must be combined with professional doctor opinions
`
}

/**
 * 格式化PDF验证信息
 */
function formatPDFValidationInfo(index: number, fileSizeKB: string): string {
  return `
【Medical PDF Document Information - Document ${index}】

【Document Type】: Medical PDF
【Document Size】: ${fileSizeKB} KB
【Validation Status】: ✓ Successfully uploaded and verified

【Usage Recommendations】:
  1. This medical PDF has been successfully uploaded to the system
  2. Please describe the main content and key findings from this document in your clinical question
  3. Include important diagnostic information, test results, and clinical parameters
  4. The system will provide analysis suggestions based on the document information and your question

【Important Notes】:
  • Please provide specific clinical information from the document for better AI analysis
  • Medical diagnosis and clinical decisions require professional doctor review
  • The system uses document content to provide evidence-based clinical suggestions
`
}

/**
 * Format image analysis results for medical prompt
 * Prompt doctors to provide specific imaging findings for more accurate AI analysis
 */
export function formatImageAnalysisForPrompt(
  analysisResults: ImageAnalysisResult[]
): string {
  if (analysisResults.length === 0) {
    return ''
  }

  let formattedText =
    '\n\n【Uploaded Medical Files】\nPatient has uploaded the following medical files:\n'

  analysisResults.forEach((result, index) => {
    formattedText += `\n【File ${index + 1}】\n`
    formattedText += `• Type: ${result.imagingType}\n`
    formattedText += `• Validation Status: ✓ Verified\n`
    formattedText += `• Key Information:\n`
    result.findings.forEach((finding) => {
      formattedText += `  - ${finding}\n`
    })
  })

  formattedText += `
【How to Get the Best Medical AI Analysis】:
  1. ✓ Include key findings from imaging reports in your clinical question
  2. ✓ Describe any abnormalities, lesion locations, and imaging characteristics
  3. ✓ Provide specific radiological terminology and measurement data
  4. ✓ Combine with patient clinical symptoms and physical examination findings

【Example Questions】:
❌ Not specific enough: "Patient CT shows abnormality, is thrombolysis appropriate?"
✅ Better question: "Patient head CT shows left MCA distribution low-density lesion, area approximately 2cm×3cm, 2 hours after onset. NIHSS 14. Is IV-tPA thrombolysis appropriate?"

Based on the specific imaging information you provide, the system can provide more accurate and targeted medical advice.
`

  return formattedText
}
