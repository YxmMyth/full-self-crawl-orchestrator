-- 初始数据库迁移
-- 创建调研任务和站点结果表

-- 调研任务记录
CREATE TABLE IF NOT EXISTS research_tasks (
    id SERIAL PRIMARY KEY,
    task_id TEXT NOT NULL UNIQUE,
    user_query TEXT NOT NULL,
    refined_requirement JSONB DEFAULT '{}',
    candidate_sites JSONB DEFAULT '[]',
    total_sites INTEGER DEFAULT 0,
    successful_sites INTEGER DEFAULT 0,
    status TEXT NOT NULL,  -- pending/running/completed/failed
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- 站点探测结果
CREATE TABLE IF NOT EXISTS site_results (
    id SERIAL PRIMARY KEY,
    task_id TEXT NOT NULL,
    site_url TEXT NOT NULL,
    site_name TEXT,
    quality_score FLOAT,
    total_records INTEGER,
    sample_records JSONB DEFAULT '[]',
    duration_sec INTEGER,
    strategy_used TEXT,
    difficulty TEXT,
    status TEXT,  -- success/failed
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(task_id, site_url)
);

-- 样本数据存储
CREATE TABLE IF NOT EXISTS sample_records (
    id SERIAL PRIMARY KEY,
    task_id TEXT NOT NULL,
    site_url TEXT NOT NULL,
    record_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_site_results_task ON site_results(task_id);
CREATE INDEX IF NOT EXISTS idx_site_results_score ON site_results(quality_score);
CREATE INDEX IF NOT EXISTS idx_sample_records_task ON sample_records(task_id);
CREATE INDEX IF NOT EXISTS idx_research_tasks_status ON research_tasks(status);
CREATE INDEX IF NOT EXISTS idx_research_tasks_created_at ON research_tasks(created_at);
