'use client';

import React, { useState } from 'react';
import { PdfExporter } from '../../components/PdfExporter';
import { Toaster } from 'sonner';

export default function PdfTestPage() {
  const [reportContent, setReportContent] = useState(`· 检查方法
头颅 CT 平扫 (NCCT) + 三期 CT 血管成像 (mCTA：动脉期、静脉期、延迟期)

· 影像学表现
常规准直，增强薄层扫描，层厚层间距0.5mm，VR、CPR、MIP、MFR重建。多时相增强后于扫描区域分别选取两侧额叶、颞叶、顶叶、基底节区及枕叶层面为感兴趣区。测量平均脑血流量（CBF）、平均血容量（CBV）、平均通过时间（MTT）及达峰时间（TTP）、延迟图像（DT）。测量显示左侧大脑中动脉供血区较对侧CBV降低，CBF较对侧轻度增高，MTT、TTP较对侧延长。

· 血管评估
灌注早期成像示：颅内动脉粗细不均，左侧大脑中动脉M1段局部重度狭窄；右侧大脑前动脉A1段局部轻度狭窄；双侧颈内动脉虹吸段、双侧椎动脉V5段多发钙化斑块，管腔轻-中度狭窄。

· 诊断意见
1. 左侧大脑中动脉供血区异常灌注，其内散在片状核心梗死区，周围可见缺血半暗带存在，请结合临床。
2. 灌注早期成像示：颅内动脉粗细不均，左侧大脑中动脉M1段局部重度狭窄；右侧大脑前动脉A1段局部轻度狭窄；双侧颈内动脉虹吸段、双侧椎动脉V5段多发钙化斑块，管腔轻-中度狭窄。必要时行CTA检查。

· 治疗建议
1. 建议行血管内介入治疗
2. 尽快完善头颈 CTA 检查评估血管情况
3. 监测生命体征，维持血压稳定`);

  const [patientId, setPatientId] = useState('P12345');
  const [patientName, setPatientName] = useState('张三');
  const [patientGender, setPatientGender] = useState('男');
  const [patientAge, setPatientAge] = useState('68');
  const [ctNumber, setCtNumber] = useState('T81336');
  const [emergency, setEmergency] = useState('急诊');
  const [bedNumber, setBedNumber] = useState('');
  const [examDate, setExamDate] = useState('2025-12-15 12:08');
  const [reportDate, setReportDate] = useState('2025-12-17 11:50');
  const [examName, setExamName] = useState('颅脑灌注CT');

  return (
    <div className="container mx-auto p-4">
      <Toaster position="top-right" />
      
      <h1 className="text-2xl font-bold mb-6">PDF 导出测试</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div>
          <label className="block mb-2">患者ID</label>
          <input 
            type="text" 
            value={patientId} 
            onChange={(e) => setPatientId(e.target.value)}
            className="w-full p-2 border rounded"
          />
        </div>
        
        <div>
          <label className="block mb-2">患者姓名</label>
          <input 
            type="text" 
            value={patientName} 
            onChange={(e) => setPatientName(e.target.value)}
            className="w-full p-2 border rounded"
          />
        </div>
        
        <div>
          <label className="block mb-2">性别</label>
          <select 
            value={patientGender} 
            onChange={(e) => setPatientGender(e.target.value)}
            className="w-full p-2 border rounded"
          >
            <option value="男">男</option>
            <option value="女">女</option>
          </select>
        </div>
        
        <div>
          <label className="block mb-2">年龄</label>
          <input 
            type="text" 
            value={patientAge} 
            onChange={(e) => setPatientAge(e.target.value)}
            className="w-full p-2 border rounded"
          />
        </div>
        
        <div>
          <label className="block mb-2">CT号</label>
          <input 
            type="text" 
            value={ctNumber} 
            onChange={(e) => setCtNumber(e.target.value)}
            className="w-full p-2 border rounded"
          />
        </div>
        
        <div>
          <label className="block mb-2">急诊</label>
          <input 
            type="text" 
            value={emergency} 
            onChange={(e) => setEmergency(e.target.value)}
            className="w-full p-2 border rounded"
          />
        </div>
        
        <div>
          <label className="block mb-2">床号</label>
          <input 
            type="text" 
            value={bedNumber} 
            onChange={(e) => setBedNumber(e.target.value)}
            className="w-full p-2 border rounded"
          />
        </div>
        
        <div>
          <label className="block mb-2">检查日期</label>
          <input 
            type="text" 
            value={examDate} 
            onChange={(e) => setExamDate(e.target.value)}
            className="w-full p-2 border rounded"
          />
        </div>
        
        <div>
          <label className="block mb-2">报告日期</label>
          <input 
            type="text" 
            value={reportDate} 
            onChange={(e) => setReportDate(e.target.value)}
            className="w-full p-2 border rounded"
          />
        </div>
        
        <div>
          <label className="block mb-2">检查名称</label>
          <input 
            type="text" 
            value={examName} 
            onChange={(e) => setExamName(e.target.value)}
            className="w-full p-2 border rounded"
          />
        </div>
      </div>
      
      <div className="mb-6">
        <label className="block mb-2">报告内容</label>
        <textarea 
          value={reportContent} 
          onChange={(e) => setReportContent(e.target.value)}
          className="w-full p-2 border rounded h-64"
        />
      </div>
      
      <div className="mt-6">
        <PdfExporter 
          reportContent={reportContent} 
          patientId={patientId} 
          patientName={patientName}
          patientGender={patientGender}
          patientAge={patientAge}
          ctNumber={ctNumber}
          emergency={emergency}
          bedNumber={bedNumber}
          examDate={examDate}
          reportDate={reportDate}
          examName={examName}
        />
      </div>
    </div>
  );
}