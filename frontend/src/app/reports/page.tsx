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
  content: any;
  pdf_url: string | null;
  created_at: string;
  status: string | null;
}

interface ReportResponse {
  status: string;
  data: Report[];
  count: number;
}

const fetchReports = async (filters: any): Promise<Report[]> => {
  const params = new URLSearchParams();
  
  if (filters.patientId) params.append('patient_id', filters.patientId);
  if (filters.startDate) params.append('start_date', filters.startDate);
  if (filters.endDate) params.append('end_date', filters.endDate);
  if (filters.status) params.append('status', filters.status);
  if (filters.reportType) params.append('report_type', filters.reportType);
  
  const response = await fetch(`http://localhost:8766/api/reports?${params.toString()}`);
  if (!response.ok) {
    throw new Error('Failed to fetch reports');
  }
  
  const data: ReportResponse = await response.json();
  return data.data;
};

export default function ReportsPage() {
  const [filters, setFilters] = useState({
    patientId: '',
    startDate: '',
    endDate: '',
    status: '',
    reportType: ''
  });
  
  const { data: reports, isLoading, error, refetch } = useQuery({
    queryKey: ['reports', filters],
    queryFn: () => fetchReports(filters),
  });
  
  const handleFilterChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFilters(prev => ({ ...prev, [name]: value }));
  };
  
  const handleResetFilters = () => {
    setFilters({
      patientId: '',
      startDate: '',
      endDate: '',
      status: '',
      reportType: ''
    });
  };
  
  const handleDownload = (pdfUrl: string | null, reportTitle: string | null) => {
    if (!pdfUrl) {
      toast.error('报告PDF链接不存在');
      return;
    }
    
    const link = document.createElement('a');
    link.href = pdfUrl;
    link.download = reportTitle || `report_${Date.now()}.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    toast.success('报告下载成功');
  };
  
  const handlePreview = (report: Report) => {
    // 这里可以实现报告预览功能
    // 例如：打开一个模态框显示报告内容
    toast.info('报告预览功能开发中');
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
              onClick={() => refetch()}
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
          <span className="ml-2 text-sm text-gray-500">({reports.length} 条)</span>
        </h2>
        
        {reports.length === 0 ? (
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
                {reports.map((report) => (
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
    </div>
  );
}
