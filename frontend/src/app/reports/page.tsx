'use client';

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Search, Calendar, Filter, Download, Eye, Clock, User, FileText, Tag } from 'lucide-react';

interface Report {
  id: number;
  patient_id: number;
  report_type: string;
  report_title: string | null;
  report_description: string | null;
  content: {
    patient_data?: {
      id: number;
      age: number;
      name: string;
      gender: string;
      created_at: string;
      hemisphere: string;
      onset_time: string;
      nihss_score: number;
      mismatch_ratio: number;
      analysis_status: string;
      penumbra_volume: number;
      core_infarct_volume: number;
    };
    report_content?: {
      aiResults: string;
      doctorNotes: string;
      imagingFindings: string;
      uncertainty: string;
    };
  } | null;
  pdf_url: string | null;
  created_at: string;
  status: string | null;
}

interface ReportResponse {
  status: string;
  data: Report[];
  count?: number; // 可选字段，后端可能不返回
}

const fetchReports = async (filters: any): Promise<Report[]> => {
  const params = new URLSearchParams();
  
  if (filters.patientId) params.append('patient_id', filters.patientId);
  if (filters.patientName) params.append('patient_name', filters.patientName);
  if (filters.startDate) params.append('start_date', filters.startDate);
  if (filters.endDate) params.append('end_date', filters.endDate);
  if (filters.status) params.append('status', filters.status);
  if (filters.reportType) params.append('report_type', filters.reportType);
  
  const response = await fetch(`http://localhost:8766/api/reports?${params.toString()}`);
  if (!response.ok) {
    throw new Error('Failed to fetch reports');
  }
  
  const data: ReportResponse = await response.json();
  
  // 确保返回的是普通对象，避免序列化问题
  return data.data.map(report => {
    let content = null;
    try {
      if (report.content) {
        // 尝试解析content字段
        if (typeof report.content === 'string') {
          content = JSON.parse(report.content);
        } else {
          // 如果content已经是对象，直接使用
          content = report.content;
        }
      }
    } catch (error) {
      console.error('解析content字段失败:', error);
      content = null;
    }
    return {
      ...report,
      content
    };
  });
};

export default function ReportsPage() {
  const [filters, setFilters] = useState({
    patientId: '',
    patientName: '',
    startDate: '',
    endDate: '',
    status: '',
    reportType: ''
  });
  
  const [searchFilters, setSearchFilters] = useState({
    patientId: '',
    patientName: '',
    startDate: '',
    endDate: '',
    status: '',
    reportType: ''
  });
  
  const [previewReport, setPreviewReport] = useState<Report | null>(null);
  
  const { data: reports = [], isLoading, error, refetch } = useQuery({
    queryKey: ['reports', filters],
    queryFn: () => fetchReports(filters),
    enabled: false, // 禁用自动查询，只在手动调用时执行
  });
  
  const handleFilterChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFilters(prev => ({ ...prev, [name]: value }));
  };
  
  const handleResetFilters = () => {
    setFilters({
      patientId: '',
      patientName: '',
      startDate: '',
      endDate: '',
      status: '',
      reportType: ''
    });
  };
  
  const handleSearch = () => {
    // 直接使用当前的filters进行查询，而不是等待setSearchFilters更新
    refetch();
  };
  
  const handleDownload = async (pdfUrl: string | null, reportTitle: string | null) => {
    if (!pdfUrl) {
      toast.error('报告PDF链接不存在');
      return;
    }
    
    // 检查URL是否有效
    if (pdfUrl === 'test_url' || pdfUrl.includes('example.com')) {
      toast.error('报告PDF链接无效');
      return;
    }
    
    try {
      // 只使用Supabase Storage URL获取数据
      const response = await fetch(pdfUrl, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/pdf',
          'Accept': 'application/pdf'
        },
        cache: 'no-cache'
      });
      
      if (!response.ok) {
        // 检查是否是400错误（文件不存在）
        if (response.status === 400 || response.status === 404) {
          throw new Error('报告文件不存在或已被删除');
        }
        throw new Error(`下载失败: ${response.status}`);
      }
      
      const blob = await response.blob();
      // 确保创建Blob对象时指定正确的MIME类型
      const pdfBlob = new Blob([blob], { type: 'application/pdf' });
      const url = URL.createObjectURL(pdfBlob);
      const link = document.createElement('a');
      link.href = url;
      link.download = reportTitle || `report_${Date.now()}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      
      toast.success('报告下载成功');
    } catch (error) {
      console.error('下载失败:', error);
      toast.error(`下载失败: ${(error as Error).message || '请稍后重试'}`);
    }
  };
  
  const handlePreview = (report: Report) => {
    setPreviewReport(report);
  };
  
  const handleClosePreview = () => {
    setPreviewReport(null);
  };
  
  if (isLoading) {
    return (
      <div className="container mx-auto p-4">
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="container mx-auto p-4">
        <div className="bg-red-100 border-l-4 border-red-500 p-4">
          <p className="text-red-700">获取报告失败: {error.message}</p>
          <button 
            className="mt-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700" 
            onClick={() => refetch()}
          >
            重试
          </button>
        </div>
      </div>
    );
  }
  
  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">报告历史查询</h1>
      
      {/* 筛选表单 */}
      <div className="bg-white rounded-lg shadow-md p-4 mb-6">
        <h2 className="text-lg font-semibold mb-4 flex items-center">
          <Filter size={18} className="mr-2" />
          筛选条件
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">患者ID</label>
          <div className="relative">
            <User size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              name="patientId"
              value={filters.patientId}
              onChange={handleFilterChange}
              placeholder="输入患者ID"
              className="pl-10 pr-4 py-2 border border-gray-300 rounded-md w-full focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">患者姓名</label>
          <div className="relative">
            <User size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              name="patientName"
              value={filters.patientName}
              onChange={handleFilterChange}
              placeholder="输入患者姓名"
              className="pl-10 pr-4 py-2 border border-gray-300 rounded-md w-full focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">开始日期</label>
            <div className="relative">
              <Calendar size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
              <input
                type="date"
                name="startDate"
                value={filters.startDate}
                onChange={handleFilterChange}
                className="pl-10 pr-4 py-2 border border-gray-300 rounded-md w-full focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">结束日期</label>
            <div className="relative">
              <Calendar size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
              <input
                type="date"
                name="endDate"
                value={filters.endDate}
                onChange={handleFilterChange}
                className="pl-10 pr-4 py-2 border border-gray-300 rounded-md w-full focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">报告类型</label>
            <select
              name="reportType"
              value={filters.reportType}
              onChange={handleFilterChange}
              className="pl-4 pr-4 py-2 border border-gray-300 rounded-md w-full focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">所有类型</option>
              <option value="standard">标准报告</option>
              <option value="complex">复杂报告</option>
              <option value="simple">简单报告</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">报告状态</label>
            <select
              name="status"
              value={filters.status}
              onChange={handleFilterChange}
              className="pl-4 pr-4 py-2 border border-gray-300 rounded-md w-full focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">所有状态</option>
              <option value="generated">已生成</option>
              <option value="reviewed">已审核</option>
              <option value="approved">已批准</option>
            </select>
          </div>
          
          <div className="flex items-end">
            <button
              onClick={handleResetFilters}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 mr-2"
            >
              重置
            </button>
            <button
              onClick={handleSearch}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center"
            >
              <Search size={16} className="mr-2" />
              查询
            </button>
          </div>
        </div>
      </div>
      
      {/* 报告列表 */}
      <div className="bg-white rounded-lg shadow-md p-4">
        <h2 className="text-lg font-semibold mb-4 flex items-center">
          <FileText size={18} className="mr-2" />
          报告列表
          <span className="ml-2 text-sm text-gray-500">({(reports || []).length} 条)</span>
        </h2>
        
        {(reports || []).length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            暂无报告数据
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    报告ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    患者ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    报告类型
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    报告标题
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    生成时间
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    状态
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    操作
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {(reports || []).map((report) => (
                  <tr key={report.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {report.id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {report.patient_id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      <span className={`px-2 py-1 text-xs rounded-full ${report.report_type === 'complex' ? 'bg-purple-100 text-purple-800' : report.report_type === 'simple' ? 'bg-green-100 text-green-800' : 'bg-blue-100 text-blue-800'}`}>
                        {report.report_type === 'complex' ? '复杂报告' : report.report_type === 'simple' ? '简单报告' : '标准报告'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      {report.report_title || '无标题'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(report.created_at).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {report.status ? (
                        <span className={`px-2 py-1 text-xs rounded-full ${report.status === 'generated' ? 'bg-yellow-100 text-yellow-800' : report.status === 'reviewed' ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'}`}>
                          {report.status === 'generated' ? '已生成' : report.status === 'reviewed' ? '已审核' : '已批准'}
                        </span>
                      ) : (
                        <span className="px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-800">
                          未设置
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <button
                        onClick={() => handlePreview(report)}
                        className="text-blue-600 hover:text-blue-900 mr-3 flex items-center"
                      >
                        <Eye size={16} className="mr-1" />
                        预览
                      </button>
                      {report.pdf_url && (
                        <button
                          onClick={() => handleDownload(report.pdf_url, report.report_title)}
                          className="text-green-600 hover:text-green-900 flex items-center"
                        >
                          <Download size={16} className="mr-1" />
                          下载
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      
      {/* 报告预览模态框 */}
      {previewReport && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[80vh] overflow-y-auto">
            <div className="p-6 border-b flex justify-between items-center">
              <h3 className="text-xl font-semibold">报告预览</h3>
              <button 
                onClick={handleClosePreview} 
                className="text-gray-500 hover:text-gray-700"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-6">
              {/* 报告标题 */}
              <h4 className="text-lg font-medium mb-4">{previewReport.report_title || '无标题'}</h4>
              
              {/* 报告基本信息 */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div>
                  <p className="text-sm text-gray-500">报告ID</p>
                  <p>{previewReport.id}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">患者ID</p>
                  <p>{previewReport.patient_id}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">报告类型</p>
                  <p>
                    {previewReport.report_type === 'complex' ? '复杂报告' : 
                     previewReport.report_type === 'simple' ? '简单报告' : '标准报告'}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">生成时间</p>
                  <p>{new Date(previewReport.created_at).toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">状态</p>
                  <p>{previewReport.status || '未设置'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">PDF链接</p>
                  <p className="text-blue-600 truncate">{previewReport.pdf_url || '无'}</p>
                </div>
              </div>
              
              {/* 患者信息 */}
              {previewReport.content?.patient_data && (
                <div className="mb-6">
                  <h5 className="text-md font-medium mb-2">患者信息</h5>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-gray-500">姓名</p>
                      <p>{previewReport.content.patient_data.name}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">年龄</p>
                      <p>{previewReport.content.patient_data.age}岁</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">性别</p>
                      <p>{previewReport.content.patient_data.gender}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">发病侧</p>
                      <p>{previewReport.content.patient_data.hemisphere}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">NIHSS评分</p>
                      <p>{previewReport.content.patient_data.nihss_score}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">不匹配比值</p>
                      <p>{previewReport.content.patient_data.mismatch_ratio}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">核心梗死体积</p>
                      <p>{previewReport.content.patient_data.core_infarct_volume}ml</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">半暗带体积</p>
                      <p>{previewReport.content.patient_data.penumbra_volume}ml</p>
                    </div>
                  </div>
                </div>
              )}
              
              {/* 报告内容 */}
              {previewReport.content?.report_content && (
                <div className="mb-6">
                  <h5 className="text-md font-medium mb-2">报告内容</h5>
                  <div className="space-y-4">
                    <div>
                      <p className="text-sm text-gray-500">AI分析结果</p>
                      <p className="text-sm bg-gray-50 p-3 rounded">{previewReport.content.report_content.aiResults}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">影像表现</p>
                      <p className="text-sm bg-gray-50 p-3 rounded">{previewReport.content.report_content.imagingFindings}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">医生备注</p>
                      <p className="text-sm bg-gray-50 p-3 rounded">{previewReport.content.report_content.doctorNotes}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">不确定性</p>
                      <p className="text-sm bg-gray-50 p-3 rounded">{previewReport.content.report_content.uncertainty}</p>
                    </div>
                  </div>
                </div>
              )}
              
              {/* 无内容提示 */}
              {!previewReport.content && (
                <div className="text-center py-8 text-gray-500">
                  报告内容为空
                </div>
              )}
            </div>
            <div className="p-6 border-t flex justify-end">
              <button 
                onClick={handleClosePreview} 
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 mr-2"
              >
                关闭
              </button>
              {previewReport.pdf_url && (
                <button 
                  onClick={() => handleDownload(previewReport.pdf_url, previewReport.report_title)}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center"
                >
                  <Download size={16} className="mr-2" />
                  下载PDF
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
