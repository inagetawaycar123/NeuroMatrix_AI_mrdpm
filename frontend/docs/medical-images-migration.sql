-- 图像存储表
CREATE TABLE IF NOT EXISTS medical_images (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
  image_data TEXT NOT NULL,
  image_type VARCHAR(50),
  analysis_result JSONB,
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);

-- 创建索引以提高查询性能
CREATE INDEX idx_medical_images_session_id ON medical_images(session_id);
CREATE INDEX idx_medical_images_created_at ON medical_images(created_at);

-- 行级安全性（RLS）
ALTER TABLE medical_images ENABLE ROW LEVEL SECURITY;

-- RLS 策略：允许用户访问自己会话的图像
CREATE POLICY "medical_images_select_by_session"
ON medical_images FOR SELECT
USING (
  session_id IN (
    SELECT id FROM chat_sessions 
    WHERE user_id = auth.uid() OR user_id IS NULL
  )
);

CREATE POLICY "medical_images_insert_by_session"
ON medical_images FOR INSERT
WITH CHECK (
  session_id IN (
    SELECT id FROM chat_sessions 
    WHERE user_id = auth.uid() OR user_id IS NULL
  )
);

CREATE POLICY "medical_images_update_by_session"
ON medical_images FOR UPDATE
USING (
  session_id IN (
    SELECT id FROM chat_sessions 
    WHERE user_id = auth.uid() OR user_id IS NULL
  )
);

-- 自动更新 updated_at 时间戳的触发器
CREATE OR REPLACE FUNCTION update_medical_images_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_medical_images_timestamp
BEFORE UPDATE ON medical_images
FOR EACH ROW
EXECUTE FUNCTION update_medical_images_timestamp();
