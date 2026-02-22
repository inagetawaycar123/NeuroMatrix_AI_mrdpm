ALTER TABLE patient_info
ADD COLUMN available_modalities text[] DEFAULT '{}'::text[];