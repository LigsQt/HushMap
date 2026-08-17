-- Sanitized development seed (not production data).
INSERT INTO points (point_id, latitude, longitude, barangay_name, city) VALUES
  (1, 14.5995, 120.9842, 'Sample Barangay', 'Manila')
ON CONFLICT (point_id) DO NOTHING;

INSERT INTO sessions (session_id, point_id, session_number, start_date, end_date) VALUES
  (1, 1, 1, CURRENT_DATE, CURRENT_DATE)
ON CONFLICT (session_id) DO NOTHING;

INSERT INTO audio_recordings (session_id, db_level, start_time, analysis_text)
SELECT 1, 62.4, '09:00', 'Distant traffic. Voices nearby.'
WHERE NOT EXISTS (
  SELECT 1 FROM audio_recordings WHERE session_id = 1 AND start_time = '09:00'
);

INSERT INTO audio_recordings (session_id, db_level, start_time, analysis_text)
SELECT 1, 58.1, '09:20', 'Bird calls. Light wind.'
WHERE NOT EXISTS (
  SELECT 1 FROM audio_recordings WHERE session_id = 1 AND start_time = '09:20'
);
