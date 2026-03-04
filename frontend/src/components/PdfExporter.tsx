'use client';

import React, { useState, useEffect } from 'react';
import { Cloud, Server } from 'lucide-react';
import { toast } from 'sonner';
import { createClient } from '@supabase/supabase-js';

// Supabase配置
const supabaseUrl = 'https://ppyexzqdbsnwqfyugfvc.supabase.co';
const supabaseKey = 'sb_secret_WBmItfnIGaEwC-xg4Xbfog_r9UCd2U0';
const supabase = createClient(supabaseUrl, supabaseKey);

interface PdfExporterProps {
  reportContent: string;
  patientId: string;
  patientName: string;
  patientGender?: string;
  patientAge?: string;
  ctNumber?: string;
  emergency?: string;
  bedNumber?: string;
  examDate?: string;
  reportDate?: string;
  examName?: string;
}

export const PdfExporter: React.FC<PdfExporterProps> = ({ 
  reportContent, 
  patientId, 
  patientName, 
  patientGender, 
  patientAge, 
  ctNumber, 
  emergency, 
  bedNumber, 
  examDate, 
  reportDate, 
  examName 
}) => {
  const [isSimpleLoading, setIsSimpleLoading] = useState(false);
  const [isComplexLoading, setIsComplexLoading] = useState(false);
  
  const handleUploadToSupabase = async (pdfBlob: Blob, type: string) => {
    try {
      // 生成文件名
      const fileName = `report_${patientId}_${Date.now()}.pdf`;
      
      try {
        // 尝试上传到Supabase Storage
        const { data, error } = await supabase
          .storage
          .from('patient_imaging')
          .upload(`pdfs/${fileName}`, pdfBlob, {
            cacheControl: '3600',
            upsert: false
          });
        
        if (error) {
          // 如果是bucket不存在的错误，显示友好提示
          if (error.message.includes('Bucket not found')) {
            toast.warning('存储桶未创建，PDF已下载但未上传到云端');
            console.warn('存储桶未创建:', error);
            return;
          }
          throw error;
        }
        
        // 获取公共URL
        const { data: urlData } = supabase
          .storage
          .from('patient_imaging')
          .getPublicUrl(`pdfs/${fileName}`);
        
        toast.success('报告已成功上传到云端');
        console.log('PDF上传成功:', urlData.publicUrl);
        
        // 将URL写入数据库（仅复杂报告）
        if (type === 'complex') {
          try {
            const response = await fetch('http://localhost:8766/api/save-report-url', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json'
              },
              body: JSON.stringify({
                patient_id: parseInt(patientId) || 0,
                report_url: urlData.publicUrl,
                report_type: type
              })
            });
            
            if (response.ok) {
              console.log('报告URL已写入数据库');
            } else {
              const errorData = await response.json();
              console.error('写入数据库失败:', errorData);
              toast.warning('PDF已上传，但写入数据库失败');
            }
          } catch (error) {
            console.error('写入数据库失败:', error);
            toast.warning('PDF已上传，但写入数据库失败');
          }
        }
        
      } catch (error) {
        // 捕获存储错误，但允许PDF下载完成
        console.error('上传失败:', error);
        toast.warning('PDF已下载，但上传到云端失败');
      }
      
    } catch (error) {
      console.error('处理失败:', error);
      toast.error('处理失败，请稍后重试');
    }
  };
  
  const handlePdfDownload = async (type: string) => {
    try {
      // Set loading state based on type
      if (type === 'simple') {
        setIsSimpleLoading(true);
      } else {
        setIsComplexLoading(true);
      }
      
      // 调用后端API生成PDF（简单报告不包含水印、复杂表格和电子签名）
      const response = await fetch('http://localhost:8766/api/generate-pdf', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          report_content: reportContent,
          patient_id: parseInt(patientId) || 0,
          patient_name: patientName,
          report_type: type // 传递报告类型
        })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const blob = await response.blob();
      
      // 创建下载链接
      const downloadUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `report_${patientId}_${type}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(downloadUrl);
      
      // 同时尝试上传到Supabase
      await handleUploadToSupabase(blob, type);
      
    } catch (error) {
      console.error('下载失败:', error);
      toast.error('下载失败，请稍后重试');
    } finally {
      // Reset loading state based on type
      if (type === 'simple') {
        setIsSimpleLoading(false);
      } else {
        setIsComplexLoading(false);
      }
    }
  };
  
  const handleBackendPdfExport = async () => {
    // 直接调用 handlePdfDownload 函数，传入 'complex' 类型
    await handlePdfDownload('complex');
  };
  
  return (
    <div className="flex space-x-2 items-center">
      {/* 简单报告按钮 */}
      <button
        className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
        disabled={isSimpleLoading}
        onClick={handlePdfDownload.bind(this, 'simple')}
      >
        <Cloud size={16} className="mr-2" />
        {isSimpleLoading ? '处理中...' : '简单报告'}
      </button>
      
      {/* 复杂报告按钮 */}
      <button
        className="flex items-center px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
        disabled={isComplexLoading}
        onClick={handleBackendPdfExport}
      >
        <Server size={16} className="mr-2" />
        {isComplexLoading ? '处理中...' : '复杂报告'}
      </button>
    </div>
  );
};