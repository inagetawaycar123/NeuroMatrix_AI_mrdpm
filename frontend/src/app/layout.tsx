import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'

const inter = Inter({ subsets: ['latin'] })

// 创建 QueryClient 实例
const queryClient = new QueryClient()

export const metadata: Metadata = {
  title: 'NeuroMatrix AI Chat',
  description: 'Interactive Q&A interface for medical imaging',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN">
      <body className={inter.className}>
        <QueryClientProvider client={queryClient}>
          {children}
          <Toaster position="top-right" />
        </QueryClientProvider>
      </body>
    </html>
  )
}